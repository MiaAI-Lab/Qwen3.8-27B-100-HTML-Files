#!/usr/bin/env python3
"""Parent-level gallery check: N html + N txt pairs named NNN-slug.* in one dir.

Usage: python3 verify-gallery-pairs.py <dir> [expected=100]

Checks every index 1..expected has BOTH .html and .txt; doctype; no external
refs; size floor; byte-unique html (no duplicated pages); txt has the five
blocks. Exits non-zero on any problem or count mismatch. Ignores files that
start with '_' or '.'. Run after EVERY delegated batch and at the end.
"""
import hashlib, html.parser, os, re, sys


class P(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.err = None
    def error(self, m):
        self.err = m


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else '.'
    expected = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    problems = []
    htmls, txts = {}, {}
    for fn in sorted(os.listdir(root)):
        if fn.startswith('_') or fn.startswith('.'):
            continue
        base, ext = os.path.splitext(fn)
        if ext == '.html':
            htmls[base] = fn
        elif ext == '.txt':
            txts[base] = fn
    print(f"html: {len(htmls)}  txt: {len(txts)}  expected pairs: {expected}")
    # Match by 3-digit PREFIX: basenames are "001-aurora-glass", so an
    # exact-key lookup ("001" not in {"001-aurora-glass", ...}) is always True
    # and falsely reports EVERY file missing. Never `n not in htmls` directly.
    prefixes = {b[:3] for b in htmls} | {b[:3] for b in txts}
    for i in range(1, expected + 1):
        n = f"{i:03d}"
        if n not in prefixes:
            problems.append(f"MISSING {n}.html")
            problems.append(f"MISSING {n}.txt")
    for base in sorted(set(htmls) | set(txts)):
        if base in htmls and base not in txts:
            problems.append(f"NO TXT for {base}.html")
        if base in txts and base not in htmls:
            problems.append(f"NO HTML for {base}.txt")
    hashes = {}
    for base, fn in sorted(htmls.items()):
        path = os.path.join(root, fn)
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                src = f.read()
        except Exception as e:
            problems.append(f"UNREADABLE {fn}: {e}")
            continue
        size = os.path.getsize(path)
        if size < 3000:
            problems.append(f"SMALL ({size}B) {fn}")
        if not re.search(r'<!doctype\s+html', src, re.I):
            problems.append(f"NO DOCTYPE {fn}")
        for pat in [r'https?://', r'@import', r'//cdn',
                    r'<script[^>]+src=', r'<link[^>]+href=[^#]']:
            m = re.search(pat, src)
            if m:
                problems.append(f"EXTERNAL REF {fn}: {src[max(0,m.start()-30):m.start()+30]!r}")
        parser = P()
        try:
            parser.feed(src)
            parser.close()
        except Exception as e:
            problems.append(f"PARSE FAIL {fn}: {e}")
        else:
            if parser.err:
                problems.append(f"PARSE ERR {fn}: {parser.err}")
        hashes.setdefault(hashlib.md5(src.encode('utf-8', 'replace')).hexdigest(), []).append(fn)
    for base, fn in sorted(txts.items()):
        with open(os.path.join(root, fn), 'r', encoding='utf-8', errors='replace') as f:
            t = f.read()
        if len(t.strip()) < 300:
            problems.append(f"THIN TXT ({len(t.strip())} chars) {fn}")
        low = t.lower()
        for kw in ['title', 'prompt', 'description', 'techniques', 'interaction']:
            if kw not in low:
                problems.append(f"TXT MISSING '{kw}' {fn}")
    dups = [v for v in hashes.values() if len(v) > 1]
    if dups:
        problems.append(f"DUPLICATE PAGES {dups}")
    total = len(htmls) + len(txts)
    print(f"TOTAL FILES: {total}")
    for p in problems:
        print(" - " + p)
    ok = (len(htmls) == expected and len(txts) == expected and not problems)
    print("RESULT:", "PASS" if ok else "PROBLEMS FOUND")
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
