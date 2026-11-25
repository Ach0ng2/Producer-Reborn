"""
Spotify Basic Pitch Audio-to-MIDI & Chord Analyzer (BPM-Synced & Krumhansl-Schmuckler Key)
Producer Reborn Studio

Features:
1. Auto-detect song BPM with librosa.
2. Run Spotify Basic Pitch (ONNX) to generate accurate polyphonic MIDI.
3. Inject the detected BPM into the MIDI file so it snaps cleanly to your DAW grid.
4. Krumhansl-Schmuckler Key profile correlation to accurately distinguish Major vs. relative Minor.
5. Identify and print chord progression across time.
"""

import sys
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

# Krumhansl-Schmuckler Key Profiles (12 values for each scale degree)
KRUMHANSL_MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
KRUMHANSL_MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])

CHORD_DICTIONARY = {
    (0, 4, 7): "Major",
    (0, 3, 7): "Minor",
    (0, 4, 7, 11): "Maj7",
    (0, 3, 7, 10): "m7",
    (0, 4, 7, 10): "7 (Dominant)",
    (0, 3, 6): "Dim",
    (0, 4, 8): "Aug",
    (0, 2, 7): "sus2",
    (0, 5, 7): "sus4",
    (0, 2, 4, 7): "add9",
    (0, 4, 7, 11, 14): "Maj9",
    (0, 3, 7, 10, 14): "m9",
}

def detect_bpm(audio_path):
    """Detect BPM using librosa beat tracking."""
    try:
        y, sr = librosa.load(str(audio_path), sr=22050, duration=90)
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        bpm = float(tempo.item()) if hasattr(tempo, 'item') else float(tempo)
        return round(bpm, 2)
    except Exception as e:
        print(f"[!] Warning: Failed to detect BPM ({e}), defaulting to 120.0")
        return 120.0

def estimate_key_krumhansl(midi_data):
    """Accurately estimate key using Krumhansl-Schmuckler profile correlation."""
    pitch_durations = np.zeros(12)
    for instrument in midi_data.instruments:
        if instrument.is_drum:
            continue
        for note in instrument.notes:
            pitch_durations[note.pitch % 12] += (note.end - note.start)

    total = np.sum(pitch_durations)
    if total == 0:
        return "C Major", "C", "Major"

    norm_dist = pitch_durations / total

    best_corr = -999.0
    best_key = "C Major"
    best_root = "C"
    best_type = "Major"

    for root_idx in range(12):
        maj_profile = np.roll(KRUMHANSL_MAJOR, root_idx)
        min_profile = np.roll(KRUMHANSL_MINOR, root_idx)

        corr_maj = np.corrcoef(norm_dist, maj_profile)[0, 1]
        corr_min = np.corrcoef(norm_dist, min_profile)[0, 1]

        if corr_maj > best_corr:
            best_corr = corr_maj
            best_root = NOTE_NAMES[root_idx]
            best_type = "Major"
            best_key = f"{best_root} Major"

        if corr_min > best_corr:
            best_corr = corr_min
            best_root = NOTE_NAMES[root_idx]
            best_type = "Minor"
            best_key = f"{best_root} Minor"

    return best_key, best_root, best_type

def identify_chord(pitch_classes):
    """Identify chord name from active pitch classes."""
    if not pitch_classes or len(pitch_classes) < 2:
        return None
    unique_pcs = sorted(list(set(pitch_classes)))
    best_match = None
    for root in unique_pcs:
        root_name = NOTE_NAMES[root]
        intervals = tuple(sorted([(p - root) % 12 for p in unique_pcs]))
        if intervals in CHORD_DICTIONARY:
            return f"{root_name}{CHORD_DICTIONARY[intervals]}"
        for chord_intervals, chord_type in CHORD_DICTIONARY.items():
            if set(chord_intervals).issubset(set(intervals)) and len(chord_intervals) >= 3:
                best_match = f"{root_name}{chord_type}"
                break
        if best_match:
            break
    return best_match

