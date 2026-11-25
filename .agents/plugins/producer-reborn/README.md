# Producer Reborn Studio — Antigravity Plugin

An open-source, zero-budget ($0) AI-assisted independent music production and distribution pipeline built as an Antigravity workspace plugin. Designed to keep human artists in full creative control while automating applied music theory, procedural MIDI generation, audio analysis, mastering, and release compliance.

---

## 7-Phase Production Pipeline

```text
1. Songwriting & Composition    (skills: songwriting, music-composition)
   - Lyrical craft, ABABCB anatomy, hooks, applied voice leading, modal interchange, & 24+ genre frameworks.
2. Procedural & Synced MIDI     (skills: music-composition -> generate_pattern.py, audio-analysis -> analyze_audio.py)
   - Procedural voice-led chord progressions, generative basslines, Euclidean rhythms, & audio-to-MIDI transcription.
3. Stem & Intonation Review     (skill: audio-analysis -> stem_advisor.py)
   - Scale-aware vocal & bass clash detection + pYIN microtonal cents analysis.
4. Mix Doctor                   (skill: mix-doctor -> mix_check.py)
   - Headroom (-6 to -3 dBFS), stereo phase correlation, low-end mono compatibility (< 120 Hz), & spectral curves.
5. AI Reference Mastering       (skill: mastering -> master_track.py)
   - Matchering 2.0.6 matching EQ/dynamics, 24-bit WAV + 16-bit FLAC export, & EBU R128 LUFS/True-Peak measurement.
6. RouteNote Validator & Fix    (skill: routenote-release -> validate_release.py)
   - Audio (16-bit 44.1 kHz FLAC / 320 kbps MP3) & artwork (3000x3000px RGB JPG < 25 MB) with `--fix` auto-conversion.
7. Release & $0 Marketing       (skill: routenote-release -> release_timeline.py)
   - H-28 countdown timeline, loop provenance ledger (strict YouTube Content ID guardrails), & `.ics` calendar sync.
```

---

## Release Folder Structure (Data Model)

Each single, EP, or album is tracked inside the `releases/` directory:

```text
releases/<project-slug>/
├── release.md                 # Tracklist status, target release date, mastering & checklist
└── tracks/<track-slug>/
    ├── track.md               # BPM, key, loop provenance ledger, credits, metadata
    ├── lyrics.md              # Lyric drafts & revisions
    ├── midi/                  # Generated procedural or transcribed MIDI files
    ├── mix/                   # Pre-master WAV exports from your DAW
    ├── master/                # 24-bit WAV & 16-bit 44.1 kHz FLAC masters
    └── reports/               # Mix Doctor & Stem Advisor diagnostic reports
```

---

## Requirements & Setup

- **Python 3.10+** (tested on Python 3.12 with `.venv`)
- **Python packages:** `pretty_midi`, `basic-pitch`, `onnxruntime`, `demucs-onnx`, `matchering`, `librosa`, `soundfile`, `pillow`, `mutagen`, `scipy`, `numpy`
- **FFmpeg:** Installed and available on system `PATH` (used for EBU R128 LUFS & True-Peak measurement).

---

## Open-Source Credits & Acknowledgments

- **[NuNaught/suno-songwriting-skill](https://github.com/NuNaught/suno-songwriting-skill)** — Songwriting craft & arrangement heuristics.
- **[SJY051/music-composition](https://github.com/SJY051/music-composition)** — Modular composition theory, harmony, & genre references.
- **[The Prompt Index (`2094-music-theory`)](https://www.thepromptindex.com/skill/2094-music-theory)** — Descriptive applied music theory & modal interchange.
- **[Generative Music Composer](https://mcpmarket.com/tools/skills/generative-music-composer)** — Algorithmic composition & Euclidean rhythm inspiration.
- **[miqdadbadjuber/anti-slop](https://github.com/miqdadbadjuber/anti-slop)** — Anti-Slop minimal UI design guidelines.
- **[Spotify Basic Pitch](https://github.com/spotify/basic-pitch)**, **[Matchering](https://github.com/sergree/matchering)**, **[Demucs](https://github.com/facebookresearch/demucs)**, **[librosa](https://github.com/librosa/librosa)**, **[pretty-midi](https://github.com/craffel/pretty-midi)**, and **[FFmpeg](https://ffmpeg.org/)**.
