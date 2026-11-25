# Generative & Algorithmic Music Composition Guide

A guide to generative systems, stochastic modeling, Euclidean rhythms, and constraint-based algorithmic composition for modern producers.

---

## 1. What is Generative Composition?

Generative composition uses rule-based constraints, mathematical sequences, or stochastic processes to construct musical patterns. Instead of drawing every MIDI note manually, the producer establishes musical boundaries (scale, voice leading, rhythm probabilities) and lets algorithmic procedures generate starting material.

---

## 2. Euclidean Rhythms & The Bjorklund Algorithm

### Concept
Originally formulated by E. Bjorklund for nuclear physics and popularized in music by Godfried Toussaint, the Euclidean algorithm $E(k, n)$ distributes $k$ pulses across $n$ time steps as evenly as possible.

### Famous Musical Euclidean Rhythms:
* **$E(3, 8)$:** `[x . . x . . x .]` — The *Tresillo*, foundational to Reggaeton, Afrobeats, Dancehall, and Habanera.
* **$E(5, 8)$:** `[x . x x . x x .]` — The *Cinquillo*, common in Afro-Cuban and jazz.
* **$E(5, 16)$:** `[x . . x . . x . . x . . x . . .]` — Foundational Bossa Nova and modern Amapiano groove.
* **$E(7, 16)$:** West African and Samba bell patterns.

### How to Generate via CLI:
```powershell
# Generate a 16-step Euclidean percussion pattern with 5 pulses at 120 BPM:
python .agents/plugins/producer-reborn/skills/music-composition/scripts/generate_pattern.py --euclidean 5,16 --bpm 120 --output output_midi/euclidean_5_16.mid
```

---

## 3. Constraint-Based Harmony & Procedural Voice Leading

When generating chords programmatically, unconstrained MIDI generators produce clunky, jumpy chords in root position.

### The Voice Leading Algorithm:
Our built-in procedural script (`generate_pattern.py`) applies constraint-based optimization:
1. Calculates all pitch classes for the requested chord extensions (9ths, 11ths, sus, add9).
2. Searches candidate octave inversions in the target register (MIDI 50–74).
3. Minimizes voice displacement cost:
   $$\text{Cost} = \sum_{i=1}^{m} (p_i - q_i)^2$$
   where $p$ and $q$ are note pitches between consecutive chords.
4. Preserves common tones and avoids excessive voicing spans (> 19 semitones).

### How to Generate Chords with Voice Leading:
```powershell
# Generate a Neo-Soul progression with syncopated bass and humanized velocity:
python .agents/plugins/producer-reborn/skills/music-composition/scripts/generate_pattern.py --preset neosoul --bpm 135 --bass-style syncopated --output output_midi/neosoul.mid

# Generate custom chords with walking bass:
python .agents/plugins/producer-reborn/skills/music-composition/scripts/generate_pattern.py --chords "Fmaj7 Em7 Dm9 Cmaj7" --bpm 90 --bass-style walking --output output_midi/lofi_loop.mid
```

---

## 4. Tension-Resolution Curves

Procedural composition works best when structured around deliberate tension curves:
* **Diatonic Ground (Bars 1–2):** Low tension ($i$ or $I$), establishing key stability.
* **Harmonic Exploration (Bar 3):** Moderate tension (secondary dominant, modal mixture, or extended 9th/11th).
* **Cadential Peak & Resolution (Bar 4):** Maximum tension resolving on the final beat (tritone sub, altered dominant, or sus4 $\rightarrow$ 3 resolution).
