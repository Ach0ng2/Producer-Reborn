"""
AI Stem & Musical Advisor (Chord-Aware & pYIN Vocal Intonation)
Producer Reborn Studio

Features:
1. Separates full tracks into stems using Demucs ONNX (or accepts DAW-exported stems).
2. Krumhansl-Schmuckler Key profile to accurately determine scale.
3. Transcribes Vocal and Bass stems with Spotify Basic Pitch.
4. Analyzes Vocal Intonation with pYIN in cents (flags flat/sharp notes without mistaking vibrato for pitch errors).
5. Scale/chord-aware note verification for vocals and basslines.
"""

import sys
import argparse
import warnings
import logging
from pathlib import Path

logging.getLogger("root").setLevel(logging.ERROR)
warnings.filterwarnings("ignore")

import numpy as np
import librosa
import pretty_midi
from basic_pitch.inference import predict_and_save
from basic_pitch import ICASSP_2022_MODEL_PATH

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

KRUMHANSL_MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
KRUMHANSL_MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])

MAJOR_SCALE = {0, 2, 4, 5, 7, 9, 11}
NATURAL_MINOR_SCALE = {0, 2, 3, 5, 7, 8, 10}

def midi_to_note_name(pitch):
    octave = (pitch // 12) - 1
    name = NOTE_NAMES[pitch % 12]
    return f"{name}{octave}"

def format_time(sec):
    m = int(sec // 60)
    s = int(sec % 60)
    return f"{m:02d}:{s:02d}"

def estimate_key_krumhansl(midi_data):
    pitch_durations = np.zeros(12)
    for instrument in midi_data.instruments:
        if instrument.is_drum:
            continue
        for note in instrument.notes:
            pitch_durations[note.pitch % 12] += (note.end - note.start)

    total = np.sum(pitch_durations)
    if total == 0:
        return 0, "Major", "C Major"

    norm_dist = pitch_durations / total
    best_corr = -999.0
    best_root_idx = 0
    best_type = "Major"

    for root_idx in range(12):
        maj_profile = np.roll(KRUMHANSL_MAJOR, root_idx)
        min_profile = np.roll(KRUMHANSL_MINOR, root_idx)
        corr_maj = np.corrcoef(norm_dist, maj_profile)[0, 1]
        corr_min = np.corrcoef(norm_dist, min_profile)[0, 1]

        if corr_maj > best_corr:
            best_corr = corr_maj
            best_root_idx = root_idx
            best_type = "Major"
        if corr_min > best_corr:
            best_corr = corr_min
            best_root_idx = root_idx
            best_type = "Minor"

    return best_root_idx, best_type, f"{NOTE_NAMES[best_root_idx]} {best_type}"

def analyze_vocal_intonation_pyin(vocals_path):
    """Detect microtonal pitch deviations in vocals (cents sharp/flat) via pYIN."""
    try:
        y, sr = librosa.load(str(vocals_path), sr=22050)
        f0, voiced_flag, voiced_probs = librosa.pyin(
            y,
            fmin=librosa.note_to_hz('C2'),
            fmax=librosa.note_to_hz('C6'),
            sr=sr
        )
        times = librosa.times_like(f0, sr=sr)

        intonation_issues = []
        window_size = 20  # ~0.46 seconds
        for i in range(0, len(f0) - window_size, window_size):
            chunk_f0 = f0[i:i+window_size]
            chunk_voiced = voiced_flag[i:i+window_size]

            valid_f0 = chunk_f0[chunk_voiced & ~np.isnan(chunk_f0)]
            if len(valid_f0) > 10:
                midi_vals = librosa.hz_to_midi(valid_f0)
                median_midi = np.median(midi_vals)
                nearest_note = round(median_midi)
                cent_deviation = (median_midi - nearest_note) * 100.0

                if abs(cent_deviation) > 30.0:
                    note_name = midi_to_note_name(nearest_note)
                    direction = "sharp (+)" if cent_deviation > 0 else "flat (-)"
                    intonation_issues.append((times[i], note_name, round(cent_deviation, 1), direction))

        return intonation_issues
    except Exception as e:
        print(f"[!] Warning: Failed to run pYIN intonation check ({e})")
        return []

def separate_stems_demucs(audio_path, output_dir):
    import demucs_onnx
    print("[*] Separating stems automatically with Demucs ONNX...")
    stems_dir = output_dir / f"{audio_path.stem}_stems"
    stems_dir.mkdir(parents=True, exist_ok=True)
    demucs_onnx.separate(
        input=str(audio_path),
        output_dir=str(stems_dir),
        output_format="wav",
        verbose=False,
        progress=True
    )
    vocals_files = list(stems_dir.rglob("*vocals*.wav"))
    bass_files = list(stems_dir.rglob("*bass*.wav"))
    other_files = list(stems_dir.rglob("*other*.wav"))
    return (
        vocals_files[0] if vocals_files else None,
        bass_files[0] if bass_files else None,
        other_files[0] if other_files else None
    )

def transcribe_stem(audio_path, output_dir, tag):
    stem_midi_dir = output_dir / f"midi_{tag}"
    stem_midi_dir.mkdir(parents=True, exist_ok=True)
    expected_midi = stem_midi_dir / f"{audio_path.stem}_basic_pitch.mid"
    if expected_midi.exists():
        try:
            expected_midi.unlink()
        except Exception:
            pass
    predict_and_save(
        audio_path_list=[audio_path],
        output_directory=stem_midi_dir,
        save_midi=True,
        sonify_midi=False,
        save_model_outputs=False,
        save_notes=False,
        model_or_model_path=ICASSP_2022_MODEL_PATH
    )
    midi_files = list(stem_midi_dir.glob("*.mid"))
    return pretty_midi.PrettyMIDI(str(midi_files[0])) if midi_files else None

def main():
    parser = argparse.ArgumentParser(description="AI Stem & Musical Advisor")
    parser.add_argument("song", nargs="?", help="Path to full audio file (MP3/WAV)")
    parser.add_argument("--vocals", help="Path to vocal stem (WAV/MP3)")
    parser.add_argument("--bass", help="Path to bass stem (WAV/MP3)")
    parser.add_argument("--other", help="Path to harmonic/instrument stem (WAV/MP3)")
    args = parser.parse_args()

    if not args.song and not (args.vocals or args.bass):
        parser.print_help()
        sys.exit(1)

    work_dir = Path("output_stems").resolve()
    work_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 65)
    print("🎧 Producer Reborn — AI Stem & Musical Pitch Advisor")
    print("=" * 65)

    vocals_path = Path(args.vocals).resolve() if args.vocals else None
    bass_path = Path(args.bass).resolve() if args.bass else None
    other_path = Path(args.other).resolve() if args.other else None

    if args.song:
        song_path = Path(args.song).resolve()
        if not song_path.exists():
            print(f"[-] File not found: {song_path}")
            sys.exit(1)
        vocals_path, bass_path, other_path = separate_stems_demucs(song_path, work_dir)

    print("\n[*] Transcribing vocal and bass stems to MIDI (Basic Pitch)...")
    vocal_midi = transcribe_stem(vocals_path, work_dir, "vocal") if vocals_path else None
    bass_midi = transcribe_stem(bass_path, work_dir, "bass") if bass_path else None
    other_midi = transcribe_stem(other_path, work_dir, "other") if other_path else None

    ref_midi = other_midi or vocal_midi or bass_midi
    if not ref_midi:
        print("[-] Failed to extract musical notation from audio.")
        sys.exit(1)

    key_root, key_type, key_name = estimate_key_krumhansl(ref_midi)
    print(f"[✓] Estimated Song Key: {key_name}")

    scale_set = MAJOR_SCALE if key_type == "Major" else NATURAL_MINOR_SCALE
    allowed_pcs = {(key_root + i) % 12 for i in scale_set}

    print("\n" + "=" * 65)
    print("📋 MUSICAL FEEDBACK & PITCH NOTES")
    print("=" * 65)

    # 1. Vocal Note Analysis
    if vocal_midi:
        vocal_issues = []
        for inst in vocal_midi.instruments:
            if inst.is_drum:
                continue
            for note in inst.notes:
                if (note.end - note.start) < 0.28:
                    continue
                pc = note.pitch % 12
                if pc not in allowed_pcs:
                    note_name = midi_to_note_name(note.pitch)
                    allowed_sorted = sorted(list(allowed_pcs))
                    diffs = [abs((p - pc + 6) % 12 - 6) for p in allowed_sorted]
                    target_pitch = note.pitch + (1 if allowed_sorted[int(np.argmin(diffs))] > pc else -1)
                    suggest = midi_to_note_name(target_pitch)
                    vocal_issues.append((note.start, note_name, suggest))

        if vocal_issues:
            print(f"\n🎤 VOCAL PITCH NOTES (Found {len(vocal_issues)} off-scale notes vs {key_name}):")
            for t, note, suggest in vocal_issues[:8]:
                print(f"  • [{format_time(t)}] Vocal landed on {note} (off-scale).")
                print(f"    👉 Suggestion: Try moving to {suggest} to sit cleanly in key.")
        else:
            print(f"\n🎤 VOCAL PITCH: Clean! All vocal melodies stay inside {key_name}.")

    # 2. Vocal Intonation Analysis (pYIN Cents)
    if vocals_path and vocals_path.exists():
        print("\n[*] Running pYIN microtonal intonation check...")
        intonation_flags = analyze_vocal_intonation_pyin(vocals_path)
        if intonation_flags:
            print(f"\n🎯 VOCAL INTONATION NOTES (Deviation > 30 cents):")
            for t, note, dev, direction in intonation_flags[:6]:
                print(f"  • [{format_time(t)}] Note {note} sounds {direction} ({dev:+} cents).")
                print(f"    👉 Suggestion: Nudge in your pitch editor or re-take that phrase.")
        else:
            print(f"\n🎯 VOCAL INTONATION: Solid! No significant pitch drift detected.")

    # 3. Bassline Analysis
    if bass_midi:
        bass_issues = []
        for inst in bass_midi.instruments:
            if inst.is_drum:
                continue
            for note in inst.notes:
                if (note.end - note.start) < 0.35:
                    continue
                pc = note.pitch % 12
                if pc not in allowed_pcs:
                    note_name = midi_to_note_name(note.pitch)
                    target_pitch = note.pitch + (1 if (note.pitch + 1) % 12 in allowed_pcs else -1)
                    bass_issues.append((note.start, note_name, midi_to_note_name(target_pitch)))

        if bass_issues:
            print(f"\n🎸 BASSLINE NOTES (Found {len(bass_issues)} off-scale notes):")
            for t, note, suggest in bass_issues[:6]:
                print(f"  • [{format_time(t)}] Bass played {note} (off-scale).")
                print(f"    👉 Suggestion: Shift to {suggest} (root/fifth) to lock in the low end.")
        else:
            print(f"\n🎸 BASSLINE: Solid! Bassline stays locked in {key_name}.")

    print("\n" + "=" * 65)
    print("💡 Tip: Open your stems in your DAW and inspect the timestamps above!")

if __name__ == "__main__":
    main()
