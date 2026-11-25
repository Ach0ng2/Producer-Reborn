"""
Procedural & Algorithmic MIDI Generator (Smart Voice Leading, Time Signatures & Euclidean Rhythms)
Producer Reborn Studio — Music Composition Skill

Features:
1. Generative & Custom Chord Progressions with Voice Leading:
   - Minimizes total voice displacement between consecutive chords.
   - Retains common tones across changes to produce smooth keyboard-style voicings.
   - Supports extensions (7, 9, 11, 13, sus2/4, add9, m7b5, dim7, 6, m6, maj7#11, 7alt) and slash chords (e.g. A/C#).
   - Built-in Vibe-First presets (heartbreak, late-night, bedroom-indie, etc.).
2. Multi-Meter Time Signature Engine:
   - Supports 4/4, 3/4, 6/8, 5/4, and 7/4 with accurate MIDI TimeSignature meta-events.
3. Procedural Bassline & Euclidean Rhythm Generator:
   - Adapts syncopated, eighth-note, and walking basslines across odd and even meters.
   - Bjorklund algorithm E(k, n) for polyrhythmic percussion.
4. Humanize, Swing & Octave Shift:
   - Swing percentage, micro-timing humanize in milliseconds, octave transposition, and inversion reroll seeds.
"""

import sys
import json
import random
import itertools
import argparse
from pathlib import Path
import pretty_midi

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

NOTE_TO_PITCH_CLASS = {
    "C": 0, "B#": 0,
    "C#": 1, "DB": 1,
    "D": 2,
    "D#": 3, "EB": 3,
    "E": 4, "FB": 4,
    "F": 5, "E#": 5,
    "F#": 6, "GB": 6,
    "G": 7,
    "G#": 8, "AB": 8,
    "A": 9,
    "A#": 10, "BB": 10,
    "B": 11, "CB": 11
}

CHORD_TEMPLATES = {
    # Triads & 6ths
    "maj": [0, 4, 7],
    "min": [0, 3, 7],
    "m": [0, 3, 7],
    "6": [0, 4, 7, 9],
    "m6": [0, 3, 7, 9],
    "dim": [0, 3, 6],
    "aug": [0, 4, 8],
    "sus2": [0, 2, 7],
    "sus4": [0, 5, 7],
    "5": [0, 7],
    # 7ths
    "maj7": [0, 4, 7, 11],
    "min7": [0, 3, 7, 10],
    "m7": [0, 3, 7, 10],
    "7": [0, 4, 7, 10],
    "7sus4": [0, 5, 7, 10],
    "7alt": [0, 4, 10, 13, 15],
    "dim7": [0, 3, 6, 9],
    "m7b5": [0, 3, 6, 10],
    "mmaj7": [0, 3, 7, 11],
    # 9ths & Extensions
    "add9": [0, 4, 7, 14],
    "madd9": [0, 3, 7, 14],
    "maj9": [0, 4, 7, 11, 14],
    "min9": [0, 3, 7, 10, 14],
    "m9": [0, 3, 7, 10, 14],
    "9": [0, 4, 7, 10, 14],
    "maj7#11": [0, 4, 7, 11, 18],
    "11": [0, 4, 7, 10, 14, 17],
    "m11": [0, 3, 7, 10, 14, 17],
    "maj13": [0, 4, 7, 11, 14, 21],
    "13": [0, 4, 7, 10, 14, 21],
}

PRESETS = {
    "heartbreak": ["F#m9", "Dmaj7#11", "A/C#", "Eadd9"],
    "borrowed-minor-iv": ["C", "Cmaj7", "F", "Fm6"],
    "late-night": ["Dm9", "G13", "Cmaj9", "Am9"],
    "neosoul": ["Dm9", "G13", "Cmaj9", "Am9"],
    "dreamy-bedroom": ["Fmaj7", "Em7", "Dm9", "Cmaj7"],
    "lofi-bedroom": ["Fmaj7", "Em7", "Dm9", "Cmaj7"],
    "dark-trap": ["D#m9", "C#sus2", "Bmaj7", "A#7"],
    "dark-minor": ["D#m9", "C#sus2", "Bmaj7", "A#7"],
    "bedroom-indie": ["Emaj7", "C#m7", "G#m7", "Badd9"],
    "uplifting-indie": ["C", "G", "Am", "F"],
    "pop-axis": ["C", "G", "Am", "F"],
    "tokyo-drift": ["Fm7", "Dbmaj7", "Bbm7", "C7alt"],
    "dark-ambient": ["Cm9", "Abmaj7#11", "Fm11", "G7sus4"],
    "cinematic": ["Cm", "Abmaj7", "Bb", "Gm7"],
    "cinematic-modal": ["Cm", "Abmaj7", "Bb", "Gm7"],
    "soulful-groove": ["Dm7", "G7", "Dm7", "Em7"],
    "modal-dorian": ["Dm7", "G7", "Dm7", "Em7"],
}

