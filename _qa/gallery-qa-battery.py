#!/usr/bin/env python3
"""Parent-side one-pass gallery battery (no playwright needed).

Usage: python3 gallery-qa-battery.py <gallery_dir> [--shots]

Per .html: doctype present, no 'http' substring, no @import, size > 3000B,
file ends with </html> (tail-end check — catches multi-pass assembly that
dropped the close tags), rAF-killer regex (for(const x=...; ...; x += ...)
=> zero hits), html.parser feed, and node --check on the extracted
<script> body (written to a REAL temp file inside the gallery dir — never
piped via stdin). Then delegates to verify-gallery-pairs.py (this dir) for
pairing / duplication / txt-block checks over the full 1..100 set.

--shots additionally runs headless chromium on every page
(--headless=new --no-sandbox --disable-gpu --virtual-time-budget=6000
--screenshot) into <gallery_dir>/_shots/ and flags any page whose screenshot
is missing or < 4KB (blank/broken render). All artifacts live inside the
gallery dir (snap-confined chromium cannot read/write /tmp) — delete
_shots/ and _qa_tmp_check.js when done.

Exit 0 only when everything passes.
"""
import glob
import html.parser as hp
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KILLER = re.compile(r'for\s*\(\s*const\s+(\w+)\s*=[^;]*;[^;]*;\s*\1\s*(?:\+=|-=|\*=|/=)')


def extract_js(src):
    m = re.search(r'<script>(.*?)</script>', src, re.S)
    return m.group(1) if m else None


def check_page(path, problems, jsfile):
    fn = os.path.basename(path)
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        src = f.read()
    if not re.search(r'<!doctype\s+html', src, re.I):
        problems.append(f'{fn}: no doctype')
    m = re.search(r'http', src, re.I)
    if m:
        problems.append(f'{fn}: contains "http" :: {src[max(0, m.start() - 40):m.start() + 40]!r}')
    if '@import' in src:
        problems.append(f'{fn}: @import present')
    if os.path.getsize(path) < 3000:
        problems.append(f'{fn}: small ({os.path.getsize(path)}B)')
    if not src.rstrip().endswith('</html>'):
        problems.append(f'{fn}: missing end tags :: tail={src[-40:]!r}')
    m = KILLER.search(src)
    if m:
        problems.append(f'{fn}: rAF-KILLER for-const reassignment :: {m.group(0)!r}')

    class P(hp.HTMLParser):
        err = None

        def error(self, msg):
            self.err = msg

    p = P()
    try:
        p.feed(src)
        p.close()
    except Exception as e:
        problems.append(f'{fn}: PARSE FAIL {e}')

    js = extract_js(src)
    if js is None:
        problems.append(f'{fn}: no <script> block')
        return
    with open(jsfile, 'w') as f:
        f.write(js)
    r = subprocess.run(['node', '--check', jsfile], capture_output=True, text=True)
    if r.returncode != 0:
        problems.append(f'{fn}: node --check FAIL :: {r.stderr.strip()[:300]}')


def shots(gallery, htmls, problems):
    binpath = (shutil.which('chromium-browser') or shutil.which('chromium')
               or shutil.which('google-chrome'))
    if not binpath:
        problems.append('--shots: no chromium binary found')
        return
    shotdir = os.path.join(gallery, '_shots')
    os.makedirs(shotdir, exist_ok=True)
    bad = []
    for p in htmls:
        fn = os.path.basename(p)[:-5]
        out = os.path.join(shotdir, fn + '.png')
        cmd = [binpath, '--headless=new', '--no-sandbox', '--disable-gpu',
               '--hide-scrollbars', '--force-device-scale-factor=1',
               '--virtual-time-budget=6000', f'--screenshot={out}',
               'file://' + p]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        except subprocess.TimeoutExpired:
            r = None
        if (r is None or r.returncode != 0 or not os.path.exists(out)
                or os.path.getsize(out) < 4000):
            bad.append(fn)
    if bad:
        problems.append('shots blank/failed: ' + ', '.join(bad))
    else:
        print(f'shots: all {len(htmls)} rendered -> {shotdir} (delete when done)')


def main():
    args = list(sys.argv[1:])
    do_shots = '--shots' in args
    args = [a for a in args if a != '--shots']
    gallery = os.path.abspath(args[0] if args else os.getcwd())
    htmls = sorted(glob.glob(os.path.join(gallery, '*.html')))
    print(f'gallery: {gallery}   html files: {len(htmls)}')
    problems = []
    jsfile = os.path.join(gallery, '_qa_tmp_check.js')
    for p in htmls:
        check_page(p, problems, jsfile)
    if os.path.exists(jsfile):
        os.remove(jsfile)
    pairs = os.path.join(HERE, 'verify-gallery-pairs.py')
    if os.path.exists(pairs):
        r = subprocess.run(['python3', pairs, gallery, '100'],
                           capture_output=True, text=True)
        print(r.stdout.strip())
        if r.returncode != 0:
            problems.append('verify-gallery-pairs.py reported problems (see above)')
    else:
        problems.append('verify-gallery-pairs.py not found next to battery script')
    if do_shots:
        shots(gallery, htmls, problems)
    if problems:
        print('=== PROBLEMS ===')
        for x in problems:
            print(' - ' + x)
        sys.exit(1)
    print('BATTERY PASS')


if __name__ == '__main__':
    main()
