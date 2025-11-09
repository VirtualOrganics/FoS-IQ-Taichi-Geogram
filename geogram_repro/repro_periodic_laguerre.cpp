// repro_periodic_laguerre.cpp
// Standalone C++ repro for periodic Laguerre diagram crash investigation
// Uses Bruno's required SmartPointer pattern exactly as documented

#include <geogram/basic/common.h>
#include <geogram/basic/command_line.h>
#include <geogram/basic/logger.h>
#include <geogram/basic/smart_pointer.h>
#include <geogram/delaunay/periodic_delaunay_3d.h>
#include <geogram/voronoi/convex_cell.h>

#include <cmath>
#include <vector>
#include <random>
#include <iostream>
#include <cassert>

using GEO::index_t;

static void jittered_grid_points(size_t N, std::vector<double>& P01, std::vector<double>& W) {
    // Create ~cuberoot(N)^3 jittered grid in [0,1)^3, fixed seed for determinism
    std::mt19937_64 rng(0xBEEF);
    std::uniform_real_distribution<double> u(-1.0, 1.0);

    size_t m = std::max<size_t>(4, std::lround(std::cbrt(double(N))));
    std::vector<double> gx(m);
    for (size_t i=0;i<m;++i) gx[i] = (i + 0.5) / double(m);

    std::vector<std::array<double,3>> pts;
    pts.reserve(m*m*m);
    for (size_t ix=0; ix<m; ++ix)
    for (size_t iy=0; iy<m; ++iy)
    for (size_t iz=0; iz<m; ++iz) {
        if (pts.size() >= N) break;
        double j = 0.15 / double(m); // small jitter
        pts.push_back({ gx[ix] + j*u(rng), gx[iy] + j*u(rng), gx[iz] + j*u(rng) });
    }
    pts.resize(N);

    P01.resize(3*N);
    for (size_t i=0;i<N;++i){
        for (int k=0;k<3;++k){
            double v = pts[i][k];
            // wrap to [0,1)
            v = v - std::floor(v);
            if (v >= 1.0) v = std::nextafter(1.0, 0.0);
            if (v < 0.0)  v += 1.0;
            P01[3*i+k] = v;
        }
    }
    // Positive finite weights (use radii^2 style)
    W.resize(N);
    for (size_t i=0;i<N;++i){
        // mild variation in weights
        double r = 0.02 + 0.01 * std::sin(0.618*i);
        W[i] = r*r;
    }
}

int main(int argc, char** argv) {
    GEO::initialize();
    GEO::Logger::instance()->set_quiet(false);

    const size_t N = (argc > 1 ? std::stoul(argv[1]) : 1000);
    const size_t CYCLES = (argc > 2 ? std::stoul(argv[2]) : 300); // Aim past your historical crash window

    std::cout << "========================================\n";
    std::cout << "Geogram Periodic Laguerre Repro\n";
    std::cout << "========================================\n";
    std::cout << "N = " << N << "\n";
    std::cout << "CYCLES = " << CYCLES << "\n";
    std::cout << "Pattern: SmartPointer<PeriodicDelaunay3d>\n";
    std::cout << "Target: Survive past historical crash (~62-87 cycles at N=1000)\n";
    std::cout << "========================================\n\n";

    std::vector<double> P01, W;
    jittered_grid_points(N, P01, W);

    // Fixed input for all cycles (if you want to also test moving seeds, randomize P01/W per cycle).
    for (size_t cyc = 0; cyc < CYCLES; ++cyc) {
        // --- Bruno's required allocation pattern:
        GEO::SmartPointer<GEO::PeriodicDelaunay3d> pd =
            new GEO::PeriodicDelaunay3d(/*periodic=*/true, /*period=*/1.0);

        pd->set_vertices(index_t(N), P01.data());
        pd->set_weights(W.data());
        pd->compute();

        // Extract Laguerre cells & accumulate simple metrics
        VBW::ConvexCell cell;
        GEO::PeriodicDelaunay3d::IncidentTetrahedra work;

        double sumV = 0.0;
        double sumS = 0.0;
        size_t empty_cells = 0;

        for (index_t v = 0; v < index_t(N); ++v) {
            cell.clear();
            pd->copy_Laguerre_cell_from_Delaunay(v, cell, work);
            if (cell.empty()) { ++empty_cells; continue; }
            cell.compute_geometry();

            double V = cell.volume();
            double S = 0.0;
            const index_t nv = cell.nb_v();
            for (index_t lv=0; lv<nv; ++lv) {
                if (!cell.vertex_is_contributing(lv)) continue;
                double a = cell.facet_area(lv);
                if (a > 0.0) S += a;
            }
            if (V > 0.0) sumV += V;
            sumS += S;
        }

        if ((cyc % 10) == 0 || cyc == 62 || cyc == 87 || cyc == 125) {
            std::cout << "[cycle " << cyc << "] sumV=" << sumV
                      << " sumS=" << sumS
                      << " empty=" << empty_cells << std::endl;
        }

        // Milestones
        if (cyc == 62) {
            std::cout << "\n*** PASSED cycle 62 (historical crash start) ***\n\n";
        }
        if (cyc == 87) {
            std::cout << "\n*** PASSED cycle 87 (historical crash end) ***\n\n";
        }
        if (cyc == 125) {
            std::cout << "\n*** PASSED cycle 125 (equivalent to 3000 frames) ***\n\n";
        }

        // In a periodic unit cube, total volume should be ~1.0 (or ~N*mean_cell_vol)
        if (!std::isfinite(sumV)) {
            std::cerr << "ERROR: Non-finite sumV at cycle " << cyc << "\n";
            return 2;
        }
        // Tolerate small numeric drift
        if (std::fabs(sumV - 1.0) > 1e-2) {
            std::cerr << "WARNING: sumV deviates from 1.0 by " << (sumV - 1.0)
                      << " at cycle " << cyc << "\n";
            // not fatal; continue to see if any cycle actually crashes
        }
    }

    std::cout << "\n========================================\n";
    std::cout << "✅ SUCCESS!\n";
    std::cout << "Completed " << CYCLES << " cycles without crash.\n";
    std::cout << "SmartPointer pattern is STABLE.\n";
    std::cout << "========================================\n";
    return 0;
}