TIME_SIGNATURES = {
    "4/4": (4, 4, 4.0),
    "3/4": (3, 4, 3.0),
    "6/8": (6, 8, 3.0),   # 6 eighth notes = 3 quarter-note beats
    "5/4": (5, 4, 5.0),
    "7/4": (7, 4, 7.0),   # 7 quarter-note beats per measure (4+3 / 3+4)
}


def midi_to_note_name(pitch: int) -> str:
    octave = (pitch // 12) - 1
    return f"{NOTE_NAMES[pitch % 12]}{octave}"


def bjorklund(k: int, n: int) -> list[int]:
    """Distribute k pulses evenly across n steps using Bjorklund's Euclidean algorithm."""
    if k >= n:
        return [1] * n
    if k <= 0:
        return [0] * n

    pattern = [[1] for _ in range(k)]
    zeros = [[0] for _ in range(n - k)]

    while len(zeros) > 0:
        num_merge = min(len(pattern), len(zeros))
        for i in range(num_merge):
            pattern[i].extend(zeros.pop())
        if len(pattern) > num_merge:
            zeros = pattern[num_merge:]
            pattern = pattern[:num_merge]

    result = []
    for sub in pattern:
        result.extend(sub)
    return result


def split_chord_tokens(raw_str: str) -> list[str]:
    """Accept space, comma, hyphen, or pipe-separated chord tokens cleanly."""
    cleaned = raw_str.replace(",", " ").replace("|", " ").replace("->", " ")
    tokens = []
    for part in cleaned.split():
        # Strip standalone '-' separator while preserving flats/sharps or chord suffixes
        if part == "-":
            continue
        # Handle "Dm9-G13-Cmaj9" written without spaces
        if "-" in part and not part.startswith("-"):
            tokens.extend([p for p in part.split("-") if p])
        else:
            tokens.append(part)
    return tokens


def parse_chord_symbol(symbol: str) -> tuple[int, int, list[int], str]:
    """
    Parse chord symbol (including slash bass, e.g. A/C#) into:
    (chord_root_pc, bass_pc, intervals_list, clean_symbol).
    """
    sym = symbol.strip()
    if not sym:
        raise ValueError("Empty chord symbol")

    bass_part = None
    chord_part = sym
    if "/" in sym:
        chord_part, bass_part = sym.split("/", 1)

    root_str = chord_part[0].upper()
    idx = 1
    if len(chord_part) > 1 and chord_part[1] in ["#", "b", "B"]:
        acc = "#" if chord_part[1] == "#" else "B"
        root_str += acc
        idx = 2

    quality_raw = chord_part[idx:].strip()
    quality_key = quality_raw.lower()
    if quality_key in ("", "major", "maj"):
        quality_key = "maj"
    elif quality_key == "minor":
        quality_key = "min"

    if root_str not in NOTE_TO_PITCH_CLASS:
        raise ValueError(f"Unknown root note in chord: '{symbol}'")

    root_pc = NOTE_TO_PITCH_CLASS[root_str]
    intervals = CHORD_TEMPLATES.get(quality_key)
    if intervals is None:
        # Fallback heuristic for unknown compound suffixes
        if quality_key.startswith("m") and "maj" not in quality_key:
            intervals = CHORD_TEMPLATES["m7"] if "7" in quality_key else CHORD_TEMPLATES["m"]
        elif "maj7" in quality_key:
            intervals = CHORD_TEMPLATES["maj7"]
        elif "9" in quality_key:
            intervals = CHORD_TEMPLATES["9"]
        elif "7" in quality_key:
            intervals = CHORD_TEMPLATES["7"]
        else:
            intervals = CHORD_TEMPLATES["maj"]

    bass_pc = root_pc
    if bass_part:
        b_str = bass_part.strip()[0].upper()
        if len(bass_part.strip()) > 1 and bass_part.strip()[1] in ["#", "b", "B"]:
            b_str += "#" if bass_part.strip()[1] == "#" else "B"
        if b_str in NOTE_TO_PITCH_CLASS:
            bass_pc = NOTE_TO_PITCH_CLASS[b_str]

    return root_pc, bass_pc, intervals, sym


def generate_voice_leading(chord_list, octave_offset: int = 0, reroll_seed: int = 0):
    """
    Construct voice-led chord voicings minimizing pitch displacement between consecutive chords.
    Supports octave_offset (-2..+2) and reroll_seed for alternative initial inversions.
    """
    voicings = []
    target_octave = 4 + octave_offset
    min_midi = 48 + (octave_offset * 12)
    max_midi = 76 + (octave_offset * 12)
    prev_pitches = None

    for chord_idx, (root_pc, bass_pc, intervals, _) in enumerate(chord_list):
        pcs = [(root_pc + iv) % 12 for iv in intervals]
        unique_pcs = []
        for p in pcs:
            if p not in unique_pcs:
                unique_pcs.append(p)
        if len(unique_pcs) > 5:
            unique_pcs = unique_pcs[:5]

        if prev_pitches is None:
            chosen = []
            for i, p in enumerate(unique_pcs):
                pitch = 12 * (target_octave + 1) + p
                while pitch < min_midi + 5:
                    pitch += 12
                while pitch > max_midi - 2:
                    pitch -= 12
                # Apply reroll inversion shift cleanly
                if reroll_seed > 0 and ((i + reroll_seed) % len(unique_pcs) == 0):
                    shifted = pitch + 12 if pitch + 12 <= max_midi else pitch - 12
                    pitch = shifted
                chosen.append(pitch)
            # Ensure slash bass if different from root
            if bass_pc != root_pc:
                slash_bass = 12 * target_octave + bass_pc
                while slash_bass < min_midi - 4:
                    slash_bass += 12
                while slash_bass > min_midi + 8:
                    slash_bass -= 12
                if slash_bass not in chosen:
                    chosen.insert(0, slash_bass)
            chosen = sorted(list(set(chosen)))
            voicings.append(chosen)
            prev_pitches = chosen
        else:
            best_voicing = None
            best_cost = 999999

            candidates = []
            for p in unique_pcs:
                options = []
                for oct_shift in [-1, 0, 1]:
                    cand = 12 * (target_octave + 1 + oct_shift) + p
                    if (min_midi - 2) <= cand <= (max_midi + 4):
                        options.append(cand)
                if not options:
                    options.append(12 * (target_octave + 1) + p)
                candidates.append(options)

            for comb in itertools.product(*candidates):
                comb_sorted = sorted(list(set(comb)))
                if len(comb_sorted) != len(unique_pcs):
                    continue

                cost = 0
                for a, b in zip(sorted(prev_pitches), comb_sorted):
                    cost += (a - b) ** 2

                span = comb_sorted[-1] - comb_sorted[0]
                if span > 19:
                    cost += 60
                if span < 5:
                    cost += 50

                if cost < best_cost:
                    best_cost = cost
                    best_voicing = comb_sorted

            if best_voicing is None:
                best_voicing = sorted([12 * (target_octave + 1) + p for p in unique_pcs])

            if bass_pc != root_pc:
                slash_bass = 12 * target_octave + bass_pc
                while slash_bass >= best_voicing[0]:
                    slash_bass -= 12
                best_voicing = sorted(list(set([slash_bass] + best_voicing)))

            voicings.append(best_voicing)
            prev_pitches = best_voicing

    return voicings


def get_bass_hits(bass_style: str, beats_per_bar: float, sec_per_beat: float) -> list[tuple[float, float, int]]:
    """Return list of (beat_offset, duration_beats, interval_semitones_from_root) for one measure."""
    if bass_style == "eighth":
        steps = int(round(beats_per_bar * 2))
        return [(s * 0.5, 0.42, 0) for s in range(steps)]

    if bass_style == "walking":
        num_beats = int(round(beats_per_bar))
        walk_intervals = [0, 7, 12, -1, 4, 7, -1]
        return [(float(b), 0.88, walk_intervals[b % len(walk_intervals)]) for b in range(num_beats)]

    # Default: syncopated groove tailored to time signature
    if abs(beats_per_bar - 7.0) < 0.01:
        # 7/4 groove (4+3 subdivision): hits on 1, 2&, 4, 5, 6&
        beats = [(0.0, 1.2, 0), (1.5, 1.2, 0), (3.0, 0.9, 0), (4.0, 1.2, 0), (5.5, 1.2, 7)]
    elif abs(beats_per_bar - 5.0) < 0.01:
        # 5/4 groove (3+2 subdivision)
        beats = [(0.0, 1.2, 0), (1.5, 1.2, 0), (3.0, 0.9, 0), (4.0, 0.9, 7)]
    elif abs(beats_per_bar - 3.0) < 0.01:
        # 3/4 or 6/8 groove
        beats = [(0.0, 1.2, 0), (1.5, 1.2, 0)]
    else:
        # 4/4 groove
        beats = [(0.0, 1.2, 0), (1.5, 1.3, 0), (3.0, 0.9, 0)]
    return beats


def build_midi_pattern(
    chord_symbols: list[str],
    bpm: float = 130.0,
    time_sig: str = "4/4",
    bars_per_chord: float = 1.0,
    repeats: int = 1,
    octave_offset: int = 0,
    reroll_seed: int = 0,
    include_bass: bool = True,
    bass_style: str = "syncopated",
    euclidean_spec: tuple[int, int] | None = None,
    custom_steps: list[int] | None = None,
    swing_pct: float = 0.0,
    humanize_ms: float = 10.0,
):
    rng = random.Random(42 + reroll_seed) if reroll_seed > 0 else random.Random()
    num, den, beats_per_bar = TIME_SIGNATURES.get(time_sig, (4, 4, 4.0))

    midi = pretty_midi.PrettyMIDI(initial_tempo=bpm)
    midi.time_signature_changes.append(pretty_midi.TimeSignature(num, den, 0.0))

    chords_inst = pretty_midi.Instrument(program=4, name="Keys (Chords)")
    bass_inst = pretty_midi.Instrument(program=33, name="Bassline")
    drum_inst = pretty_midi.Instrument(program=0, is_drum=True, name="Euclidean Percussion")

    parsed_chords = [parse_chord_symbol(s) for s in chord_symbols]
    chord_voicings = generate_voice_leading(parsed_chords, octave_offset=octave_offset, reroll_seed=reroll_seed)

    sec_per_beat = 60.0 / bpm
    sec_per_bar = sec_per_beat * beats_per_bar
    chord_duration = sec_per_bar * bars_per_chord
    hum_sec = humanize_ms / 1000.0

    current_time = 0.0
    bar_metadata = []

    for rep in range(repeats):
        for idx, (root_pc, bass_pc, _, clean_sym) in enumerate(parsed_chords):
            voicing = chord_voicings[idx]
            end_time = current_time + chord_duration

            bar_bass_events = []

            for pitch in voicing:
                offset = rng.uniform(-hum_sec, hum_sec) if hum_sec > 0 else 0.0
                vel = rng.randint(76, 94) if hum_sec > 0 else 84
                note_start = max(0.0, current_time + offset)
                note_end = max(note_start + 0.1, end_time - 0.04 + offset)
                chords_inst.notes.append(pretty_midi.Note(velocity=vel, pitch=pitch, start=note_start, end=note_end))

            if include_bass:
                bass_root_pitch = 12 * 3 + bass_pc
                while bass_root_pitch < 33:
                    bass_root_pitch += 12
                while bass_root_pitch > 50:
                    bass_root_pitch -= 12

                hits = get_bass_hits(bass_style, beats_per_bar, sec_per_beat)
                for beat_pos, dur_beats, iv in hits:
                    swing_shift_beats = 0.0
                    if swing_pct > 0 and abs((beat_pos * 2) % 2 - 1.0) < 0.05:
                        swing_shift_beats = (swing_pct / 100.0) * 0.25

                    b_start = max(0.0, current_time + ((beat_pos + swing_shift_beats) * sec_per_beat))
                    b_end = min(end_time - 0.02, b_start + (dur_beats * sec_per_beat))
                    if b_end <= b_start:
                        continue
                    b_vel = rng.randint(84, 102) if hum_sec > 0 else 92
                    b_pitch = bass_root_pitch + iv
                    bass_inst.notes.append(pretty_midi.Note(
                        velocity=b_vel,
                        pitch=b_pitch,
                        start=b_start,
                        end=b_end
                    ))
                    if rep == 0:
                        bar_bass_events.append({
                            "beat": round(beat_pos + swing_shift_beats, 3),
                            "dur_beats": dur_beats,
                            "pitch": b_pitch,
                            "note": midi_to_note_name(b_pitch),
                            "vel": b_vel,
                        })

            if rep == 0:
                bar_metadata.append({
                    "bar": idx + 1,
                    "symbol": clean_sym,
                    "pitches": voicing,
                    "notes": [midi_to_note_name(p) for p in voicing],
                    "bass_events": bar_bass_events,
                    "start_sec": round(current_time, 3),
                    "duration_sec": round(chord_duration, 3),
                })

            current_time = end_time

    step_velocities = []
    has_perc = bool(custom_steps) or bool(euclidean_spec)
    if custom_steps:
        step_velocities = [max(0, min(127, int(v))) for v in custom_steps]
    elif euclidean_spec:
        k, n = euclidean_spec
        steps_per_bar = n
        if abs(beats_per_bar - 7.0) < 0.01 and n == 16:
            steps_per_bar = 14
        elif abs(beats_per_bar - 5.0) < 0.01 and n == 16:
            steps_per_bar = 10
        raw_pat = bjorklund(k, steps_per_bar)
        for s_idx, hit in enumerate(raw_pat):
            if hit:
                is_accent = (s_idx == 0) or (s_idx == steps_per_bar // 2)
                step_velocities.append(115 if is_accent else 82)
            else:
                step_velocities.append(0)

    if step_velocities and any(v > 0 for v in step_velocities):
        steps_per_bar = len(step_velocities)
        step_duration = sec_per_bar / float(steps_per_bar)
        total_bars = bars_per_chord * len(parsed_chords) * repeats
        total_steps = int(round(total_bars * steps_per_bar))
        drum_pitch = 42  # Closed Hi-Hat

        for s in range(total_steps):
            base_vel = step_velocities[s % steps_per_bar]
            if base_vel > 0:
                swing_shift = (swing_pct / 100.0) * (step_duration * 0.35) if (s % 2 == 1 and swing_pct > 0) else 0.0
                t_offset = rng.uniform(-hum_sec * 0.5, hum_sec * 0.5) if hum_sec > 0 else 0.0
                t_start = max(0.0, s * step_duration + swing_shift + t_offset)
                vel = max(1, min(127, base_vel + (rng.randint(-5, 5) if hum_sec > 0 else 0)))
                drum_inst.notes.append(pretty_midi.Note(
                    velocity=vel,
                    pitch=drum_pitch,
                    start=t_start,
                    end=t_start + (step_duration * 0.65)
                ))

    midi.instruments.append(chords_inst)
    if include_bass:
        midi.instruments.append(bass_inst)
    if step_velocities and any(v > 0 for v in step_velocities):
        midi.instruments.append(drum_inst)

    meta = {
        "bpm": bpm,
        "time_signature": time_sig,
        "beats_per_bar": beats_per_bar,
        "octave_offset": octave_offset,
        "bars": bar_metadata,
        "step_velocities": step_velocities,
        "tracks": [i.name for i in midi.instruments],
    }
    return midi, meta


def main():
    parser = argparse.ArgumentParser(description="Procedural MIDI Pattern & Chord Progression Generator")
    parser.add_argument("--chords", help="Space, comma, or hyphen-separated chord progression (e.g. 'Dm9 - G13 - Cmaj9')")
    parser.add_argument("--preset", choices=list(PRESETS.keys()), help="Built-in chord progression preset")
    parser.add_argument("--bpm", type=float, default=130.0, help="Tempo in BPM (default: 130)")
    parser.add_argument("--time-signature", choices=list(TIME_SIGNATURES.keys()), default="4/4", help="Time signature (4/4, 3/4, 6/8, 5/4, 7/4)")
    parser.add_argument("--bars-per-chord", type=float, default=1.0, help="Number of bars per chord (default: 1.0)")
    parser.add_argument("--repeats", type=int, default=1, help="Number of progression loops (default: 1)")
    parser.add_argument("--octave-offset", type=int, default=0, help="Octave transposition (-2 to +2)")
    parser.add_argument("--reroll", type=int, default=0, help="Inversion variation seed (0 = default)")
    parser.add_argument("--swing", type=float, default=0.0, help="Swing percentage (0 to 50)")
    parser.add_argument("--humanize-ms", type=float, default=10.0, help="Micro-timing humanize in milliseconds")
    parser.add_argument("--no-bass", action="store_true", help="Do not generate accompanying bassline")
    parser.add_argument("--bass-style", choices=["syncopated", "eighth", "walking"], default="syncopated", help="Bass groove style")
    parser.add_argument("--euclidean", help="Generate Euclidean rhythm track as K,N (e.g. '5,16' or '3,8')")
    parser.add_argument("--custom-steps", help="Comma-separated custom step velocities (e.g. '115,0,0,82,...')")
    parser.add_argument("--output", default="output_midi/procedural_pattern.mid", help="Output MIDI file path")
    parser.add_argument("--json-meta", help="Optional path to write structured bar/voicing JSON metadata")
    args = parser.parse_args()

    if args.chords and args.chords.strip():
        chord_list = split_chord_tokens(args.chords)
    elif args.preset:
        chord_list = PRESETS[args.preset]
    else:
        chord_list = PRESETS["heartbreak"]

    euclidean_tuple = None
    if args.euclidean and args.euclidean.strip():
        try:
            parts = [int(p.strip()) for p in args.euclidean.split(",")]
            euclidean_tuple = (parts[0], parts[1])
        except Exception:
            print("[!] Invalid format for --euclidean. Use 'K,N' (e.g. '5,16').")
            sys.exit(1)

    custom_steps_list = None
    if args.custom_steps and args.custom_steps.strip():
        try:
            custom_steps_list = [int(x.strip()) for x in args.custom_steps.split(",") if x.strip() != ""]
        except Exception:
            print("[!] Invalid format for --custom-steps. Use comma-separated integers.")
            sys.exit(1)

    out_path = Path(args.output).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print("=" * 65)
    print("Producer Reborn — Procedural MIDI & Voice-Leading Engine")
    print(f"Progression    : {' -> '.join(chord_list)}")
    print(f"Tempo & Meter  : {args.bpm} BPM | {args.time_signature} | Octave {args.octave_offset:+d}")
    print(f"Groove         : Swing {args.swing:.0f}% | Humanize ±{args.humanize_ms:.0f}ms")
    if not args.no_bass:
        print(f"Bassline Track : Enabled ({args.bass_style})")
    if euclidean_tuple:
        print(f"Euclidean Perc : E({euclidean_tuple[0]}, {euclidean_tuple[1]})")
    print("=" * 65)

    midi, meta = build_midi_pattern(
        chord_symbols=chord_list,
        bpm=args.bpm,
        time_sig=args.time_signature,
        bars_per_chord=args.bars_per_chord,
        repeats=args.repeats,
        octave_offset=args.octave_offset,
        reroll_seed=args.reroll,
        include_bass=not args.no_bass,
        bass_style=args.bass_style,
        euclidean_spec=euclidean_tuple,
        custom_steps=custom_steps_list,
        swing_pct=args.swing,
        humanize_ms=args.humanize_ms,
    )

    midi.write(str(out_path))
    meta["output_file"] = str(out_path)
    meta["file_size_kb"] = round(out_path.stat().st_size / 1024.0, 2)

    if args.json_meta:
        Path(args.json_meta).write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print("\nVoicing Breakdown:")
    for b in meta["bars"]:
        print(f"  Bar {b['bar']} [{b['symbol']}]: {' · '.join(b['notes'])}")

    print(f"\n[✓] MIDI exported: {out_path} ({meta['file_size_kb']} KB)")


if __name__ == "__main__":
    main()
