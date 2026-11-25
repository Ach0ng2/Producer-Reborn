"""
Producer Reborn Studio — Anti-Slop Minimal Local Web GUI
A tactile, hardware-inspired DAW companion for by-ear producers ($0 Budget, Zero-CMD).
Uses Python standard library http.server + browser Web Audio API synthesis.
"""

import os
import sys
import json
import time
import socket
import argparse
import importlib.util
import webbrowser
import subprocess
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

PLUGIN_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = PLUGIN_DIR.parent.parent.parent
UPLOADS_DIR = WORKSPACE_ROOT / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

SCRIPTS = {
    "generate_pattern": PLUGIN_DIR / "skills" / "music-composition" / "scripts" / "generate_pattern.py",
    "analyze_audio": PLUGIN_DIR / "skills" / "audio-analysis" / "scripts" / "analyze_audio.py",
    "stem_advisor": PLUGIN_DIR / "skills" / "audio-analysis" / "scripts" / "stem_advisor.py",
    "mix_check": PLUGIN_DIR / "skills" / "mix-doctor" / "scripts" / "mix_check.py",
    "master_track": PLUGIN_DIR / "skills" / "mastering" / "scripts" / "master_track.py",
    "validate_release": PLUGIN_DIR / "skills" / "routenote-release" / "scripts" / "validate_release.py",
    "release_timeline": PLUGIN_DIR / "skills" / "routenote-release" / "scripts" / "release_timeline.py",
}


def resolve_python() -> str:
    """Prefer workspace .venv Python, fall back to current interpreter."""
    candidates = [
        WORKSPACE_ROOT / ".venv" / "Scripts" / "python.exe",
        WORKSPACE_ROOT / ".venv" / "bin" / "python",
    ]
    for cand in candidates:
        if cand.exists():
            return str(cand)
    return sys.executable


PYTHON_BIN = resolve_python()

# Import generate_pattern in-process for sub-5ms chord voicing previews
_gp_spec = importlib.util.spec_from_file_location("generate_pattern", str(SCRIPTS["generate_pattern"]))
_gp_mod = importlib.util.module_from_spec(_gp_spec)
_gp_spec.loader.exec_module(_gp_mod)


def safe_filename(name: str) -> str:
    base = Path(name).name
    cleaned = "".join(c if (c.isalnum() or c in "._- ") else "_" for c in base).strip()
    return cleaned or f"upload_{int(time.time())}"


