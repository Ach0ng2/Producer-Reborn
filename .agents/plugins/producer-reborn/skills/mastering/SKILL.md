---
name: mastering
description: "Performs AI Reference-Based Mastering using Matchering 2.0.6, measures Integrated LUFS & True-Peak via FFmpeg EBU R128, exports 24-bit WAV & 16-bit 44.1 kHz dithered FLAC (RouteNote-ready), and supports Anchor Mastering for EPs/Albums."
triggers:
  - master song
  - matchering
  - master track
  - check lufs
  - reference mastering
---

# AI Reference Mastering Guide

This skill uses **Matchering 2.0.6** to match the frequency response, RMS/LUFS loudness, and stereo width of your target mix to a commercial reference track.

## Execution Procedure

### 1. Single Track Mastering:
```powershell
.\.venv\Scripts\python.exe .agents/plugins/producer-reborn/skills/mastering/scripts/master_track.py --target "path/to/my_mix.wav" --reference "path/to/reference.mp3" [--output-dir "output_master/"]
```

### 2. Batch EP/Album Mastering (Anchor Method):
To maintain a cohesive *tonal balance* across an entire EP or album:
1. Master your lead single (*anchor track*) first against a commercial reference track.
2. Use that mastered anchor track as the `--reference` for all subsequent tracks on the EP!

## Outputs:
- **24-bit Master WAV:** High-resolution master for studio archiving.
- **16-bit 44.1 kHz Master FLAC (Dithered):** Lossless master ready for RouteNote standard distribution.
- **EBU R128 Loudness Report:** Integrated LUFS (streaming sweet spot ~`-14` to `-11 LUFS`), Loudness Range (LRA), and True-Peak (`dBFS`).
