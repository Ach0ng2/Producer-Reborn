---
name: routenote-release
description: "Validates technical compliance of audio files (16-bit 44.1 kHz FLAC / 320 kbps MP3) and cover artwork (3000x3000 px RGB JPG) for RouteNote with --fix auto-conversion, and generates H-28 release timelines + .ics calendar files."
triggers:
  - validate routenote
  - check cover artwork
  - check release audio
  - create release schedule
  - release timeline
---

# RouteNote Release Compliance & Timeline Guide

This skill ensures all release assets pass RouteNote moderation smoothly without triggering *Action Needed* rejections.

## 1. Technical Audio & Artwork Validation (with `--fix` Mode)

```powershell
# Audit assets only:
.\.venv\Scripts\python.exe .agents/plugins/producer-reborn/skills/routenote-release/scripts/validate_release.py --audio "path/to/master.flac" --artwork "path/to/cover.jpg"

# Audit and auto-fix (converts audio to 16-bit 44.1 kHz FLAC & resizes artwork to 3000x3000px RGB JPG):
.\.venv\Scripts\python.exe .agents/plugins/producer-reborn/skills/routenote-release/scripts/validate_release.py --audio "path/to/master.wav" --artwork "path/to/cover.png" --fix
```

## 2. Release Countdown Timeline & `.ics` Calendar Export

```powershell
.\.venv\Scripts\python.exe .agents/plugins/producer-reborn/skills/routenote-release/scripts/release_timeline.py --title "Single or EP Title" --release-date "2026-12-25"
```
Generates an H-28 (RouteNote submission), H-14 (approval check), H-7 (Spotify editorial pitch deadline), and Release Day schedule, along with a `release_timeline.ics` file ready to import into Google Calendar or Apple Calendar.
