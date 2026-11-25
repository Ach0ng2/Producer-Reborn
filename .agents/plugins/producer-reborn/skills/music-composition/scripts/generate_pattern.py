"""
Procedural & Algorithmic MIDI Generator (Smart Voice Leading & Euclidean Rhythms)
Producer Reborn Studio — Music Composition Skill

Features:
1. Generative Chord Progressions with Voice Leading:
   - Minimizes total voice displacement between consecutive chords.
   - Retains common tones across changes to produce silky, keyboard-style voicings.
   - Supports 7ths, 9ths, 11ths, 13ths, sus2/4, add9, and borrowed chords.
   - Built-in genre presets (neo-soul, lo-fi bedroom, cinematic minor, pop axis, modal lift).
2. Procedural Bassline Generator:
   - Follows harmonic root notes with selectable groove styles (syncopated, eighth-note, walking).
3. Euclidean Rhythm Generator:
   - Uses the Bjorklund algorithm E(k, n) for polyrhythmic hi-hats, percussion, or melodic ostinatos.
4. Humanized Performance:
   - Velocity variation and micro-timing offsets to avoid robotic quantization.
"""

import sys
import random
import argparse
from pathlib import Path
import pretty_midi

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
    # Triads
    "maj": [0, 4, 7],
    "min": [0, 3, 7],
    "m": [0, 3, 7],
    "dim": [0, 3, 6],
    "aug": [0, 4, 8],
    "sus2": [0, 2, 7],
    "sus4": [0, 5, 7],
    # 7ths
    "maj7": [0, 4, 7, 11],
    "min7": [0, 3, 7, 10],
    "m7": [0, 3, 7, 10],
    "7": [0, 4, 7, 10],
    "dim7": [0, 3, 6, 9],
    "m7b5": [0, 3, 6, 10],
    # 9ths & Extensions
    "add9": [0, 4, 7, 14],
    "madd9": [0, 3, 7, 14],
    "maj9": [0, 4, 7, 11, 14],
    "min9": [0, 3, 7, 10, 14],
    "m9": [0, 3, 7, 10, 14],
    "9": [0, 4, 7, 10, 14],
    "11": [0, 4, 7, 10, 14, 17],
    "m11": [0, 3, 7, 10, 14, 17],
    "maj13": [0, 4, 7, 11, 14, 21],
    "13": [0, 4, 7, 10, 14, 21],
}

PRESETS = {
    "neosoul": ["Dm9", "G13", "Cmaj9", "Am9"],
    "late-night": ["Dm9", "G13", "Cmaj9", "Am9"],
    "lofi-bedroom": ["Fmaj7", "Em7", "Dm9", "Cmaj7"],
    "dreamy-bedroom": ["Fmaj7", "Em7", "Dm9", "Cmaj7"],
    "dark-minor": ["D#m9", "C#sus2", "Bmaj7", "A#7"],
    "dark-trap": ["D#m9", "C#sus2", "Bmaj7", "A#7"],
    "cinematic-modal": ["Cm", "Abmaj7", "Bb", "Gm7"],
    "cinematic": ["Cm", "Abmaj7", "Bb", "Gm7"],
    "pop-axis": ["C", "G", "Am", "F"],
    "uplifting-indie": ["C", "G", "Am", "F"],
    "borrowed-minor-iv": ["C", "Cmaj7", "F", "Fm6"],
    "heartbreak": ["C", "Cmaj7", "F", "Fm6"],
    "modal-dorian": ["Dm7", "G7", "Dm7", "Em7"],
    "soulful-groove": ["Dm7", "G7", "Dm7", "Em7"]
}

def bjorklund(k, n):
    """
    Bjorklund algorithm for Euclidean rhythms E(k, n).
    Distributes k pulses as evenly as possible across n steps.
    """
    if k >= n:
        return [1] * n
    if k == 0:
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

