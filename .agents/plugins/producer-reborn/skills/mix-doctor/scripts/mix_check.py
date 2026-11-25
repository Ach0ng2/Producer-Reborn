"""
Mix Doctor — Pre-Mastering Audio Diagnostic Tool
Producer Reborn Studio

Features:
1. Peak & Headroom Check (verifies target -6 dBFS to -3 dBFS headroom for clean mastering).
2. True-peak / Clipping Detection.
3. Stereo Phase Correlation & Mono Compatibility Check.
4. Low-End Mono Check (< 120 Hz).
5. Spectral Energy Distribution (Sub, Bass, Mid, High) vs. Commercial Reference.
"""

import sys
import argparse
import warnings
import logging
from pathlib import Path

logging.getLogger("root").setLevel(logging.ERROR)
warnings.filterwarnings("ignore")

import numpy as np
import soundfile as sf
import librosa

def calculate_spectral_energy(y, sr):
    """Calculate percentage of energy across 4 key frequency bands."""
    D = np.abs(librosa.stft(y)) ** 2
    freqs = librosa.fft_frequencies(sr=sr)

    sub_mask = (freqs >= 20) & (freqs < 60)
    bass_mask = (freqs >= 60) & (freqs < 250)
    mid_mask = (freqs >= 250) & (freqs < 4000)
    high_mask = (freqs >= 4000) & (freqs <= 20000)

    total_energy = np.sum(D)
    if total_energy == 0:
        return 0, 0, 0, 0

    sub_pct = np.sum(D[sub_mask, :]) / total_energy * 100.0
    bass_pct = np.sum(D[bass_mask, :]) / total_energy * 100.0
    mid_pct = np.sum(D[mid_mask, :]) / total_energy * 100.0
    high_pct = np.sum(D[high_mask, :]) / total_energy * 100.0

    return sub_pct, bass_pct, mid_pct, high_pct

