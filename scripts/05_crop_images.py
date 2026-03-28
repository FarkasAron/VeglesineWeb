"""
05_crop_images.py
-----------------
Crops the full problem region from each source PDF as a PNG.
Produces one PNG per problem number (all sub-parts a/b/c share the same image).

Output per PDF (pdf_stem = filename without .pdf):
  scripts/data/problems/{pdf_stem}/crops/{pdf_stem}_prob_{number:03d}.png

The crop covers the full horizontal text area and the vertical extent of the
entire problem on its first source page, rendered at 2× scale.

Run standalone:
  python scripts/05_crop_images.py

Called by the Streamlit launcher (pipeline_app.py).
"""

from __future__ import annotations

import json
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
# Rendering constants
# ---------------------------------------------------------------------------

CROP_SCALE    = 2.0   # render at 2× for retina sharpness
CROP_MARGIN_X = 40.0  # horizontal margin — trims page number / binding area
CROP_PAD_Y    = 8.0   # vertical padding above/below the problem region

# ---------------------------------------------------------------------------
# Manifest helpers
# ---------------------------------------------------------------------------

def _load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_manifest(manifest: dict) -> None:
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Step-04 import (for y-range computation)
# ---------------------------------------------------------------------------

def _import_step04():
    """Lazy import of step-04 internals to avoid circular import issues."""
    import importlib.util
    name = "step04_segment_problems"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(
        name, SCRIPTS_DIR / "04_segment_problems.py"
    )
    mod = importlib.util.module_from_spec(spec)
    # Must register BEFORE exec_module so @dataclass can resolve cls.__module__
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def compute_problem_yranges(
    pages_data: dict[int, dict],
) -> dict[int, dict[int, tuple[float, float]]]:
    """
    Re-run step-04 segmentation on the extracted page data and return:
      {problem_number: {page_num: (y_start, y_end)}}

    y_end is the y0 of the next problem on that page, or the page height.
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
            starts_on_page = [y for y, p in page_starts[pg] if y > min(ys) + 5]
            y_end = min(starts_on_page) if starts_on_page else 9999.0
            ranges[pg] = (y_start, y_end)
        yranges[pn] = ranges

    return yranges


# ---------------------------------------------------------------------------
# PDF path resolution
# ---------------------------------------------------------------------------

def _find_pdf_path(pdf_stem: str, manifest_entry: dict) -> Path | None:
    local = manifest_entry.get("local_path", "")
    if local:
        p = SCRIPTS_DIR / local
        if p.exists():
            return p
    for candidate in (DATA_DIR / "raw_pdfs").rglob(f"{pdf_stem}.pdf"):
        return candidate
    return None


# ---------------------------------------------------------------------------
# Crop one problem region
# ---------------------------------------------------------------------------

def crop_problem_png(
    doc: fitz.Document,
    page_num_1indexed: int,
    y_start: float,
    y_end: float,
    out_path: Path,
) -> bool:
    """
    Render the problem region [y_start, y_end] on the given page at CROP_SCALE
    and save as PNG. Returns True on success.
    """
    page = doc[page_num_1indexed - 1]

    # Clamp y_end to page height if it was left at the sentinel value
    if y_end >= 9999.0:
        y_end = page.rect.height - CROP_MARGIN_X

    clip = fitz.Rect(
        CROP_MARGIN_X,
        max(0.0, y_start - CROP_PAD_Y),
        page.rect.width - CROP_MARGIN_X,
        min(page.rect.height, y_end + CROP_PAD_Y),
    )
    clip = clip & page.rect

    if clip.is_empty or clip.width < 10 or clip.height < 5:
        return False

    mat = fitz.Matrix(CROP_SCALE, CROP_SCALE)
    pix = page.get_pixmap(matrix=mat, clip=clip, colorspace=fitz.csRGB)
    pix.save(str(out_path))
    return True


# ---------------------------------------------------------------------------
# Per-PDF processing
# ---------------------------------------------------------------------------

def process_pdf(
    pdf_stem: str,
    manifest_entry: dict,
    log: Callable[[str], None],
) -> dict:
    """
    Crop full-problem-region PNGs for every problem in one exam PDF.
    Returns {"crops": int, "ok": bool}.
    """
    ext_dir  = EXTRACTED_DIR / pdf_stem
    prob_dir = PROBLEMS_DIR  / pdf_stem

    if not ext_dir.exists():
        log(f"    [SKIP] Nincs extracted mappa: {pdf_stem}")
        return {"crops": 0, "ok": True}

    # ── Load extracted page JSONs ─────────────────────────────────────────────
    page_files = sorted(
        ext_dir.glob("page_*.json"),
        key=lambda p: int(p.stem.split("_")[1]),
    )
    pages_data: dict[int, dict] = {}
    for pf in page_files:
        d = json.loads(pf.read_text(encoding="utf-8"))
        pages_data[d["page_number"]] = d

    if not pages_data:
        log(f"    [SKIP] Nincs page JSON: {pdf_stem}")
        return {"crops": 0, "ok": True}

    # ── Compute problem y-ranges via step-04 segmentation ────────────────────
    try:
        yranges = compute_problem_yranges(pages_data)
    except Exception as exc:
        log(f"    [HIBA] Y-range számítás sikertelen: {exc}")
        return {"crops": 0, "ok": False, "error": str(exc)}

    if not yranges:
        log(f"    [SKIP] Nincs feladat határvonal: {pdf_stem}")
        return {"crops": 0, "ok": True}

    # ── Find PDF ──────────────────────────────────────────────────────────────
    pdf_path = _find_pdf_path(pdf_stem, manifest_entry)
    if not pdf_path:
        log(f"    [HIBA] PDF nem található: {pdf_stem}")
        return {"crops": 0, "ok": False, "error": "pdf_not_found"}

    # ── Create crops directory ────────────────────────────────────────────────
    crops_dir = prob_dir / "crops"
    crops_dir.mkdir(parents=True, exist_ok=True)

    # ── Open PDF and crop ─────────────────────────────────────────────────────
    doc = fitz.open(str(pdf_path))
    crop_count = 0

    try:
        for prob_num, page_ranges in sorted(yranges.items()):
            # Use the first source page for this problem
            first_page = min(page_ranges.keys())
            y_start, y_end = page_ranges[first_page]

            out_path = crops_dir / f"{pdf_stem}_prob_{prob_num:03d}.png"
            if crop_problem_png(doc, first_page, y_start, y_end, out_path):
                crop_count += 1
    finally:
        doc.close()

    return {"crops": crop_count, "ok": True}


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run(
    log: Callable[[str], None] = print,
    progress_callback: Callable[[int, int], None] | None = None,
) -> dict:
    """
    Crop problem-region PNGs for all PDFs that have been segmented but not yet
    cropped. Sets `crops_generated=True` in the manifest on success.

    Returns summary: processed, skipped, total_crops
    """
    log("=== 05 - Feladat régió kivágás ===")
    manifest = _load_manifest()

    targets = [
        (fname, entry)
        for fname, entry in manifest.items()
        if entry.get("segmented") and not entry.get("crops_generated")
    ]

    if not targets:
        log("Nincs feldolgozandó PDF — minden már ki van vágva.")
        return {"processed": 0, "skipped": 0, "total_crops": 0}

    total = len(targets)
    processed = 0
    total_crops = 0

    for idx, (fname, entry) in enumerate(targets):
        if progress_callback:
            progress_callback(idx, total)

        pdf_stem = Path(entry.get("local_path", fname)).stem
        log(f"  [{idx+1}/{total}] {fname} ...")

        try:
            result = process_pdf(pdf_stem, entry, log)
            total_crops += result["crops"]
            log(f"    OK — {result['crops']} kivágás")
            if result.get("ok", True):
                entry["crops_generated"] = True
                _save_manifest(manifest)
                processed += 1
        except Exception as exc:
            log(f"    [HIBA] {exc}")

    if progress_callback:
        progress_callback(total, total)

    log(f"\nKész: {processed} PDF feldolgozva, {total_crops} kivágás összesen.")
    return {"processed": processed, "skipped": total - processed, "total_crops": total_crops}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    run()
    sys.exit(0)
