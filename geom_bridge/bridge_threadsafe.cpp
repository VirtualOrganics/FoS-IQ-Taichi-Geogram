// bridge_threadsafe.cpp — pybind11 → Geogram bridge WITH MUTEX GUARD
// Thread-safe version for multi-threaded Python workers
// Drop-in replacement for bridge.cpp

#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <pybind11/stl.h>

#include <vector>
#include <cmath>
#include <mutex>  // ← ADD THIS

// Geogram headers
#include <geogram/basic/common.h>
#include <geogram/basic/logger.h>
#include <geogram/delaunay/periodic_delaunay_3d.h>
#include <geogram/voronoi/convex_cell.h>

namespace py = pybind11;

// ============================================================================
// CRITICAL: Global mutex to make Geogram calls thread-safe
// ============================================================================
static std::mutex g_geo_mutex;

// Result structure
struct GeometryResult {
    std::vector<double> volume;  // size N
    std::vector<double> area;    // size N
    std::vector<int>    fsc;     // face count per cell
    std::vector<int>    flags;   // 0=ok, >0 degenerate/repair applied
};

// Main function - Thread-safe version with mutex guard
GeometryResult compute_power_cells(
    const double* points_norm,  // N×3, row-major
    const double* weights,      // N
    int N,
    bool periodic               // always true
) {
    // ========================================================================
    // CRITICAL: Acquire lock before ANY Geogram operations
    // ========================================================================
    std::lock_guard<std::mutex> lock(g_geo_mutex);
    
    GeometryResult out;
    out.volume.resize(N, 0.0);
    out.area.resize(N, 0.0);
    out.fsc.resize(N, 0);
    out.flags.resize(N, 0);

    // 1) Initialize Geogram once per process (safe to call multiple times)
    static bool geo_inited = false;
    if(!geo_inited) {
        GEO::initialize();
        GEO::Logger::instance()->set_quiet(true);
        geo_inited = true;
    }

    // 2) Build periodic, weighted triangulation on the unit cube
    GEO::SmartPointer<GEO::PeriodicDelaunay3d> pd =
        new GEO::PeriodicDelaunay3d(/*periodic=*/true, /*period=*/1.0);

    pd->set_vertices(GEO::index_t(N), points_norm);
    pd->set_weights(weights);
    pd->compute();

    // 3) Reusable workspace + cell object
    VBW::ConvexCell cell;
    cell.use_exact_predicates(true);
    GEO::PeriodicDelaunay3d::IncidentTetrahedra W;

    // 4) Extract each Laguerre cell, compute V, S, FSC
    for(GEO::index_t v = 0; v < GEO::index_t(N); ++v) {
        try {
            cell.clear();
            pd->copy_Laguerre_cell_from_Delaunay(v, cell, W);

            // CRITICAL: Compute geometry
            cell.compute_geometry();

            if(cell.empty()) {
                out.flags[v] = 1;
                out.volume[v] = 0.0;
                out.area[v] = 0.0;
                out.fsc[v] = 0;
                continue;
            }

            // Volume
            const double V = cell.volume();

            // Surface area and face count
            double S = 0.0;
            int FSC = 0;
            for(GEO::index_t lv = 1; lv < cell.nb_v(); ++lv) {
                if(cell.vertex_is_contributing(lv)) {
                    ++FSC;
                    S += cell.facet_area(lv);
                }
            }

            out.volume[v] = V;
            out.area[v]   = S;
            out.fsc[v]    = FSC;
        } catch(const std::exception& e) {
            out.flags[v] = 2;
            out.volume[v] = 0.0;
            out.area[v] = 0.0;
            out.fsc[v] = 0;
        }
    }

    return out;
    // ========================================================================
    // Mutex automatically released here (lock_guard destructor)
    // ========================================================================
}

// Python module binding (unchanged)
PYBIND11_MODULE(geom_bridge, m) {
    m.doc() = "Geogram bridge for periodic power cell computation (THREAD-SAFE)";
    
    py::class_<GeometryResult>(m, "GeometryResult")
        .def(py::init<>())
        .def_readwrite("volume", &GeometryResult::volume)
        .def_readwrite("area", &GeometryResult::area)
        .def_readwrite("fsc", &GeometryResult::fsc)
        .def_readwrite("flags", &GeometryResult::flags);

    m.def("compute_power_cells", &compute_power_cells,
          "Computes periodic power cells (Laguerre diagram) metrics - THREAD-SAFE",
          py::arg("points_norm"), py::arg("weights"), py::arg("N"), py::arg("periodic"));
}