def analyze_chords(midi_data, window_sec=2.0):
    """Extract chords along the timeline."""
    end_time = midi_data.get_end_time()
    if end_time <= 0:
        return []

    progression = []
    current_time = 0.0

    while current_time < end_time:
        window_end = current_time + window_sec
        active_notes = []
        for instrument in midi_data.instruments:
            if instrument.is_drum:
                continue
            for note in instrument.notes:
                if note.start < window_end and note.end > current_time:
                    active_notes.append(note.pitch)

        if active_notes:
            pitch_classes = [p % 12 for p in active_notes]
            chord_name = identify_chord(pitch_classes)
            if chord_name and (not progression or progression[-1][1] != chord_name):
                progression.append((current_time, chord_name))

        current_time += window_sec

    return progression

def fix_midi_tempo(midi_file_path, detected_bpm):
    """Re-write MIDI file with the detected BPM so DAWs snap notes directly to grid."""
    try:
        midi = pretty_midi.PrettyMIDI(str(midi_file_path))
        midi.initial_tempo = detected_bpm
        midi._tick_scales = [(0, 60.0 / (detected_bpm * midi.resolution))]
        midi.write(str(midi_file_path))
    except Exception as e:
        print(f"[!] Warning: Failed to update MIDI tempo ({e})")

def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_audio.py <path_to_audio_file> [--output <output_dir>]")
        sys.exit(1)

    audio_path = Path(sys.argv[1]).resolve()
    if not audio_path.exists():
        print(f"[-] File not found: {audio_path}")
        sys.exit(1)

    output_dir = Path("output_midi").resolve()
    if "--output" in sys.argv:
        idx = sys.argv.index("--output")
        if idx + 1 < len(sys.argv):
            output_dir = Path(sys.argv[idx + 1]).resolve()

    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 65)
    print("🎵 Producer Reborn — Audio to Grid-Synced MIDI & Chord Analysis")
    print(f"Input File : {audio_path.name}")
    print("=" * 65)

    print("[*] Detecting BPM...")
    detected_bpm = detect_bpm(audio_path)
    half_time_bpm = round(detected_bpm / 2, 2)
    print(f"[✓] Detected BPM: {detected_bpm} (or half-time: {half_time_bpm})")

    print("[*] Running Spotify Basic Pitch (ONNX)...")
    expected_midi = output_dir / f"{audio_path.stem}_basic_pitch.mid"
    if expected_midi.exists():
        try:
            expected_midi.unlink()
        except Exception:
            pass

    predict_and_save(
        audio_path_list=[audio_path],
        output_directory=output_dir,
        save_midi=True,
        sonify_midi=False,
        save_model_outputs=False,
        save_notes=False,
        model_or_model_path=ICASSP_2022_MODEL_PATH,
    )

    expected_midi = output_dir / f"{audio_path.stem}_basic_pitch.mid"
    if not expected_midi.exists():
        candidates = list(output_dir.glob(f"{audio_path.stem}*.mid"))
        if candidates:
            expected_midi = candidates[0]

    if not expected_midi.exists():
        print("[-] Failed to generate MIDI file.")
        sys.exit(1)

    fix_midi_tempo(expected_midi, detected_bpm)
    print(f"[✓] MIDI file generated (tempo synced to {detected_bpm} BPM):")
    print(f"    👉 {expected_midi}")

    midi_data = pretty_midi.PrettyMIDI(str(expected_midi))
    key_name, root, mode = estimate_key_krumhansl(midi_data)
    print(f"\n[✓] Estimated Key (Krumhansl-Schmuckler): {key_name}")

    print("\n--- DETECTED CHORD PROGRESSION ---")
    chords = analyze_chords(midi_data, window_sec=2.0)
    if chords:
        for timestamp, chord in chords[:35]:
            m = int(timestamp // 60)
            s = int(timestamp % 60)
            print(f"[{m:02d}:{s:02d}]  ->  {chord}")
        if len(chords) > 35:
            print(f"... and {len(chords) - 35} more chord changes.")
    else:
        print("[i] No full triads detected; audio appears monophonic or ambient.")

    print("----------------------------------")
    print(f"💡 Tip: Drag the MIDI file into your DAW Piano Roll and set project tempo to {detected_bpm} BPM.")

if __name__ == "__main__":
    main()
