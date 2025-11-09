// bridge.cpp — pybind11 → Geogram with OWNED COPIES + GIL RELEASE
// Fixes memory lifetime issues that cause crashes at 1500+ frames

#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <pybind11/stl.h>

#include <vector>
#include <cmath>
#include <cstring>

// Geogram headers
#include <geogram/basic/common.h>
#include <geogram/basic/logger.h>
#include <geogram/delaunay/periodic_delaunay_3d.h>
#include <geogram/voronoi/convex_cell.h>

namespace py = pybind11;

// Result structure
struct GeometryResult {
    std::vector<double> volume;
    std::vector<double> area;
    std::vector<int>    fsc;
    std::vector<int>    flags;
};

// Core computation: Takes OWNED std::vectors, returns result
// This runs with GIL released - no Python interaction during Geogram calls
static GeometryResult compute_power_cells_periodic_vec(
    const std::vector<double>& P,  // size 3*N (flat: x0,y0,z0, x1,y1,z1, ...)
    const std::vector<double>& W   // size N (weights = r^2)
) {
    GeometryResult out;
    const size_t N = W.size();
    out.volume.resize(N, 0.0);
    out.area.resize(N, 0.0);
    out.fsc.resize(N, 0);
    out.flags.resize(N, 0);

    // Initialize Geogram once per process
    static bool geo_inited = false;
    if (!geo_inited) {
        GEO::initialize();
        GEO::Logger::instance()->set_quiet(true);
        geo_inited = true;
    }

    // Bruno's required pattern: SmartPointer<PeriodicDelaunay3d>
    GEO::SmartPointer<GEO::PeriodicDelaunay3d> pd =
        new GEO::PeriodicDelaunay3d(/*periodic=*/true, /*period=*/1.0);

    pd->set_vertices(GEO::index_t(N), P.data());
    pd->set_weights(W.data());
    pd->compute();

    // Workspace for cell extraction
    VBW::ConvexCell cell;
    cell.use_exact_predicates(true);
    GEO::PeriodicDelaunay3d::IncidentTetrahedra wk;

    // Extract each Laguerre cell
    for (GEO::index_t v = 0; v < GEO::index_t(N); ++v) {
        try {
            cell.clear();
            pd->copy_Laguerre_cell_from_Delaunay(v, cell, wk);
            
            if (cell.empty()) {
                out.flags[v] = 1; // Mark empty/degenerate
                continue;
            }
            
            cell.compute_geometry();
            
            // Volume
            double V = cell.volume();
            if (!std::isfinite(V) || V < 0.0) {
                out.flags[v] = 2;
                V = 0.0;
            }
            out.volume[v] = V;
            
            // Surface area and face count
            double S = 0.0;
            int F = 0;
            const GEO::index_t nv = cell.nb_v();
            for (GEO::index_t lv = 0; lv < nv; ++lv) {
                if (!cell.vertex_is_contributing(lv)) continue;
                ++F;
                double a = cell.facet_area(lv);
                if (a > 0.0) S += a;
            }
            out.area[v] = S;
            out.fsc[v] = F;
            
        } catch (const std::exception& e) {
            out.flags[v] = 3; // Exception during extraction
            out.volume[v] = 0.0;
            out.area[v] = 0.0;
            out.fsc[v] = 0;
        }
    }

    return out;
}

// Python module binding with PROPER MEMORY MANAGEMENT
PYBIND11_MODULE(geom_bridge, m) {
    m.doc() = "Geogram periodic power cell bridge with owned-copy + GIL-release pattern";

    m.def("compute_power_cells",
    [](py::array_t<double, py::array::c_style | py::array::forcecast> points,
       py::array_t<double, py::array::c_style | py::array::forcecast> weights)
    {
        // STEP 1: Snapshot Python buffers into OWNED std::vectors
        // This ensures data survives even if Python GC frees the original arrays
        auto bp = points.request();
        auto bw = weights.request();

        // Validate input shapes
        if (bp.ndim != 2 || bp.shape[1] != 3) {
            throw std::runtime_error("points must be (N, 3)");
        }
        if (bw.ndim != 1) {
            throw std::runtime_error("weights must be (N,)");
        }
        
        const size_t N = static_cast<size_t>(bw.shape[0]);
        if (bp.shape[0] != static_cast<ssize_t>(N)) {
            throw std::runtime_error("points and weights size mismatch");
        }

        // Copy into OWNED vectors (no aliasing, no views)
        std::vector<double> P(3 * N);
        std::vector<double> W(N);
        
        const double* p_ptr = static_cast<const double*>(bp.ptr);
        const double* w_ptr = static_cast<const double*>(bw.ptr);
        
        std::memcpy(P.data(), p_ptr, sizeof(double) * 3 * N);
        std::memcpy(W.data(), w_ptr, sizeof(double) * N);

        // STEP 2: Release GIL and run Geogram computation
        // Python cannot interfere with our owned C++ memory during this
        GeometryResult gr;
        {
            py::gil_scoped_release nogil;
            gr = compute_power_cells_periodic_vec(P, W);
        }
        // GIL reacquired here automatically

        // STEP 3: Return NEW NumPy arrays (owned copies, not views)
        // This ensures Python owns its own memory, separate from std::vector
        py::array_t<double> V_out(gr.volume.size());
        std::memcpy(V_out.mutable_data(), gr.volume.data(),
                    gr.volume.size() * sizeof(double));

        py::array_t<double> A_out(gr.area.size());
        std::memcpy(A_out.mutable_data(), gr.area.data(),
                    gr.area.size() * sizeof(double));

        py::array_t<int> FSC_out(gr.fsc.size());
        std::memcpy(FSC_out.mutable_data(), gr.fsc.data(),
                    gr.fsc.size() * sizeof(int));

        py::array_t<int> FL_out(gr.flags.size());
        std::memcpy(FL_out.mutable_data(), gr.flags.data(),
                    gr.flags.size() * sizeof(int));

        // Return as tuple: (volume, area, fsc, flags)
        return py::make_tuple(V_out, A_out, FSC_out, FL_out);
    },
    py::arg("points"), py::arg("weights"),
    R"doc(
        Compute periodic power cells (Laguerre diagram) in [0,1]³.
        
        Args:
            points: (N, 3) float64 array, positions in [0,1]³
            weights: (N,) float64 array, weights (typically r²)
        
        Returns:
            tuple: (volume, area, fsc, flags) all as NumPy arrays of size N
                - volume: cell volumes
                - area: cell surface areas
                - fsc: face counts
                - flags: 0=OK, >0=degenerate/error
        
        Implementation:
            - Uses owned std::vector copies (no NumPy views)
            - Releases GIL during Geogram computation
            - Returns fresh NumPy arrays (no memory aliasing)
            - SmartPointer<PeriodicDelaunay3d> per Bruno's guidance
    )doc");
}
