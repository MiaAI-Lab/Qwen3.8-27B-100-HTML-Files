GALLERY 100 - PRODUCTION REQUIREMENTS (Zuri's DGX Spark)

You are one of 33 parallel artists producing a gallery of 100 self-contained HTML pages. You own exactly the page indices in your slice file. Work only in /home/zurih/models/Qwen3.8-27b-SGLang/tests/100/ . NEVER look in any other folder.

FOR EACH INDEX IN YOUR SLICE, PRODUCE EXACTLY TWO FILES:
  <NNN-slug>.html   (the exact filename given in your slice)
  <NNN-slug>.txt    (same base name)
Author the HTML by hand - one file at a time, in full. No generators, no templates, no copied boilerplate between pages.

HARD RULES (violations = rejected page):
1. <!DOCTYPE html> line 1; <meta charset=utf-8> and viewport meta; <title> set.
2. ALL CSS in ONE <style> in head. ALL JS in ONE <script> at end of body, inside one IIFE.
3. NO external anything. The substring "http" (and "//cdn", "www.") must appear NOWHERE in the file - not in comments, not in href (use href="#"), not in code (no SVG createElementNS - build runtime SVG as a string via container innerHTML instead). System font stacks only (system-ui / Georgia serif / ui-monospace). No @import, no @font-face with url, no images, no CDN.
4. Fully offline: opening the file alone must work.
5. Responsive down to 360px: clamp() display type, fluid grids, 100dvh.
6. Canvas pages: DPR-aware resize, and call fit() once at boot (not just on resize event).
7. JS quality bar: no "for(const i=0;...;i+=n)" (use let), no duplicated let declarations of shared vars, no bare closePath()/undefined-helper calls, every called function must exist, state declared before boot-time calls that write it. If a rAF frame can throw, the page dies silently - guard it.
8. Size: each .html well over 3000 bytes of real craft.

TXT FORMAT (plain text, exactly these five block labels):
TITLE: <short title>
PROMPT: <the full creative brief for this page - paste your assigned slice text verbatim, it is the exact prompt>
DESCRIPTION: <one paragraph on the intended design>
TECHNIQUES: <comma list of major visual techniques>
INTERACTION: <the intended interaction model - must match what the HTML actually implements: buttons, chips, sliders, keys, pointer>

WORKFLOW (do not skip):
1. Read your slice file (given in goal) ONCE. Do not re-read it or the requirements later.
2. Write the .html for index N with a SINGLE write_file call (full page, ~10-15KB), then the .txt, then verify.
3. Verify page N with the QA runner:
   cd /home/zurih/models/Qwen3.8-27b-SGLang/tests/100 && python3 _qa/run-qa.py NNN
   It runs: html parse, http-substring grep, size check, node --check on the script, then headless-chromium runtime smoke (console errors + canvas pixel probe, ~15s).
   Fix anything it flags; re-run until "PASS".
4. Repeat for the next index. Keep your replies short (progress lines only).

DESIGN STANDARD: each page is a showcase-grade piece - unique concept, palette, layout, motion per your brief. Polish: easing, micro-details, a visible caption/HUD with tracked-caps page name. If a page would not pass as award work, redesign it before verifying.

FINAL: after all indices PASS, your last message = one line per index: "NNN <slug>: PASS" (or "FIXED"). Nothing else.
