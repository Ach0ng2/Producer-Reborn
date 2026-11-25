"""
AI Reference Mastering Tool (Matchering 2.0.6 + EBU R128 LUFS + RouteNote FLAC Export)
Producer Reborn Studio

Features:
1. Headroom pre-check on target mix.
2. Process target with reference audio using matchering.process.
3. Automatically export Master WAV (24-bit) + RouteNote-ready FLAC (16-bit 44.1 kHz).
4. Measure Integrated LUFS, Loudness Range (LRA), and True-Peak using FFmpeg EBU R128 filter.
"""

import shutil
import sys
import argparse
import subprocess
import re
import warnings
import logging
from pathlib import Path

logging.getLogger("root").setLevel(logging.ERROR)
warnings.filterwarnings("ignore")

import numpy as np
import soundfile as sf
import matchering as mg

def resolve_ffmpeg():
    """Resolve FFmpeg binary from system PATH or common Windows install paths."""
    found = shutil.which("ffmpeg")
    if found:
        return found
    fallback = Path(r"C:\Program Files (x86)\Common Files\AutoPod\ffmpeg\bin\ffmpeg.exe")
    if fallback.exists():
        return str(fallback)
    return "ffmpeg"

FFMPEG_PATH = resolve_ffmpeg()

def measure_lufs_ffmpeg(audio_path):
    """Measure Integrated LUFS, LRA, and True-Peak using FFmpeg ebur128 filter."""
    try:
        cmd = [
            FFMPEG_PATH, "-nostats", "-i", str(audio_path),
            "-filter_complex", "ebur128=peak=true", "-f", "null", "-"
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        out = res.stderr

        lufs_match = re.findall(r"I:\s+([-\d.]+)\s+LUFS", out)
        lra_match = re.findall(r"LRA:\s+([-\d.]+)\s+LU", out)
        tpk_match = re.findall(r"Peak:\s+([-\d.]+)\s+dBFS", out)

        i_lufs = float(lufs_match[-1]) if lufs_match else None
        lra = float(lra_match[-1]) if lra_match else None
        tpk = float(tpk_match[-1]) if tpk_match else None

        return i_lufs, lra, tpk
    except Exception as e:
        print(f"[!] Warning: Could not measure LUFS via FFmpeg ({e})")
        return None, None, None

def convert_to_routenote_flac(wav_path, flac_path):
    """Convert master WAV to 16-bit 44.1 kHz FLAC using soundfile."""
    data, sr = sf.read(str(wav_path))
    if sr != 44100:
        import librosa
        data = librosa.resample(data.T, orig_sr=sr, target_sr=44100).T
        sr = 44100

    sf.write(str(flac_path), data, 44100, subtype='PCM_16', format='FLAC')

def main():
    parser = argparse.ArgumentParser(description="Matchering AI Reference Mastering")
    parser.add_argument("--target", required=True, help="Path to target mix file (WAV/FLAC)")
    parser.add_argument("--reference", required=True, help="Path to commercial reference track (WAV/MP3/FLAC)")
    parser.add_argument("--output-dir", default="output_master", help="Output directory for mastered files")
    args = parser.parse_args()

    target_path = Path(args.target).resolve()
    ref_path = Path(args.reference).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    if not target_path.exists():
        print(f"[-] Target mix not found: {target_path}")
        sys.exit(1)
    if not ref_path.exists():
        print(f"[-] Reference file not found: {ref_path}")
        sys.exit(1)

    print("=" * 65)
    print("🎚️ Producer Reborn — Matchering AI Reference Mastering")
    print(f"Target Mix : {target_path.name}")
    print(f"Reference  : {ref_path.name}")
    print("=" * 65)

    # Pre-check headroom
    target_data, _ = sf.read(str(target_path))
    peak_db = 20 * np.log10(np.max(np.abs(target_data)))
    print(f"[*] Target Headroom Pre-Check: Peak {peak_db:.2f} dBFS")
    if peak_db > -0.2:
        print("    ⚠️ WARNING: Target mix is clipping/hitting 0 dBFS.")
        print("       Lower your DAW master fader to -6 to -3 dBFS for optimal mastering results.")

    master_wav_path = output_dir / f"{target_path.stem}_master_24bit.wav"
    master_flac_path = output_dir / f"{target_path.stem}_master_RouteNote.flac"

    print("\n[*] Running Matchering 2.0.6 (matching frequency, RMS & limiting)...")
    mg.process(
        target=str(target_path),
        reference=str(ref_path),
        results=[
            mg.pcm24(str(master_wav_path))
        ]
    )

    print(f"[✓] Master WAV (24-bit) exported: {master_wav_path.name}")

    print("[*] Exporting 16-bit 44.1 kHz FLAC for RouteNote...")
    convert_to_routenote_flac(master_wav_path, master_flac_path)
    print(f"[✓] RouteNote FLAC master exported: {master_flac_path.name}")

    print("\n[*] Measuring EBU R128 Loudness...")
    lufs, lra, tpk = measure_lufs_ffmpeg(master_flac_path)

    print("\n" + "=" * 65)
    print("📊 MASTERING LOUDNESS REPORT")
    print("=" * 65)
    if lufs is not None:
        print(f"  • Integrated Loudness : {lufs:.1f} LUFS")
        print(f"  • Loudness Range (LRA): {lra:.1f} LU")
        print(f"  • True-Peak           : {tpk:.2f} dBFS / dBTP")

        print("\n  💡 Streaming Recommendation:")
        if lufs > -9.0:
            print("     ⚠️ Very loud master (> -9 LUFS). Spotify normalization will turn it down ~5 dB.")
        elif -14.0 <= lufs <= -9.0:
            print("     ✅ Modern Streaming Sweet Spot! Punchy and competitive dynamics.")
        else:
            print("     ℹ️ Dynamic/ballad-style master. Spotify will play it without aggressive limiting.")

        if tpk > -0.3:
            print("     ⚠️ True-peak is close to 0 dBTP. Ideal streaming target is ≤ -1.0 dBTP.")
        else:
            print("     ✅ True-peak has safe headroom against lossy codec inter-sample clipping.")

    print(f"\n📂 Ready for RouteNote Upload:")
    print(f"   👉 {master_flac_path}")
    print("=" * 65)

if __name__ == "__main__":
    main()
