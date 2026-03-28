"""
05_crop_images.py
-----------------
Detects formula regions in each problem's source pages, renders them at 3×
scale as PNG crops, and rebuilds statement_text with {{formula:...}} placeholders.

Formula regions are identified by "constructor" spans — Symbol-font glyphs in
the Private Use Area that Microsoft Equation Editor uses to build extensible
brackets, fractions, integrals, and other multi-line structures:
  \\uf8e0–\\uf8ff  — Equation Editor bracket/fraction constructors
  \\uf0e6–\\uf0ee  — large parenthesis / brace parts  (⎛⎜⎝ etc.)
  \\uf0f6–\\uf0f8  — large right parenthesis parts
  \\uf0ef–\\uf0f2  — integral top/mid/bottom parts

All other Symbol-font PUA chars (simple math operators, Greek letters, etc.)
are replaced inline using SYMBOL_MAP without generating an image.

Input:
  scripts/data/manifest.json
  scripts/data/extracted/{pdf_stem}/page_*.json
  scripts/data/problems/{pdf_stem}/problem_*.json
  scripts/data/raw_pdfs/.../{pdf_stem}.pdf

Output:
  scripts/data/problems/{pdf_stem}/formulas/{stem}_p{page:02d}_{idx:03d}.png
  scripts/data/problems/{pdf_stem}/problem_*.json   (updated statement_text, image_refs)

Run standalone:
  python scripts/05_crop_images.py
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Callable

import fitz  # PyMuPDF

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SCRIPTS_DIR   = Path(__file__).parent
DATA_DIR      = SCRIPTS_DIR / "data"
MANIFEST_PATH = DATA_DIR / "manifest.json"
EXTRACTED_DIR = DATA_DIR / "extracted"
PROBLEMS_DIR  = DATA_DIR / "problems"

# ---------------------------------------------------------------------------
# Symbol font PUA → Unicode mapping
# (chars that PyMuPDF did NOT auto-map; simple inline replacements)
# ---------------------------------------------------------------------------

SYMBOL_MAP: dict[str, str] = {
    "\uf020": " ",
    "\uf021": "!",
    "\uf022": "\u2200",  # ∀
    "\uf023": "#",
    "\uf024": "\u2203",  # ∃
    "\uf025": "%",
    "\uf026": "&",
    "\uf027": "\u220b",  # ∋
    "\uf028": "(",
    "\uf029": ")",
    "\uf02a": "\u2217",  # ∗
    "\uf02b": "+",
    "\uf02c": ",",
    "\uf02d": "\u2212",  # − (minus)
    "\uf02e": ".",
    "\uf02f": "/",
    "\uf030": "0", "\uf031": "1", "\uf032": "2", "\uf033": "3", "\uf034": "4",
    "\uf035": "5", "\uf036": "6", "\uf037": "7", "\uf038": "8", "\uf039": "9",
    "\uf03a": ":", "\uf03b": ";",
    "\uf03c": "<", "\uf03d": "=", "\uf03e": ">",
    "\uf03f": "?",
    "\uf040": "\u2245",  # ≅
    # Greek uppercase
    "\uf041": "Α", "\uf042": "Β", "\uf043": "Χ", "\uf044": "Δ", "\uf045": "Ε",
    "\uf046": "Φ", "\uf047": "Γ", "\uf048": "Η", "\uf049": "Ι", "\uf04a": "ϑ",
    "\uf04b": "Κ", "\uf04c": "Λ", "\uf04d": "Μ", "\uf04e": "Ν", "\uf04f": "Ο",
    "\uf050": "Π", "\uf051": "Θ", "\uf052": "Ρ", "\uf053": "Σ", "\uf054": "Τ",
    "\uf055": "Υ", "\uf056": "ς", "\uf057": "Ω", "\uf058": "Ξ", "\uf059": "Ψ",
    "\uf05a": "Ζ",
    "\uf05b": "[", "\uf05c": "\u2234",  # ∴
    "\uf05d": "]", "\uf05e": "\u22a5",  # ⊥
    "\uf05f": "_", "\uf060": "\u203e",  # ‾
    # Greek lowercase
    "\uf061": "α", "\uf062": "β", "\uf063": "χ", "\uf064": "δ", "\uf065": "ε",
    "\uf066": "φ", "\uf067": "γ", "\uf068": "η", "\uf069": "ι", "\uf06a": "ϕ",
    "\uf06b": "κ", "\uf06c": "λ", "\uf06d": "μ", "\uf06e": "ν", "\uf06f": "ο",
    "\uf070": "π", "\uf071": "θ", "\uf072": "ρ", "\uf073": "σ", "\uf074": "τ",
    "\uf075": "υ", "\uf076": "ϖ", "\uf077": "ω", "\uf078": "ξ", "\uf079": "ψ",
    "\uf07a": "ζ",
    "\uf07b": "{", "\uf07c": "|", "\uf07d": "}", "\uf07e": "~",
    # Extended math symbols
    "\uf0a0": "\u20ac",  # € (sometimes)
    "\uf0a3": "\u2264",  # ≤
    "\uf0a5": "\u221e",  # ∞
    "\uf0a6": "\u0192",  # ƒ
    "\uf0a7": "\u2663",  # ♣
    "\uf0a8": "\u2666",  # ♦
    "\uf0a9": "\u2665",  # ♥
    "\uf0aa": "\u2660",  # ♠
    "\uf0ab": "\u2194",  # ↔
    "\uf0ac": "\u2190",  # ←
    "\uf0ad": "\u2191",  # ↑
    "\uf0ae": "\u2192",  # →
    "\uf0af": "\u2193",  # ↓
    "\uf0b0": "\u00b0",  # °
    "\uf0b1": "\u00b1",  # ±
    "\uf0b2": "\u2033",  # ″
    "\uf0b3": "\u2265",  # ≥
    "\uf0b4": "\u00d7",  # ×
    "\uf0b5": "\u00b5",  # μ (micro)
    "\uf0b6": "\u2202",  # ∂
    "\uf0b7": "\u2022",  # •
    "\uf0b8": "\u00f7",  # ÷
    "\uf0b9": "\u2260",  # ≠
    "\uf0ba": "\u2261",  # ≡
    "\uf0bb": "\u2248",  # ≈
    "\uf0bc": "\u2026",  # …
    "\uf0be": "\u21b5",  # ↵
    "\uf0bf": "\u2135",  # ℵ
    "\uf0c0": "\u2111",  # ℑ
    "\uf0c1": "\u211c",  # ℜ
    "\uf0c2": "\u2118",  # ℘
    "\uf0c3": "\u2297",  # ⊗
    "\uf0c4": "\u2295",  # ⊕
    "\uf0c5": "\u2205",  # ∅
    "\uf0c6": "\u2229",  # ∩
    "\uf0c7": "\u222a",  # ∪
    "\uf0c8": "\u2283",  # ⊃
    "\uf0c9": "\u2287",  # ⊇
    "\uf0ca": "\u2284",  # ⊄
    "\uf0cb": "\u2282",  # ⊂
    "\uf0cc": "\u2286",  # ⊆
    "\uf0cd": "\u2208",  # ∈
    "\uf0ce": "\u2209",  # ∉
    "\uf0cf": "\u2220",  # ∠
    "\uf0d0": "\u2207",  # ∇
    "\uf0d1": "\u00ae",  # ®
    "\uf0d2": "\u00a9",  # ©
    "\uf0d3": "\u2122",  # ™
    "\uf0d4": "\u220f",  # ∏
    "\uf0d5": "\u221a",  # √
    "\uf0d6": "\u22c5",  # ⋅
    "\uf0d7": "\u00d7",  # × (multiplication, 0xD7 in Symbol)
    "\uf0d8": "\u2227",  # ∧
    "\uf0d9": "\u2228",  # ∨
    "\uf0da": "\u21d4",  # ⟺
    "\uf0db": "\u21d4",  # ⟺
    "\uf0dc": "\u21d2",  # ⟹
    "\uf0dd": "\u21d0",  # ⟸
    "\uf0de": "\u25ca",  # ◊
    "\uf0e0": "\u00ae",  # ®
    "\uf0e1": "\u00a9",  # ©
    "\uf0e2": "\u2122",  # ™
    "\uf0e3": "\u2211",  # ∑
    "\uf0ee": "\u23aa",  # ⎪ (brace middle)
    # Scalar braces handled as constructors, but their ASCII fallback:
}

# ---------------------------------------------------------------------------
# Formula constructor character detection
# These characters form multi-line visual structures and MUST be cropped as PNG
# ---------------------------------------------------------------------------

def _is_constructor_char(c: str) -> bool:
    """True if the character is a multi-line Equation Editor constructor glyph."""
    cp = ord(c)
    return (
        0xf8e0 <= cp <= 0xf8ff or   # Equation Editor (MathType) bracket/fraction constructors
        0xf0e4 <= cp <= 0xf0e9 or   # Large parenthesis & bracket parts (⎛⎜⎝ ⎡⎢⎣)
        0xf0f3 <= cp <= 0xf0f5 or   # Integral middle/extensible parts
        0xf0f6 <= cp <= 0xf0f8 or   # Large right parenthesis parts (⎞⎟⎠)
        0xf0f9 <= cp <= 0xf0fb or   # Large right bracket / brace parts
        0xf0ec <= cp <= 0xf0ef or   # Large brace parts (⎧⎨⎩ piecewise)
        0xf0f0 <= cp <= 0xf0f2      # Integral top / mid / bottom
    )


def _has_constructor(span: dict) -> bool:
    return any(_is_constructor_char(c) for c in span.get("text", ""))


def _apply_symbol_map(text: str) -> str:
    """Replace known Symbol PUA chars with their Unicode equivalents."""
    return "".join(SYMBOL_MAP.get(c, c) for c in text)

# ---------------------------------------------------------------------------
# Bounding-box helpers
# ---------------------------------------------------------------------------

def _union_bbox(bboxes: list[list]) -> list[float]:
    return [
        min(b[0] for b in bboxes), min(b[1] for b in bboxes),
        max(b[2] for b in bboxes), max(b[3] for b in bboxes),
    ]


def _bboxes_overlap(b1: list, b2: list, gap: float = 0.0) -> bool:
    """True if b1 and b2 overlap or are within `gap` pt of each other."""
    return (
        b1[0] <= b2[2] + gap and b2[0] <= b1[2] + gap and
        b1[1] <= b2[3] + gap and b2[1] <= b1[3] + gap
    )


def _span_inside(span_bbox: list, region_bbox: list, tol: float = 2.0) -> bool:
    """True if span_bbox is fully inside region_bbox (with tolerance)."""
    return (
        span_bbox[0] >= region_bbox[0] - tol and
        span_bbox[1] >= region_bbox[1] - tol and
        span_bbox[2] <= region_bbox[2] + tol and
        span_bbox[3] <= region_bbox[3] + tol
    )

# ---------------------------------------------------------------------------
# Formula region detection
# ---------------------------------------------------------------------------

_SCORE_RE = re.compile(r"\d+\s*pont", re.IGNORECASE)


def find_formula_regions(page_data: dict) -> list[list[float]]:
    """
    Find formula regions on a page using constructor-span flood-fill.

    Algorithm:
    1. Seed regions from spans with constructor characters.
    2. Iteratively expand each region to include any span whose bbox
       overlaps with the current region bbox (flood-fill).
    3. Merge overlapping regions.
    4. Add CROP_PAD around each final region for the PNG clip rect.

    Returns list of [x0, y0, x1, y1] clip rects (in PDF pt coordinates).
    """
    # Step 1: collect seed bboxes
    seeds: list[list[float]] = []
    for block in page_data.get("text_blocks", []):
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                if _has_constructor(span):
                    seeds.append(list(span["bbox"]))

    if not seeds:
        return []

    # Step 2: flood-fill each seed into a region
    FLOOD_GAP = 2.0   # spans may barely touch the region
    regions: list[list[float]] = []

    for seed in seeds:
        region = list(seed)
        changed = True
        while changed:
            changed = False
            for block in page_data.get("text_blocks", []):
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        sb = span["bbox"]
                        if _bboxes_overlap(sb, region, gap=FLOOD_GAP):
                            expanded = _union_bbox([region, list(sb)])
                            if expanded != region:
                                region = expanded
                                changed = True
        regions.append(region)

    # Step 3: merge overlapping/nearby regions
    # Use a larger gap so that left+right bracket halves of the same formula merge
    MERGE_GAP = 15.0
    merged = True
    while merged:
        merged = False
        new_regions: list[list[float]] = []
        used = [False] * len(regions)
        for i, r1 in enumerate(regions):
            if used[i]:
                continue
            current = r1[:]
            for j in range(i + 1, len(regions)):
                if used[j]:
                    continue
                if _bboxes_overlap(current, regions[j], gap=MERGE_GAP):
                    current = _union_bbox([current, regions[j]])
                    used[j] = True
                    merged = True
            new_regions.append(current)
        regions = new_regions

    # Step 3.5: horizontal expansion — include all spans whose vertical range
    # overlaps the region. This captures equation content beside a large brace
    # (e.g. system of equations where the { is in a narrow column and the
    # equations are horizontally offset by more than FLOOD_GAP).
    V_GAP = 3.0  # vertical tolerance for "same row"
    all_spans: list[list[float]] = [
        list(span["bbox"])
        for block in page_data.get("text_blocks", [])
        for line in block.get("lines", [])
        for span in line.get("spans", [])
    ]
    for idx, region in enumerate(regions):
        ry0, ry1 = region[1], region[3]
        for sb in all_spans:
            # span overlaps region vertically?
            if sb[3] + V_GAP >= ry0 and sb[1] - V_GAP <= ry1:
                # expand region horizontally only
                if sb[0] < region[0]:
                    region[0] = sb[0]
                if sb[2] > region[2]:
                    region[2] = sb[2]
        regions[idx] = region

    # Step 4: add crop padding
    CROP_PAD = 4.0
    return [
        [r[0] - CROP_PAD, r[1] - CROP_PAD, r[2] + CROP_PAD, r[3] + CROP_PAD]
        for r in regions
    ]

# ---------------------------------------------------------------------------
# Segmentation import (y-range computation)
# ---------------------------------------------------------------------------

def _import_step04():
    """Lazy import of step-04 internals to avoid circular issues."""
    import importlib.util, sys as _sys
    name = "step04_segment_problems"
    if name in _sys.modules:
        return _sys.modules[name]
    spec = importlib.util.spec_from_file_location(
        name, SCRIPTS_DIR / "04_segment_problems.py"
    )
    mod = importlib.util.module_from_spec(spec)
    # Must register before exec_module so @dataclass can resolve cls.__module__
    _sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def compute_problem_yranges(pages_data: dict[int, dict]) -> dict[int, dict[int, tuple]]:
    """
    Re-run step-04 segmentation on the given pages and return a mapping:
      {problem_number: {page_num: (y_start, y_end)}}

    y_end is the y0 of the NEXT problem's first line on that page (or 9999).
    """
    mod = _import_step04()

    all_lines: list = []
    all_images: list = []
    for page_num in sorted(pages_data):
        page_data = pages_data[page_num]
        lines = mod._page_lines(page_data)
        if mod._is_instruction_page(lines):
            continue
        if mod._is_cover_page(lines):
            # Preserve section header sentinels
            for ln in lines:
                if (ln.max_size >= mod.SECTION_MIN_SIZE and ln.has_bold
                        and mod.SECTION_RE.match(ln.text)):
                    all_lines.append(ln)
            continue
        all_lines.extend(lines)
        all_images.extend(mod._page_images(page_data))

    raw_problems = mod.segment_into_problems(all_lines, all_images)

    # Build {prob_num: {page: [y0, ...]}} from lines
    prob_page_ys: dict[int, dict[int, list[float]]] = {}
    for prob in raw_problems:
        by_page: dict[int, list[float]] = defaultdict(list)
        for ln in prob.lines:
            by_page[ln.page_number].append(ln.y0)
        prob_page_ys[prob.problem_number] = dict(by_page)

    # Determine y_end as the start of the next problem on the same page
    # Build sorted list of (first_y_on_page, prob_num) per page
    page_starts: dict[int, list[tuple]] = defaultdict(list)
    for pn, by_page in prob_page_ys.items():
        for pg, ys in by_page.items():
            page_starts[pg].append((min(ys), pn))
    for pg in page_starts:
        page_starts[pg].sort()

    yranges: dict[int, dict[int, tuple]] = {}
    for pn, by_page in prob_page_ys.items():
        ranges: dict[int, tuple] = {}
        for pg, ys in by_page.items():
            y_start = min(ys) - 10
            # next problem's y_start on this page
            starts_on_page = [y for y, p in page_starts[pg] if y > min(ys) + 5]
            y_end = min(starts_on_page) if starts_on_page else 9999.0
            ranges[pg] = (y_start, y_end)
        yranges[pn] = ranges

    return yranges

# ---------------------------------------------------------------------------
# Render and crop
# ---------------------------------------------------------------------------

RENDER_SCALE = 3.0


def crop_formula_png(
    doc: fitz.Document,
    page_num_1indexed: int,
    clip_bbox: list[float],
    out_path: Path,
) -> None:
    """Render a clip rect from a PDF page at RENDER_SCALE and save as PNG."""
    page = doc[page_num_1indexed - 1]
    clip = fitz.Rect(*clip_bbox)
    # Clamp to page bounds
    clip = clip & page.rect
    if clip.is_empty:
        return
    mat = fitz.Matrix(RENDER_SCALE, RENDER_SCALE)
    pix = page.get_pixmap(matrix=mat, clip=clip, colorspace=fitz.csRGB)
    pix.save(str(out_path))

# ---------------------------------------------------------------------------
# Statement-text update: apply symbol map + replace constructor runs with PNGs
# ---------------------------------------------------------------------------

# Constructor chars that remain after SYMBOL_MAP and must become formula PNGs
_CONSTRUCTOR_RE = re.compile(
    r"[\uf8e0-\uf8ff"        # Equation Editor constructors
    r"\uf0e4-\uf0e9"         # Large paren / bracket parts
    r"\uf0ec-\uf0ef"         # Large brace parts
    r"\uf0f0-\uf0fb]+"       # Integral + right-bracket parts
)

# Window (chars) within which two constructor runs are considered part of the
# same formula.  Large enough to span numerator/denominator content (digits,
# operators, Greek letters) between the left and right bracket halves.
_FORMULA_WINDOW = 80


def apply_formulas_to_text(
    existing_text: str,
    formula_files: list[str],           # formula PNG filenames in reading order
    formula_bboxes: list[list[float]],  # matching clip bboxes
    formula_pages: list[int],           # matching page numbers
) -> tuple[str, list[dict]]:
    """
    Given the existing statement_text (as produced by step 04):
    1. Apply SYMBOL_MAP to all PUA chars.
    2. Find runs of remaining constructor chars; group nearby runs into
       formula-groups (within _FORMULA_WINDOW chars of each other).
    3. Replace each formula-group span in the text with {{formula:filename.png}}.

    Returns (new_text, image_refs).

    If the number of formula-groups ≠ number of formula PNGs, the first
    min(groups, PNGs) pairs are matched; extras on either side are left as-is
    (text groups remain, extra PNGs go into image_refs without placeholder).
    """
    # Step 1: apply symbol map
    text = _apply_symbol_map(existing_text)

    # Step 2: find all constructor char positions
    matches = list(_CONSTRUCTOR_RE.finditer(text))
    if not matches:
        # No constructors remain — text is already clean
        return text, []

    # Step 3: group nearby matches into formula-groups
    # A group is a list of match objects whose start positions are within
    # _FORMULA_WINDOW chars of the previous match's end.
    groups: list[list] = []   # list of (start, end) pairs covering a formula-group
    current_start = matches[0].start()
    current_end   = matches[0].end()

    for m in matches[1:]:
        if m.start() - current_end <= _FORMULA_WINDOW:
            current_end = m.end()   # extend the current group
        else:
            groups.append((current_start, current_end))
            current_start = m.start()
            current_end   = m.end()
    groups.append((current_start, current_end))

    # Step 4: replace each group with a placeholder (right-to-left to keep indices valid)
    image_refs: list[dict] = []
    n_pairs = min(len(groups), len(formula_files))

    for i in range(n_pairs - 1, -1, -1):
        grp_start, grp_end = groups[i]
        fname  = formula_files[i]
        bbox   = formula_bboxes[i]
        page   = formula_pages[i]
        placeholder = f"{{{{formula:{fname}}}}}"
        text = text[:grp_start] + placeholder + text[grp_end:]
        image_refs.insert(0, {"page": page, "bbox": bbox, "filename": fname})

    # Add any extra formula PNGs (no matching group in text) to image_refs only
    for i in range(n_pairs, len(formula_files)):
        image_refs.append({
            "page": formula_pages[i],
            "bbox": formula_bboxes[i],
            "filename": formula_files[i],
        })

    return text.strip(), image_refs

# ---------------------------------------------------------------------------
# Per-PDF processing
# ---------------------------------------------------------------------------

def _find_pdf_path(pdf_stem: str, manifest_entry: dict) -> Path | None:
    local = manifest_entry.get("local_path", "")
    if local:
        p = SCRIPTS_DIR / local
        if p.exists():
            return p
    # Fallback: search raw_pdfs
    for candidate in (SCRIPTS_DIR / "data" / "raw_pdfs").rglob(f"{pdf_stem}.pdf"):
        return candidate
    return None


def process_pdf(
    pdf_stem: str,
    manifest_entry: dict,
    log: Callable[[str], None],
) -> dict:
    """
    Process one exam PDF: find formula regions, crop PNGs, update problem JSONs.
    Returns summary dict.
    """
    ext_dir  = EXTRACTED_DIR / pdf_stem
    prob_dir = PROBLEMS_DIR  / pdf_stem

    if not ext_dir.exists() or not prob_dir.exists():
        log(f"    [SKIP] Nincs extracted/problems mappa: {pdf_stem}")
        return {"formulas": 0, "updated": 0, "ok": True}

    # ── Load page JSONs ─────────────────────────────────────────────────────
    page_files = sorted(ext_dir.glob("page_*.json"),
                        key=lambda p: int(p.stem.split("_")[1]))
    pages_data: dict[int, dict] = {}
    for pf in page_files:
        d = json.loads(pf.read_text(encoding="utf-8"))
        pages_data[d["page_number"]] = d

    if not pages_data:
        log(f"    [SKIP] Nincs page JSON: {pdf_stem}")
        return {"formulas": 0, "updated": 0, "ok": True}

    # ── Check if any pages have formula constructors ─────────────────────────
    has_any = False
    for page_data in pages_data.values():
        for block in page_data.get("text_blocks", []):
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    if _has_constructor(span):
                        has_any = True
                        break
                if has_any:
                    break
            if has_any:
                break
        if has_any:
            break

    # Even without constructor spans, there may be simple PUA chars (SYMBOL_MAP)
    has_simple_pua = False
    for page_data in pages_data.values():
        for block in page_data.get("text_blocks", []):
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    for c in span.get("text", ""):
                        if 0xe000 <= ord(c) <= 0xf8ff and not _is_constructor_char(c):
                            has_simple_pua = True
                            break

    if not has_any and not has_simple_pua:
        log(f"    [SKIP] Nincs formula: {pdf_stem}")
        return {"formulas": 0, "updated": 0, "ok": True}

    # ── Compute problem y-ranges via step-04 segmentation ───────────────────
    try:
        yranges = compute_problem_yranges(pages_data)
    except Exception as exc:
        log(f"    [HIBA] Y-range szamitas: {exc}")
        return {"formulas": 0, "updated": 0, "ok": False, "error": str(exc)}

    # ── Find formula regions per page ────────────────────────────────────────
    page_regions: dict[int, list[list[float]]] = {}
    for page_num, page_data in pages_data.items():
        regions = find_formula_regions(page_data)
        if regions:
            page_regions[page_num] = regions

    # ── Open PDF for rendering (only if there are constructor formulas) ───────
    pdf_path = _find_pdf_path(pdf_stem, manifest_entry) if has_any else None
    pdf_opened = False
    formulas_dir = prob_dir / "formulas"

    # ── Crop formula PNGs ─────────────────────────────────────────────────────
    # region_info[page_num] = [(clip_bbox, filename), ...]
    region_info: dict[int, list[tuple[list[float], str]]] = {}
    formula_counter = 0

    if pdf_path and pdf_path.exists() and page_regions:
        formulas_dir.mkdir(exist_ok=True)
        doc = fitz.open(str(pdf_path))
        pdf_opened = True
        try:
            for page_num in sorted(page_regions):
                for ri, clip_bbox in enumerate(page_regions[page_num]):
                    fname = f"{pdf_stem}_p{page_num:02d}_{formula_counter:03d}.png"
                    out_path = formulas_dir / fname
                    try:
                        crop_formula_png(doc, page_num, clip_bbox, out_path)
                        region_info.setdefault(page_num, []).append((clip_bbox, fname))
                        formula_counter += 1
                    except Exception as exc:
                        log(f"    [WARN] Crop hiba p{page_num} r{ri}: {exc}")
        finally:
            doc.close()
    elif has_any and (not pdf_path or not pdf_path.exists()):
        log(f"    [WARN] PDF nem talalhato rendereléshez: {pdf_stem}")

    # ── Update each problem JSON ──────────────────────────────────────────────
    prob_files = sorted(prob_dir.glob("problem_*.json"))
    updated_count = 0

    for prob_file in prob_files:
        prob_data = json.loads(prob_file.read_text(encoding="utf-8"))
        source_pages = prob_data.get("source_pages", [])
        prob_num = prob_data.get("problem_number", 0)

        # Gather formula regions that belong to this problem
        prob_formula_regions: list[list[float]] = []
        prob_formula_files: list[str] = []
        prob_formula_pages: list[int] = []

        for page_num in sorted(source_pages):
            y_start, y_end = yranges.get(prob_num, {}).get(page_num, (0.0, 9999.0))
            for clip_bbox, fname in region_info.get(page_num, []):
                region_cy = (clip_bbox[1] + clip_bbox[3]) / 2
                if y_start <= region_cy <= y_end:
                    prob_formula_regions.append(clip_bbox)
                    prob_formula_files.append(fname)
                    prob_formula_pages.append(page_num)

        # Check if this problem has any PUA chars at all
        stmt = prob_data.get("statement_text", "")
        has_pua = any(0xe000 <= ord(c) <= 0xffff for c in stmt)
        has_regions = bool(prob_formula_regions)

        if not has_pua and not has_regions:
            continue  # Nothing to update

        # Rebuild statement_text
        try:
            new_text, image_refs = apply_formulas_to_text(
                existing_text=prob_data.get("statement_text", ""),
                formula_files=prob_formula_files,
                formula_bboxes=prob_formula_regions,
                formula_pages=prob_formula_pages,
            )
        except Exception as exc:
            log(f"    [WARN] Text update hiba {prob_file.name}: {exc}")
            new_text = _apply_symbol_map(prob_data.get("statement_text", ""))
            image_refs = []

        if new_text == prob_data.get("statement_text") and not image_refs:
            continue  # Nothing changed

        prob_data["statement_text"] = new_text
        if image_refs:
            existing = {r["filename"] for r in prob_data.get("image_refs", [])}
            for ref in image_refs:
                if ref["filename"] not in existing:
                    prob_data.setdefault("image_refs", []).append(ref)

        prob_file.write_text(
            json.dumps(prob_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        updated_count += 1

    if pdf_opened:
        log(f"    OK — {formula_counter} formula PNG, {updated_count} JSON frissitve")
    else:
        log(f"    OK — {updated_count} JSON frissitve (csak SYMBOL_MAP, nincs PNG)")

    return {"formulas": formula_counter, "updated": updated_count, "ok": True}

# ---------------------------------------------------------------------------
# Manifest helpers
# ---------------------------------------------------------------------------

def load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_manifest(manifest: dict) -> None:
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run(
    log: Callable[[str], None] = print,
    progress_callback: Callable[[int, int], None] | None = None,
) -> dict:
    log("=== 05 - Formula kepek kivagasa ===")
    manifest = load_manifest()

    targets = [
        (fname, entry)
        for fname, entry in manifest.items()
        if entry.get("segmented")
        and not entry.get("is_solution_pdf")
        and not entry.get("skip_reason")
        and not entry.get("formulas_processed")
    ]

    if not targets:
        log("Nincs feldolgozando PDF (minden mar kesz, vagy nincs szegmentalt adat).")
        return {"processed": 0, "total_formulas": 0, "total_updated": 0}

    total = len(targets)
    total_formulas = 0
    total_updated = 0

    for idx, (fname, entry) in enumerate(targets):
        if progress_callback:
            progress_callback(idx, total)

        pdf_stem = Path(fname).stem
        log(f"  [{idx+1}/{total}] {fname} ...")

        try:
            result = process_pdf(pdf_stem, entry, log)
            if result.get("ok", True):   # mark processed only on success
                entry["formulas_processed"] = True
            entry["formula_processing"] = result
            save_manifest(manifest)
            total_formulas += result.get("formulas", 0)
            total_updated  += result.get("updated", 0)
        except Exception as exc:
            import traceback
            log(f"    HIBA: {exc}")
            log(traceback.format_exc())

    if progress_callback:
        progress_callback(total, total)

    log(
        f"\nKesz: {total} PDF feldolgozva, "
        f"{total_formulas} formula PNG, "
        f"{total_updated} problem JSON frissitve."
    )
    return {
        "processed": total,
        "total_formulas": total_formulas,
        "total_updated": total_updated,
    }

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    run()
    sys.exit(0)
