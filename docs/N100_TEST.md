# N=100 Diagnostic Test

## 🎯 Hypothesis:

**IF** the crash is related to particle count/complexity:
- N=100 should run **forever** (10k+ frames)
- Smaller triangulation = less stress on Geogram

**IF** Geogram has a fundamental bug:
- N=100 will **still crash** around 20-30 Geogram calls (~1600-2100 frames)
- Confirms the issue is in Geogram itself, not our usage

---

## 🧪 Test Configuration:

- **N:** 100 (down from 1000)
- **k_freeze:** 24 (same)
- **Expected Geogram calls:** ~70 calls per 1600 frames
- **Runtime to 10k frames:** ~60 minutes at ~170 FPS

---

## 📊 What to Watch:

### Success Indicators (N=100 stable):
- ✅ Runs past **5000 frames** (30+ minutes)
- ✅ Runs past **10000 frames** (60+ minutes)
- ✅ No crashes, smooth FPS
- **Conclusion:** Scale-related issue, can run lower N safely

### Failure Indicators (N=100 crashes):
- ❌ Crashes around **1600-2100 frames** (same as N=1000)
- ❌ Same Geogram call count (~20-30 calls)
- **Conclusion:** Geogram has fundamental bug, N doesn't matter

---

## 🚀 Run the Test:

```bash
cd /Users/chimel/Desktop/Cursor_FoS-Custom-Grid && source venv/bin/activate && python FoS-IQ-Taichi-Geogram/run_geogram_foam.py
```

---

## ⏱️ Test Duration:

**Let it run until:**
1. **Crashes** → Note frame number, compare to previous (~1600-2100?)
2. **Hits 5000 frames** → Good sign! Let it continue
3. **Hits 10000 frames** → SUCCESS! N=100 is stable

**You can check progress:**
- Terminal shows frame count every 100 frames
- Window title shows FPS
- HUD shows IQ, k, t_geom

---

## 📝 Things to Note:

**Expected behavior at N=100:**
- **FPS:** ~170-200 (faster than N=1000 due to smaller geometry)
- **t_geom:** ~5-10ms (much faster than N=1000's 20-30ms)
- **k:** Will stay at 24 or drop to 16 (adaptive to fast t_geom)
- **IQ μ:** ~0.4-0.6 (similar range)
- **Particles:** 100 visible spheres (smaller cloud)

**Visual differences:**
- Smaller particle cloud
- Less dense
- Still shows IQ coloring (blue/gray/red)
- Still smooth animation

---

## 🎯 Decision Tree:

```
Run N=100 test
    │
    ├─ Crashes at ~1600-2100 frames?
    │   └─> Geogram is fundamentally broken
    │       Options:
    │       - Accept limitation (restart loop)
    │       - Process isolation
    │       - Try RVD path
    │       - Switch to approximate geometry
    │
    └─ Runs past 10k frames?
        └─> Scale-related issue
            Options:
            - Find stable N (binary search: 200? 500?)
            - Use that N for production
            - Or implement batching smarter
```

---

## 💬 After the Test:

**Report back:**
1. Did it crash? At what frame?
2. Or did it reach 5k/10k?
3. What was the FPS/t_geom?

**Then we'll decide together:**
- If stable: Find optimal N
- If crashes: Choose mitigation strategy

---

**Good luck! Let's see what happens!** 🚀