def run_script(cmd_args: list[str]) -> tuple[bool, str]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    try:
        proc = subprocess.run(
            [PYTHON_BIN, *cmd_args],
            cwd=str(WORKSPACE_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )
        return proc.returncode == 0, proc.stdout
    except Exception as exc:
        return False, f"Execution error: {exc}"


def to_rel_download(path: Path) -> str | None:
    try:
        rel = path.resolve().relative_to(WORKSPACE_ROOT.resolve())
        return f"/api/download?file={rel.as_posix()}"
    except ValueError:
        return None


HTML_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Producer Reborn / Studio</title>
  <style>
    :root {
      --bg: #0b0d11;
      --surface: #12151c;
      --surface-2: #181c26;
      --border: #242936;
      --border-hi: #343b4e;
      --text: #eef1f6;
      --muted: #8b93a7;
      --stark: #f4f6fb;
      --stark-fg: #0b0d11;
      --mint: #10b981;
      --amber: #f59e0b;
      --red: #ef4444;
      --mono: ui-monospace, "JetBrains Mono", "SF Mono", Menlo, Consolas, monospace;
      --sans: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: var(--sans);
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      font-size: 13px;
      line-height: 1.45;
    }

    /* Top Nav */
    .topbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 12px 24px;
      border-bottom: 1px solid var(--border);
      background: var(--surface);
      gap: 16px;
      flex-wrap: wrap;
    }
    .brand {
      font-weight: 600;
      font-size: 13px;
      letter-spacing: 0.02em;
      color: var(--text);
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .brand span.sep { color: var(--muted); }
    .brand span.sub { color: var(--muted); font-weight: 400; }

    .nav-tabs {
      display: flex;
      gap: 4px;
      background: var(--bg);
      padding: 3px;
      border: 1px solid var(--border);
      border-radius: 6px;
      flex-wrap: wrap;
    }
    .nav-tab {
      background: transparent;
      border: none;
      color: var(--muted);
      padding: 6px 12px;
      border-radius: 4px;
      font-size: 12px;
      font-weight: 500;
      cursor: pointer;
      font-family: var(--sans);
    }
    .nav-tab:hover { color: var(--text); }
    .nav-tab.active {
      background: var(--surface-2);
      color: var(--stark);
      border: 1px solid var(--border-hi);
    }

    .telemetry-badge {
      font-family: var(--mono);
      font-size: 11px;
      font-variant-numeric: tabular-nums;
      color: var(--mint);
      background: var(--bg);
      border: 1px solid var(--border);
      padding: 5px 10px;
      border-radius: 4px;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .dot { width: 6px; height: 6px; border-radius: 50%; background: var(--mint); display: inline-block; }

    /* Container */
    .main {
      max-width: 1280px;
      width: 100%;
      margin: 0 auto;
      padding: 20px 24px 36px;
      flex: 1;
    }
    .tab-pane { display: none; }
    .tab-pane.active { display: block; }

    /* Panels */
    .panel {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 16px;
      margin-bottom: 14px;
    }
    .panel-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 12px;
      gap: 12px;
      flex-wrap: wrap;
    }
    .panel-title {
      font-family: var(--mono);
      font-size: 11px;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--muted);
    }
    .panel-meta {
      font-family: var(--mono);
      font-size: 11px;
      color: var(--muted);
      font-variant-numeric: tabular-nums;
    }

    /* Mode Switcher */
    .seg-group {
      display: inline-flex;
      background: var(--bg);
      border: 1px solid var(--border);
      border-radius: 4px;
      padding: 2px;
      gap: 2px;
    }
    .seg-btn {
      background: transparent;
      border: none;
      color: var(--muted);
      padding: 4px 10px;
      font-size: 11px;
      font-family: var(--mono);
      border-radius: 3px;
      cursor: pointer;
    }
    .seg-btn:hover { color: var(--text); }
    .seg-btn.active {
      background: var(--stark);
      color: var(--stark-fg);
      font-weight: 600;
    }

    /* Vibe Preset Strip */
    .preset-strip {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-bottom: 14px;
    }
    .preset-btn {
      background: var(--surface-2);
      border: 1px solid var(--border);
      color: var(--muted);
      padding: 7px 12px;
      border-radius: 4px;
      font-size: 12px;
      font-weight: 500;
      cursor: pointer;
      transition: border-color 0.1s ease;
    }
    .preset-btn:hover { color: var(--text); border-color: var(--border-hi); }
    .preset-btn.active {
      background: var(--stark);
      color: var(--stark-fg);
      border-color: var(--stark);
      font-weight: 600;
    }

    /* Custom Chords Input Row */
    .custom-row {
      display: none;
      gap: 8px;
      align-items: center;
      margin-bottom: 14px;
      flex-wrap: wrap;
    }
    .custom-row.active { display: flex; }
    .input-mono {
      flex: 1;
      min-width: 240px;
      background: var(--bg);
      border: 1px solid var(--border-hi);
      color: var(--stark);
      font-family: var(--mono);
      font-size: 13px;
      padding: 8px 12px;
      border-radius: 4px;
    }
    .input-mono:focus { outline: none; border-color: var(--stark); }
    .helper-chips { display: flex; gap: 4px; flex-wrap: wrap; }
    .chip-btn {
      background: var(--surface-2);
      border: 1px solid var(--border);
      color: var(--muted);
      font-family: var(--mono);
      font-size: 11px;
      padding: 5px 8px;
      border-radius: 4px;
      cursor: pointer;
    }
    .chip-btn:hover { color: var(--text); border-color: var(--border-hi); }

    /* Controls Bar */
    .controls-row {
      display: flex;
      align-items: flex-end;
      gap: 16px;
      flex-wrap: wrap;
      padding-top: 12px;
      border-top: 1px solid var(--border);
    }
    .ctrl-block { display: flex; flex-direction: column; gap: 6px; }
    .ctrl-label {
      font-family: var(--mono);
      font-size: 10px;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--muted);
    }
    .stepper {
      display: inline-flex;
      align-items: center;
      background: var(--bg);
      border: 1px solid var(--border);
      border-radius: 4px;
      height: 30px;
    }
    .stepper button {
      background: transparent;
      border: none;
      color: var(--text);
      width: 28px;
      height: 100%;
      cursor: pointer;
      font-family: var(--mono);
      font-size: 14px;
    }
    .stepper button:hover { background: var(--surface-2); }
    .stepper span {
      min-width: 32px;
      text-align: center;
      font-family: var(--mono);
      font-size: 12px;
      font-variant-numeric: tabular-nums;
    }
    select.ctrl-select, input.ctrl-input {
      background: var(--bg);
      border: 1px solid var(--border);
      color: var(--text);
      height: 30px;
      padding: 0 10px;
      border-radius: 4px;
      font-size: 12px;
      font-family: var(--sans);
    }
    .tempo-wrap { display: flex; align-items: center; gap: 10px; height: 30px; }
    input[type="range"] { accent-color: var(--stark); cursor: pointer; }
    .tempo-val {
      font-family: var(--mono);
      font-size: 12px;
      font-variant-numeric: tabular-nums;
      min-width: 68px;
    }

    /* Buttons */
    .btn-primary {
      background: var(--stark);
      color: var(--stark-fg);
      border: 1px solid var(--stark);
      padding: 8px 14px;
      border-radius: 4px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      text-decoration: none;
    }
    .btn-primary:hover { opacity: 0.92; }
    .btn-primary:disabled { opacity: 0.45; cursor: not-allowed; }
    .btn-secondary {
      background: var(--surface-2);
      color: var(--text);
      border: 1px solid var(--border);
      padding: 8px 12px;
      border-radius: 4px;
      font-size: 12px;
      font-weight: 500;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
    }
    .btn-secondary:hover { border-color: var(--border-hi); }

    /* 2-Column Workspace */
    .workspace-grid {
      display: grid;
      grid-template-columns: minmax(0, 1.85fr) minmax(300px, 1fr);
      gap: 14px;
    }
    @media (max-width: 920px) {
      .workspace-grid { grid-template-columns: 1fr; }
    }

    /* 4-Bar Chord Strip */
    .bars-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
      gap: 8px;
      margin-bottom: 12px;
    }
    .bar-card {
      background: var(--bg);
      border: 1px solid var(--border);
      border-radius: 4px;
      padding: 10px;
      cursor: pointer;
      transition: border-color 0.1s;
    }
    .bar-card:hover { border-color: var(--border-hi); }
    .bar-card.active { border-color: var(--stark); background: var(--surface-2); }
    .bar-card.playing { border-color: var(--mint); }
    .bar-top {
      display: flex;
      justify-content: space-between;
      font-family: var(--mono);
      font-size: 10px;
      color: var(--muted);
      margin-bottom: 4px;
    }
    .bar-chord { font-size: 15px; font-weight: 600; color: var(--stark); margin-bottom: 4px; }
    .bar-notes { font-family: var(--mono); font-size: 10px; color: var(--muted); }

    /* Harmonic Piano Roll Canvas (True Pitch-Row Matrix) */
    .pianoroll-wrap {
      background: var(--bg);
      border: 1px solid var(--border);
      border-radius: 4px;
      padding: 8px;
      overflow-x: auto;
    }
    .pianoroll-grid {
      display: grid;
      gap: 0;
      min-width: 520px;
    }
    .pr-header-cell {
      font-family: var(--mono);
      font-size: 10px;
      color: var(--muted);
      padding: 4px 6px;
      border-bottom: 1px solid var(--border);
      border-right: 1px solid var(--border);
      text-align: center;
      background: var(--surface);
    }
    .pr-ruler-cell {
      font-family: var(--mono);
      font-size: 10px;
      color: var(--muted);
      padding: 0 6px;
      height: 22px;
      display: flex;
      align-items: center;
      justify-content: flex-end;
      border-right: 1px solid var(--border);
      border-bottom: 1px solid #181c24;
      background: #101319;
    }
    .pr-ruler-cell.black-key {
      background: #0b0d12;
      color: #5e667b;
    }
    .pr-slot {
      height: 22px;
      border-right: 1px solid var(--border);
      border-bottom: 1px solid #181c24;
      background: #101319;
      padding: 2px 3px;
      display: flex;
      align-items: center;
    }
    .pr-slot.black-row {
      background: #0b0d12;
    }
    .pr-note {
      width: 100%;
      height: 100%;
      background: #272d3d;
      border: 1px solid #404a66;
      color: var(--text);
      font-family: var(--mono);
      font-size: 10px;
      padding: 0 6px;
      border-radius: 3px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      cursor: pointer;
    }
    .pr-note:hover { border-color: var(--stark); }
    .pr-note.accent {
      background: var(--stark);
      color: var(--stark-fg);
      border-color: var(--stark);
      font-weight: 600;
    }

    /* Step Sequencer Grid */
    .steps-grid {
      display: grid;
      grid-template-columns: repeat(8, 1fr);
      gap: 5px;
      margin-top: 10px;
    }
    .step-cell {
      background: var(--bg);
      border: 1px solid var(--border);
      border-radius: 4px;
      padding: 6px 4px;
      text-align: center;
      font-family: var(--mono);
      font-size: 10px;
      color: var(--muted);
      cursor: pointer;
      user-select: none;
      transition: border-color 0.08s;
    }
    .step-cell:hover { border-color: var(--border-hi); }
    .step-cell.hit {
      background: var(--surface-2);
      border-color: var(--border-hi);
      color: var(--text);
    }
    .step-cell.accent {
      background: var(--stark);
      border-color: var(--stark);
      color: var(--stark-fg);
      font-weight: 700;
    }
    .step-cell.playing-step {
      outline: 2px solid var(--mint);
      outline-offset: -1px;
    }

    /* Mini Piano Keyboard */
    .kbd-wrap {
      display: flex;
      position: relative;
      height: 84px;
      background: var(--bg);
      border: 1px solid var(--border);
      border-radius: 4px;
      padding: 4px;
      user-select: none;
      margin-bottom: 8px;
    }
    .key-white {
      flex: 1;
      background: #1d222e;
      border: 1px solid #2b3142;
      border-radius: 0 0 3px 3px;
      margin: 0 1px;
      position: relative;
      cursor: pointer;
      display: flex;
      align-items: flex-end;
      justify-content: center;
      padding-bottom: 4px;
      font-family: var(--mono);
      font-size: 9px;
      color: var(--muted);
    }
    .key-white.active {
      background: var(--stark);
      color: var(--stark-fg);
      font-weight: 700;
    }
    .key-black {
      width: 62%;
      height: 54%;
      background: #090b0f;
      border: 1px solid #2b3142;
      border-radius: 0 0 3px 3px;
      position: absolute;
      top: 0;
      right: -32%;
      z-index: 2;
      cursor: pointer;
    }
    .key-black.active {
      background: var(--mint);
      border-color: var(--mint);
    }

    /* Suggestion Rows */
    .suggest-card {
      background: var(--bg);
      border: 1px solid var(--border);
      border-radius: 4px;
      padding: 10px 12px;
      margin-bottom: 8px;
    }
    .suggest-top {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 4px;
      font-weight: 600;
      font-size: 12px;
    }
    .suggest-tag {
      font-family: var(--mono);
      font-size: 10px;
      color: var(--mint);
    }
    .suggest-desc { font-size: 11px; color: var(--muted); margin-bottom: 8px; }

    /* Dropzones & Outputs for Tools Tabs */
    .dropzone {
      border: 1px dashed var(--border-hi);
      border-radius: 4px;
      padding: 16px;
      text-align: center;
      background: var(--bg);
      cursor: pointer;
    }
    .dropzone:hover, .dropzone.dragover { border-color: var(--stark); background: var(--surface-2); }
    .dropzone input { display: none; }
    .dropzone .fname { font-family: var(--mono); font-size: 11px; color: var(--mint); margin-top: 6px; }
    .console-out {
      background: #08090c;
      border: 1px solid var(--border);
      border-radius: 4px;
      padding: 12px;
      font-family: var(--mono);
      font-size: 12px;
      line-height: 1.55;
      white-space: pre-wrap;
      color: #d4dae6;
      max-height: 360px;
      overflow-y: auto;
      margin-top: 12px;
      display: none;
    }
    .dl-bar { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 10px; }

    /* Footer */
    footer {
      border-top: 1px solid var(--border);
      background: var(--surface);
      padding: 10px 24px;
      display: flex;
      justify-content: space-between;
      font-family: var(--mono);
      font-size: 11px;
      color: var(--muted);
    }
  </style>
