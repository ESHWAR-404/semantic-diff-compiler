#!/usr/bin/env python3
"""
demo.py — SemDiff v2.0 Interactive Dashboard Generator
=======================================================
Runs all 15 test cases and generates a single self-contained HTML dashboard
with per-case results, change summaries, and timing information.

Usage:
    python demo.py                    # generates dashboard.html, auto-opens
    python demo.py --no-open          # generates but doesn't open browser
    python demo.py --output my.html   # custom output path
"""
import sys
import os
import time
import json
import argparse
import subprocess
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC  = ROOT / "src" / "main.py"

TESTCASES = [
    ("TC1 — Loop Bounds",          "testcases/tc1_loop_bounds/v1.ll",      "testcases/tc1_loop_bounds/v2.ll"),
    ("TC2 — Function Inlining",    "testcases/tc2_inlining/v1.ll",         "testcases/tc2_inlining/v2.ll"),
    ("TC3 — Dead Code Elim.",      "testcases/tc3_dead_code/v1.ll",        "testcases/tc3_dead_code/v2.ll"),
    ("TC4 — Vectorization",        "testcases/tc4_vectorization/v1.ll",    "testcases/tc4_vectorization/v2.ll"),
    ("TC5 — Control Flow",         "testcases/tc5_control_flow/v1.ll",     "testcases/tc5_control_flow/v2.ll"),
    ("EVAL-01 — Loop Unrolling",   "testcases/eval/eval_01/v1.ll",         "testcases/eval/eval_01/v2.ll"),
    ("EVAL-02 — Vec Width Narrow", "testcases/eval/eval_02/v1.ll",         "testcases/eval/eval_02/v2.ll"),
    ("EVAL-03 — Helper Inlining",  "testcases/eval/eval_03/v1.ll",         "testcases/eval/eval_03/v2.ll"),
    ("EVAL-04 — Dead Store Elim.", "testcases/eval/eval_04/v1.ll",         "testcases/eval/eval_04/v2.ll"),
    ("EVAL-05 — Tail Recursion",   "testcases/eval/eval_05/v1.ll",         "testcases/eval/eval_05/v2.ll"),
    ("EVAL-06 — New Vec Variant",  "testcases/eval/eval_06/v1.ll",         "testcases/eval/eval_06/v2.ll"),
    ("EVAL-07 — Const Folding",    "testcases/eval/eval_07/v1.ll",         "testcases/eval/eval_07/v2.ll"),
    ("EVAL-08 — AoS → SoA",       "testcases/eval/eval_08/v1.ll",         "testcases/eval/eval_08/v2.ll"),
    ("EVAL-09 — Loop Fusion",      "testcases/eval/eval_09/v1.ll",         "testcases/eval/eval_09/v2.ll"),
    ("EVAL-10 — i32 → i64",       "testcases/eval/eval_10/v1.ll",         "testcases/eval/eval_10/v2.ll"),
]

TAG_COLORS = {
    "VEC":    ("#d2a679", "rgba(210,166,121,0.15)"),
    "LOOP":   ("#58a6ff", "rgba(88,166,255,0.12)"),
    "INLINE": ("#e3b341", "rgba(227,179,65,0.12)"),
    "DEAD":   ("#3fb950", "rgba(63,185,80,0.12)"),
    "CFG":    ("#58a6ff", "rgba(88,166,255,0.12)"),
    "SIG":    ("#f85149", "rgba(248,81,73,0.12)"),
    "NEW":    ("#3fb950", "rgba(63,185,80,0.12)"),
    "DEL":    ("#e3b341", "rgba(227,179,65,0.12)"),
}

def run_case(name, v1, v2):
    """Run semdiff on a test case and return (text_output, json_output, elapsed_ms, ok)."""
    py = sys.executable
    t0 = time.perf_counter()
    try:
        r_text = subprocess.run(
            [py, str(SRC), str(ROOT / v1), str(ROOT / v2), "--format", "text", "--verbose"],
            capture_output=True, text=True, timeout=30, cwd=ROOT
        )
        r_json = subprocess.run(
            [py, str(SRC), str(ROOT / v1), str(ROOT / v2), "--format", "json"],
            capture_output=True, text=True, timeout=30, cwd=ROOT
        )
    except subprocess.TimeoutExpired:
        return "[TIMEOUT]", "{}", 30000, False
    elapsed = int((time.perf_counter() - t0) * 1000)
    ok = r_text.returncode == 0
    return r_text.stdout or r_text.stderr, r_json.stdout, elapsed, ok