def parse_chord_symbol(symbol):
    """Parse string chord symbol into (root_pitch_class, intervals_list)."""
    sym = symbol.strip()
    root_str = sym[0].upper()
    idx = 1
    if len(sym) > 1 and sym[1] in ["#", "b", "B"]:
        root_str += sym[1].upper()
        idx = 2

    quality_str = sym[idx:].lower()
    if quality_str == "" or quality_str == "major":
        quality_str = "maj"
    elif quality_str == "minor":
        quality_str = "min"

    if root_str not in NOTE_TO_PITCH_CLASS:
        raise ValueError(f"Unknown root note in chord: '{symbol}'")

    root_pc = NOTE_TO_PITCH_CLASS[root_str]
    intervals = CHORD_TEMPLATES.get(quality_str, CHORD_TEMPLATES["maj"])
    return root_pc, intervals, root_str

def generate_voice_leading(chord_list, target_octave=4):
    """
    Given a list of (root_pc, intervals), construct a 4-part chord progression
    minimizing pitch displacement between consecutive chords.
    """
    voicings = []
    base_center = 12 * (target_octave + 1)  # C4 = 60

    prev_pitches = None

    for root_pc, intervals, _ in chord_list:
        # Build raw pitch classes
        pcs = [(root_pc + iv) % 12 for iv in intervals]
        # Keep 3 to 4 core voices (root, 3rd, 5th, 7th/9th)
        unique_pcs = []
        for p in pcs:
            if p not in unique_pcs:
                unique_pcs.append(p)
        if len(unique_pcs) > 4:
            unique_pcs = unique_pcs[:4]

        # First chord: register near center (MIDI 55 to 72)
        if prev_pitches is None:
            chosen = []
            for p in unique_pcs:
                # Place near base_center
                oct = target_octave
                pitch = 12 * (oct + 1) + p
                while pitch < 55:
                    pitch += 12
                while pitch > 74:
                    pitch -= 12
                chosen.append(pitch)
            chosen.sort()
            voicings.append(chosen)
            prev_pitches = chosen
        else:
            # Optimize inversion & octave of each voice to minimize sum of squared distances to prev_pitches
            best_voicing = None
            best_cost = 999999

            # Generate candidate octave assignments (-1, 0, +1 octave relative to previous voices)
            candidates = []
            for p in unique_pcs:
                options = []
                for oct_offset in [-1, 0, 1]:
                    cand = 12 * (target_octave + 1 + oct_offset) + p
                    if 48 <= cand <= 80:
                        options.append(cand)
                candidates.append(options)

            # Cartesian search for optimal voice matching
            import itertools
            for comb in itertools.product(*candidates):
                comb_sorted = sorted(list(set(comb)))
                if len(comb_sorted) != len(unique_pcs):
                    continue

                # Voice leading distance cost: pair closest voices
                cost = 0
                for a, b in zip(sorted(prev_pitches), comb_sorted):
                    cost += (a - b) ** 2

                # Penalize extreme range
                span = comb_sorted[-1] - comb_sorted[0]
                if span > 19:  # more than an octave and a fifth
                    cost += 50
                if span < 5:
                    cost += 50

                if cost < best_cost:
                    best_cost = cost
                    best_voicing = comb_sorted

            if best_voicing is None:
                best_voicing = [p + 60 for p in unique_pcs]

            voicings.append(best_voicing)
            prev_pitches = best_voicing

    return voicings

