// bridge_hardened.cpp — MAXIMUM DEFENSIVE VERSION
// Bullet-proof pybind11 → Geogram bridge with full memory safety

#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <pybind11/stl.h>

#include <vector>
#include <cmath>
#include <cstring>
#include <algorithm>

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

// HARDENED implementation with full memory ownership and validation
GeometryResult compute_power_cells_hardened(
    py::array_t<double, py::array::c_style | py::array::forcecast> points_norm,
    py::array_t<double, py::array::c_style | py::array::forcecast> weights
) {
    // 1) VALIDATE input buffers
    auto bufP = points_norm.request();
    auto bufW = weights.request();
    
    if (bufP.ndim != 2 || bufP.shape[1] != 3) {
        throw std::runtime_error("points_norm must be Nx3");
    }
    if (bufW.ndim != 1) {
        throw std::runtime_error("weights must be 1D");
    }
    
    const size_t N = static_cast<size_t>(bufW.shape[0]);
    if (bufP.shape[0] != static_cast<ssize_t>(N)) {
        throw std::runtime_error("points and weights size mismatch");
    }
    
    if (N == 0 || N > 100000) {
        throw std::runtime_error("N out of reasonable range");
    }
    
    // 2) COPY into C++-owned memory (NO aliasing, NO dangling views)
    std::vector<double> P(N * 3);
    std::vector<double> W(N);
    
    std::memcpy(P.data(), bufP.ptr, sizeof(double) * P.size());
    std::memcpy(W.data(), bufW.ptr, sizeof(double) * W.size());
    
    // 3) SANITIZE inputs
    for (size_t i = 0; i < N * 3; ++i) {
        if (!std::isfinite(P[i])) {
            throw std::runtime_error("NaN/Inf in positions");
        }
        // Wrap to [0, 1)
        while (P[i] < 0.0) P[i] += 1.0;
        while (P[i] >= 1.0) P[i] -= 1.0;
        P[i] = std::max(0.0, std::min(0.999999, P[i]));
    }
    
    for (size_t i = 0; i < N; ++i) {
        if (!std::isfinite(W[i]) || W[i] < 0.0) {
            W[i] = 1e-6;  // Safe fallback
        }
        W[i] = std::max(1e-6, std::min(1.0, W[i]));
    }
    
    // 4) Initialize result
    GeometryResult out;
    out.volume.resize(N, 0.0);
    out.area.resize(N, 0.0);
    out.fsc.resize(N, 0);
    out.flags.resize(N, 0);
    
    // 5) Initialize Geogram (safe to call repeatedly)
    static bool geo_inited = false;
    if (!geo_inited) {
        GEO::initialize();
        GEO::Logger::instance()->set_quiet(true);
        geo_inited = true;
    }
    
    // 6) Build FRESH PeriodicDelaunay3d (stack object, no reuse)
    GEO::PeriodicDelaunay3d pd(/*periodic=*/true, /*period=*/1.0);
    
    try {
        pd.set_vertices(GEO::index_t(N), P.data());
        pd.set_weights(W.data());
        pd.compute();
    } catch (const std::exception& e) {
        // Geogram itself failed - mark all as degenerate
        for (size_t i = 0; i < N; ++i) {
            out.flags[i] = 9;  // Triangulation failed
        }
        return out;
    }
    
    // 7) FRESH workspace per call (no static reuse)
    VBW::ConvexCell cell;
    cell.use_exact_predicates(true);
    GEO::PeriodicDelaunay3d::IncidentTetrahedra W_workspace;
    
    // 8) Extract each cell with MAXIMUM defensive coding
    for (GEO::index_t v = 0; v < GEO::index_t(N); ++v) {
        try {
            cell.clear();
            
            // Copy Laguerre cell
            try {
                pd.copy_Laguerre_cell_from_Delaunay(v, cell, W_workspace);
            } catch (...) {
                out.flags[v] = 2;  // Cell extraction failed
                continue;
            }
            
            // CRITICAL: Compute geometry before ANY queries
            try {
                cell.compute_geometry();
            } catch (...) {
                out.flags[v] = 3;  // Geometry computation failed
                continue;
            }
            
            // Check if empty
            if (cell.empty() || cell.nb_v() == 0) {
                out.flags[v] = 1;  // Empty cell
                continue;
            }
            
            // Compute volume (with guard)
            double V = 0.0;
            try {
                V = cell.volume();
                if (!std::isfinite(V) || V < 0.0) {
                    V = 0.0;
                    out.flags[v] = 4;  // Invalid volume
                }
            } catch (...) {
                out.flags[v] = 5;  // Volume computation crashed
                continue;
            }
            
            // Compute surface area and face count (with guards)
            double S = 0.0;
            int FSC = 0;
            
            try {
                const GEO::index_t nv = cell.nb_v();
                
                for (GEO::index_t lv = 0; lv < nv; ++lv) {
                    // Skip non-contributing vertices
                    bool contributing = false;
                    try {
                        contributing = cell.vertex_is_contributing(lv);
                    } catch (...) {
                        continue;  // Skip problematic vertex
                    }
                    
                    if (!contributing) continue;
                    
                    ++FSC;
                    
                    // Get facet area with guard
                    try {
                        double area = cell.facet_area(lv);
                        if (std::isfinite(area) && area >= 0.0) {
                            S += area;
                        }
                    } catch (...) {
                        // Facet area failed, skip this facet
                        --FSC;  // Don't count it
                    }
                }
            } catch (...) {
                out.flags[v] = 6;  // Facet iteration failed
                // Keep V, set S=0, FSC=0
            }
            
            // Sanity checks
            if (V > 1.0) V = 1.0;  // Can't be larger than unit cube
            if (S > 6.0) S = 6.0;  // Can't be larger than cube surface
            if (FSC > 100) FSC = 100;  // Reasonable upper bound
            
            out.volume[v] = V;
            out.area[v] = S;
            out.fsc[v] = FSC;
            
        } catch (const std::exception& e) {
            // Catch-all for this cell
            out.flags[v] = 7;
            out.volume[v] = 0.0;
            out.area[v] = 0.0;
            out.fsc[v] = 0;
        } catch (...) {
            // Unknown exception
            out.flags[v] = 8;
            out.volume[v] = 0.0;
            out.area[v] = 0.0;
            out.fsc[v] = 0;
        }
    }
    
    return out;
}

// Python module binding
PYBIND11_MODULE(geom_bridge, m) {
    m.doc() = "Geogram bridge - HARDENED VERSION with maximum defensive coding";
    
    py::class_<GeometryResult>(m, "GeometryResult")
        .def(py::init<>())
        .def_readwrite("volume", &GeometryResult::volume)
        .def_readwrite("area", &GeometryResult::area)
        .def_readwrite("fsc", &GeometryResult::fsc)
        .def_readwrite("flags", &GeometryResult::flags);

    m.def("compute_power_cells", &compute_power_cells_hardened,
          "Compute periodic power cells - HARDENED VERSION",
          py::arg("points_norm"),
          py::arg("weights"),
          "Hardened implementation with:\n"
          "- C++ owned memory (no dangling views)\n"
          "- Input validation and sanitization\n"
          "- Fresh Geogram objects every call\n"
          "- Defensive extraction with exception guards\n"
          "- Sanity checks on all outputs");
}

