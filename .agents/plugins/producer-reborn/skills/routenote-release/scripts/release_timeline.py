"""
Release Timeline & iCalendar Generator
Producer Reborn Studio

Features:
1. Calculates exact target milestones:
   - H-28: Submit to RouteNote (accounts for 7-21 business days moderation).
   - H-14: Follow-up & check Approved status in RouteNote.
   - H-7 : Strict deadline for Spotify for Artists Editorial Pitching.
   - H-3 : Launch Pre-Save & short-form video teasers (TikTok / Reels / Shorts).
   - H-0 : Release Day! Celebrate & share direct streaming links.
2. Exports a standard .ics iCalendar file for Google Calendar / Apple Calendar.
"""

import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path

def create_ics(events, output_path):
    ics_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Producer Reborn Studio//Release Planner//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH"
    ]
    for date_str, summary, description in events:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        dt_stamp = datetime.now().strftime("%Y%m%dT%H%M%SZ")
        dt_start = dt.strftime("%Y%m%d")
        ics_lines.extend([
            "BEGIN:VEVENT",
            f"UID:release-{dt_start}-{abs(hash(summary)) % 100000}@producer-reborn",
            f"DTSTAMP:{dt_stamp}",
            f"DTSTART;VALUE=DATE:{dt_start}",
            f"SUMMARY:{summary}",
            f"DESCRIPTION:{description}",
            "STATUS:CONFIRMED",
            "END:VEVENT"
        ])
    ics_lines.append("END:VCALENDAR")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(ics_lines))

def main():
    parser = argparse.ArgumentParser(description="Release Timeline & Calendar Generator")
    parser.add_argument("--title", required=True, help="Single, EP, or Album title")
    parser.add_argument("--release-date", required=True, help="Target official release date (Format: YYYY-MM-DD)")
    parser.add_argument("--output", default="release_timeline.ics", help="Output .ics file path")
    args = parser.parse_args()

    try:
        rel_date = datetime.strptime(args.release_date, "%Y-%m-%d")
    except ValueError:
        print("[-] Invalid date format. Use YYYY-MM-DD (e.g., 2026-12-25).")
        sys.exit(1)

    h_28 = rel_date - timedelta(days=28)
    h_14 = rel_date - timedelta(days=14)
    h_7  = rel_date - timedelta(days=7)
    h_3  = rel_date - timedelta(days=3)

    events = [
        (
            h_28.strftime("%Y-%m-%d"),
            f"🚀 [H-28] Submit '{args.title}' to RouteNote",
            "Upload 16-bit 44.1kHz FLAC audio and 3000x3000px RGB JPG cover art to RouteNote. Uncheck YouTube Content ID if using non-exclusive loops."
        ),
        (
            h_14.strftime("%Y-%m-%d"),
            f"🔍 [H-14] Check RouteNote Approval Status ('{args.title}')",
            "Verify release status is 'Approved' and delivered to Spotify. Grab your pre-save link in Artist Services."
        ),
        (
            h_7.strftime("%Y-%m-%d"),
            f"🎯 [H-7] Spotify for Artists Pitch Deadline ('{args.title}')",
            "Open artists.spotify.com > Music > Upcoming > Pitch a song. Submit your track story and genre tags before H-7!"
        ),
        (
            h_3.strftime("%Y-%m-%d"),
            f"📱 [H-3] Launch Teasers & Pre-Save ('{args.title}')",
            "Post short-form vertical videos (TikTok / Reels / Shorts) featuring your hook or bridge and your pre-save link in bio."
        ),
        (
            rel_date.strftime("%Y-%m-%d"),
            f"🎉 [RELEASE DAY] '{args.title}' IS LIVE ON SPOTIFY!",
            "Your track is live! Update your Linktree bio, share Spotify Canvas to IG Stories, and monitor streams in Spotify for Artists."
        )
    ]

    print("=" * 65)
    print(f"📅 Producer Reborn — Release Countdown: {args.title}")
    print(f"Target Release Date : {args.release_date}")
    print("=" * 65)

    for d, title, desc in events:
        print(f"\n[{d}]  {title}")
        print(f"    ℹ️  {desc}")

    out_path = Path(args.output).resolve()
    create_ics(events, out_path)
    print("\n" + "=" * 65)
    print("[✓] iCalendar file generated:")
    print(f"    👉 {out_path}")
    print("    💡 Tip: Drag this .ics file into Google Calendar or Apple Calendar!")
    print("=" * 65)

if __name__ == "__main__":
    main()
