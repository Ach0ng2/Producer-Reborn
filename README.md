# 🎹 Producer Reborn Studio

An **open-source, $0-budget AI music production co-pilot** packaged as an [Antigravity](https://antigravity.dev) workspace plugin—complete with a **Zero-CMD Local Web Studio GUI** and **Vibe-First MIDI tools**.

Built for independent artists and bedroom producers who work **by ear** rather than formal music theory, and want to go from a rough beat idea to a release-ready Spotify single or EP without paying for expensive plugins, mastering services, or distributors.

---

## 🎯 Who Is This For?
- **By-Ear / Beat-First Producers:** Pick moods like *Heartbreak Nostalgia* or *Late Night Sadboy* instead of memorizing chord theory.
- **No-Terminal Creators:** Use the **1-click Visual Web GUI** or simply drag & drop audio files into Antigravity chat.
- **Independent Artists on a $0 Budget:** 100% local open-source DSP/AI tools + RouteNote Free tier compliance.
- **Human-in-the-Loop:** You write the beats, record the vocals, and keep 100% creative control—no passive AI prompt-to-song generators.

---

## 🛠️ Core Features (7-Phase Pipeline)

| Phase | Tool / Skill | What It Does |
| :--- | :--- | :--- |
| **1. Songwriting & Harmony** | `songwriting` & `music-composition` | Lyric craft, ABABCB structure, hook design, modal interchange, and 24+ genre frameworks. |
| **2. Vibe-to-MIDI & Audio-to-MIDI** | `generate_pattern.py` & `analyze_audio.py` | Generate voice-led chords, basslines, and Euclidean grooves by mood—or transcribe audio/loops into BPM-synced MIDI via Spotify Basic Pitch (ONNX). |
| **3. Stem & Pitch Doctor** | `stem_advisor.py` | Splits full tracks with Demucs ONNX (or accepts DAW stems) and flags off-key notes + pYIN vocal pitch drift in cents. |
| **4. Mix Doctor** | `mix_check.py` | Checks headroom (`-6` to `-3 dBFS`), stereo phase correlation, low-end mono safety (`< 120 Hz`), and 4-band EQ balance vs. a reference track. |
| **5. AI Reference Mastering** | `master_track.py` | Masters your mix against any commercial reference using **Matchering 2.0.6**, exports 24-bit WAV + 16-bit FLAC, and measures EBU R128 LUFS/True-Peak. |
| **6. RouteNote Validator (`--fix`)** | `validate_release.py` | Audits audio (`16-bit / 44.1 kHz FLAC` or `320 kbps MP3`) and cover art (`3000×3000 RGB JPG < 25 MB`), with `--fix` auto-conversion. |
| **7. Release & $0 Marketing** | `release_timeline.py` | Generates an H-28 countdown schedule, Spotify editorial pitch reminder (H-7), loop provenance ledger, and `.ics` calendar file. |

---

## 🚀 Quick Start

### 1. Prerequisites
- **Python 3.10 – 3.12**
- **FFmpeg** installed and available on your system `PATH` (for LUFS loudness measurement)

### 2. Install Dependencies
```bash
python -m venv .venv

# Windows:
.venv\Scripts\activate
pip install -r requirements.txt

# macOS / Linux:
source .venv/bin/activate
pip install -r requirements.txt
```
> **Note for Python 3.12+:** `basic-pitch` pins older TensorFlow versions; if `pip install -r requirements.txt` hits a resolver conflict, install `basic-pitch==0.4.0 --no-deps` after installing `onnxruntime`, `librosa`, `pretty_midi`, `resampy`, `scipy`, and `scikit-learn`.

---

## 🎛️ How to Use (3 Ways)

### Option A: 1-Click Visual Web Studio (Zero Terminal!)
- **Windows:** Double-click `Start_Studio.bat`
- **macOS / Linux:** Run `./Start_Studio.sh`

Your browser opens a minimal, hardware-inspired studio dashboard with 5 drag-and-drop tabs:
1. **Vibe-to-MIDI** (pick a mood OR write custom chords, choose `4/4` / `3/4` / `6/8` / `5/4` / `7/4`, audition live with the built-in browser Rhodes synth, & download `.mid`)
2. **Song & Stem Doctor** (drop track $\rightarrow$ BPM, chords & vocal/bass pitch report)
3. **Mix Doctor** (drop mix $\rightarrow$ headroom, stereo phase & bass mono check)
4. **AI Mastering** (drop mix + reference $\rightarrow$ download 16-bit RouteNote FLAC)
5. **RouteNote & Timeline** (auto-fix audio/cover + export `.ics` release calendar)

### Option B: Antigravity Chat-First (AI Co-Pilot)
Open this folder in **Antigravity**. The workspace plugin at `.agents/plugins/producer-reborn/` loads automatically. Just drop an audio file or ask in plain language:
- *"Open the Studio GUI for me"*
- *"Generate a heartbreak chord progression at 130 BPM"*
- *"Check if my mix is ready for mastering"*
- *"Validate and fix my audio & cover art for RouteNote"*

### Option C: Direct CLI
All scripts live under `.agents/plugins/producer-reborn/skills/<skill>/scripts/`. See [.agents/plugins/producer-reborn/README.md](.agents/plugins/producer-reborn/README.md) for full CLI flags.

---

## ⚠️ Important Legal Note (Royalty-Free Loops)
If your track uses non-exclusive loops (Looperman, Splice, etc.), you **can** distribute it to Spotify, Apple Music, and YouTube Music, **but you MUST uncheck YouTube Content ID, TikTok, and Meta Rights Manager** during distributor submission to avoid false copyright claims.

---

## 📄 License
MIT License — free to use, modify, and share.