</head>
<body>

  <header class="topbar">
    <div class="brand">
      <span>Producer Reborn</span>
      <span class="sep">/</span>
      <span class="sub">Studio</span>
    </div>
    <nav class="nav-tabs">
      <button class="nav-tab active" onclick="switchTab('vibe', this)">Vibe-to-MIDI</button>
      <button class="nav-tab" onclick="switchTab('song', this)">Song Doctor</button>
      <button class="nav-tab" onclick="switchTab('mix', this)">Mix Doctor</button>
      <button class="nav-tab" onclick="switchTab('master', this)">AI Mastering</button>
      <button class="nav-tab" onclick="switchTab('release', this)">RouteNote</button>
    </nav>
    <div class="telemetry-badge">
      <span class="dot"></span>
      <span id="hdr-telemetry">130.0 BPM • 4/4</span>
    </div>
  </header>

  <main class="main">

    <!-- ================= TAB 1: VIBE-TO-MIDI ================= -->
    <section id="pane-vibe" class="tab-pane active">
      <div class="panel">
        <div class="panel-header">
          <span class="panel-title">Vibe &amp; Harmonic Profile</span>
          <div class="seg-group">
            <button class="seg-btn active" id="mode-btn-preset" onclick="setInputMode('preset')">Vibe Presets</button>
            <button class="seg-btn" id="mode-btn-custom" onclick="setInputMode('custom')">✎ Custom Chords</button>
          </div>
        </div>

        <!-- Preset Pills -->
        <div class="preset-strip" id="preset-strip">
          <button class="preset-btn active" data-preset="heartbreak" data-chords="F#m9 - Dmaj7#11 - A/C# - Eadd9" onclick="pickPreset(this)">Heartbreak Nostalgia</button>
          <button class="preset-btn" data-preset="late-night" data-chords="Dm9 - G13 - Cmaj9 - Am9" onclick="pickPreset(this)">Late Night Sadboy</button>
          <button class="preset-btn" data-preset="dreamy-bedroom" data-chords="Fmaj7 - Em7 - Dm9 - Cmaj7" onclick="pickPreset(this)">Dreamy Bedroom</button>
          <button class="preset-btn" data-preset="dark-trap" data-chords="D#m9 - C#sus2 - Bmaj7 - A#7" onclick="pickPreset(this)">Dark Emo Trap</button>
          <button class="preset-btn" data-preset="bedroom-indie" data-chords="Emaj7 - C#m7 - G#m7 - Badd9" onclick="pickPreset(this)">Bedroom Indie</button>
          <button class="preset-btn" data-preset="tokyo-drift" data-chords="Fm7 - Dbmaj7 - Bbm7 - C7alt" onclick="pickPreset(this)">Tokyo Drift</button>
          <button class="preset-btn" data-preset="dark-ambient" data-chords="Cm9 - Abmaj7#11 - Fm11 - G7sus4" onclick="pickPreset(this)">Dark Ambient</button>
          <button class="preset-btn" data-preset="uplifting-indie" data-chords="C - G - Am - F" onclick="pickPreset(this)">Uplifting Indie</button>
        </div>

        <!-- Custom Chords Input -->
        <div class="custom-row" id="custom-row">
          <input type="text" class="input-mono" id="custom-chords-input" value="F#m9 - Dmaj7#11 - A/C# - Eadd9" placeholder="Type any chords: e.g. Dm9 - G13 - Cmaj9 - Am9 or C - Cmaj7 - F - Fm6" onkeydown="if(event.key==='Enter') refreshPreview()" />
          <button class="btn-primary" onclick="refreshPreview()">Apply Chords</button>
          <div class="helper-chips">
            <button class="chip-btn" onclick="appendChord('Fm6')" title="Sad minor iv">+ Fm6 (Sad iv)</button>
            <button class="chip-btn" onclick="appendChord('Cmaj9')" title="Dreamy 9th">+ Cmaj9</button>
            <button class="chip-btn" onclick="appendChord('Asus2')" title="Open suspended">+ Asus2</button>
          </div>
        </div>

        <!-- Parameter Controls -->
        <div class="controls-row">
          <div class="ctrl-block">
            <span class="ctrl-label">Octave</span>
            <div class="stepper">
              <button onclick="stepOctave(-1)">-</button>
              <span id="octave-val">0</span>
              <button onclick="stepOctave(1)">+</button>
            </div>
          </div>

          <div class="ctrl-block">
            <span class="ctrl-label">Time Signature</span>
            <div class="seg-group" id="timesig-group">
              <button class="seg-btn active" data-ts="4/4" onclick="pickTimeSig(this)">4/4</button>
              <button class="seg-btn" data-ts="3/4" onclick="pickTimeSig(this)">3/4</button>
              <button class="seg-btn" data-ts="6/8" onclick="pickTimeSig(this)">6/8</button>
              <button class="seg-btn" data-ts="5/4" onclick="pickTimeSig(this)">5/4</button>
              <button class="seg-btn" data-ts="7/4" onclick="pickTimeSig(this)">7/4</button>
            </div>
          </div>

          <div class="ctrl-block">
            <span class="ctrl-label">Tempo</span>
            <div class="tempo-wrap">
              <input type="range" id="bpm-slider" min="65" max="180" value="130" oninput="onTempoChange(this.value)" />
              <span class="tempo-val" id="bpm-display">130.0 BPM</span>
            </div>
          </div>

          <div class="ctrl-block">
            <span class="ctrl-label">Preview Synth &amp; Transport</span>
            <div style="display:flex; gap:6px; align-items:center; flex-wrap:wrap;">
              <select class="ctrl-select" id="synth-tone">
                <option value="rhodes">Fender Rhodes Mk I</option>
                <option value="pad">Warm Analog Pad</option>
                <option value="pluck">Soft Keys Pluck</option>
              </select>
              <button class="btn-secondary" id="metro-btn" onclick="toggleMetronome()" style="height:30px; padding:0 10px; border-color:var(--mint); color:var(--mint);" title="Toggle Beat Metronome">⏱ Metro: ON</button>
              <button class="btn-primary" id="play-btn" onclick="togglePlay()" style="height:30px; padding:0 12px;">▶ Play</button>
              <button class="btn-secondary" onclick="stopPlayback()" style="height:30px; padding:0 10px;">■</button>
            </div>
          </div>
        </div>
      </div>

      <div class="workspace-grid">
        <!-- LEFT COLUMN -->
        <div>
          <div class="panel">
            <div class="panel-header">
              <span class="panel-title">Harmonic Piano Roll</span>
              <span class="panel-meta" id="pr-meta">4 Bars • 4/4 • Voice-Led</span>
            </div>
            <div class="bars-grid" id="bars-grid"></div>
            <div class="pianoroll-wrap">
              <div class="pianoroll-grid" id="pianoroll-grid"></div>
            </div>
          </div>

          <div class="panel">
            <div class="panel-header">
              <span class="panel-title">Rhythm Pattern &amp; Velocity</span>
              <span class="panel-meta" id="groove-meta">Swing: 18% • Humanize: ±10ms</span>
            </div>
            <div class="controls-row" style="border-top:none; padding-top:0; margin-bottom:8px;">
              <div class="ctrl-block">
                <span class="ctrl-label">Bassline Feel</span>
                <select class="ctrl-select" id="bass-style" onchange="refreshPreview()">
                  <option value="syncopated">Chill Syncopated</option>
                  <option value="eighth">Driving 8th-Note Pulse</option>
                  <option value="walking">Melodic Walking Bass</option>
                  <option value="none">No Bassline</option>
                </select>
              </div>
              <div class="ctrl-block">
                <span class="ctrl-label">Percussion Groove</span>
                <select class="ctrl-select" id="euclidean-groove" onchange="state.customStepsEdited=false; refreshPreview()">
                  <option value="">None (Keys + Bass only)</option>
                  <option value="5,16" selected>Afrobeat / Amapiano E(5,16)</option>
                  <option value="3,8">Reggaeton / Tresillo E(3,8)</option>
                  <option value="5,8">Syncopated Cinquillo E(5,8)</option>
                </select>
              </div>
              <div class="ctrl-block">
                <span class="ctrl-label">Swing (<span id="swing-val">18</span>%)</span>
                <input type="range" id="swing-slider" min="0" max="45" value="18" oninput="document.getElementById('swing-val').innerText=this.value; updateGrooveMeta()" onchange="refreshPreview()" />
              </div>
              <div class="ctrl-block">
                <span class="ctrl-label">Humanize (±<span id="hum-val">10</span>ms)</span>
                <input type="range" id="hum-slider" min="0" max="25" value="10" oninput="document.getElementById('hum-val').innerText=this.value; updateGrooveMeta()" onchange="refreshPreview()" />
              </div>
            </div>
            <div class="steps-grid" id="steps-grid"></div>
          </div>
        </div>

        <!-- RIGHT COLUMN -->
        <div>
          <div class="panel">
            <div class="panel-header">
              <span class="panel-title">Export MIDI</span>
              <span class="panel-meta" id="midi-meta">Standard Type-1</span>
            </div>
            <button class="btn-primary" style="width:100%; margin-bottom:8px; height:38px;" onclick="exportMidi(this)">⬇ Export .MID File</button>
            <button class="btn-secondary" style="width:100%;" onclick="rerollInversion()">🎲 Reroll Voice-Leading Inversion</button>
            <div id="midi-dl-bar" class="dl-bar"></div>
          </div>

          <div class="panel">
            <div class="panel-header">
              <span class="panel-title">Chord Suggestions</span>
              <span class="panel-meta">Modal Borrow</span>
            </div>
            <div id="suggestions-list">
              <div class="suggest-card">
                <div class="suggest-top">
                  <span>Fm6 (Borrowed Minor iv)</span>
                  <span class="suggest-tag">Nostalgic Lift</span>
                </div>
                <div class="suggest-desc">Adds bittersweet emotional tension before looping back to Bar 1.</div>
                <button class="btn-secondary" style="padding:4px 10px; font-size:11px;" onclick="applySuggestion('Fm6')">Apply to Bar 4</button>
              </div>
              <div class="suggest-card">
                <div class="suggest-top">
                  <span>Bm7 (Dorian IV)</span>
                  <span class="suggest-tag">Neo-Soul</span>
                </div>
                <div class="suggest-desc">Smooth natural-6th lift ideal for R&amp;B and bedroom-pop turnarounds.</div>
                <button class="btn-secondary" style="padding:4px 10px; font-size:11px;" onclick="applySuggestion('Bm7')">Apply to Bar 4</button>
              </div>
              <div class="suggest-card">
                <div class="suggest-top">
                  <span>C#7alt (Dominant)</span>
                  <span class="suggest-tag">Resolution Pull</span>
                </div>
                <div class="suggest-desc">Strong dominant tension pulling back strongly to Bar 1.</div>
                <button class="btn-secondary" style="padding:4px 10px; font-size:11px;" onclick="applySuggestion('C#7alt')">Apply to Bar 4</button>
              </div>
            </div>
          </div>

          <div class="panel">
            <div class="panel-header">
              <span class="panel-title">Current Voicing</span>
              <span class="panel-meta" id="voicing-chord-name">F#m9</span>
            </div>
            <div class="kbd-wrap" id="mini-kbd"></div>
            <div class="panel-meta" id="voicing-notes-text">Notes: C#4 · E4 · F#4 · G#4 · A4</div>
          </div>

          <div class="panel">
            <div class="panel-header">
              <span class="panel-title">Algorithmic Provenance</span>
            </div>
            <div style="font-size:11.5px; color:var(--muted);">
              Synthesized locally with mathematical voice-leading constraints. 100% royalty-free and safe for commercial streaming platforms.
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ================= TAB 2: SONG & STEM DOCTOR ================= -->
    <section id="pane-song" class="tab-pane">
      <div class="panel">
        <div class="panel-header">
          <span class="panel-title">Song &amp; Stem Pitch Doctor (Basic Pitch ONNX + Demucs + pYIN)</span>
        </div>
        <div class="dropzone" onclick="this.querySelector('input').click()" ondragover="dragOver(event,this)" ondragleave="dragLeave(this)" ondrop="dropFile(event,this,'analyze-song')">
          <div>Drop Full Track or Audio Loop (MP3 / WAV)</div>
          <div class="fname" id="name-analyze-song">Click or drag file here</div>
          <input type="file" accept="audio/*" onchange="uploadInput(this,'analyze-song')" />
        </div>
        <div style="display:flex; gap:8px; margin-top:12px; flex-wrap:wrap;">
          <button class="btn-primary" onclick="runAnalyze('chords', this)">Extract BPM, Chords &amp; MIDI</button>
          <button class="btn-secondary" onclick="runAnalyze('stems', this)">Audit Vocal &amp; Bass Intonation (Cents)</button>
        </div>
        <pre id="out-analyze" class="console-out"></pre>
        <div id="dl-analyze" class="dl-bar"></div>
      </div>
    </section>

    <!-- ================= TAB 3: MIX DOCTOR ================= -->
    <section id="pane-mix" class="tab-pane">
      <div class="panel">
        <div class="panel-header">
          <span class="panel-title">Mix Doctor (Pre-Mastering Audit)</span>
        </div>
        <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(240px,1fr)); gap:10px; margin-bottom:12px;">
          <div class="dropzone" onclick="this.querySelector('input').click()" ondragover="dragOver(event,this)" ondragleave="dragLeave(this)" ondrop="dropFile(event,this,'mix-target')">
            <div>Drop Pre-Master Mix (WAV/FLAC/MP3)</div>
            <div class="fname" id="name-mix-target">Required</div>
            <input type="file" accept="audio/*" onchange="uploadInput(this,'mix-target')" />
          </div>
          <div class="dropzone" onclick="this.querySelector('input').click()" ondragover="dragOver(event,this)" ondragleave="dragLeave(this)" ondrop="dropFile(event,this,'mix-ref')">
            <div>Drop Reference Track (Optional)</div>
            <div class="fname" id="name-mix-ref">Optional</div>
            <input type="file" accept="audio/*" onchange="uploadInput(this,'mix-ref')" />
          </div>
        </div>
        <button class="btn-primary" onclick="runMixCheck(this)">Run Mix Diagnostic</button>
        <pre id="out-mix" class="console-out"></pre>
      </div>
    </section>

    <!-- ================= TAB 4: AI MASTERING ================= -->
    <section id="pane-master" class="tab-pane">
      <div class="panel">
        <div class="panel-header">
          <span class="panel-title">AI Reference Mastering (Matchering 2.0.6 + EBU R128)</span>
        </div>
        <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(240px,1fr)); gap:10px; margin-bottom:12px;">
          <div class="dropzone" onclick="this.querySelector('input').click()" ondragover="dragOver(event,this)" ondragleave="dragLeave(this)" ondrop="dropFile(event,this,'master-target')">
            <div>Drop Pre-Master Mix (WAV/FLAC)</div>
            <div class="fname" id="name-master-target">Required</div>
            <input type="file" accept="audio/*" onchange="uploadInput(this,'master-target')" />
          </div>
          <div class="dropzone" onclick="this.querySelector('input').click()" ondragover="dragOver(event,this)" ondragleave="dragLeave(this)" ondrop="dropFile(event,this,'master-ref')">
            <div>Drop Commercial Reference Track</div>
            <div class="fname" id="name-master-ref">Required</div>
            <input type="file" accept="audio/*" onchange="uploadInput(this,'master-ref')" />
          </div>
        </div>
        <button class="btn-primary" onclick="runMaster(this)">Master to 24-bit WAV + 16-bit FLAC</button>
        <pre id="out-master" class="console-out"></pre>
        <div id="dl-master" class="dl-bar"></div>
      </div>
    </section>

    <!-- ================= TAB 5: ROUTENOTE & TIMELINE ================= -->
    <section id="pane-release" class="tab-pane">
      <div class="panel">
        <div class="panel-header">
          <span class="panel-title">RouteNote Pre-Flight Validator &amp; Auto-Fix</span>
        </div>
        <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(240px,1fr)); gap:10px; margin-bottom:12px;">
          <div class="dropzone" onclick="this.querySelector('input').click()" ondragover="dragOver(event,this)" ondragleave="dragLeave(this)" ondrop="dropFile(event,this,'rn-audio')">
            <div>Drop Master Audio (WAV/FLAC/MP3)</div>
            <div class="fname" id="name-rn-audio">Optional</div>
            <input type="file" accept="audio/*" onchange="uploadInput(this,'rn-audio')" />
          </div>
          <div class="dropzone" onclick="this.querySelector('input').click()" ondragover="dragOver(event,this)" ondragleave="dragLeave(this)" ondrop="dropFile(event,this,'rn-art')">
            <div>Drop Cover Artwork (PNG/JPG)</div>
            <div class="fname" id="name-rn-art">Optional</div>
            <input type="file" accept="image/*" onchange="uploadInput(this,'rn-art')" />
          </div>
        </div>
        <label style="display:flex; align-items:center; gap:8px; margin-bottom:12px; cursor:pointer; font-size:12px;">
          <input type="checkbox" id="rn-fix" checked /> Auto-Fix non-compliant files (Export 16-bit 44.1kHz FLAC &amp; 3000×3000 RGB JPG)
        </label>
        <button class="btn-primary" onclick="runValidate(this)">Validate &amp; Auto-Fix Assets</button>
        <pre id="out-rn" class="console-out"></pre>
        <div id="dl-rn" class="dl-bar"></div>
      </div>

      <div class="panel">
        <div class="panel-header">
          <span class="panel-title">H-28 Release Countdown &amp; Calendar Export</span>
        </div>
        <div style="display:flex; gap:10px; flex-wrap:wrap; margin-bottom:12px;">
          <input type="text" class="input-mono" id="tl-title" placeholder="Track or EP Title" style="max-width:320px;" />
          <input type="date" class="ctrl-input" id="tl-date" value="2026-12-31" />
          <button class="btn-primary" onclick="runTimeline(this)">Generate .ICS Calendar</button>
        </div>
        <pre id="out-tl" class="console-out"></pre>
        <div id="dl-tl" class="dl-bar"></div>
      </div>
    </section>

  </main>

  <footer>
    <span>Audio: Local Python + Basic Pitch ONNX + Matchering 2.0.6</span>
    <span>Producer Reborn</span>
  </footer>

