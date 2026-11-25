---
name: producer-pipeline
description: "Main 7-phase music production orchestrator for Producer Reborn Studio: manages song concepts, songwriting, composition & applied theory, procedural MIDI drafting, audio analysis, stem intonation review, mix diagnostics, Matchering reference mastering, RouteNote validation, and $0 release marketing."
triggers:
  - producer pipeline
  - start new song
  - start new ep
  - album roadmap
  - music production workflow
---

# Producer Reborn Studio — Master Pipeline Guide

This skill is the unified orchestrator guiding an independent artist from a blank DAW session all the way to a compliant Spotify and DSP release on a $0 budget.

---

## 7-Phase Production Workflow

```text
[Phase 1: Songwriting & Composition] -> Hook craft, structure, voice leading, modal interchange, & genre harmony (skills: songwriting, music-composition)
        ↓
[Phase 2: Procedural & Synced MIDI]  -> Generate voice-led chords & Euclidean rhythms OR transcribe audio (generate_pattern.py / analyze_audio.py)
        ↓
[Phase 3: Stem & Pitch Review]       -> Export DAW stems (or auto-split) + detect off-key notes & pYIN cents (stem_advisor.py)
        ↓
[Phase 4: Mix Doctor]                -> Check -6dB headroom, stereo phase, mono low-end & spectral balance (mix_check.py)
        ↓
[Phase 5: AI Mastering]              -> Matchering 2.0.6 + EBU R128 LUFS/True-Peak + 16-bit FLAC export (master_track.py)
        ↓
[Phase 6: RouteNote Validator]       -> Audit audio & artwork with --fix auto-conversion (validate_release.py --fix)
        ↓
[Phase 7: Release & Marketing]       -> H-28 countdown timeline, loop provenance ledger, Spotify pitch & .ics (release_timeline.py)
```

---

## Release State Management (`releases/`)

Every single, EP, or album project is organized under `releases/` at the workspace root:

```text
releases/<project-slug>/
├── release.md                 # Tracklist dashboard, target release date, mastering status
└── tracks/<track-slug>/
    ├── track.md               # BPM, key, loop provenance ledger, credits
    ├── lyrics.md              # Lyrics & revision notes
    ├── midi/                  # Exported procedural or transcribed MIDI patterns
    ├── mix/                   # Pre-master WAV exports from DAW
    └── master/                # 24-bit WAV & RouteNote-ready 16-bit FLAC masters
```

### `track.md` Template:
```markdown
# Track: [Track Title]
- **Status:** [Draft / Beat Done / Vocal Recorded / Mixed / Mastered / Released]
- **BPM:** [BPM Value]
- **Key:** [Estimated Key / Scale]
- **Primary Artist:** [Artist Name]
- **Featuring:** [Featured Artist or None]
- **Title Version:** [None / Acoustic / Radio Edit]

## Loop Provenance Ledger
- **Used Loops:** [Looperman / Splice URL or None]
- **Author/License:** [Royalty-Free / Non-Exclusive]
- **Content ID Eligible:** NO (Must UNCHECK YouTube Content ID in RouteNote if using non-exclusive loops!)

## Target Checklist
- [ ] Lyrics & Hook finalized
- [ ] Chords & voice leading drafted (via music-composition or generate_pattern.py)
- [ ] Beat & chord progression aligned in DAW
- [ ] Vocals & bassline audited via stem_advisor.py
- [ ] Mix audited via mix_check.py (Peak between -6 and -3 dBFS)
- [ ] Mastered via master_track.py (LUFS verified & 16-bit FLAC ready)
- [ ] Passed validation via validate_release.py
```
