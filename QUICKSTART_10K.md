# 🚀 Quick Start Guide — 10K Particle Testing

**All fixes applied. Ready to test!**

---

## ▶️ Launch Program

```bash
cd /Users/chimel/Desktop/Cursor_FoS-Custom-Grid/FoS-IQ-Taichi-Geogram
source ../../venv/bin/activate  # If not already activated
python run_geogram_foam.py
```

---

## 🎮 New Controls

| Action | Control |
|--------|---------|
| **Pause/Resume** | SPACEBAR |
| **Rotate View** | Hold RIGHT MOUSE + drag trackpad |
| **Zoom** | Pinch or scroll |
| **Pan Camera** | WASD keys |
| **Set N to 10k** | Drag slider, click "Restart with New N" |

---

## 🧪 Test 10K Particles

### Step 1: Start Safe
```
1. Launch program (starts at N=100)
2. Verify it runs smoothly
3. Press SPACEBAR to test pause
4. Hold RIGHT MOUSE + drag to test rotation
```

### Step 2: Scale Up
```
1. Drag "N particles" slider to 500
2. Click "Restart with New N"
3. Let it run 100 frames
4. Check FPS and t_geom stats
```

### Step 3: Go to 10K
```
1. Drag slider to 10000
2. Warning appears: "⚠ WARNING: N>5k may be unstable!"
3. Click "Restart with New N"
4. Program restarts with N=10000
```

### Step 4: Apply Anti-Overlap Settings
```
To maximize stability at 10k:
1. Set IQ_min = 0.70
2. Set IQ_max = 0.80
3. Set beta_grow = 0.3
4. Set beta_shrink = 0.5
5. Uncheck "Auto cadence"
6. Set k_freeze = 48
7. Click "Save Settings"
```

---

## 📊 What to Expect at 10K

### With Anti-Overlap Settings:
- **FPS:** ~10-20
- **t_geom:** ~100-200ms
- **Stability:** May run 1000+ frames
- **Colors:** Mostly gray (stable band)

### Without (Default Settings):
- **FPS:** ~5-10
- **t_geom:** ~200-500ms
- **Stability:** Crashes after 100-500 frames
- **Crash Reason:** Overlaps → degenerate geometry

---

## 🛟 If It Crashes

### Before Restart:
1. Check terminal for last frame number
2. Note IQ μ and σ at crash time
3. Delete `foam_settings.json` if corrupted

### Try These Fixes:
- **Lower N:** Start at 5000 instead
- **Tighter band:** IQ_min=0.72, IQ_max=0.78
- **Gentler rates:** beta_grow=0.2, beta_shrink=0.4
- **More relax time:** k_freeze=64
- **Pause early:** Use SPACEBAR to inspect at frame 100

---

## 💾 Save Your Working Config

Once you find stable settings:
1. Click "Save Settings"
2. Close window
3. Relaunch → loads your config automatically!

---

## 🎯 Goal: 10K for 1000 Frames

**Target:** N=10000 running for 1000+ frames without crash

**How to achieve:**
1. Use anti-overlap settings (see above)
2. Monitor IQ σ - keep it below 0.15
3. Use SPACEBAR pause to check stats every 100 frames
4. If `% Below` goes above 20%, tighten IQ_min/IQ_max
5. If crashes persist, reduce N to 8000 or 7500

---

## 📞 Report Results

After testing, note:
- **Max N achieved:** (e.g., 8500)
- **Frames before crash:** (e.g., 1250)
- **Settings used:** (copy from foam_settings.json)
- **Last known IQ μ/σ:** (from control panel)
- **FPS at stable point:** (from stats)

This will help diagnose if the issue is:
- Memory allocation (immediate crash)
- Stub dynamics (crash after 100-1000 frames)
- Geogram tolerance (crash at specific geometry)

---

## ✅ Quick Checklist

- [ ] Activate venv
- [ ] Launch program
- [ ] Test SPACEBAR pause
- [ ] Test RIGHT MOUSE rotation
- [ ] Start at N=100 (verify)
- [ ] Scale to N=500 (verify)
- [ ] Scale to N=1000 (verify)
- [ ] Apply anti-overlap settings
- [ ] Save settings
- [ ] Scale to N=10000
- [ ] Monitor for 100 frames
- [ ] Note FPS and t_geom
- [ ] Report results!

---

**Good luck with 10K testing! 🚀**

Remember: crashes at high N with stub dynamics are expected. The real solution is integrating proper physics. These fixes prevent system crashes from memory overallocation.