def main():
    parser = argparse.ArgumentParser(description="Mix Doctor Pre-Mastering Diagnostic")
    parser.add_argument("mix", help="Path to your pre-master mix file (WAV/FLAC/MP3)")
    parser.add_argument("--reference", help="Path to commercial reference track for spectral comparison")
    args = parser.parse_args()

    mix_path = Path(args.mix).resolve()
    if not mix_path.exists():
        print(f"[-] Mix file not found: {mix_path}")
        sys.exit(1)

    print("=" * 65)
    print("🩺 Producer Reborn — Mix Doctor Pre-Mastering Diagnostic")
    print(f"Target Mix : {mix_path.name}")
    print("=" * 65)

    data, sr = sf.read(str(mix_path), always_2d=True)
    channels = data.shape[1]

    # 1. Peak & Headroom Check
    peak_linear = np.max(np.abs(data))
    peak_db = 20 * np.log10(peak_linear) if peak_linear > 0 else -100.0
    rms_linear = np.sqrt(np.mean(data ** 2))
    rms_db = 20 * np.log10(rms_linear) if rms_linear > 0 else -100.0

    print("\n1. PEAK & HEADROOM:")
    print(f"   • Peak Level: {peak_db:.2f} dBFS")
    print(f"   • RMS Level : {rms_db:.2f} dBFS")

    if peak_db > -0.1:
        print("   ❌ CLIPPING ALERT! Mix is hitting or exceeding 0 dBFS.")
        print("      👉 Fix in DAW: Lower your master fader or bus gain until peaks sit between -6 and -3 dBFS.")
    elif peak_db > -3.0:
        print("   ⚠️ Tight headroom (between -3 dB and 0 dB).")
        print("      👉 Recommendation: Safe to master, though pulling down 2–3 dB gives Matchering more breathing room.")
    elif -8.0 <= peak_db <= -3.0:
        print("   ✅ IDEAL HEADROOM! Sitting cleanly in the -6 to -3 dBFS sweet spot.")
    else:
        print("   ℹ️ Quiet mix (below -8 dBFS). Matchering will bring up the loudness automatically.")

    # 2. Stereo Correlation & Phase Check
    if channels >= 2:
        left = data[:, 0]
        right = data[:, 1]
        corr = np.corrcoef(left, right)[0, 1]
        print("\n2. STEREO PHASE CORRELATION:")
        print(f"   • Phase Correlation: {corr:+.2f} (Scale: -1.0 to +1.0)")

        if corr >= 0.5:
            print("   ✅ SAFE! Strong mono compatibility (no severe phase cancellation).")
        elif 0.0 <= corr < 0.5:
            print("   ⚠️ Wide stereo image; some mid/high elements may thin out on mono speakers.")
        else:
            print("   ❌ PHASE COLLISION! Negative correlation (< 0). Elements will vanish on mono playback.")

        # 3. Low-End Mono Check (< 120 Hz)
        side = (left - right) / 2.0
        b_low = librosa.stft(side)
        freqs = librosa.fft_frequencies(sr=sr)
        low_mask = (freqs < 120)
        low_side_energy = np.sum(np.abs(b_low[low_mask, :]) ** 2)
        total_side_energy = np.sum(np.abs(b_low) ** 2)
        low_leak_pct = (low_side_energy / total_side_energy * 100.0) if total_side_energy > 0 else 0

        print("\n3. LOW-END MONO CHECK (< 120 Hz):")
        if low_leak_pct < 5.0:
            print(f"   ✅ SOLID! Low-end is centered in mono (only {low_leak_pct:.1f}% stereo side bleed).")
        else:
            print(f"   ⚠️ Stereo energy detected in sub-bass ({low_leak_pct:.1f}% side-channel bleed).")
            print("      👉 Fix in DAW: Add a mid/side EQ or stereo shaper on the master bus and mono below 120 Hz.")
    else:
        print("\n2. STEREO CHECK: File is Mono.")

    # 4. Spectral Distribution vs. Reference
    y_target = np.mean(data, axis=1)
    sub, bass, mid, high = calculate_spectral_energy(y_target, sr)

    print("\n4. SPECTRAL FREQUENCY BALANCE:")
    print(f"   • Sub-Bass (20-60 Hz) : {sub:.1f}%")
    print(f"   • Bass (60-250 Hz)    : {bass:.1f}%")
    print(f"   • Mid (250-4000 Hz)   : {mid:.1f}%")
    print(f"   • High (4000-20k Hz)  : {high:.1f}%")

    if args.reference:
        ref_path = Path(args.reference).resolve()
        if ref_path.exists():
            data_ref, sr_ref = sf.read(str(ref_path), always_2d=True)
            y_ref = np.mean(data_ref, axis=1)
            r_sub, r_bass, r_mid, r_high = calculate_spectral_energy(y_ref, sr_ref)
            print(f"\n   📊 COMPARISON VS. REFERENCE ({ref_path.name}):")
            print(f"   • Sub-Bass : {sub:.1f}%  vs  {r_sub:.1f}%  (diff: {sub - r_sub:+.1f}%)")
            print(f"   • Bass     : {bass:.1f}%  vs  {r_bass:.1f}%  (diff: {bass - r_bass:+.1f}%)")
            print(f"   • Mid      : {mid:.1f}%  vs  {r_mid:.1f}%  (diff: {mid - r_mid:+.1f}%)")
            print(f"   • High     : {high:.1f}%  vs  {r_high:.1f}%  (diff: {high - r_high:+.1f}%)")

            if (sub + bass) - (r_sub + r_bass) > 8.0:
                print("   💡 Tip: Your mix is noticeably heavier/muddier in the low-end than the reference.")
            elif (high - r_high) < -6.0:
                print("   💡 Tip: Your mix sounds darker than the reference; consider a gentle high-shelf boost above 10 kHz.")

    print("\n" + "=" * 65)
    print("🎯 Summary: Once peak is around -6 to -3 dBFS and phase is safe, proceed to Matchering!")
    print("=" * 65)

if __name__ == "__main__":
    main()