def build_midi_pattern(
    chord_symbols,
    bpm=120.0,
    bars_per_chord=1.0,
    repeats=1,
    include_bass=True,
    bass_style="syncopated",
    euclidean_spec=None,
    humanize=True
):
    midi = pretty_midi.PrettyMIDI(initial_tempo=bpm)

    # 1. Chords Instrument (Electric Piano / Pad, Program 4 = Electric Piano 1)
    chords_inst = pretty_midi.Instrument(program=4, name="Keys (Chords)")

    # 2. Bass Instrument (Fingered Bass, Program 33)
    bass_inst = pretty_midi.Instrument(program=33, name="Bassline")

    # 3. Drums / Percussion Instrument (Euclidean Rhythms, is_drum=True)
    drum_inst = pretty_midi.Instrument(program=0, is_drum=True, name="Euclidean Percussion")

    parsed_chords = [parse_chord_symbol(s) for s in chord_symbols]
    chord_voicings = generate_voice_leading(parsed_chords)

    sec_per_beat = 60.0 / bpm
    sec_per_bar = sec_per_beat * 4.0
    chord_duration = sec_per_bar * bars_per_chord

    current_time = 0.0

    for _ in range(repeats):
        for idx, (root_pc, _, root_name) in enumerate(parsed_chords):
            voicing = chord_voicings[idx]
            end_time = current_time + chord_duration

            # Add chord notes
            for pitch in voicing:
                offset = (random.uniform(-0.012, 0.012)) if humanize else 0.0
                vel = int(random.randint(76, 92)) if humanize else 84
                note_start = max(0.0, current_time + offset)
                note_end = max(note_start + 0.1, end_time - 0.05 + offset)

                note = pretty_midi.Note(
                    velocity=vel,
                    pitch=pitch,
                    start=note_start,
                    end=note_end
                )
                chords_inst.notes.append(note)

            # Add Bass notes if requested
            if include_bass:
                bass_root_pitch = 12 * 3 + root_pc  # In octave 2 (e.g. C2 = 36)
                while bass_root_pitch < 33:  # below A1
                    bass_root_pitch += 12
                while bass_root_pitch > 50:  # above D3
                    bass_root_pitch -= 12

                if bass_style == "eighth":
                    # Pumping 8th notes across the bar
                    total_eighths = int(4 * bars_per_chord * 2)
                    step_sec = sec_per_beat / 2.0
                    for step in range(total_eighths):
                        b_start = current_time + (step * step_sec)
                        b_vel = random.randint(82, 98) if humanize else 90
                        if step % 2 == 1:
                            b_vel -= 12  # accent on downbeats
                        b_note = pretty_midi.Note(
                            velocity=b_vel,
                            pitch=bass_root_pitch,
                            start=b_start,
                            end=b_start + (step_sec * 0.85)
                        )
                        bass_inst.notes.append(b_note)

                elif bass_style == "walking":
                    # 4 beats per bar walking: root, 5th, octave, approach
                    fifth_pitch = bass_root_pitch + 7
                    oct_pitch = bass_root_pitch + 12
                    approach = bass_root_pitch - 1
                    walk_notes = [bass_root_pitch, fifth_pitch, oct_pitch, approach]
                    for b_idx in range(int(4 * bars_per_chord)):
                        b_start = current_time + (b_idx * sec_per_beat)
                        p_choice = walk_notes[b_idx % len(walk_notes)]
                        b_note = pretty_midi.Note(
                            velocity=random.randint(85, 96) if humanize else 90,
                            pitch=p_choice,
                            start=b_start,
                            end=b_start + (sec_per_beat * 0.88)
                        )
                        bass_inst.notes.append(b_note)

                else:  # syncopated (groove on beat 1, beat 2&, and beat 4)
                    hit_beats = [0.0, 1.5, 3.0]
                    for beat_pos in hit_beats:
                        b_start = current_time + (beat_pos * sec_per_beat)
                        dur = sec_per_beat * 0.9 if beat_pos != 1.5 else sec_per_beat * 1.3
                        b_note = pretty_midi.Note(
                            velocity=random.randint(88, 102) if humanize else 95,
                            pitch=bass_root_pitch,
                            start=b_start,
                            end=b_start + dur
                        )
                        bass_inst.notes.append(b_note)

            current_time = end_time

    # Add Euclidean rhythm if requested
    if euclidean_spec:
        k, n = euclidean_spec
        pattern = bjorklund(k, n)
        step_duration = sec_per_bar / float(n)  # 1 bar = n steps (e.g. 16th notes)
        total_bars = bars_per_chord * len(parsed_chords) * repeats

        total_steps = int(total_bars * n)
        drum_pitch = 42  # Closed Hi-Hat in General MIDI
        for s in range(total_steps):
            if pattern[s % n] == 1:
                t_start = s * step_duration
                t_offset = random.uniform(-0.006, 0.006) if humanize else 0.0
                vel = random.randint(78, 105) if humanize else 90
                # Accent beat 1 of each measure
                if (s % n) == 0:
                    vel = min(120, vel + 15)
                drum_note = pretty_midi.Note(
                    velocity=vel,
                    pitch=drum_pitch,
                    start=max(0.0, t_start + t_offset),
                    end=t_start + (step_duration * 0.7)
                )
                drum_inst.notes.append(drum_note)

    midi.instruments.append(chords_inst)
    if include_bass:
        midi.instruments.append(bass_inst)
    if euclidean_spec:
        midi.instruments.append(drum_inst)

    return midi