<script>
const state = {
  inputMode: "preset",
  preset: "heartbreak",
  customChords: "F#m9 - Dmaj7#11 - A/C# - Eadd9",
  octave: 0,
  timeSignature: "4/4",
  beatsPerBar: 4,
  bpm: 130,
  reroll: 0,
  metronome: true,
  customStepsEdited: false,
  stepVelocities: [],
  selectedBarIdx: 0,
  barsData: [],
  uploaded: {}
};

// Web Audio API Multi-Track Synth (Keys, Bass, Percussion, Metronome)
let audioCtx = null;
let noiseBuffer = null;
let isPlaying = false;
let playTimer = null;
let uiTimers = [];

function ensureAudioCtx() {
  if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  if (audioCtx.state === 'suspended') audioCtx.resume();
  if (!noiseBuffer) {
    const bufSize = audioCtx.sampleRate * 0.2;
    noiseBuffer = audioCtx.createBuffer(1, bufSize, audioCtx.sampleRate);
    const out = noiseBuffer.getChannelData(0);
    for (let i = 0; i < bufSize; i++) out[i] = Math.random() * 2 - 1;
  }
}

function midiToFreq(m) { return 440 * Math.pow(2, (m - 69) / 12); }

function playTone(midiNote, startTime, duration) {
  ensureAudioCtx();
  const mode = document.getElementById('synth-tone').value;
  const freq = midiToFreq(midiNote);

  const osc1 = audioCtx.createOscillator();
  const osc2 = audioCtx.createOscillator();
  const filter = audioCtx.createBiquadFilter();
  const gain = audioCtx.createGain();

  if (mode === 'pad') {
    osc1.type = 'sawtooth';
    osc2.type = 'triangle';
    osc2.detune.value = 6;
    filter.type = 'lowpass';
    filter.frequency.value = 1200;
    gain.gain.setValueAtTime(0.001, startTime);
    gain.gain.linearRampToValueAtTime(0.055, startTime + 0.18);
    gain.gain.exponentialRampToValueAtTime(0.001, startTime + duration);
  } else if (mode === 'pluck') {
    osc1.type = 'triangle';
    osc2.type = 'sine';
    filter.type = 'lowpass';
    filter.frequency.setValueAtTime(3200, startTime);
    filter.frequency.exponentialRampToValueAtTime(500, startTime + 0.4);
    gain.gain.setValueAtTime(0.001, startTime);
    gain.gain.linearRampToValueAtTime(0.10, startTime + 0.012);
    gain.gain.exponentialRampToValueAtTime(0.001, startTime + Math.min(duration, 0.9));
  } else {
    osc1.type = 'sine';
    osc2.type = 'triangle';
    osc2.detune.value = 3.5;
    filter.type = 'lowpass';
    filter.frequency.setValueAtTime(2000, startTime);
    filter.frequency.exponentialRampToValueAtTime(700, startTime + 0.6);
    gain.gain.setValueAtTime(0.001, startTime);
    gain.gain.linearRampToValueAtTime(0.085, startTime + 0.015);
    gain.gain.exponentialRampToValueAtTime(0.001, startTime + duration);
  }

  osc1.frequency.setValueAtTime(freq, startTime);
  osc2.frequency.setValueAtTime(freq, startTime);
  osc1.connect(filter);
  osc2.connect(filter);
  filter.connect(gain);
  gain.connect(audioCtx.destination);

  osc1.start(startTime);
  osc2.start(startTime);
  osc1.stop(startTime + duration + 0.05);
  osc2.stop(startTime + duration + 0.05);
}

