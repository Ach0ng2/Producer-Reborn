"""
Producer Reborn Studio — Zero-CMD Local Web GUI
A Vibe-First, DAW-style visual dashboard for independent artists and beatmakers.
Zero external web dependencies (uses Python standard library http.server).
"""

import os
import sys
import json
import time
import shutil
import socket
import argparse
import webbrowser
import subprocess
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

PLUGIN_DIR = Path(__file__).resolve().parent
# Workspace root is 3 levels up from .agents/plugins/producer-reborn/
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
  <title>Producer Reborn Studio</title>
  <style>
    :root {
      --bg: #0e1015;
      --panel: #161922;
      --panel-2: #1d212d;
      --border: #2a3040;
      --text: #eef1f7;
      --muted: #939db4;
      --accent: #7c5cff;
      --accent-2: #19d3a2;
      --warn: #f5b942;
      --err: #ff5c7a;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Inter, sans-serif;
      background: radial-gradient(circle at top right, #1a1630 0%, var(--bg) 55%);
      color: var(--text);
      min-height: 100vh;
    }
    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 18px 28px;
      border-bottom: 1px solid var(--border);
      background: rgba(14, 16, 21, 0.85);
      backdrop-filter: blur(10px);
      position: sticky;
      top: 0;
      z-index: 10;
    }
    .brand { display: flex; align-items: center; gap: 12px; }
    .brand-badge {
      width: 38px; height: 38px; border-radius: 10px;
      background: linear-gradient(135deg, var(--accent), var(--accent-2));
      display: grid; place-items: center; font-size: 20px; font-weight: 700;
    }
    .brand h1 { margin: 0; font-size: 18px; letter-spacing: 0.2px; }
    .brand p { margin: 2px 0 0; font-size: 12px; color: var(--muted); }
    .pill {
      font-size: 12px; padding: 6px 12px; border-radius: 999px;
      background: var(--panel-2); border: 1px solid var(--border); color: var(--accent-2);
    }
    .container { max-width: 1080px; margin: 24px auto; padding: 0 20px 48px; }
    .tabs {
      display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 20px;
    }
    .tab-btn {
      background: var(--panel); border: 1px solid var(--border); color: var(--muted);
      padding: 10px 16px; border-radius: 10px; cursor: pointer; font-size: 14px; font-weight: 600;
      transition: all 0.15s ease;
    }
    .tab-btn:hover { color: var(--text); border-color: #3d465e; }
    .tab-btn.active {
      background: linear-gradient(135deg, rgba(124,92,255,0.22), rgba(25,211,162,0.12));
      border-color: var(--accent); color: var(--text);
    }
    .card {
      background: var(--panel); border: 1px solid var(--border);
      border-radius: 14px; padding: 22px; margin-bottom: 18px;
    }
    .card h2 { margin: 0 0 6px; font-size: 18px; }
    .card .sub { margin: 0 0 18px; color: var(--muted); font-size: 13px; }
    .panel-tab { display: none; }
    .panel-tab.active { display: block; }
    .vibe-grid {
      display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px;
      margin-bottom: 18px;
    }
    .vibe-card {
      background: var(--panel-2); border: 1px solid var(--border); border-radius: 10px;
      padding: 12px; cursor: pointer; transition: 0.15s;
    }
    .vibe-card:hover { border-color: #4b5575; }
    .vibe-card.selected {
      border-color: var(--accent-2);
      background: rgba(25, 211, 162, 0.08);
    }
    .vibe-card .title { font-weight: 600; font-size: 14px; margin-bottom: 4px; }
    .vibe-card .desc { font-size: 12px; color: var(--muted); }
    .row { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; margin-bottom: 16px; }
    label { display: block; font-size: 12px; color: var(--muted); margin-bottom: 6px; font-weight: 600; }
    select, input[type="text"], input[type="date"], input[type="number"] {
      width: 100%; background: var(--panel-2); border: 1px solid var(--border);
      color: var(--text); padding: 10px 12px; border-radius: 8px; font-size: 14px;
    }
    input[type="range"] { width: 100%; accent-color: var(--accent); }
    .dropzone {
      border: 2px dashed var(--border); border-radius: 12px; padding: 18px;
      text-align: center; background: var(--panel-2); cursor: pointer; transition: 0.15s;
    }
    .dropzone:hover, .dropzone.dragover { border-color: var(--accent); background: rgba(124,92,255,0.08); }
    .dropzone input { display: none; }
    .dropzone .file-name { margin-top: 6px; font-size: 13px; color: var(--accent-2); font-weight: 600; }
    .btn {
      background: linear-gradient(135deg, var(--accent), #5d42e0);
      color: #fff; border: none; border-radius: 10px; padding: 12px 20px;
      font-size: 14px; font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; gap: 8px;
    }
    .btn:disabled { opacity: 0.55; cursor: not-allowed; }
    .btn-secondary {
      background: var(--panel-2); border: 1px solid var(--border); color: var(--text);
    }
    .output-box {
      background: #090b0f; border: 1px solid var(--border); border-radius: 10px;
      padding: 14px; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 12.5px; line-height: 1.55; white-space: pre-wrap; color: #d5dce9;
      max-height: 360px; overflow-y: auto; margin-top: 14px; display: none;
    }
    .downloads { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 12px; }
    .dl-link {
      text-decoration: none; background: rgba(25, 211, 162, 0.14);
      border: 1px solid var(--accent-2); color: var(--accent-2);
      padding: 8px 14px; border-radius: 8px; font-size: 13px; font-weight: 600;
    }
    .checkbox-row { display: flex; align-items: center; gap: 8px; font-size: 13px; margin: 10px 0 16px; }
    .checkbox-row input { width: 16px; height: 16px; accent-color: var(--accent); }
  </style>
</head>
<body>
  <header>
    <div class="brand">
      <div class="brand-badge">🎹</div>
      <div>
        <h1>Producer Reborn Studio</h1>
        <p>Zero-Theory, Zero-CMD Music Production &amp; Release Suite ($0 Budget)</p>
      </div>
    </div>
    <div class="pill">Local • Offline-First • 100% Free</div>
  </header>

  <div class="container">
    <div class="tabs">
      <button class="tab-btn active" onclick="switchTab('vibe', this)">🎹 1. Vibe-to-MIDI</button>
      <button class="tab-btn" onclick="switchTab('analyze', this)">🎧 2. Song &amp; Stem Doctor</button>
      <button class="tab-btn" onclick="switchTab('mix', this)">🩺 3. Mix Doctor</button>
      <button class="tab-btn" onclick="switchTab('master', this)">🎚️ 4. AI Mastering</button>
      <button class="tab-btn" onclick="switchTab('release', this)">🚀 5. RouteNote &amp; Timeline</button>
    </div>

    <!-- TAB 1: VIBE TO MIDI -->
    <div id="tab-vibe" class="panel-tab active">
      <div class="card">
        <h2>Vibe-to-MIDI Generator (No Music Theory Needed)</h2>
        <p class="sub">Pick a mood, dial in your tempo, and export smooth voice-led chords + bass + groove ready to drag into your DAW.</p>

        <label>1. Choose Your Mood / Vibe</label>
        <div class="vibe-grid" id="vibe-grid">
          <div class="vibe-card selected" data-preset="heartbreak" onclick="selectVibe(this)">
            <div class="title">💔 Heartbreak Nostalgia</div>
            <div class="desc">Warm, bittersweet major-to-minor lift</div>
          </div>
          <div class="vibe-card" data-preset="late-night" onclick="selectVibe(this)">
            <div class="title">🌙 Late Night Sadboy</div>
            <div class="desc">Lush R&amp;B / bedroom-pop 9th chords</div>
          </div>
          <div class="vibe-card" data-preset="dreamy-bedroom" onclick="selectVibe(this)">
            <div class="title">☁️ Dreamy Bedroom Pop</div>
            <div class="desc">Floating lo-fi keys, gentle resolution</div>
          </div>
          <div class="vibe-card" data-preset="dark-trap" onclick="selectVibe(this)">
            <div class="title">🔥 Dark Emo Trap</div>
            <div class="desc">Moody minor progression with tension</div>
          </div>
          <div class="vibe-card" data-preset="uplifting-indie" onclick="selectVibe(this)">
            <div class="title">☀️ Uplifting Indie Pop</div>
            <div class="desc">Bright, anthemic chorus energy</div>
          </div>
          <div class="vibe-card" data-preset="cinematic" onclick="selectVibe(this)">
            <div class="title">🎬 Cinematic Modal</div>
            <div class="desc">Wide, dramatic, emotional swell</div>
          </div>
        </div>

        <div class="row">
          <div>
            <label>2. Tempo: <span id="bpm-val">125</span> BPM</label>
            <input type="range" id="vibe-bpm" min="65" max="175" value="125" oninput="document.getElementById('bpm-val').innerText=this.value" />
          </div>
          <div>
            <label>3. Bassline Feel</label>
            <select id="vibe-bass">
              <option value="syncopated">Chill Syncopated Bounce</option>
              <option value="eighth">Driving 8th-Note Pulse</option>
              <option value="walking">Melodic Walking Bass</option>
              <option value="none">No Bassline</option>
            </select>
          </div>
          <div>
            <label>4. Percussion Groove</label>
            <select id="vibe-groove">
              <option value="">None (Chords + Bass only)</option>
              <option value="5,16">Afrobeat / Amapiano Bounce</option>
              <option value="3,8">Reggaeton / Tresillo Pulse</option>
              <option value="5,8">Syncopated Indie Shaker</option>
            </select>
          </div>
        </div>

        <button class="btn" onclick="runVibeMidi(this)">✨ Generate Drag-and-Drop MIDI</button>
        <div id="out-vibe" class="output-box"></div>
        <div id="dl-vibe" class="downloads"></div>
      </div>
    </div>

    <!-- TAB 2: SONG & STEM DOCTOR -->
    <div id="tab-analyze" class="panel-tab">
      <div class="card">
        <h2>Song &amp; Stem Doctor</h2>
        <p class="sub">Drop a beat, loop, or full track to detect BPM, key, chords, and check if vocals or bass drift off-key.</p>
        <div class="row">
          <div class="dropzone" onclick="this.querySelector('input').click()" ondragover="dragOver(event,this)" ondragleave="dragLeave(this)" ondrop="dropFile(event,this,'analyze-song')">
            <div>🎵 Drop Full Track / Loop (MP3 or WAV)</div>
            <div class="file-name" id="name-analyze-song">Click or drag file here</div>
            <input type="file" accept="audio/*" onchange="uploadInput(this,'analyze-song')" />
          </div>
        </div>
        <div style="display:flex; gap:10px; flex-wrap:wrap;">
          <button class="btn" onclick="runAnalyze('chords', this)">🎼 Extract BPM, Chords &amp; MIDI</button>
          <button class="btn btn-secondary" onclick="runAnalyze('stems', this)">🎤 Audit Vocal &amp; Bass Pitch (Demucs + pYIN)</button>
        </div>
        <div id="out-analyze" class="output-box"></div>
        <div id="dl-analyze" class="downloads"></div>
      </div>
    </div>

    <!-- TAB 3: MIX DOCTOR -->
    <div id="tab-mix" class="panel-tab">
      <div class="card">
        <h2>Mix Doctor (Pre-Mastering Check)</h2>
        <p class="sub">Check headroom (-6 to -3 dBFS), stereo phase safety, mono bass (&lt; 120 Hz), and EQ balance vs. a reference track.</p>
        <div class="row">
          <div class="dropzone" onclick="this.querySelector('input').click()" ondragover="dragOver(event,this)" ondragleave="dragLeave(this)" ondrop="dropFile(event,this,'mix-target')">
            <div>🎚️ Drop Your Pre-Master Mix (WAV/FLAC/MP3)</div>
            <div class="file-name" id="name-mix-target">Required</div>
            <input type="file" accept="audio/*" onchange="uploadInput(this,'mix-target')" />
          </div>
          <div class="dropzone" onclick="this.querySelector('input').click()" ondragover="dragOver(event,this)" ondragleave="dragLeave(this)" ondrop="dropFile(event,this,'mix-ref')">
            <div>💿 Drop Commercial Reference Track (Optional)</div>
            <div class="file-name" id="name-mix-ref">Optional</div>
            <input type="file" accept="audio/*" onchange="uploadInput(this,'mix-ref')" />
          </div>
        </div>
        <button class="btn" onclick="runMixCheck(this)">🩺 Diagnose My Mix</button>
        <div id="out-mix" class="output-box"></div>
      </div>
    </div>

    <!-- TAB 4: AI MASTERING -->
    <div id="tab-master" class="panel-tab">
      <div class="card">
        <h2>AI Reference Mastering (Matchering 2.0.6)</h2>
        <p class="sub">Match the loudness and tonal curve of any commercial track. Exports 24-bit WAV + 16-bit RouteNote-ready FLAC.</p>
        <div class="row">
          <div class="dropzone" onclick="this.querySelector('input').click()" ondragover="dragOver(event,this)" ondragleave="dragLeave(this)" ondrop="dropFile(event,this,'master-target')">
            <div>🎚️ Drop Your Mix (WAV/FLAC)</div>
            <div class="file-name" id="name-master-target">Required</div>
            <input type="file" accept="audio/*" onchange="uploadInput(this,'master-target')" />
          </div>
          <div class="dropzone" onclick="this.querySelector('input').click()" ondragover="dragOver(event,this)" ondragleave="dragLeave(this)" ondrop="dropFile(event,this,'master-ref')">
            <div>💿 Drop Commercial Reference Track</div>
            <div class="file-name" id="name-master-ref">Required</div>
            <input type="file" accept="audio/*" onchange="uploadInput(this,'master-ref')" />
          </div>
        </div>
        <button class="btn" onclick="runMaster(this)">🔥 Master Track Now</button>
        <div id="out-master" class="output-box"></div>
        <div id="dl-master" class="downloads"></div>
      </div>
    </div>

    <!-- TAB 5: ROUTENOTE & TIMELINE -->
    <div id="tab-release" class="panel-tab">
      <div class="card">
        <h2>RouteNote Pre-Flight Validator &amp; Auto-Fix</h2>
        <p class="sub">Automatically checks and converts audio to 16-bit 44.1 kHz FLAC and artwork to 3000×3000 RGB JPG.</p>
        <div class="row">
          <div class="dropzone" onclick="this.querySelector('input').click()" ondragover="dragOver(event,this)" ondragleave="dragLeave(this)" ondrop="dropFile(event,this,'rn-audio')">
            <div>🎵 Drop Master Audio (WAV/FLAC/MP3)</div>
            <div class="file-name" id="name-rn-audio">Optional</div>
            <input type="file" accept="audio/*" onchange="uploadInput(this,'rn-audio')" />
          </div>
          <div class="dropzone" onclick="this.querySelector('input').click()" ondragover="dragOver(event,this)" ondragleave="dragLeave(this)" ondrop="dropFile(event,this,'rn-art')">
            <div>🖼️ Drop Cover Artwork (PNG/JPG)</div>
            <div class="file-name" id="name-rn-art">Optional</div>
            <input type="file" accept="image/*" onchange="uploadInput(this,'rn-art')" />
          </div>
        </div>
        <div class="checkbox-row">
          <input type="checkbox" id="rn-fix" checked />
          <label for="rn-fix" style="margin:0; cursor:pointer;">Auto-Fix issues (Convert to 16-bit FLAC &amp; Resize cover to 3000×3000 RGB JPG)</label>
        </div>
        <button class="btn" onclick="runValidate(this)">✅ Validate &amp; Auto-Fix Assets</button>
        <div id="out-rn" class="output-box"></div>
        <div id="dl-rn" class="downloads"></div>
      </div>

      <div class="card">
        <h2>H-28 Release Countdown &amp; Calendar Export</h2>
        <p class="sub">Generates your RouteNote submission, Spotify editorial pitch deadline (H-7), and `.ics` calendar file.</p>
        <div class="row">
          <div>
            <label>Single / EP Title</label>
            <input type="text" id="tl-title" placeholder="e.g., Midnight Drive" />
          </div>
          <div>
            <label>Target Release Date</label>
            <input type="date" id="tl-date" value="2026-12-31" />
          </div>
        </div>
        <button class="btn" onclick="runTimeline(this)">📅 Generate Release Calendar (.ics)</button>
        <div id="out-tl" class="output-box"></div>
        <div id="dl-tl" class="downloads"></div>
      </div>
    </div>
  </div>

<script>
const uploadedPaths = {};
let selectedPreset = "heartbreak";

function switchTab(id, btn) {
  document.querySelectorAll('.panel-tab').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('tab-' + id).classList.add('active');
  btn.classList.add('active');
}

function selectVibe(el) {
  document.querySelectorAll('.vibe-card').forEach(c => c.classList.remove('selected'));
  el.classList.add('selected');
  selectedPreset = el.dataset.preset;
}

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
  const label = document.getElementById('name-' + key);
  label.innerText = "Uploading " + file.name + "...";
  const res = await fetch('/api/upload', {
    method: 'POST',
    headers: { 'X-Filename': encodeURIComponent(file.name) },
    body: file
  });
  const data = await res.json();
  if (data.path) {
    uploadedPaths[key] = data.path;
    label.innerText = "✅ " + data.name;
  } else {
    label.innerText = "❌ Upload failed";
  }
}

async function callApi(action, params, btn, outId, dlId) {
  const origText = btn.innerText;
  btn.disabled = true;
  btn.innerText = "⏳ Running...";
  const out = document.getElementById(outId);
  out.style.display = "block";
  out.innerText = "Processing... please wait.";
  if (dlId) document.getElementById(dlId).innerHTML = "";

  try {
    const res = await fetch('/api/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action, params })
    });
    const data = await res.json();
    out.innerText = data.output || data.error || "Done.";
    if (dlId && data.downloads && data.downloads.length) {
      const container = document.getElementById(dlId);
      data.downloads.forEach(d => {
        const a = document.createElement('a');
        a.href = d.url;
        a.className = 'dl-link';
        a.innerText = "⬇ Download " + d.label;
        container.appendChild(a);
      });
    }
  } catch (err) {
    out.innerText = "Error: " + err;
  } finally {
    btn.disabled = false;
    btn.innerText = origText;
  }
}

function runVibeMidi(btn) {
  callApi('vibe_midi', {
    preset: selectedPreset,
    bpm: document.getElementById('vibe-bpm').value,
    bass: document.getElementById('vibe-bass').value,
    groove: document.getElementById('vibe-groove').value
  }, btn, 'out-vibe', 'dl-vibe');
}

function runAnalyze(mode, btn) {
  if (!uploadedPaths['analyze-song']) return alert("Please upload an audio file first!");
  callApi(mode === 'chords' ? 'analyze_audio' : 'stem_advisor', {
    song: uploadedPaths['analyze-song']
  }, btn, 'out-analyze', 'dl-analyze');
}

function runMixCheck(btn) {
  if (!uploadedPaths['mix-target']) return alert("Please upload your mix file first!");
  callApi('mix_check', {
    mix: uploadedPaths['mix-target'],
    reference: uploadedPaths['mix-ref'] || null
  }, btn, 'out-mix', null);
}

function runMaster(btn) {
  if (!uploadedPaths['master-target'] || !uploadedPaths['master-ref']) {
    return alert("Please upload both your Mix and a Reference track!");
  }
  callApi('master_track', {
    target: uploadedPaths['master-target'],
    reference: uploadedPaths['master-ref']
  }, btn, 'out-master', 'dl-master');
}

function runValidate(btn) {
  if (!uploadedPaths['rn-audio'] && !uploadedPaths['rn-art']) {
    return alert("Please upload an audio file and/or cover artwork!");
  }
  callApi('validate_release', {
    audio: uploadedPaths['rn-audio'] || null,
    artwork: uploadedPaths['rn-art'] || null,
    fix: document.getElementById('rn-fix').checked
  }, btn, 'out-rn', 'dl-rn');
}

function runTimeline(btn) {
  const title = document.getElementById('tl-title').value.trim() || "My New Single";
  const date = document.getElementById('tl-date').value;
  callApi('release_timeline', { title, date }, btn, 'out-tl', 'dl-tl');
}
</script>
</body>
</html>
"""


class StudioHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Keep terminal output clean

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

        if parsed.path == "/api/run":
            raw = self.rfile.read(length).decode("utf-8")
            req = json.loads(raw)
            action = req.get("action")
            params = req.get("params", {})
            downloads = []

            if action == "vibe_midi":
                preset = params.get("preset", "heartbreak")
                bpm = str(params.get("bpm", "125"))
                bass = params.get("bass", "syncopated")
                groove = params.get("groove", "")
                out_file = WORKSPACE_ROOT / "output_midi" / f"{preset}_{bpm}bpm.mid"
                args = [str(SCRIPTS["generate_pattern"]), "--preset", preset, "--bpm", bpm, "--output", str(out_file)]
                if bass == "none":
                    args.append("--no-bass")
                else:
                    args.extend(["--bass-style", bass])
                if groove:
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
                title = params.get("title", "My New Single")
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
    print(f"🎹 Producer Reborn Studio GUI running at: {url}")
    print(f"   Python runtime: {PYTHON_BIN}")
    print("   Press Ctrl+C to stop.")

    if not args.no_browser:
        webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down Producer Reborn Studio GUI.")
        server.server_close()


if __name__ == "__main__":
    main()