def main():
    parser = argparse.ArgumentParser(description="Procedural MIDI Pattern & Chord Progression Generator")
    parser.add_argument("--chords", help="Space-separated chord progression (e.g. 'Dm9 G13 Cmaj9 Am9')")
    parser.add_argument("--preset", choices=list(PRESETS.keys()), help="Built-in chord progression preset")
    parser.add_argument("--bpm", type=float, default=120.0, help="Tempo in BPM (default: 120)")
    parser.add_argument("--bars-per-chord", type=float, default=1.0, help="Number of bars per chord (default: 1.0)")
    parser.add_argument("--repeats", type=int, default=2, help="Number of progression loops (default: 2)")
    parser.add_argument("--no-bass", action="store_true", help="Do not generate accompanying bassline")
    parser.add_argument("--bass-style", choices=["syncopated", "eighth", "walking"], default="syncopated", help="Bass groove style")
    parser.add_argument("--euclidean", help="Generate Euclidean rhythm track as K,N (e.g. '5,16' or '3,8')")
    parser.add_argument("--output", default="output_midi/procedural_pattern.mid", help="Output MIDI file path")
    args = parser.parse_args()

    if not args.chords and not args.preset:
        print("[!] No chords or preset specified. Using default preset 'neosoul'.")
        chord_list = PRESETS["neosoul"]
    elif args.preset:
        chord_list = PRESETS[args.preset]
    else:
        chord_list = args.chords.split()

    euclidean_tuple = None
    if args.euclidean:
        try:
            parts = [int(p.strip()) for p in args.euclidean.split(",")]
            euclidean_tuple = (parts[0], parts[1])
        except Exception:
            print("[!] Invalid format for --euclidean. Use 'K,N' (e.g. '5,16').")
            sys.exit(1)

    out_path = Path(args.output).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print("=" * 65)
    print("🎹 Producer Reborn — Procedural & Algorithmic MIDI Generator")
    print(f"Chords Progression : {' -> '.join(chord_list)}")
    print(f"Tempo & Bars       : {args.bpm} BPM, {args.bars_per_chord} bar(s)/chord, {args.repeats} loop(s)")
    if not args.no_bass:
        print(f"Bassline Track     : Enabled (style: {args.bass_style})")
    if euclidean_tuple:
        print(f"Euclidean Rhythm   : E({euclidean_tuple[0]}, {euclidean_tuple[1]})")
    print("=" * 65)

    midi = build_midi_pattern(
        chord_symbols=chord_list,
        bpm=args.bpm,
        bars_per_chord=args.bars_per_chord,
        repeats=args.repeats,
        include_bass=not args.no_bass,
        bass_style=args.bass_style,
        euclidean_spec=euclidean_tuple,
        humanize=True
    )

    midi.write(str(out_path))

    print(f"\n[✓] MIDI file successfully generated:")
    print(f"    👉 {out_path}")
    print(f"    Tracks included: {[i.name for i in midi.instruments]}")
    print("=" * 65)
    print("💡 Tip: Drag this file into your DAW (FL Studio Piano Roll)!")

if __name__ == "__main__":
    main()