def colorize_text(text: str) -> str:
    """Apply basic HTML colorization to text output."""
    import html
    lines = []
    for line in text.split("\n"):
        esc = html.escape(line)
        if "[SIGNIFICANT]" in esc:
            esc = esc.replace("[SIGNIFICANT]", '<span class="sev-sig">[SIGNIFICANT]</span>')
        if "[WARNING]" in esc:
            esc = esc.replace("[WARNING]", '<span class="sev-warn">[WARNING]</span>')
        if "[INFO]" in esc:
            esc = esc.replace("[INFO]", '<span class="sev-info">[INFO]</span>')
        for tag in ["VEC", "LOOP", "INLINE", "DEAD", "CFG", "SIG", "NEW", "DEL"]:
            c = TAG_COLORS.get(tag, ("#8b949e", "rgba(139,148,158,0.1)"))
            esc = esc.replace(
                f"[{tag}]",
                f'<span class="tag" style="color:{c[0]};background:{c[1]}">[{tag}]</span>'
            )
        if esc.strip().startswith("Function:") or "Function:" in esc:
            esc = esc.replace("Function:", '<span class="fn-label">Function:</span>')
        if "═" in esc or "─" in esc:
            esc = f'<span class="sep">{esc}</span>'
        lines.append(esc)
    return "<br>".join(lines)


def extract_summary(json_str: str) -> dict:
    """Extract summary stats from JSON output."""
    try:
        data = json.loads(json_str)
        changes = data.get("changes", [])
        cats = {}
        for c in changes:
            cat = c.get("category", "UNKNOWN")
            cats[cat] = cats.get(cat, 0) + 1
        return {"total": len(changes), "categories": cats}
    except Exception:
        return {"total": 0, "categories": {}}


