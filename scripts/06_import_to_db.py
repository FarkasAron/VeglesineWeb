"""
06_import_to_db.py
------------------
Uploads formula PNGs to Supabase Storage and upserts every problem JSON as a
row in the `problems` table with human_reviewed=false.

Pre-requisites:
  1. Run supabase/migrations/001_create_problems.sql in the Supabase SQL editor
     ONCE before the first run of this script.
  2. .env.local (project root) must contain:
       NEXT_PUBLIC_SUPABASE_URL=...
       SUPABASE_SERVICE_ROLE_KEY=...

Re-running is safe:
  - Already-imported rows are updated (upsert on source_key).
  - Rows that have already been reviewed (human_reviewed=true) are SKIPPED to
    avoid overwriting the teacher's review work.
  - Formula PNGs are uploaded with upsert=true (overwrite if changed).

Run standalone:
  python scripts/06_import_to_db.py

Called by the Streamlit launcher (pipeline_app.py).
"""

from __future__ import annotations

import json
import os
import sys
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
PROBLEMS_DIR  = DATA_DIR / "problems"
ENV_PATH      = SCRIPTS_DIR.parent / ".env.local"

STORAGE_BUCKET = "problem-images"

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

def _load_env() -> None:
    """Load .env.local into os.environ (python-dotenv)."""
    try:
        from dotenv import load_dotenv
        load_dotenv(ENV_PATH, override=False)
    except ImportError:
        pass  # fall back to variables already set in the environment


def _get_supabase_client():
    """Return an authenticated Supabase client using the service-role key."""
    from supabase import create_client
    url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        raise RuntimeError(
            "Hiányzó környezeti változók: NEXT_PUBLIC_SUPABASE_URL és/vagy "
            "SUPABASE_SERVICE_ROLE_KEY. Ellenőrizd a .env.local fájlt."
        )
    return create_client(url, key)


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
# Storage helpers
# ---------------------------------------------------------------------------

def _upload_formula_pngs(
    supabase,
    pdf_stem: str,
    log: Callable,
) -> dict[str, str]:
    """
    Upload all formula PNGs for `pdf_stem` to Supabase Storage.

    Returns a mapping  {filename: public_url}  for every uploaded PNG.
    """
    formulas_dir = PROBLEMS_DIR / pdf_stem / "formulas"
    if not formulas_dir.exists():
        return {}

    url_map: dict[str, str] = {}
    pngs = sorted(formulas_dir.glob("*.png"))

    for png_path in pngs:
        storage_path = f"{pdf_stem}/formulas/{png_path.name}"
        try:
            data = png_path.read_bytes()
            supabase.storage.from_(STORAGE_BUCKET).upload(
                path=storage_path,
                file=data,
                file_options={"content-type": "image/png", "upsert": "true"},
            )
            public_url = supabase.storage.from_(STORAGE_BUCKET).get_public_url(
                storage_path
            )
            url_map[png_path.name] = public_url
        except Exception as exc:
            log(f"    [FIGYELEM] PNG feltöltés sikertelen: {png_path.name} — {exc}")

    return url_map


# ---------------------------------------------------------------------------
# Row builder
# ---------------------------------------------------------------------------

def _make_source_key(pdf_stem: str, problem_number: int, sub_part: str | None) -> str:
    """
    Stable natural key for upsert conflict detection.
    Examples:
      e_mat_24okt_fl__009__c
      k_mat_25okt_fl__001__        (no sub_part)
    """
    return f"{pdf_stem}__{problem_number:03d}__{sub_part or ''}"


def _build_row(
    problem: dict,
    formula_url_map: dict[str, str],
) -> dict:
    """
    Convert a problem JSON dict to a Supabase row dict.

    formula_url_map: {filename: public_url} — built from uploaded PNGs.
    The formula_image_urls column stores URLs in the same order as
    image_refs so the renderer can resolve {{formula:filename.png}} → URL.
    """
    pdf_stem = problem["pdf_stem"]
    problem_number = problem["problem_number"]
    sub_part = problem.get("sub_part")

    # Build ordered list of public URLs from image_refs
    formula_image_urls = []
    for ref in problem.get("image_refs", []):
        fname = ref.get("filename", "")
        url = formula_url_map.get(fname, "")
        if url:
            formula_image_urls.append(url)

    return {
        "source_key":            _make_source_key(pdf_stem, problem_number, sub_part),
        "pdf_stem":              pdf_stem,
        "pdf_filename":          problem["pdf_filename"],
        "year":                  problem["year"],
        "exam_type":             problem["exam_type"],
        "exam_session":          problem["exam_session"],
        "is_secondary_language": problem.get("is_secondary_language", False),
        "exam_part":             problem.get("exam_part"),
        "problem_number":        problem_number,
        "sub_part":              sub_part,
        "statement_text":        problem.get("statement_text", ""),
        "max_points":            problem.get("max_points"),
        "formula_image_urls":    formula_image_urls,
        "has_figure":            bool(problem.get("image_refs")),
        "ocr_used":              problem.get("ocr_used", False),
        "notes":                 problem.get("notes", ""),
        "human_reviewed":        False,
    }


# ---------------------------------------------------------------------------
# Per-PDF import
# ---------------------------------------------------------------------------

