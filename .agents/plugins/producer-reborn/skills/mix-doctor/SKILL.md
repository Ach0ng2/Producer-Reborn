---
name: mix-doctor
description: "Evaluates mix quality prior to mastering: checks headroom (-6 to -3 dBFS), stereo phase correlation, low-end mono compatibility (< 120 Hz), and 4-band spectral balance against a commercial reference track."
triggers:
  - check mix
  - mix doctor
  - check headroom
  - check stereo phase
  - evaluate mix
---

# Mix Doctor Guide

This skill performs technical diagnostics on your pre-master mix (WAV export from your DAW with no limiter on the master bus) before entering Matchering AI mastering.

## Execution Procedure

```powershell
.\.venv\Scripts\python.exe .agents/plugins/producer-reborn/skills/mix-doctor/scripts/mix_check.py "path/to/my_mix.wav" [--reference "path/to/reference.mp3"]
```

## Diagnostic Checklist:
1. **Headroom & Peak:** Ensures peak levels sit between `-6 dBFS` and `-3 dBFS` (no true-peak clipping on the DAW master bus).
2. **Stereo Phase Correlation:** Target range `+0.5` to `+1.0` (safe playback on phone speakers and mono systems without phase cancellation).
3. **Low-End Mono Check (< 120 Hz):** Verifies that sub-bass and kick energy are centered in mono for solid low-end translation.
4. **Spectral Balance Comparison:** Compares energy distribution across Sub (20–60 Hz), Bass (60–250 Hz), Mid (250–4k Hz), and High (4k–20k Hz) against your reference track.
