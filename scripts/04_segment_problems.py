"""
04_segment_problems.py
----------------------
Segments extracted page JSON files into individual problem JSON files,
one per problem (or per sub-part when a)/b)/c) are present).

Input:  scripts/data/extracted/{pdf_stem}/page_*.json
Output: scripts/data/problems/{pdf_stem}/problem_{n:03d}[_{part}].json

Problem JSON schema:
  {
    "pdf_filename": str,
    "pdf_stem": str,
    "year": int,
    "exam_type": str,         # "kozep" | "emelt"
    "exam_session": str,      # "majus" | "oktober" | "februar"
    "is_secondary_language": bool,
    "exam_part": str | None,  # "I" | "II" | None
    "problem_number": int,
    "sub_part": str | None,   # "a" | "b" | "c" | None
    "statement_text": str,    # plain text; image refs as {{formula:filename}}
    "max_points": int | None,
    "source_pages": [int],
    "image_refs": [           # bounding boxes for step 05 (image cropping)
      {"page": int, "bbox": [x0,y0,x1,y1], "filename": str|None}
    ],
    "ocr_used": bool,
    "human_reviewed": false,
    "notes": str
  }

Run standalone:
  python scripts/04_segment_problems.py

Called by the Streamlit launcher (pipeline_app.py).
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

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
# Layout constants  (A4 in points: 595 × 842)
# ---------------------------------------------------------------------------

# Problem number: bold, large font, left-aligned
PROB_NUM_MIN_SIZE  = 13.0   # pt  (observed: 13.98–14.0)
PROB_NUM_MAX_X     = 85     # left-margin threshold

# Matches "13." (number only) OR "14.  Az ABCD..." (number + inline text)
PROB_NUM_ONLY_RE   = re.compile(r"^(\d{1,2})\.$")
PROB_NUM_INLINE_RE = re.compile(r"^(\d{1,2})\.\s{1,5}(\S.*)$")

# Section header: "I." / "II." separating exam parts
# NOTE: no x0 constraint — közép exams have centred "II." headers
SECTION_MIN_SIZE   = 15.0
SECTION_RE         = re.compile(r"^(I{1,3}|IV|V)\.$")

# Sub-part label: "a)" / "b)" / "c)" at left margin
SUBPART_MAX_X      = 85
SUBPART_RE         = re.compile(r"^([a-e])\)\s*")

# Score box: "N pont" or "Ö.: N pont" — right-side column
SCORE_MIN_X        = 180
SCORE_RE           = re.compile(r"(\d+)\s*pont", re.IGNORECASE)
TOTAL_SCORE_RE     = re.compile(r"[OÖ]\.\s*:?\s*.*?(\d+)\s*pont", re.IGNORECASE)

# Header/footer strip zone (y < TOP_SKIP or y > BOTTOM_SKIP)
TOP_SKIP    = 70    # pt from top of page
BOTTOM_SKIP = 760   # pt from top (A4 height ~842)

# Instruction page detector
INSTRUCTION_MARKERS = ["Fontos tudnivalók", "tudnivalók"]


# ---------------------------------------------------------------------------
# Line dataclass
# ---------------------------------------------------------------------------

@dataclass
class Line:
    page_number: int
    y0: float
    x0: float
    text: str         # joined span texts
    max_size: float
    has_bold: bool
    spans: list       # raw span list (kept for formula detection)
    block_no: int


@dataclass
class ImageRef:
    page: int
    bbox: list
    filename: str | None


# ---------------------------------------------------------------------------
# Page parsing helpers
# ---------------------------------------------------------------------------

def _page_lines(page_data: dict) -> list[Line]:
    """
    Convert a page JSON dict into a flat list of Line objects,
    filtering header/footer zones.
    """
    lines: list[Line] = []
    page_num = page_data["page_number"]
    page_h   = page_data["height"]
    bottom   = min(BOTTOM_SKIP, page_h - 30)

    for block in page_data["text_blocks"]:
        x0_block = block["bbox"][0]
        for ln in block["lines"]:
            y0 = ln["bbox"][1]
            # Skip header and footer zones
            if y0 < TOP_SKIP or y0 > bottom:
                continue
            spans = ln["spans"]
            text = "".join(sp["text"] for sp in spans)
            stripped = text.strip()
            if not stripped:
                continue
            max_size = max((sp["size"] for sp in spans), default=0)
            has_bold = any(bool(sp["flags"] & 4) for sp in spans)
            lines.append(Line(
                page_number=page_num,
                y0=y0,
                x0=x0_block,
                text=stripped,
                max_size=max_size,
                has_bold=has_bold,
                spans=spans,
                block_no=block["block_no"],
            ))
    return lines


def _page_images(page_data: dict) -> list[ImageRef]:
    """Extract image block refs from a page JSON."""
    refs = []
    for ib in page_data.get("image_blocks", []):
        if ib.get("image_filename"):
            refs.append(ImageRef(
                page=page_data["page_number"],
                bbox=ib["bbox"],
                filename=ib["image_filename"],
            ))
    return refs


def _is_instruction_page(lines: list[Line]) -> bool:
    joined = " ".join(ln.text for ln in lines[:20])
    return any(marker in joined for marker in INSTRUCTION_MARKERS)


def _is_cover_page(lines: list[Line]) -> bool:
    """Cover pages have large centred text (ÉRETTSÉGI VIZSGA) but no problem numbers."""
    if not lines:
        return True
    has_problem = any(
        (PROB_NUM_ONLY_RE.match(ln.text) or PROB_NUM_INLINE_RE.match(ln.text))
        and ln.x0 <= PROB_NUM_MAX_X
        and ln.max_size >= PROB_NUM_MIN_SIZE
        for ln in lines
    )
    return not has_problem


def _is_score_line(ln: Line) -> bool:
    return ln.x0 >= SCORE_MIN_X and bool(SCORE_RE.search(ln.text))


def _extract_points(ln: Line) -> int | None:
    """Try to extract a total point value from a score-box line."""
    m = TOTAL_SCORE_RE.search(ln.text)
    if m:
        return int(m.group(1))
    m = SCORE_RE.search(ln.text)
    if m:
        return int(m.group(1))
    return None


# ---------------------------------------------------------------------------
# Core segmentation
# ---------------------------------------------------------------------------

@dataclass
class RawProblem:
    problem_number: int
    exam_part: str | None
    source_pages: list[int] = field(default_factory=list)
    lines: list[Line] = field(default_factory=list)
    images: list[ImageRef] = field(default_factory=list)
    max_points: int | None = None


def segment_into_problems(all_lines: list[Line], all_images: list[ImageRef]) -> list[RawProblem]:
    """
    Walk all lines and group them into RawProblem objects.
    Detects:
      - Section headers (I. / II.) → updates current exam_part
      - Problem boundaries (bold N. at left margin) → starts new problem
    Score-box lines are used only to extract max_points, then discarded.
    """
    problems: list[RawProblem] = []
    current: RawProblem | None = None
    current_part: str | None = None
    image_iter_idx = 0

    def _attach_images_up_to_y(prob: RawProblem, page: int, y: float) -> None:
        nonlocal image_iter_idx
        while image_iter_idx < len(all_images):
            ref = all_images[image_iter_idx]
            if ref.page < page or (ref.page == page and ref.bbox[1] <= y):
                if current is not None:
                    prob.images.append(ref)
                image_iter_idx += 1
            else:
                break

    for ln in all_lines:
        # ── Section header (I. / II.) ────────────────────────────────────────
        # No x0 constraint: közép "II." headers are centred on the page
        if ln.max_size >= SECTION_MIN_SIZE and ln.has_bold:
            m = SECTION_RE.match(ln.text)
            if m:
                new_part = m.group(1)
                # If we're seeing "II." for the first time and previous problems
                # had no part, retroactively assign them to "I"
                if new_part == "II" and current_part is None:
                    for prob in problems:
                        if prob.exam_part is None:
                            prob.exam_part = "I"
                    if current is not None and current.exam_part is None:
                        current.exam_part = "I"
                current_part = new_part
                continue

        # ── Problem boundary (number-only line: "13.") ───────────────────────
        if (ln.max_size >= PROB_NUM_MIN_SIZE and ln.has_bold
                and ln.x0 <= PROB_NUM_MAX_X):

            m_only   = PROB_NUM_ONLY_RE.match(ln.text)
            m_inline = PROB_NUM_INLINE_RE.match(ln.text)

            if m_only or m_inline:
                num = int((m_only or m_inline).group(1))
                if current is not None:
                    _attach_images_up_to_y(current, ln.page_number, ln.y0)
                    problems.append(current)
                current = RawProblem(
                    problem_number=num,
                    exam_part=current_part,
                    source_pages=[ln.page_number],
                )
                # If number and text are on the same line, keep the text part
                if m_inline:
                    inline_text = m_inline.group(2).strip()
                    if inline_text:
                        # Re-use the same line but with the number stripped
                        text_ln = Line(
                            page_number=ln.page_number,
                            y0=ln.y0,
                            x0=ln.x0,
                            text=inline_text,
                            max_size=ln.max_size,
                            has_bold=ln.has_bold,
                            spans=ln.spans,
                            block_no=ln.block_no,
                        )
                        current.lines.append(text_ln)
                continue

        if current is None:
            continue  # text before first problem — skip

        # Track which pages this problem spans
        if ln.page_number not in current.source_pages:
            current.source_pages.append(ln.page_number)

        # ── Score box line ───────────────────────────────────────────────────
        if _is_score_line(ln):
            pts = _extract_points(ln)
            if pts is not None:
                # Keep highest value (multi-sub-part total > sub-part scores)
                if current.max_points is None or pts > current.max_points:
                    current.max_points = pts
            continue

        current.lines.append(ln)

    # Flush last problem
    if current is not None:
        _attach_images_up_to_y(current, 9999, 9999)
        problems.append(current)

    return problems


# ---------------------------------------------------------------------------
# Sub-part splitting
# ---------------------------------------------------------------------------

@dataclass
class SubPart:
    label: str | None          # "a", "b", "c", or None
    lines: list[Line]
    images: list[ImageRef]
    max_points: int | None = None


def split_subparts(prob: RawProblem) -> list[SubPart]:
    """
    Split a RawProblem's lines at sub-part labels (a), b), c)…).
    Returns a list of SubPart objects.  If no sub-parts found,
    returns a single SubPart with label=None.
    """
    # Find lines that START a new sub-part (at left margin)
    split_indices: list[tuple[int, str]] = []   # (line_index, label)
    for i, ln in enumerate(prob.lines):
        if ln.x0 <= SUBPART_MAX_X:
            m = SUBPART_RE.match(ln.text)
            if m:
                split_indices.append((i, m.group(1)))

    if not split_indices:
        return [SubPart(label=None, lines=prob.lines, images=prob.images)]

    parts: list[SubPart] = []
    boundaries = [idx for idx, _ in split_indices]
    labels     = [lbl for _, lbl  in split_indices]

    # Text before first sub-part = shared preamble
    preamble_lines  = prob.lines[:boundaries[0]]
    preamble_images = [
        img for img in prob.images
        if not split_indices or img.bbox[3] <= (prob.lines[boundaries[0]].y0 if preamble_lines else 0)
    ]

    for i, (start, label) in enumerate(zip(boundaries, labels)):
        end = boundaries[i + 1] if i + 1 < len(boundaries) else len(prob.lines)
        part_lines = preamble_lines + prob.lines[start:end]

        # Images whose bottom y sits within this sub-part's y range
        y_start = prob.lines[start].y0 if start < len(prob.lines) else 0
        y_end   = prob.lines[end - 1].y0 if end - 1 < len(prob.lines) else 999999
        part_images = [
            img for img in prob.images
            if y_start <= img.bbox[1] <= y_end or img in preamble_images
        ]

        parts.append(SubPart(label=label, lines=part_lines, images=part_images))

    return parts


# ---------------------------------------------------------------------------
# Text assembly
# ---------------------------------------------------------------------------

# Spans whose text is mostly non-letter Unicode (math symbols, etc.)
# These mark inline formula regions and will be replaced by a placeholder.
_MATH_SYMBOL_RE = re.compile(r"^[\s\u0000-\u001f\u00b0-\u00bf\u03b1-\u03c9\u2200-\u22ff\ufb00-\ufffd]+$")

def _is_formula_span(span: dict) -> bool:
    """True if a span looks like a formula symbol (tiny size or non-Latin chars)."""
    text = span.get("text", "").strip()
    if not text:
        return False
    # Very small superscript/subscript often indicates formula content
    if span.get("size", 12) < 9:
        return True
    # Predominantly non-letter characters
    letter_ratio = sum(1 for c in text if c.isalpha()) / max(len(text), 1)
    return letter_ratio < 0.3 and len(text) < 10


def assemble_text(lines: list[Line], images: list[ImageRef], pdf_stem: str) -> str:
    """
    Join line texts into a readable statement_text.
    Images are inserted as {{formula:filename}} placeholders at their
    approximate reading position.

    Image y-positions are interleaved with line y-positions so they appear
    in the correct reading order.
    """
    # Build a combined event list: (y, page, type, content)
    events: list[tuple[float, int, str, object]] = []

    for ln in lines:
        events.append((ln.y0, ln.page_number, "line", ln))

    for img in images:
        if img.filename:
            events.append((img.bbox[1], img.page, "image", img))

    events.sort(key=lambda e: (e[1], e[0]))  # sort by page then y

    parts: list[str] = []
    prev_y: float | None = None
    prev_page: int | None = None

    for y, page, kind, content in events:
        if kind == "image":
            img: ImageRef = content
            parts.append(f"{{{{formula:{img.filename}}}}}")
            prev_y = y
            prev_page = page
            continue

        ln: Line = content

        # Insert blank line for large vertical gaps (paragraph break)
        if prev_y is not None and prev_page == page:
            gap = y - prev_y
            if gap > 30:
                parts.append("")

        # Use the already-processed line text (avoids re-reading raw spans
        # which would re-introduce stripped prefixes like "14.")
        line_text = ln.text.strip()
        if line_text:
            parts.append(line_text)

        prev_y = y
        prev_page = page

    return "\n".join(parts).strip()


# ---------------------------------------------------------------------------
# JSON output
# ---------------------------------------------------------------------------

def build_problem_json(
    sub: SubPart,
    prob: RawProblem,
    manifest_entry: dict,
    pdf_stem: str,
    ocr_used: bool,
) -> dict:
    return {
        "pdf_filename": manifest_entry.get("url", "").rsplit("/", 1)[-1] or pdf_stem + ".pdf",
        "pdf_stem": pdf_stem,
        "year": manifest_entry.get("year"),
        "exam_type": manifest_entry.get("exam_type"),
        "exam_session": manifest_entry.get("exam_session"),
        "is_secondary_language": manifest_entry.get("is_secondary_language", False),
        "exam_part": prob.exam_part,
        "problem_number": prob.problem_number,
        "sub_part": sub.label,
        "statement_text": assemble_text(sub.lines, sub.images, pdf_stem),
        "max_points": prob.max_points,
        "source_pages": prob.source_pages,
        "image_refs": [
            {"page": img.page, "bbox": img.bbox, "filename": img.filename}
            for img in sub.images
        ],
        "ocr_used": ocr_used,
        "human_reviewed": False,
        "notes": "",
    }


def save_problem(data: dict, out_dir: Path, prob_num: int, sub_label: str | None) -> Path:
    if sub_label:
        fname = f"problem_{prob_num:03d}_{sub_label}.json"
    else:
        fname = f"problem_{prob_num:03d}.json"
    path = out_dir / fname
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Per-PDF pipeline
# ---------------------------------------------------------------------------

def process_pdf(pdf_stem: str, manifest_entry: dict, log: Callable) -> dict:
    """
    Segment one PDF's extracted pages into problem JSONs.
    Returns summary: {problems, sub_parts, skipped_pages, ocr_used}
    """
    ext_dir  = EXTRACTED_DIR / pdf_stem
    prob_dir = PROBLEMS_DIR / pdf_stem
    prob_dir.mkdir(parents=True, exist_ok=True)

    # Load all page JSONs in order
    page_files = sorted(ext_dir.glob("page_*.json"),
                        key=lambda p: int(p.stem.split("_")[1]))
    if not page_files:
        log(f"  [HIBA] Nincs page JSON: {ext_dir}")
        return {"problems": 0, "sub_parts": 0, "skipped_pages": 0, "ocr_used": False}

    all_lines:  list[Line]     = []
    all_images: list[ImageRef] = []
    skipped = 0
    ocr_used = False

    for pf in page_files:
        page_data = json.loads(pf.read_text(encoding="utf-8"))
        if page_data.get("ocr_used"):
            ocr_used = True

        lines = _page_lines(page_data)

        if _is_instruction_page(lines):
            skipped += 1
            continue

        if _is_cover_page(lines):
            # Cover/title pages have no problems but may carry section headers
            # (e.g. közép "II." is centred on a standalone cover page).
            # Add a sentinel line for each section header so the segmenter sees it.
            for ln in lines:
                if ln.max_size >= SECTION_MIN_SIZE and ln.has_bold and SECTION_RE.match(ln.text):
                    all_lines.append(ln)
            skipped += 1
            continue

        all_lines.extend(lines)
        all_images.extend(_page_images(page_data))

    if not all_lines:
        log(f"  [WARN] Nincs szoveges tartalom: {pdf_stem}")
        return {"problems": 0, "sub_parts": 0, "skipped_pages": skipped, "ocr_used": ocr_used}

    raw_problems = segment_into_problems(all_lines, all_images)
    sub_part_count = 0

    for prob in raw_problems:
        sub_parts = split_subparts(prob)
        for sub in sub_parts:
            data = build_problem_json(sub, prob, manifest_entry, pdf_stem, ocr_used)
            save_problem(data, prob_dir, prob.problem_number, sub.label)
            sub_part_count += 1

    return {
        "problems": len(raw_problems),
        "sub_parts": sub_part_count,
        "skipped_pages": skipped,
        "ocr_used": ocr_used,
    }


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
    log("=== 04 - Feladatok szegmentalasa ===")
    manifest = load_manifest()

    targets = [
        (fname, entry)
        for fname, entry in manifest.items()
        if entry.get("extracted")
        and not entry.get("is_solution_pdf")
        and not entry.get("skip_reason")
        and not entry.get("segmented")
    ]

    if not targets:
        log("Nincs szegmentalando PDF.")
        return {"processed": 0, "total_problems": 0, "total_sub_parts": 0}

    total = len(targets)
    total_problems = 0
    total_sub_parts = 0

    for idx, (fname, entry) in enumerate(targets):
        if progress_callback:
            progress_callback(idx, total)

        pdf_stem = Path(fname).stem
        ext_dir  = EXTRACTED_DIR / pdf_stem

        if not ext_dir.exists():
            log(f"  [{idx+1}/{total}] {fname} — hiányzó extracted mappa, kihagyva")
            continue

        log(f"  [{idx+1}/{total}] {fname} ...")
        try:
            result = process_pdf(pdf_stem, entry, log)
            entry["segmented"] = True
            entry["segmentation"] = result
            save_manifest(manifest)
            total_problems   += result["problems"]
            total_sub_parts  += result["sub_parts"]
            log(f"    OK - {result['problems']} feladat, {result['sub_parts']} sor "
                f"({result['skipped_pages']} oldal kihagyva)")
        except Exception as exc:
            import traceback
            log(f"    HIBA: {exc}")
            log(traceback.format_exc())

    if progress_callback:
        progress_callback(total, total)

    log(f"\nKesz: {total} PDF feldolgozva, {total_problems} feladat, {total_sub_parts} sor ossz.")
    return {"processed": total, "total_problems": total_problems, "total_sub_parts": total_sub_parts}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    run()
    sys.exit(0)