def _import_pdf(
    supabase,
    pdf_stem: str,
    reviewed_keys: set[str],
    log: Callable,
) -> dict:
    """
    Upload formula PNGs and upsert all problem rows for `pdf_stem`.

    Returns {"uploaded_pngs": int, "inserted": int, "updated": int, "skipped": int}
    """
    problem_dir = PROBLEMS_DIR / pdf_stem
    if not problem_dir.exists():
        log(f"    [SKIP] Nincs feladat könyvtár: {pdf_stem}")
        return {"uploaded_pngs": 0, "inserted": 0, "updated": 0, "skipped": 0}

    # 1. Upload formula PNGs
    url_map = _upload_formula_pngs(supabase, pdf_stem, log)

    # 2. Load all problem JSONs
    json_files = sorted(problem_dir.glob("problem_*.json"))
    if not json_files:
        return {"uploaded_pngs": len(url_map), "inserted": 0, "updated": 0, "skipped": 0}

    inserted = updated = skipped = 0

    for jf in json_files:
        with open(jf, encoding="utf-8") as f:
            problem = json.load(f)

        source_key = _make_source_key(
            problem["pdf_stem"],
            problem["problem_number"],
            problem.get("sub_part"),
        )

        # Skip rows that have already been reviewed — preserve review work
        if source_key in reviewed_keys:
            skipped += 1
            continue

        row = _build_row(problem, url_map)

        # Determine insert vs update for reporting
        is_new = source_key not in reviewed_keys  # rough heuristic; fine for logging

        try:
            supabase.table("problems").upsert(
                row, on_conflict="source_key"
            ).execute()
            # Count as inserted on first run, updated on subsequent runs
            # (we can't easily distinguish without an extra SELECT per row)
            inserted += 1
        except Exception as exc:
            log(f"    [HIBA] Upsert sikertelen: {source_key} — {exc}")

    return {
        "uploaded_pngs": len(url_map),
        "inserted": inserted,
        "updated": updated,
        "skipped": skipped,
    }


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run(
    log: Callable[[str], None] = print,
    progress_callback: Callable[[int, int], None] | None = None,
) -> dict:
    """
    Import all segmented PDFs that haven't been imported yet (or re-import
    if the user explicitly resets `db_imported` in the manifest).

    Returns summary: imported, skipped, total_pngs, total_rows
    """
    log("=== 06 - Feladatok feltöltése Supabase-be ===")

    _load_env()

    try:
        supabase = _get_supabase_client()
    except RuntimeError as exc:
        log(f"[HIBA] {exc}")
        return {"error": str(exc)}

    # Verify the table exists by doing a lightweight query
    try:
        supabase.table("problems").select("id").limit(1).execute()
    except Exception as exc:
        log(
            "[HIBA] A 'problems' tábla nem létezik vagy nem elérhető.\n"
            "  → Futtasd le a supabase/migrations/001_create_problems.sql fájlt\n"
            "    a Supabase SQL szerkesztőjében, majd próbáld újra."
        )
        log(f"  (Részletek: {exc})")
        return {"error": "table_not_found"}

    manifest = _load_manifest()

    # Only process PDFs that have been segmented
    targets = [
        (fname, entry)
        for fname, entry in manifest.items()
        if entry.get("segmented") and not entry.get("db_imported")
    ]

    if not targets:
        log("Nincs feltöltendő PDF. Minden már importálva van, vagy le kell futtatni a szegmentálást.")
        return {"imported": 0, "skipped": 0, "total_pngs": 0, "total_rows": 0}

    total = len(targets)

    # Fetch all already-reviewed source_keys in one query (to protect review work)
    log("  Jóváhagyott feladatok lekérdezése...")
    try:
        result = supabase.table("problems").select("source_key").eq(
            "human_reviewed", True
        ).execute()
        reviewed_keys: set[str] = {row["source_key"] for row in result.data}
        log(f"  {len(reviewed_keys)} már jóváhagyott feladat védve.")
    except Exception as exc:
        log(f"  [FIGYELEM] Nem sikerült lekérdezni a jóváhagyott feladatokat: {exc}")
        reviewed_keys = set()

    imported_count = 0
    total_pngs = 0
    total_rows = 0

    for idx, (fname, entry) in enumerate(targets):
        if progress_callback:
            progress_callback(idx, total)

        pdf_stem = Path(entry.get("local_path", fname)).stem
        log(f"  [{idx+1}/{total}] {fname} ...")

        try:
            result = _import_pdf(supabase, pdf_stem, reviewed_keys, log)
            rows = result["inserted"] + result["updated"]
            total_pngs += result["uploaded_pngs"]
            total_rows += rows
            log(
                f"    OK — {result['uploaded_pngs']} PNG feltöltve, "
                f"{rows} sor upsert"
                + (f", {result['skipped']} kihagyva (már jóváhagyott)" if result["skipped"] else "")
            )
            entry["db_imported"] = True
            _save_manifest(manifest)
            imported_count += 1
        except Exception as exc:
            log(f"    [HIBA] {exc}")

    if progress_callback:
        progress_callback(total, total)

    log(
        f"\nKész: {imported_count} PDF importálva, "
        f"{total_pngs} PNG feltöltve, "
        f"{total_rows} feladatsor az adatbázisban."
    )
    return {
        "imported": imported_count,
        "skipped": total - imported_count,
        "total_pngs": total_pngs,
        "total_rows": total_rows,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    run()
    sys.exit(0)