function playBassTone(midiNote, startTime, duration, velocity = 95) {
  ensureAudioCtx();
  const freq = midiToFreq(midiNote);
  const oscSub = audioCtx.createOscillator();
  const oscHarm = audioCtx.createOscillator();
  const filter = audioCtx.createBiquadFilter();
  const gain = audioCtx.createGain();

  oscSub.type = 'sine';
  oscHarm.type = 'triangle';
  oscSub.frequency.setValueAtTime(freq, startTime);
  oscHarm.frequency.setValueAtTime(freq * 2, startTime);

  filter.type = 'lowpass';
  filter.frequency.setValueAtTime(480, startTime);
  filter.frequency.exponentialRampToValueAtTime(160, startTime + Math.min(duration, 0.45));

  const amp = 0.22 * (velocity / 110);
  gain.gain.setValueAtTime(0.001, startTime);
  gain.gain.linearRampToValueAtTime(amp, startTime + 0.012);
  gain.gain.exponentialRampToValueAtTime(0.001, startTime + Math.max(0.12, duration));

  oscSub.connect(filter);
  oscHarm.connect(filter);
  filter.connect(gain);
  gain.connect(audioCtx.destination);

  oscSub.start(startTime);
  oscHarm.start(startTime);
  oscSub.stop(startTime + duration + 0.05);
  oscHarm.stop(startTime + duration + 0.05);
}

function playPercHit(startTime, velocity = 90) {
  ensureAudioCtx();
  const src = audioCtx.createBufferSource();
  src.buffer = noiseBuffer;
  const hp = audioCtx.createBiquadFilter();
  hp.type = 'highpass';
  hp.frequency.setValueAtTime(6200, startTime);

  const gain = audioCtx.createGain();
  const amp = 0.14 * (velocity / 115);
  gain.gain.setValueAtTime(0.001, startTime);
  gain.gain.linearRampToValueAtTime(amp, startTime + 0.003);
  gain.gain.exponentialRampToValueAtTime(0.001, startTime + 0.055);

  src.connect(hp);
  hp.connect(gain);
  gain.connect(audioCtx.destination);

  src.start(startTime);
  src.stop(startTime + 0.07);
}

function playMetroClick(startTime, accentType = 'normal') {
  ensureAudioCtx();
  const osc = audioCtx.createOscillator();
  const gain = audioCtx.createGain();
  osc.type = 'sine';
  const freq = accentType === 'downbeat' ? 1320 : accentType === 'secondary' ? 990 : 780;
  const amp = accentType === 'downbeat' ? 0.16 : 0.09;

  osc.frequency.setValueAtTime(freq, startTime);
  osc.frequency.exponentialRampToValueAtTime(freq * 0.72, startTime + 0.025);

  gain.gain.setValueAtTime(0.001, startTime);
  gain.gain.linearRampToValueAtTime(amp, startTime + 0.002);
  gain.gain.exponentialRampToValueAtTime(0.001, startTime + 0.032);

  osc.connect(gain);
  gain.connect(audioCtx.destination);
  osc.start(startTime);
  osc.stop(startTime + 0.04);
}

function toggleMetronome() {
  state.metronome = !state.metronome;
  const btn = document.getElementById('metro-btn');
  btn.innerText = state.metronome ? "⏱ Metro: ON" : "⏱ Metro: OFF";
  btn.style.borderColor = state.metronome ? "var(--mint)" : "var(--border)";
  btn.style.color = state.metronome ? "var(--mint)" : "var(--muted)";
}

function playChord(pitches, duration = 1.2) {
  ensureAudioCtx();
  const now = audioCtx.currentTime;
  const humSec = parseFloat(document.getElementById('hum-slider').value) / 1000.0;
  pitches.forEach((p, idx) => {
    const jitter = (Math.random() * 2 - 1) * humSec;
    playTone(p, Math.max(now, now + idx * 0.012 + jitter), duration);
  });
}

function clearUiTimers() {
  uiTimers.forEach(t => clearTimeout(t));
  uiTimers = [];
  document.querySelectorAll('.step-cell.playing-step').forEach(el => el.classList.remove('playing-step'));
}

