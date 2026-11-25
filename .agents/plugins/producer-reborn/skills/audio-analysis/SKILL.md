---
name: audio-analysis
description: "Extracts audio files or loops (MP3/WAV) into BPM-synced MIDI notes, detects the musical Key via Krumhansl-Schmuckler correlation, analyzes chord progressions, and audits vocal/bass intonation."
triggers:
  - analyze audio
  - convert audio to midi
  - extract chords
  - detect bpm
  - check song key
  - stem review
---

# Audio Analysis & Chord-to-MIDI Guide

This skill uses **Spotify Basic Pitch (ONNX)**, **librosa**, and **Demucs ONNX** to transcribe tracks or audio loops into grid-synced MIDI files with chord progression and pitch/intonation analysis.

## Execution Procedures

### 1. Audio-to-MIDI & Chord Progression (`analyze_audio.py`)
```powershell
.\.venv\Scripts\python.exe .agents/plugins/producer-reborn/skills/audio-analysis/scripts/analyze_audio.py "path/to/song.mp3" [--output "path/to/output_dir"]
```

**Outputs:**
1. **Detected BPM:** Estimated tempo (e.g., 143.55 BPM or half-time 71.78 BPM).
2. **Estimated Key / Scale:** Determined via *Krumhansl-Schmuckler* tonality profiles (accurately distinguishes parallel/relative Major vs. Minor keys).
3. **Detected Chord Progression:** Chord sequence per interval (`Major`, `Minor`, `7th`, `Maj7`, `sus2/4`, etc.).
4. **Grid-Synced MIDI File (`.mid`):** Tempo-synced MIDI ready to drag-and-drop into any DAW Piano Roll.

### 2. Stem & Vocal/Bass Intonation Review (`stem_advisor.py`)
```powershell
# Using DAW-exported stems:
.\.venv\Scripts\python.exe .agents/plugins/producer-reborn/skills/audio-analysis/scripts/stem_advisor.py --vocals "path/to/vocals.wav" --bass "path/to/bass.wav" [--other "path/to/other.wav"]

# Or auto-separate a full mix using Demucs ONNX:
.\.venv\Scripts\python.exe .agents/plugins/producer-reborn/skills/audio-analysis/scripts/stem_advisor.py "path/to/full_song.mp3"
```
