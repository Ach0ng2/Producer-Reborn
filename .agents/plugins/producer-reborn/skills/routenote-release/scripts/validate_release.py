"""
RouteNote Release Asset Validator (with Auto-Fix Mode)
Producer Reborn Studio

Features:
1. Audio Check:
   - Rejects WAV directly (RouteNote standard distribution requires FLAC or MP3).
   - Validates FLAC: 16-bit, 44.1 kHz, 2 channels (stereo).
   - Validates MP3: 320 kbps, 44.1 kHz, stereo.
2. Artwork Check:
   - Validates JPG/JPEG.
   - Validates dimensions: Exactly 3000 x 3000 pixels (1:1 square).
   - Validates Color Space: RGB (rejects CMYK or RGBA).
   - Validates File Size: Under 25 MB.
3. Auto-Fix Mode (--fix):
   - Converts WAV/non-compliant audio into compliant 16-bit 44.1 kHz stereo FLAC.
   - Converts/resizes any image into a compliant 3000 x 3000 px RGB JPG.
"""

import sys
import argparse
from pathlib import Path
import numpy as np
from PIL import Image
import soundfile as sf
from mutagen.mp3 import MP3

def validate_audio(audio_path, auto_fix=False):
    path = Path(audio_path).resolve()
    print(f"\n[*] Auditing Audio File: {path.name}")
    issues = []

    ext = path.suffix.lower()

    if ext == ".wav":
        issues.append("❌ RouteNote does NOT accept WAV for standard uploads! Must be FLAC (16-bit / 44.1 kHz) or 320 kbps MP3.")
    elif ext not in [".flac", ".mp3"]:
        issues.append(f"❌ Unsupported format {ext}. Must be .flac or .mp3.")

    try:
        info = sf.info(str(path))
        if info.samplerate != 44100:
            issues.append(f"❌ Sample rate: {info.samplerate} Hz (Must be exactly 44,100 Hz).")
        else:
            print("   [✓] Sample rate: 44,100 Hz")

        if info.channels != 2:
            issues.append(f"❌ Channels: {info.channels} (Must be 2 channels / Stereo).")
        else:
            print("   [✓] Channels: Stereo (2 ch)")

        if ext == ".flac":
            if info.subtype != "PCM_16":
                issues.append(f"❌ FLAC bit depth: {info.subtype} (RouteNote standard requires 16-bit PCM_16).")
            else:
                print("   [✓] Bit depth: 16-bit (PCM_16)")
        elif ext == ".mp3":
            try:
                mp3_info = MP3(str(path)).info
                bitrate_kbps = int(round(mp3_info.bitrate / 1000))
                if bitrate_kbps < 310:
                    issues.append(f"❌ MP3 bitrate: {bitrate_kbps} kbps (Must be 320 kbps CBR).")
                else:
                    print(f"   [✓] Bitrate: ~{bitrate_kbps} kbps (Meets 320 kbps requirement)")
            except Exception as e:
                issues.append(f"⚠️ Could not verify MP3 bitrate: {e}")
    except Exception as e:
        issues.append(f"❌ Failed to read audio stream: {e}")

    if issues:
        print("\n   Audio Issues Found:")
        for iss in issues:
            print(f"   {iss}")

        if auto_fix:
            print("\n   🛠️ Running Audio Auto-Fix...")
            fixed_path = path.parent / f"{path.stem}_RouteNote_Fixed.flac"
            data, sr = sf.read(str(path))
            if data.ndim == 1:
                data = np.column_stack((data, data))
            if sr != 44100:
                import librosa
                data = librosa.resample(data.T, orig_sr=sr, target_sr=44100).T
            sf.write(str(fixed_path), data, 44100, subtype='PCM_16', format='FLAC')
            print("   ✅ Exported to 16-bit 44.1 kHz stereo FLAC:")
            print(f"      👉 {fixed_path}")
            return False, fixed_path
        return False, None
    else:
        print("   ✅ AUDIO MEETS 100% OF ROUTENOTE TECHNICAL REQUIREMENTS!")
        return True, path

def validate_artwork(art_path, auto_fix=False):
    path = Path(art_path).resolve()
    print(f"\n[*] Auditing Cover Artwork: {path.name}")
    issues = []

    if path.suffix.lower() not in [".jpg", ".jpeg"]:
        issues.append(f"❌ File format {path.suffix} (RouteNote requires .jpg or .jpeg).")

    size_mb = path.stat().st_size / (1024 * 1024)
    if size_mb > 25.0:
        issues.append(f"❌ File size {size_mb:.2f} MB (Maximum 25 MB).")
    else:
        print(f"   [✓] File size: {size_mb:.2f} MB (< 25 MB)")

    try:
        with Image.open(str(path)) as img:
            w, h = img.size
            mode = img.mode

            if w != 3000 or h != 3000:
                issues.append(f"❌ Dimensions: {w} × {h} px (Must be exactly 3000 × 3000 pixels).")
            else:
                print("   [✓] Dimensions: Exactly 3000 × 3000 pixels (1:1 square)")

            if mode != "RGB":
                issues.append(f"❌ Color mode: {mode} (Must be RGB; RouteNote rejects CMYK / RGBA).")
            else:
                print("   [✓] Color mode: RGB")
    except Exception as e:
        issues.append(f"❌ Failed to read image: {e}")

    if issues:
        print("\n   Artwork Issues Found:")
        for iss in issues:
            print(f"   {iss}")

        if auto_fix:
            print("\n   🛠️ Running Artwork Auto-Fix...")
            fixed_path = path.parent / f"{path.stem}_RouteNote_3000x3000.jpg"
            with Image.open(str(path)) as img:
                rgb_img = img.convert("RGB")
                resized = rgb_img.resize((3000, 3000), Image.Resampling.LANCZOS)
                resized.save(str(fixed_path), "JPEG", quality=95)
            print("   ✅ Converted to 3000x3000px RGB JPG:")
            print(f"      👉 {fixed_path}")
            return False, fixed_path
        return False, None
    else:
        print("   ✅ ARTWORK MEETS 100% OF ROUTENOTE TECHNICAL REQUIREMENTS!")
        return True, path

def main():
    parser = argparse.ArgumentParser(description="RouteNote Release Asset Validator")
    parser.add_argument("--audio", help="Path to master audio file")
    parser.add_argument("--artwork", help="Path to cover artwork file")
    parser.add_argument("--fix", action="store_true", help="Automatically fix issues (auto-resize & auto-convert)")
    args = parser.parse_args()

    if not args.audio and not args.artwork:
        parser.print_help()
        sys.exit(1)

    print("=" * 65)
    print("📋 Producer Reborn — RouteNote Pre-Flight Asset Validator")
    print("=" * 65)

    if args.audio:
        validate_audio(args.audio, auto_fix=args.fix)

    if args.artwork:
        validate_artwork(args.artwork, auto_fix=args.fix)

    print("\n" + "=" * 65)
    print("💡 Non-Technical Metadata Reminders:")
    print("   • Do NOT check YouTube Content ID if your track contains non-exclusive loops (Looperman/Splice).")
    print("   • Never put artist names or '(prod. by)' in the title. Use 'Track (feat. Artist)' for features.")
    print("=" * 65)

if __name__ == "__main__":
    main()