function togglePlay() {
  if (isPlaying) { stopPlayback(); return; }
  if (!state.barsData.length) return;
  ensureAudioCtx();
  isPlaying = true;
  document.getElementById('play-btn').innerText = "⏸ Playing";
  let barCounter = 0;

  function scheduleNextBar() {
    if (!isPlaying) return;
    clearUiTimers();
    const barIdx = barCounter % state.barsData.length;
    const bar = state.barsData[barIdx];
    state.selectedBarIdx = barIdx;
    renderBarsAndKeyboard(true);

    const secPerBeat = 60.0 / state.bpm;
    const beatsPerBar = state.beatsPerBar || 4.0;
    const barSec = secPerBeat * beatsPerBar;
    const humSec = parseFloat(document.getElementById('hum-slider').value) / 1000.0;
    const swingPct = parseFloat(document.getElementById('swing-slider').value);
    const barStart = audioCtx.currentTime + 0.03;

    // 1. Schedule Keys (Chord)
    bar.pitches.forEach((p, idx) => {
      const jitter = (Math.random() * 2 - 1) * humSec;
      playTone(p, Math.max(audioCtx.currentTime, barStart + idx * 0.01 + jitter), Math.max(0.4, barSec * 0.92));
    });

    // 2. Schedule Bassline Events
    if (bar.bass_events && bar.bass_events.length) {
      bar.bass_events.forEach(ev => {
        const bStart = barStart + (ev.beat * secPerBeat);
        const bDur = Math.max(0.12, ev.dur_beats * secPerBeat);
        playBassTone(ev.pitch, bStart, bDur, ev.vel || 95);
      });
    }

    // 3. Schedule Percussion Steps with Swing & Humanize
    const steps = state.stepVelocities;
    if (steps && steps.length) {
      const stepDur = barSec / steps.length;
      steps.forEach((vel, sIdx) => {
        const swingShift = (sIdx % 2 === 1 && swingPct > 0) ? (swingPct / 100.0) * (stepDur * 0.35) : 0;
        const humShift = (Math.random() * 2 - 1) * (humSec * 0.5);
        const hitTime = Math.max(barStart, barStart + sIdx * stepDur + swingShift + humShift);
        if (vel > 0) playPercHit(hitTime, vel);

        const delayMs = Math.max(0, (hitTime - audioCtx.currentTime) * 1000);
        uiTimers.push(setTimeout(() => {
          if (!isPlaying) return;
          document.querySelectorAll('.step-cell').forEach((el, i) => {
            el.classList.toggle('playing-step', i === sIdx);
          });
        }, delayMs));
      });
    }

    // 4. Schedule Metronome Clicks & Beat Readout
    const numClicks = state.timeSignature === '6/8' ? 6 : Math.round(beatsPerBar);
    const clickSpacing = state.timeSignature === '6/8' ? secPerBeat * 0.5 : secPerBeat;
    for (let c = 0; c < numClicks; c++) {
      const cTime = barStart + (c * clickSpacing);
      let accent = 'normal';
      if (c === 0) accent = 'downbeat';
      else if ((state.timeSignature === '6/8' && c === 3) || (state.timeSignature === '7/4' && c === 4) || (state.timeSignature === '5/4' && c === 3)) {
        accent = 'secondary';
      }
      if (state.metronome) playMetroClick(cTime, accent);

      const cDelayMs = Math.max(0, (cTime - audioCtx.currentTime) * 1000);
      uiTimers.push(setTimeout(() => {
        if (!isPlaying) return;
        document.getElementById('hdr-telemetry').innerText = `${state.bpm.toFixed(1)} BPM • ${state.timeSignature} • Beat ${c + 1}/${numClicks}`;
      }, cDelayMs));
    }

    barCounter++;
    playTimer = setTimeout(scheduleNextBar, barSec * 1000);
  }
  scheduleNextBar();
}

function stopPlayback() {
  isPlaying = false;
  if (playTimer) clearTimeout(playTimer);
  clearUiTimers();
  document.getElementById('play-btn').innerText = "▶ Play";
  updateTelemetry();
  renderBarsAndKeyboard(false);
}

// Navigation & Controls
function switchTab(id, btn) {
  document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-tab').forEach(b => b.classList.remove('active'));
  document.getElementById('pane-' + id).classList.add('active');
  btn.classList.add('active');
}

function setInputMode(mode) {
  state.inputMode = mode;
  document.getElementById('mode-btn-preset').classList.toggle('active', mode === 'preset');
  document.getElementById('mode-btn-custom').classList.toggle('active', mode === 'custom');
  document.getElementById('preset-strip').style.display = mode === 'preset' ? 'flex' : 'none';
  document.getElementById('custom-row').classList.toggle('active', mode === 'custom');
  refreshPreview();
}

function pickPreset(el) {
  document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
  el.classList.add('active');
  state.preset = el.dataset.preset;
  state.customChords = el.dataset.chords;
  document.getElementById('custom-chords-input').value = state.customChords;
  state.reroll = 0;
  refreshPreview();
}

function appendChord(chord) {
  const inp = document.getElementById('custom-chords-input');
  inp.value = inp.value.trim() ? inp.value.trim() + " - " + chord : chord;
  refreshPreview();
}

function applySuggestion(chord) {
  setInputMode('custom');
  const inp = document.getElementById('custom-chords-input');
  const tokens = inp.value.replace(/\|/g, ' ').replace(/,/g, ' ').split(/\s+-\s+|\s+/).filter(Boolean);
  if (tokens.length >= 2) {
    tokens[tokens.length - 1] = chord;
    inp.value = tokens.join(' - ');
  } else {
    inp.value = chord;
  }
  refreshPreview();
  setTimeout(() => {
    if (state.barsData.length) {
      state.selectedBarIdx = state.barsData.length - 1;
      renderBarsAndKeyboard(false);
      playChord(state.barsData[state.selectedBarIdx].pitches, 1.1);
    }
  }, 80);
}

function stepOctave(delta) {
  state.octave = Math.max(-2, Math.min(2, state.octave + delta));
  document.getElementById('octave-val').innerText = (state.octave > 0 ? "+" : "") + state.octave;
  refreshPreview();
}

function pickTimeSig(el) {
  document.querySelectorAll('#timesig-group .seg-btn').forEach(b => b.classList.remove('active'));
  el.classList.add('active');
  state.timeSignature = el.dataset.ts;
  state.customStepsEdited = false;
  updateTelemetry();
  refreshPreview();
}

function onTempoChange(val) {
  state.bpm = parseFloat(val);
  document.getElementById('bpm-display').innerText = state.bpm.toFixed(1) + " BPM";
  updateTelemetry();
  refreshPreview();
}

function updateTelemetry() {
  document.getElementById('hdr-telemetry').innerText = `${state.bpm.toFixed(1)} BPM • ${state.timeSignature}`;
}

function updateGrooveMeta() {
  const sw = document.getElementById('swing-slider').value;
  const hm = document.getElementById('hum-slider').value;
  document.getElementById('groove-meta').innerText = `Swing: ${sw}% • Humanize: ±${hm}ms`;
}

function rerollInversion() {
  state.reroll = (state.reroll + 1) % 8;
  refreshPreview();
}

async function refreshPreview() {
  const chordsVal = state.inputMode === 'custom'
    ? document.getElementById('custom-chords-input').value
    : "";
  const res = await fetch('/api/preview_voicing', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      preset: state.preset,
      chords: chordsVal,
      bpm: state.bpm,
      time_signature: state.timeSignature,
      octave_offset: state.octave,
      reroll: state.reroll,
      bass: document.getElementById('bass-style').value,
      euclidean: document.getElementById('euclidean-groove').value,
      custom_steps: state.customStepsEdited ? state.stepVelocities : null,
      swing: document.getElementById('swing-slider').value,
      humanize_ms: document.getElementById('hum-slider').value
    })
  });
  const data = await res.json();
  if (data.ok) {
    state.barsData = data.bars;
    state.beatsPerBar = data.beats_per_bar || 4.0;
    if (!state.customStepsEdited) {
      state.stepVelocities = data.step_velocities && data.step_velocities.length
        ? data.step_velocities
        : Array(state.timeSignature === '7/4' ? 14 : 16).fill(0);
    }
    if (state.selectedBarIdx >= state.barsData.length) state.selectedBarIdx = 0;
    document.getElementById('pr-meta').innerText = `${state.barsData.length} Bars • ${state.timeSignature} • Voice-Led`;
    renderBarsAndKeyboard(false);
    renderPianoRoll();
    renderStepsStrip();
  }
}

function renderBarsAndKeyboard(isLoopPlaying) {
  const grid = document.getElementById('bars-grid');
  grid.innerHTML = '';
  state.barsData.forEach((b, idx) => {
    const div = document.createElement('div');
    div.className = 'bar-card' + (idx === state.selectedBarIdx ? ' active' : '') + (isLoopPlaying && idx === state.selectedBarIdx ? ' playing' : '');
    div.onclick = () => {
      state.selectedBarIdx = idx;
      renderBarsAndKeyboard(false);
      playChord(b.pitches, 1.0);
    };
    div.innerHTML = `
      <div class="bar-top"><span>Bar ${b.bar}</span><span>${b.duration_sec}s</span></div>
      <div class="bar-chord">${b.symbol}</div>
      <div class="bar-notes">${b.notes.join(' · ')}</div>
    `;
    grid.appendChild(div);
  });

  // Update Mini Piano Keyboard (C3=48 to B4=71)
  const activeBar = state.barsData[state.selectedBarIdx];
  const activePitches = new Set(activeBar ? activeBar.pitches : []);
  document.getElementById('voicing-chord-name').innerText = activeBar ? activeBar.symbol : '-';
  document.getElementById('voicing-notes-text').innerText = activeBar ? ("Notes: " + activeBar.notes.join(' · ')) : '';

  const kbd = document.getElementById('mini-kbd');
  kbd.innerHTML = '';
  const whiteNotes = [0, 2, 4, 5, 7, 9, 11];
  const hasBlack = { 0: 1, 2: 3, 5: 6, 7: 8, 9: 10 };
  const names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];

  for (let oct = 3; oct <= 4; oct++) {
    whiteNotes.forEach(pc => {
      const midi = 12 * (oct + 1) + pc;
      const wKey = document.createElement('div');
      wKey.className = 'key-white' + (activePitches.has(midi) ? ' active' : '');
      wKey.innerText = names[pc] + oct;
      wKey.onclick = (e) => { e.stopPropagation(); playTone(midi, ensureTime(), 0.7); };

      if (hasBlack[pc] !== undefined) {
        const bMidi = 12 * (oct + 1) + hasBlack[pc];
        const bKey = document.createElement('div');
        bKey.className = 'key-black' + (activePitches.has(bMidi) ? ' active' : '');
        bKey.onclick = (e) => { e.stopPropagation(); playTone(bMidi, ensureTime(), 0.7); };
        wKey.appendChild(bKey);
      }
      kbd.appendChild(wKey);
    });
  }
}

