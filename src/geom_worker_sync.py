# geom_worker_sync.py
# Single-threaded version (test for thread-safety issue)

import time
import numpy as np
import sys

# Add geom_bridge to path
sys.path.insert(0, '/Users/chimel/Desktop/Cursor_FoS-Custom-Grid/FoS-IQ-Taichi-Geogram/geom_bridge')

from geom_bridge import compute_power_cells


class GeomWorkerSync:
    """
    Synchronous (single-threaded) Geogram worker.
    For testing thread-safety hypothesis.
    """
    def __init__(self, max_chunk=512):
        self.max_chunk = max_chunk
        self.pending = False
        self.last_result = None

    @staticmethod
    def _compute_batched(pts01, w, max_chunk=512):
        """Same batching logic as threaded version"""
        N = len(w)
        
        # CRITICAL: Ensure input arrays are contiguous and owned (not views)
        # Prevents dangling pointers when C++ reads the data
        pts01 = np.ascontiguousarray(pts01, dtype=np.float64)
        w = np.ascontiguousarray(w, dtype=np.float64)
        
        if N <= max_chunk:
            # Single call - arrays already contiguous from above
            res = compute_power_cells(pts01, w, periodic=True)
            return (np.asarray(res.volume, dtype=np.float64),
                    np.asarray(res.area, dtype=np.float64),
                    np.asarray(res.fsc, dtype=np.int32),
                    np.asarray(res.flags, dtype=np.int32))
        
        # Chunked path
        vols, areas, fscs, flags_list = [], [], [], []
        for i in range(0, N, max_chunk):
            j = min(i + max_chunk, N)
            
            # CRITICAL: Make owned, contiguous copies of chunks
            # Slices create views that can be freed while C++ is reading
            pts_chunk = np.ascontiguousarray(pts01[i:j].copy(), dtype=np.float64)
            w_chunk = np.ascontiguousarray(w[i:j].copy(), dtype=np.float64)
            
            res = compute_power_cells(pts_chunk, w_chunk, periodic=True)
            
            vols.append(np.asarray(res.volume, dtype=np.float64))
            areas.append(np.asarray(res.area, dtype=np.float64))
            fscs.append(np.asarray(res.fsc, dtype=np.int32))
            flags_list.append(np.asarray(res.flags, dtype=np.int32))
        
        return (np.concatenate(vols), np.concatenate(areas),
                np.concatenate(fscs), np.concatenate(flags_list))

    def try_request(self, pts01, weights):
        """
        Synchronous version: actually compute immediately.
        Returns True if accepted (always, since we're sync).
        """
        if self.pending:
            return False  # Don't pile up work
        
        try:
            t0 = time.perf_counter()
            V, S, FSC, flags = self._compute_batched(pts01, weights, self.max_chunk)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            
            self.last_result = (V, S, FSC, flags, elapsed_ms)
            self.pending = True
            return True
        except Exception as e:
            self.last_result = e
            self.pending = True
            return True

    def try_result(self):
        """Return result if available"""
        if not self.pending:
            return None
        
        result = self.last_result
        self.pending = False
        self.last_result = None
        
        if isinstance(result, Exception):
            raise result
        
        return result

