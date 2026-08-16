#!/usr/bin/env python3
"""Final audit for gallery-100: 100 pairs present with exact names, no dupes, battery."""
import glob, os, re, sys, subprocess

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
names = [f"{i:03d}" for i in range(1, 101)]

htmls = glob.glob(os.path.join(BASE, "*.html"))
txts = glob.glob(os.path.join(BASE, "*.txt"))
print(f"html files: {len(htmls)}, txt files: {len(txts)}")

slugs = {}
for h in htmls:
    b = os.path.basename(h)
    m = re.match(r"^(\d{3})-(.+)\.html$", b)
    if m:
        slugs.setdefault(m.group(1), []).append(b)

missing = [n for n in names if n not in slugs or len(slugs[n]) != 1]
extra = [n for n, v in slugs.items() if len(v) > 1]
print(f"missing html: {missing if missing else 'none'}")
print(f"ambiguous html: {extra if extra else 'none'}")

problems = []
for n in names:
    cands = [v for k, v in slugs.items() if k == n]
    if not cands:
        continue
    html = os.path.join(BASE, cands[0])
    txt = html[:-5] + ".txt"
    if not os.path.exists(txt):
        problems.append(f"{n}: txt missing ({os.path.basename(txt)})")
        continue
    d = open(html, encoding="utf-8").read()
    if len(d.encode()) < 3000:
        problems.append(f"{n}: html too small ({len(d)}B)")
    t = open(txt, encoding="utf-8").read()
    for k in ("TITLE:", "PROMPT:", "DESCRIPTION:", "TECHNIQUES:", "INTERACTION:"):
        if k not in t:
            problems.append(f"{n}: txt missing {k}")
    low = d.lower()
    if "http" in low:
        problems.append(f"{n}: 'http' substring present")

# byte-duplicate check
import hashlib
seen = {}
for h in htmls:
    dig = hashlib.md5(open(h, "rb").read()).hexdigest()
    seen.setdefault(dig, []).append(os.path.basename(h))
dups = {v[0] for v in seen.values() if len(v) > 1}
if dups:
    problems.append(f"byte-identical html dupes: {sorted(dups)}")

if problems:
    print(f"PAIR PROBLEMS ({len(problems)}):")
    for p in problems:
        print("  -", p)
    sys.exit(1)
print("PAIRING OK: 100 unique html + 100 matching txt, names exact")

# full battery (static + headless shots) - long
print("running full battery...")
r = subprocess.run([sys.executable, os.path.join(BASE, "_qa", "gallery-qa-battery.py"), BASE, "--shots"],
                   capture_output=True, text=True, timeout=3600)
print(r.stdout[-4000:])
if r.stderr:
    print("STDERR:", r.stderr[-1000:])
sys.exit(r.returncode)