function ensureTime() { ensureAudioCtx(); return audioCtx.currentTime; }

function midiToName(midi) {
  const names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
  return names[midi % 12] + (Math.floor(midi / 12) - 1);
}

function isBlackKey(midi) {
  return [1, 3, 6, 8, 10].includes(midi % 12);
}

function renderPianoRoll() {
  const pr = document.getElementById('pianoroll-grid');
  pr.innerHTML = '';
  if (!state.barsData.length) return;

  const allPitches = state.barsData.flatMap(b => b.pitches);
  const minPitch = Math.min(...allPitches) - 1;
  const maxPitch = Math.max(...allPitches) + 1;
  const numBars = state.barsData.length;

  pr.style.gridTemplateColumns = `48px repeat(${numBars}, minmax(100px, 1fr))`;

  // Header row
  const corner = document.createElement('div');
  corner.className = 'pr-header-cell';
  corner.innerText = 'PITCH';
  pr.appendChild(corner);
  state.barsData.forEach(b => {
    const h = document.createElement('div');
    h.className = 'pr-header-cell';
    h.innerText = `BAR ${b.bar} (${b.symbol})`;
    pr.appendChild(h);
  });

  // Pitch rows from top (maxPitch) to bottom (minPitch)
  for (let pitch = maxPitch; pitch >= minPitch; pitch--) {
    const black = isBlackKey(pitch);
    const ruler = document.createElement('div');
    ruler.className = 'pr-ruler-cell' + (black ? ' black-key' : '');
    ruler.innerText = midiToName(pitch);
    pr.appendChild(ruler);

    state.barsData.forEach(b => {
      const slot = document.createElement('div');
      slot.className = 'pr-slot' + (black ? ' black-row' : '');
      const idx = b.pitches.indexOf(pitch);
      if (idx !== -1) {
        const isTop = idx === b.pitches.length - 1;
        const isLowest = idx === 0;
        const noteEl = document.createElement('div');
        noteEl.className = 'pr-note' + (isTop ? ' accent' : '');
        noteEl.innerHTML = `<span>${b.notes[idx]}</span><span>${isLowest ? 'Root/Bass' : isTop ? 'Top' : ''}</span>`;
        noteEl.onclick = () => playTone(pitch, ensureTime(), 0.7);
        slot.appendChild(noteEl);
      }
      pr.appendChild(slot);
    });
  }
}

function renderStepsStrip() {
  const strip = document.getElementById('steps-grid');
  const stepArr = state.stepVelocities && state.stepVelocities.length
    ? state.stepVelocities
    : Array(16).fill(0);
  strip.style.gridTemplateColumns = `repeat(${Math.min(16, stepArr.length)}, 1fr)`;
  strip.innerHTML = '';
  stepArr.forEach((vel, idx) => {
    const cell = document.createElement('div');
    cell.className = 'step-cell' + (vel >= 105 ? ' accent' : vel > 0 ? ' hit' : '');
    cell.title = 'Click to toggle step: Off -> Hit (82) -> Accent (115)';
    cell.onclick = () => {
      state.customStepsEdited = true;
      const cur = state.stepVelocities[idx] || 0;
      const next = cur === 0 ? 82 : cur < 105 ? 115 : 0;
      state.stepVelocities[idx] = next;
      renderStepsStrip();
      if (next > 0) playPercHit(ensureTime(), next);
    };
    cell.innerHTML = `<div>${String(idx + 1).padStart(2, '0')}</div><div>${vel > 0 ? vel : '-'}</div>`;
    strip.appendChild(cell);
  });
}

async function exportMidi(btn) {
  const chordsVal = state.inputMode === 'custom' ? document.getElementById('custom-chords-input').value : "";
  const orig = btn.innerText;
  btn.disabled = true; btn.innerText = "Generating...";
  const res = await fetch('/api/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      action: 'vibe_midi',
      params: {
        preset: state.preset,
        chords: chordsVal,
        bpm: state.bpm,
        time_signature: state.timeSignature,
        octave_offset: state.octave,
        reroll: state.reroll,
        swing: document.getElementById('swing-slider').value,
        humanize_ms: document.getElementById('hum-slider').value,
        bass: document.getElementById('bass-style').value,
        groove: document.getElementById('euclidean-groove').value,
        custom_steps: state.customStepsEdited ? state.stepVelocities : null
      }
    })
  });
  const data = await res.json();
  btn.disabled = false; btn.innerText = orig;
  const dl = document.getElementById('midi-dl-bar');
  dl.innerHTML = '';
  if (data.downloads && data.downloads.length) {
    data.downloads.forEach(d => {
      const a = document.createElement('a');
      a.href = d.url; a.className = 'btn-primary';
      a.style.width = '100%';
      a.innerText = '⬇ Download ' + d.label;
      dl.appendChild(a);
    });
    document.getElementById('midi-meta').innerText = 'Ready • ' + data.downloads[0].label;
  }
}

// Generic Upload & Tool Runners
function dragOver(e, el) { e.preventDefault(); el.classList.add('dragover'); }
function dragLeave(el) { el.classList.remove('dragover'); }
function dropFile(e, el, key) {
  e.preventDefault(); el.classList.remove('dragover');
  if (e.dataTransfer.files.length) uploadFile(e.dataTransfer.files[0], key);
}
function uploadInput(input, key) {
  if (input.files.length) uploadFile(input.files[0], key);
}

async function uploadFile(file, key) {
  const lbl = document.getElementById('name-' + key);
  lbl.innerText = "Uploading " + file.name + "...";
  const res = await fetch('/api/upload', {
    method: 'POST',
    headers: { 'X-Filename': encodeURIComponent(file.name) },
    body: file
  });
  const data = await res.json();
  if (data.path) {
    state.uploaded[key] = data.path;
    lbl.innerText = "✓ " + data.name;
  } else {
    lbl.innerText = "Upload failed";
  }
}

async function runTool(action, params, btn, outId, dlId) {
  const orig = btn.innerText;
  btn.disabled = true; btn.innerText = "Running...";
  const out = document.getElementById(outId);
  out.style.display = "block"; out.innerText = "Processing locally...";
  if (dlId) document.getElementById(dlId).innerHTML = "";
  try {
    const res = await fetch('/api/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action, params })
    });
    const data = await res.json();
    out.innerText = data.output || data.error || "Done.";
    if (dlId && data.downloads) {
      const box = document.getElementById(dlId);
      data.downloads.forEach(d => {
        const a = document.createElement('a');
        a.href = d.url; a.className = 'btn-secondary';
        a.innerText = "⬇ " + d.label;
        box.appendChild(a);
      });
    }
  } finally {
    btn.disabled = false; btn.innerText = orig;
  }
}

function runAnalyze(mode, btn) {
  if (!state.uploaded['analyze-song']) return alert("Upload an audio file first.");
  runTool(mode === 'chords' ? 'analyze_audio' : 'stem_advisor', { song: state.uploaded['analyze-song'] }, btn, 'out-analyze', 'dl-analyze');
}
function runMixCheck(btn) {
  if (!state.uploaded['mix-target']) return alert("Upload a mix file first.");
  runTool('mix_check', { mix: state.uploaded['mix-target'], reference: state.uploaded['mix-ref'] || null }, btn, 'out-mix', null);
}
function runMaster(btn) {
  if (!state.uploaded['master-target'] || !state.uploaded['master-ref']) return alert("Upload both target mix and reference track.");
  runTool('master_track', { target: state.uploaded['master-target'], reference: state.uploaded['master-ref'] }, btn, 'out-master', 'dl-master');
}
function runValidate(btn) {
  if (!state.uploaded['rn-audio'] && !state.uploaded['rn-art']) return alert("Upload audio and/or cover artwork.");
  runTool('validate_release', { audio: state.uploaded['rn-audio'] || null, artwork: state.uploaded['rn-art'] || null, fix: document.getElementById('rn-fix').checked }, btn, 'out-rn', 'dl-rn');
}
function runTimeline(btn) {
  const title = document.getElementById('tl-title').value.trim() || "New Single";
  const date = document.getElementById('tl-date').value;
  runTool('release_timeline', { title, date }, btn, 'out-tl', 'dl-tl');
}

