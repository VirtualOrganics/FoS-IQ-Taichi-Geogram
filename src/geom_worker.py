# geom_worker.py
# Non-blocking Geogram calls via worker thread

import threading
import queue
import numpy as np
import sys

# Add geom_bridge to path
sys.path.insert(0, '/Users/chimel/Desktop/Cursor_FoS-Custom-Grid/FoS-IQ-Taichi-Geogram/geom_bridge')

from geom_bridge import compute_power_cells


class GeomWorker:
    def __init__(self, max_chunk=512):
        """
        Args:
            max_chunk: Max particles per Geogram call (batching threshold).
                       Default 512 = most stable across tests (conservative).
        """
        self.max_chunk = max_chunk
        self.q_in  = queue.Queue(maxsize=1)
        self.q_out = queue.Queue(maxsize=1)
        self.th = threading.Thread(target=self._loop, daemon=True)
        self.th.start()

    @staticmethod
    def _compute_batched(pts01, w, max_chunk=512):
        """
        Batch large N into chunks to avoid Geogram edge cases.
        
        Args:
            pts01: Nx3 positions in [0,1]³
            w: N weights
            max_chunk: Max particles per call
        
        Returns:
            (V, S, FSC, flags) as numpy arrays
        """
        N = len(w)
        
        # CRITICAL: Ensure input arrays are contiguous and owned (not views)
        # Prevents dangling pointers when C++ reads the data
        pts01 = np.ascontiguousarray(pts01, dtype=np.float64)
        w = np.ascontiguousarray(w, dtype=np.float64)
        
        if N <= max_chunk:
            # Single call (common path for N≤512) - arrays already contiguous
            # New binding returns tuple (V, A, FSC, flags) directly
            V, A, FSC, flags = compute_power_cells(pts01, w)
            return (V, A, FSC, flags)
        
        # Chunked path for N>512 (batching for stability)
        vols, areas, fscs, flags_list = [], [], [], []
        for i in range(0, N, max_chunk):
            j = min(i + max_chunk, N)
            
            # CRITICAL: Make owned, contiguous copies of chunks
            # Slices create views that can be freed while C++ is reading
            pts_chunk = np.ascontiguousarray(pts01[i:j].copy(), dtype=np.float64)
            w_chunk = np.ascontiguousarray(w[i:j].copy(), dtype=np.float64)
            
            # New binding returns tuple directly
            V, A, FSC, flags_chunk = compute_power_cells(pts_chunk, w_chunk)
            
            vols.append(V)
            areas.append(A)
            fscs.append(FSC)
            flags_list.append(flags_chunk)
        
        return (np.concatenate(vols), np.concatenate(areas),
                np.concatenate(fscs), np.concatenate(flags_list))

    def _loop(self):
        import time
        while True:
            pts01, w = self.q_in.get()
            try:
                t0 = time.perf_counter()
                V, S, FSC, flags = self._compute_batched(pts01, w, self.max_chunk)
                elapsed_ms = (time.perf_counter() - t0) * 1000.0
                
                self.q_out.put((V, S, FSC, flags, elapsed_ms), block=False)
            except Exception as e:
                self.q_out.put(e, block=False)

    def try_request(self, pts01, weights):
        """Returns True if job accepted; False if worker busy."""
        try:
            self.q_in.put_nowait((pts01, weights))
            return True
        except queue.Full:
            return False

    def try_result(self):
        try:
            v = self.q_out.get_nowait()
            if isinstance(v, Exception): raise v
            return v
        except queue.Empty:
            return None