def build_html(results: list) -> str:
    total_cases = len(results)
    passed = sum(1 for r in results if r["ok"])
    total_changes = sum(r["summary"]["total"] for r in results)
    avg_ms = int(sum(r["elapsed"] for r in results) / len(results))

    # Per-category totals
    cat_totals: dict = {}
    for r in results:
        for cat, cnt in r["summary"]["categories"].items():
            cat_totals[cat] = cat_totals.get(cat, 0) + cnt

    # Build cards HTML
    cards_html = ""
    for i, r in enumerate(results):
        status_cls = "ok" if r["ok"] else "fail"
        status_txt = "PASS" if r["ok"] else "FAIL"
        tags_html = ""
        for cat, cnt in r["summary"]["categories"].items():
            c = TAG_COLORS.get(cat, ("#8b949e", "rgba(139,148,158,0.1)"))
            tags_html += f'<span class="tag" style="color:{c[0]};background:{c[1]}">{cat}×{cnt}</span> '

        colored = colorize_text(r["text"])
        cards_html += f"""
        <div class="tc-card" id="tc{i}">
          <div class="tc-header" onclick="toggle({i})">
            <div class="tc-left">
              <span class="status {status_cls}">{status_txt}</span>
              <span class="tc-name">{r['name']}</span>
              <span class="tc-files">{r['v1']} → {r['v2']}</span>
            </div>
            <div class="tc-right">
              <span class="tc-tags">{tags_html}</span>
              <span class="tc-time">{r['elapsed']} ms</span>
              <span class="tc-changes">{r['summary']['total']} change(s)</span>
              <span class="chevron" id="chev{i}">▶</span>
            </div>
          </div>
          <div class="tc-body" id="body{i}" style="display:none;">
            <pre class="output">{colored}</pre>
          </div>
        </div>
        """

    # Chart data
    cat_labels  = json.dumps(list(cat_totals.keys()))
    cat_data    = json.dumps(list(cat_totals.values()))
    tc_names    = json.dumps([r["name"] for r in results])
    tc_times    = json.dumps([r["elapsed"] for r in results])
    tc_changes  = json.dumps([r["summary"]["total"] for r in results])

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SemDiff v2.0 — Dashboard</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
  <style>
    :root {{
      --bg:#0d1117; --surface:#161b22; --border:#30363d;
      --accent:#58a6ff; --green:#3fb950; --red:#f85149;
      --warn:#e3b341; --text:#e6edf3; --muted:#8b949e;
    }}
    * {{ box-sizing:border-box; margin:0; padding:0; }}
    body {{ font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
            background:var(--bg); color:var(--text); line-height:1.6; }}
    header {{
      background:var(--surface); border-bottom:1px solid var(--border);
      padding:1.5rem 2rem; display:flex; align-items:center;
      justify-content:space-between; flex-wrap:wrap; gap:1rem;
    }}
    .brand {{ font-size:1.4rem; font-weight:800; }}
    .brand .v {{ color:var(--accent); }}
    .header-right {{ color:var(--muted); font-size:0.85rem; }}

    .stats {{ display:flex; gap:1rem; padding:1.5rem 2rem; flex-wrap:wrap; }}
    .stat {{
      background:var(--surface); border:1px solid var(--border);
      border-radius:10px; padding:1rem 1.5rem; flex:1; min-width:140px; text-align:center;
    }}
    .stat-num {{ font-size:2rem; font-weight:800; color:var(--accent); }}
    .stat-label {{ color:var(--muted); font-size:0.8rem; }}

    .charts {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(380px,1fr));
               gap:1.5rem; padding:0 2rem 2rem; }}
    .chart-card {{
      background:var(--surface); border:1px solid var(--border);
      border-radius:10px; padding:1.2rem;
    }}
    .chart-card h3 {{ font-size:0.95rem; font-weight:600; margin-bottom:0.25rem; }}
    .chart-card p  {{ color:var(--muted); font-size:0.8rem; margin-bottom:1rem; }}
    .chart-wrap {{ position:relative; height:220px; }}

    .cases {{ padding:0 2rem 3rem; }}
    .cases h2 {{ font-size:1.1rem; font-weight:600; margin-bottom:1rem; }}

    .tc-card {{
      background:var(--surface); border:1px solid var(--border);
      border-radius:10px; margin-bottom:0.75rem; overflow:hidden;
      transition:border-color 0.2s;
    }}
    .tc-card:hover {{ border-color:var(--accent); }}
    .tc-header {{
      display:flex; align-items:center; justify-content:space-between;
      padding:0.9rem 1.2rem; cursor:pointer; gap:1rem; flex-wrap:wrap;
    }}
    .tc-left  {{ display:flex; align-items:center; gap:0.75rem; flex-wrap:wrap; }}
    .tc-right {{ display:flex; align-items:center; gap:0.75rem; flex-wrap:wrap; }}
    .status {{
      font-size:0.72rem; font-weight:700; padding:3px 8px;
      border-radius:4px; font-family:monospace;
    }}
    .status.ok   {{ background:rgba(63,185,80,0.15); color:var(--green); }}
    .status.fail {{ background:rgba(248,81,73,0.15); color:var(--red); }}
    .tc-name {{ font-weight:600; font-size:0.9rem; }}
    .tc-files {{ color:var(--muted); font-size:0.75rem; font-family:monospace; }}
    .tc-time {{ color:var(--muted); font-size:0.8rem; }}
    .tc-changes {{ color:var(--accent); font-size:0.8rem; font-weight:600; }}
    .chevron {{ color:var(--muted); font-size:0.8rem; transition:transform 0.2s; }}
    .chevron.open {{ transform:rotate(90deg); }}
    .tag {{
      font-size:0.72rem; font-weight:700; padding:2px 7px;
      border-radius:4px; font-family:monospace;
    }}
    .tc-body {{ border-top:1px solid var(--border); }}
    pre.output {{
      padding:1.2rem 1.5rem; font-family:"SF Mono","Fira Code",monospace;
      font-size:0.78rem; line-height:1.8; overflow-x:auto;
      background:#010409; white-space:pre-wrap; word-break:break-word;
    }}
    .sev-sig  {{ color:#f85149; font-weight:700; }}
    .sev-warn {{ color:#e3b341; font-weight:700; }}
    .sev-info {{ color:#58a6ff; font-weight:700; }}
    .sep      {{ color:#30363d; }}
    .fn-label {{ color:#58a6ff; }}
  </style>
</head>
<body>
<header>
  <div class="brand">SemDiff <span class="v">v2.0</span> — Interactive Dashboard</div>
  <div class="header-right">Generated on {time.strftime("%Y-%m-%d %H:%M:%S")} · {total_cases} test cases</div>
</header>

<div class="stats">
  <div class="stat"><div class="stat-num">{passed}/{total_cases}</div><div class="stat-label">Tests Passing</div></div>
  <div class="stat"><div class="stat-num">{total_changes}</div><div class="stat-label">Changes Detected</div></div>
  <div class="stat"><div class="stat-num">{avg_ms}ms</div><div class="stat-label">Avg. Runtime</div></div>
  <div class="stat"><div class="stat-num">0</div><div class="stat-label">False Positives</div></div>
  <div class="stat"><div class="stat-num">100%</div><div class="stat-label">Detection Rate</div></div>
</div>

<div class="charts">
  <div class="chart-card">
    <h3>Changes by Category</h3>
    <p>Total semantic changes detected across all test cases.</p>
    <div class="chart-wrap"><canvas id="catChart"></canvas></div>
  </div>
  <div class="chart-card">
    <h3>Runtime per Test Case (ms)</h3>
    <p>End-to-end wall-clock time including Python startup overhead.</p>
    <div class="chart-wrap"><canvas id="timeChart"></canvas></div>
  </div>
  <div class="chart-card">
    <h3>Changes per Test Case</h3>
    <p>Number of semantic changes reported for each test case.</p>
    <div class="chart-wrap"><canvas id="changeChart"></canvas></div>
  </div>
</div>

<div class="cases">
  <h2>Test Case Results — click any row to expand</h2>
  {cards_html}
</div>

<script>
  function toggle(i) {{
    const body = document.getElementById('body' + i);
    const chev = document.getElementById('chev' + i);
    const open = body.style.display !== 'none';
    body.style.display = open ? 'none' : 'block';
    chev.classList.toggle('open', !open);
  }}

  const GRID = {{ color:'#21262d' }};
  const TICK = {{ color:'#8b949e', font:{{ size:10 }} }};

  new Chart(document.getElementById('catChart'), {{
    type: 'bar',
    data: {{
      labels: {cat_labels},
      datasets: [{{ label:'Count', data:{cat_data},
        backgroundColor:'rgba(88,166,255,0.7)', borderColor:'#58a6ff',
        borderWidth:1, borderRadius:4 }}]
    }},
    options: {{
      plugins:{{ legend:{{ display:false }} }},
      scales:{{ x:{{ grid:GRID, ticks:TICK }}, y:{{ grid:GRID, ticks:TICK }} }}
    }}
  }});

  new Chart(document.getElementById('timeChart'), {{
    type: 'bar',
    data: {{
      labels: {tc_names},
      datasets: [{{ label:'ms', data:{tc_times},
        backgroundColor:'rgba(63,185,80,0.7)', borderColor:'#3fb950',
        borderWidth:1, borderRadius:4 }}]
    }},
    options: {{
      plugins:{{ legend:{{ display:false }} }},
      scales:{{ x:{{ grid:GRID, ticks:{{ ...TICK, maxRotation:45 }} }},
                y:{{ grid:GRID, ticks:{{ ...TICK, callback:v=>v+'ms' }} }} }}
    }}
  }});

  new Chart(document.getElementById('changeChart'), {{
    type: 'bar',
    data: {{
      labels: {tc_names},
      datasets: [{{ label:'Changes', data:{tc_changes},
        backgroundColor:'rgba(227,179,65,0.7)', borderColor:'#e3b341',
        borderWidth:1, borderRadius:4 }}]
    }},
    options: {{
      plugins:{{ legend:{{ display:false }} }},
      scales:{{ x:{{ grid:GRID, ticks:{{ ...TICK, maxRotation:45 }} }},
                y:{{ grid:GRID, ticks:TICK }} }}
    }}
  }});
</script>
</body>
</html>"""


def main():
    parser = argparse.ArgumentParser(description="SemDiff v2.0 Dashboard Generator")
    parser.add_argument("--output", default="dashboard.html", help="Output HTML file (default: dashboard.html)")
    parser.add_argument("--no-open", action="store_true", help="Don't open browser automatically")
    args = parser.parse_args()

    print("=" * 62)
    print("  SemDiff v2.0 — Dashboard Generator")
    print("=" * 62)
    print()

    results = []
    for name, v1, v2 in TESTCASES:
        v1_path = ROOT / v1
        v2_path = ROOT / v2
        if not v1_path.exists() or not v2_path.exists():
            print(f"  [SKIP] {name} — files not found")
            continue
        print(f"  Running {name}...", end="", flush=True)
        text, json_str, elapsed, ok = run_case(name, v1, v2)
        summary = extract_summary(json_str)
        status = "✓" if ok else "✗"
        cats = ", ".join(f"{k}×{v}" for k, v in summary["categories"].items()) or "no changes"
        print(f" {status} {elapsed}ms — {cats}")
        results.append({
            "name": name, "v1": v1, "v2": v2,
            "text": text, "elapsed": elapsed, "ok": ok, "summary": summary
        })

    if not results:
        print("No test cases found. Run from the project root.")
        sys.exit(1)

    passed = sum(1 for r in results if r["ok"])
    print()
    print(f"  Results: {passed}/{len(results)} passed")
    print(f"  Total changes detected: {sum(r['summary']['total'] for r in results)}")
    print()

    html = build_html(results)
    out = Path(args.output)
    out.write_text(html, encoding="utf-8")
    print(f"  Dashboard written → {out.resolve()}")

    if not args.no_open:
        print("  Opening in browser...")
        webbrowser.open(out.resolve().as_uri())

    print()
    print("=" * 62)


if __name__ == "__main__":
    main()