// Init
refreshPreview();
</script>
</body>
</html>
"""


class StudioHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def _send_json(self, code: int, payload: dict):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/":
            body = HTML_PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path == "/api/download":
            qs = parse_qs(parsed.query)
            rel_file = qs.get("file", [""])[0]
            target = (WORKSPACE_ROOT / rel_file).resolve()
            if not str(target).startswith(str(WORKSPACE_ROOT.resolve())) or not target.is_file():
                self.send_error(404, "File not found")
                return
            data = target.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Disposition", f'attachment; filename="{target.name}"')
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        self.send_error(404, "Not found")

    def do_POST(self):
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", "0"))

        if parsed.path == "/api/upload":
            raw_name = unquote(self.headers.get("X-Filename", "upload.bin"))
            fname = safe_filename(raw_name)
            dest = UPLOADS_DIR / fname
            with open(dest, "wb") as f:
                remaining = length
                while remaining > 0:
                    chunk = self.rfile.read(min(65536, remaining))
                    if not chunk:
                        break
                    f.write(chunk)
                    remaining -= len(chunk)
            self._send_json(200, {"path": str(dest), "name": fname})
            return

        if parsed.path == "/api/preview_voicing":
            raw = self.rfile.read(length).decode("utf-8")
            req = json.loads(raw)
            chords_str = (req.get("chords") or "").strip()
            preset = req.get("preset", "heartbreak")
            bpm = float(req.get("bpm", 130.0))
            time_sig = req.get("time_signature", "4/4")
            octave_offset = int(req.get("octave_offset", 0))
            reroll = int(req.get("reroll", 0))
            bass_style = req.get("bass", "syncopated")
            euc_raw = (req.get("euclidean") or "").strip()
            custom_steps = req.get("custom_steps")
            swing = float(req.get("swing", 18.0))
            humanize_ms = float(req.get("humanize_ms", 10.0))

            try:
                chord_list = _gp_mod.split_chord_tokens(chords_str) if chords_str else _gp_mod.PRESETS.get(preset, _gp_mod.PRESETS["heartbreak"])
                euc_tuple = None
                if euc_raw and "," in euc_raw:
                    k, n = [int(x.strip()) for x in euc_raw.split(",", 1)]
                    euc_tuple = (k, n)
                _, meta = _gp_mod.build_midi_pattern(
                    chord_symbols=chord_list,
                    bpm=bpm,
                    time_sig=time_sig,
                    octave_offset=octave_offset,
                    reroll_seed=reroll,
                    include_bass=(bass_style != "none"),
                    bass_style="syncopated" if bass_style == "none" else bass_style,
                    euclidean_spec=euc_tuple,
                    custom_steps=custom_steps,
                    swing_pct=swing,
                    humanize_ms=humanize_ms,
                )
                self._send_json(200, {
                    "ok": True,
                    "bars": meta["bars"],
                    "beats_per_bar": meta["beats_per_bar"],
                    "step_velocities": meta["step_velocities"],
                })
            except Exception as exc:
                self._send_json(200, {"ok": False, "error": str(exc)})
            return

        if parsed.path == "/api/run":
            raw = self.rfile.read(length).decode("utf-8")
            req = json.loads(raw)
            action = req.get("action")
            params = req.get("params", {})
            downloads = []

            if action == "vibe_midi":
                preset = params.get("preset", "heartbreak")
                chords = (params.get("chords") or "").strip()
                bpm = str(params.get("bpm", "130"))
                ts = params.get("time_signature", "4/4")
                oct_off = str(params.get("octave_offset", "0"))
                reroll = str(params.get("reroll", "0"))
                swing = str(params.get("swing", "18"))
                hum = str(params.get("humanize_ms", "10"))
                bass = params.get("bass", "syncopated")
                groove = params.get("groove", "")
                custom_steps = params.get("custom_steps")

                tag = "custom" if chords else preset
                ts_clean = ts.replace("/", "-")
                out_file = WORKSPACE_ROOT / "output_midi" / f"{tag}_{bpm}bpm_{ts_clean}.mid"
                args = [
                    str(SCRIPTS["generate_pattern"]),
                    "--bpm", bpm,
                    "--time-signature", ts,
                    "--octave-offset", oct_off,
                    "--reroll", reroll,
                    "--swing", swing,
                    "--humanize-ms", hum,
                    "--output", str(out_file),
                ]
                if chords:
                    args.extend(["--chords", chords])
                else:
                    args.extend(["--preset", preset])
                if bass == "none":
                    args.append("--no-bass")
                else:
                    args.extend(["--bass-style", bass])
                if custom_steps:
                    args.extend(["--custom-steps", ",".join(str(int(v)) for v in custom_steps)])
                elif groove:
                    args.extend(["--euclidean", groove])

                ok, output = run_script(args)
                if ok and out_file.exists():
                    url = to_rel_download(out_file)
                    if url:
                        downloads.append({"label": out_file.name, "url": url})
                self._send_json(200, {"ok": ok, "output": output, "downloads": downloads})
                return

            if action == "analyze_audio":
                song = Path(params["song"])
                out_dir = WORKSPACE_ROOT / "output_midi"
                ok, output = run_script([str(SCRIPTS["analyze_audio"]), str(song), "--output", str(out_dir)])
                midi_file = out_dir / f"{song.stem}_basic_pitch.mid"
                if ok and midi_file.exists():
                    url = to_rel_download(midi_file)
                    if url:
                        downloads.append({"label": midi_file.name, "url": url})
                self._send_json(200, {"ok": ok, "output": output, "downloads": downloads})
                return

            if action == "stem_advisor":
                song = Path(params["song"])
                ok, output = run_script([str(SCRIPTS["stem_advisor"]), str(song)])
                self._send_json(200, {"ok": ok, "output": output, "downloads": []})
                return

            if action == "mix_check":
                args = [str(SCRIPTS["mix_check"]), str(params["mix"])]
                if params.get("reference"):
                    args.extend(["--reference", str(params["reference"])])
                ok, output = run_script(args)
                self._send_json(200, {"ok": ok, "output": output, "downloads": []})
                return

            if action == "master_track":
                target = Path(params["target"])
                ref = Path(params["reference"])
                out_dir = WORKSPACE_ROOT / "output_master"
                ok, output = run_script([
                    str(SCRIPTS["master_track"]),
                    "--target", str(target),
                    "--reference", str(ref),
                    "--output-dir", str(out_dir),
                ])
                flac = out_dir / f"{target.stem}_master_RouteNote.flac"
                wav = out_dir / f"{target.stem}_master_24bit.wav"
                for fpath in (flac, wav):
                    if fpath.exists():
                        url = to_rel_download(fpath)
                        if url:
                            downloads.append({"label": fpath.name, "url": url})
                self._send_json(200, {"ok": ok, "output": output, "downloads": downloads})
                return

            if action == "validate_release":
                args = [str(SCRIPTS["validate_release"])]
                audio = params.get("audio")
                artwork = params.get("artwork")
                fix = params.get("fix", False)
                if audio:
                    args.extend(["--audio", str(audio)])
                if artwork:
                    args.extend(["--artwork", str(artwork)])
                if fix:
                    args.append("--fix")
                ok, output = run_script(args)
                if fix:
                    if audio:
                        fixed_aud = Path(audio).parent / f"{Path(audio).stem}_RouteNote_Fixed.flac"
                        if fixed_aud.exists():
                            url = to_rel_download(fixed_aud)
                            if url:
                                downloads.append({"label": fixed_aud.name, "url": url})
                    if artwork:
                        fixed_art = Path(artwork).parent / f"{Path(artwork).stem}_RouteNote_3000x3000.jpg"
                        if fixed_art.exists():
                            url = to_rel_download(fixed_art)
                            if url:
                                downloads.append({"label": fixed_art.name, "url": url})
                self._send_json(200, {"ok": ok, "output": output, "downloads": downloads})
                return

            if action == "release_timeline":
                title = params.get("title", "New Single")
                date = params.get("date", "2026-12-31")
                ics_path = WORKSPACE_ROOT / "release_timeline.ics"
                ok, output = run_script([
                    str(SCRIPTS["release_timeline"]),
                    "--title", title,
                    "--release-date", date,
                    "--output", str(ics_path),
                ])
                if ok and ics_path.exists():
                    url = to_rel_download(ics_path)
                    if url:
                        downloads.append({"label": ics_path.name, "url": url})
                self._send_json(200, {"ok": ok, "output": output, "downloads": downloads})
                return

            self._send_json(400, {"error": f"Unknown action: {action}"})
            return

        self.send_error(404, "Not found")


def find_free_port(start_port: int = 8765) -> int:
    for port in range(start_port, start_port + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return start_port


def main():
    parser = argparse.ArgumentParser(description="Producer Reborn Studio Local Web GUI")
    parser.add_argument("--port", type=int, default=8765, help="Port to bind (default: 8765)")
    parser.add_argument("--no-browser", action="store_true", help="Do not auto-open browser")
    args = parser.parse_args()

    port = find_free_port(args.port)
    url = f"http://127.0.0.1:{port}"
    server = ThreadingHTTPServer(("127.0.0.1", port), StudioHandler)
    print(f"Producer Reborn Studio GUI running at: {url}")
    print(f"Python runtime: {PYTHON_BIN}")
    print("Press Ctrl+C to stop.")

    if not args.no_browser:
        webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down Producer Reborn Studio GUI.")
        server.server_close()


if __name__ == "__main__":
    main()
