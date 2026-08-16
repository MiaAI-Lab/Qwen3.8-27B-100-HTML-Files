# Qwen3.8 27b 100 HTML Files

One hundred self-contained HTML visual studies — glassmorphism, generative canvas art, physics toys, kinetic typography, data-viz, scroll stories and more. Each page is fully offline: no external fonts, images, CDNs or libraries.

## Browsing

Open [index.html](index.html) in a browser — it lists all 100 pieces with:

- **Open** — launches the page in a new tab
- **Prompt** — expands the original generation prompt used for that piece, sourced from the matching `.txt` file
- Live search by name, number, or prompt text

## File layout

Each study is a numbered pair of files:

```
NNN-slug.html   # the page — all CSS in one <style>, all JS in one <script> IIFE
NNN-slug.txt    # metadata for that page
```

The `.txt` files follow a fixed five-field format:

```
TITLE: <short title>
PROMPT: <the full creative brief, verbatim>
DESCRIPTION: <one paragraph on the intended design>
TECHNIQUES: <comma list of major visual techniques>
INTERACTION: <the intended interaction model>
```

## Technical constraints

All pages were produced under these hard rules:

1. `<!DOCTYPE html>` on line 1, with charset and viewport meta
2. All CSS in a single `<style>` in `<head>`; all JS in a single `<script>` at end of body, wrapped in one IIFE
3. Zero external references — the substring `http` must not appear anywhere in the file; system font stacks only
4. Fully offline: opening the file alone must work
5. Responsive down to 360px (`clamp()` display type, fluid grids, `100dvh`)
6. Canvas pages are devicePixelRatio-aware and fit once at boot
7. Every page well over 3000 bytes of real, hand-authored craft

## Production notes

Each page was generated from a per-slice creative brief (its verbatim text is the `PROMPT:` field in the matching `.txt`) and verified before publishing: HTML parse, `http`-substring grep, size check, JS syntax check, and a headless-Chromium runtime smoke test (console errors + canvas pixel probe). The briefs and QA tooling were intentionally kept out of this repo.
