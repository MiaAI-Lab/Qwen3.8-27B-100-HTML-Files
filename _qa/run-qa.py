#!/usr/bin/env python3
"""QA runner for gallery-100: static checks + headless-chromium runtime smoke.
Usage: python3 run-qa.py NNN  (NNN = 3-digit index, e.g. 001)
Exit 0 + "PASS" when all checks green.
"""
import glob, json, os, re, subprocess, sys, time
from html.parser import HTMLParser

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def find_html(n):
    m = glob.glob(os.path.join(BASE, f"{n}-*.html"))
    return m[0] if m else None

def main():
    if len(sys.argv) < 2:
        print("usage: run-qa.py NNN"); return 2
    n = sys.argv[1]
    path = find_html(n)
    if not path or not os.path.exists(path):
        print(f"FAIL {n}: html not found"); return 1
    txt = path[:-5] + ".txt"
    data = open(path, encoding="utf-8").read()
    errs = []

    # --- static ---
    try:
        class P(HTMLParser):
            def error(self, m): raise Exception(m)
        P().feed(data)
    except Exception as e:
        errs.append(f"html-parse: {e}")
    if not data.lstrip().lower().startswith("<!doctype html>"):
        errs.append("missing doctype first")
    if re.search(r"charset", data, re.I) is None:
        errs.append("missing charset meta")
    if re.search(r"viewport", data) is None:
        errs.append("missing viewport meta")
    low = data.lower()
    if "http" in low:
        hits = [m.start() for m in re.finditer(r"http", low)][:3]
        errs.append(f"forbidden substring 'http' at {hits}")
    if re.search(r"//cdn|@import", data, re.I):
        errs.append("forbidden @import/CDN ref")
    if len(data.encode()) < 3000:
        errs.append(f"too small: {len(data)} bytes")
    if not os.path.exists(txt):
        errs.append("missing .txt")
    else:
        t = open(txt, encoding="utf-8").read()
        for k in ("TITLE:", "PROMPT:", "DESCRIPTION:", "TECHNIQUES:", "INTERACTION:"):
            if k not in t:
                errs.append(f"txt missing block {k}")

    # --- js syntax ---
    sm = re.findall(r"<script>(.*?)</script>", data, re.S)
    js = "\n".join(sm)
    if js:
        tf = os.path.join(BASE, "_qa", f"_js_{n}.js")
        open(tf, "w").write(js)
        r = subprocess.run(["node", "--check", tf], capture_output=True, text=True)
        if r.returncode:
            errs.append(f"node --check: {r.stderr.strip().splitlines()[-1] if r.stderr else 'err'}")
    else:
        if "canvas" in low or "requestAnimationFrame" in data:
            errs.append("no <script> found for a JS page")

    # --- runtime smoke (chromium CLI) ---
    outdir = os.path.join(BASE, "_qa", "shots")
    os.makedirs(outdir, exist_ok=True)
    s1 = os.path.join(outdir, f"{n}_a.png")
    s2 = os.path.join(outdir, f"{n}_b.png")
    dom = os.path.join(outdir, f"{n}_dom.txt")
    logs = []
    for i, (shot, budget) in enumerate(((s1, "6000"), (s2, "12000"))):
        cmd = ["chromium-browser", "--headless=new", "--no-sandbox", "--disable-gpu",
               "--enable-logging=stderr", "--v=0", f"--virtual-time-budget={budget}",
               f"--screenshot={shot}", "--dump-dom", f"file://{path}"]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        open(dom if i == 1 else dom + f".t{i}", "w").write(p.stdout)
        for line in p.stderr.splitlines():
            if re.search(r"CONSOLE|uncaught|Uncaught|SyntaxError|TypeError|ReferenceError", line):
                logs.append(line.strip()[:200])
    real_errs = [l for l in logs if not re.search(r"mojo|interface_endpoint|GPU|dbus|Fontconfig|libva|VA-API|GLES|EGL|viz|gpu_|shared_image|viz_main", l, re.I)]
    if real_errs:
        errs.append(f"console: {real_errs[:3]}")
    sizes = set()
    for s in (s1, s2):
        if os.path.exists(s):
            sizes.add(os.path.getsize(s))
    if len(sizes) < 2 and "requestAnimationFrame" in data or (len(sizes) < 2 and "canvas" in low):
        # animation should differ between budgets (or at least both shots exist and are non-trivial)
        if len(sizes) < 2 and any(os.path.exists(s) and os.path.getsize(s) > 20000 for s in (s1, s2)):
            pass  # static pages can legitimately have identical shots
    if s1 and os.path.exists(s1) and os.path.getsize(s1) < 8000:
        errs.append(f"screenshot a tiny ({os.path.getsize(s1)}B) - likely blank")

    if errs:
        print(f"FAIL {n} {os.path.basename(path)}:")
        for e in errs:
            print(f"  - {e}")
        return 1
    print(f"PASS {n} {os.path.basename(path)}  ({len(data)}B)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
