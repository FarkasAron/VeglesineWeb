"""
07_review_app.py
----------------
Image-based multi-user Streamlit review UI for the Érettségi Matematika Feladatbank.

Navigation is by problem group (one problem number = one step, even if it has
sub-parts a/b/c). The shared crop image is shown once; sub-parts are displayed
as tabs so each gets its own topic tags and difficulty.

Run with:
  python -m streamlit run scripts/07_review_app.py

Multiple reviewers can run simultaneously — all state is stored in Supabase.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from itertools import groupby
from pathlib import Path

import streamlit as st

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# Paths & env
# ---------------------------------------------------------------------------

SCRIPTS_DIR = Path(__file__).parent
ENV_PATH    = SCRIPTS_DIR.parent / ".env.local"

# ---------------------------------------------------------------------------
# Topic taxonomy
# ---------------------------------------------------------------------------

TOPIC_LABELS: dict[str, str] = {
    "halmazok":              "Halmazok",
    "logika":                "Matematikai logika",
    "kombinatorika":         "Kombinatorika",
    "grafelmelet":           "Gráfelmélet",
    "valoszinuseg":          "Valószínűség-számítás",
    "statisztika":           "Statisztika",
    "szamok-muveletek":      "Számok és műveletek",
    "szamrendszerek":        "Számrendszerek",
    "szamelmelet":           "Számelmélet",
    "algebra":               "Algebra",
    "egyenletek":            "Egyenletek és egyenlőtlenségek",
    "fuggvenyek":            "Függvények és grafikonok",
    "exponencialis":         "Exponenciális és logaritmikus függvények",
    "trigonometria":         "Trigonometria",
    "sorozatok":             "Sorozatok",
    "penzugyi-matematika":   "Pénzügyi matematika",
    "geometria-sik":         "Síkgeometria",
    "geometria-ter":         "Térgeometria",
    "koordinata-geometria":  "Koordinátageometria",
    "vektorok":              "Vektorok",
    "transzformacio":        "Geometriai transzformációk",
    "hatarertek":            "Határérték és folytonosság",
    "differencialszamitas":  "Differenciálszámítás",
    "integralszamitas":      "Integrálszámítás",
    "bizonyitasok":          "Bizonyítások és elmélet",
    "szovegfeladas":         "Szöveges feladat",
}

DIFFICULTY_OPTIONS: dict[str, str] = {
    "":        "— nincs megadva —",
    "konnyu":  "Könnyű",
    "kozepes": "Közepes",
    "nehez":   "Nehéz",
}

LABEL_TO_SLUG = {v: k for k, v in TOPIC_LABELS.items()}

# ---------------------------------------------------------------------------
# Supabase
# ---------------------------------------------------------------------------

def _load_env() -> None:
    try:
        from dotenv import load_dotenv
        load_dotenv(ENV_PATH, override=False)
    except ImportError:
        pass


@st.cache_resource
def get_supabase():
    _load_env()
    from supabase import create_client
    url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        st.error("Hiányzó Supabase környezeti változók (.env.local).")
        st.stop()
    return create_client(url, key)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

COLS = ("id,source_key,pdf_stem,pdf_filename,year,exam_type,exam_session,"
        "exam_part,problem_number,sub_part,max_points,problem_image_url,"
        "topic_tags,difficulty_level,notes,human_reviewed,ocr_used")

@st.cache_data(show_spinner=False)
def load_all_problems() -> list[dict]:
    """Load every problem row from Supabase, paginating in chunks of 1000."""
    sb = get_supabase()
    all_rows: list[dict] = []
    page_size = 1000
    offset = 0
    while True:
        result = (
            sb.table("problems")
            .select(COLS)
            .order("year", desc=True)
            .order("exam_session")
            .order("exam_type")
            .order("problem_number")
            .order("sub_part")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        rows = result.data or []
        all_rows.extend(rows)
        if len(rows) < page_size:
            break
        offset += page_size
    return all_rows


def get_counts() -> tuple[int, int]:
    sb = get_supabase()
    reviewed = sb.table("problems").select("id", count="exact").eq("human_reviewed", True).execute().count or 0
    total    = sb.table("problems").select("id", count="exact").execute().count or 0
    return reviewed, total


# ---------------------------------------------------------------------------
# Problem grouping
# ---------------------------------------------------------------------------

def build_groups(problems: list[dict]) -> list[list[dict]]:
    """
    Group rows into problem groups: (pdf_stem, problem_number) → [sub-part rows].

    groupby() only collapses CONSECUTIVE equal keys, so we must sort by the full
    grouping key first to guarantee sub-parts end up together. Afterwards we
    re-sort the groups chronologically for navigation.
    """
    # 1. Sort so all rows of the same (pdf_stem, problem_number) are adjacent.
    by_group_key = sorted(
        problems,
        key=lambda p: (p["pdf_stem"], p["problem_number"], p.get("sub_part") or ""),
    )

    # 2. Group — now groupby is safe.
    key_fn = lambda p: (p["pdf_stem"], p["problem_number"])
    groups: list[list[dict]] = []
    for _, sub_probs in groupby(by_group_key, key=key_fn):
        groups.append(list(sub_probs))  # already sorted by sub_part from step 1

    # 3. Re-sort groups chronologically: newest year first, then session/type/part/number.
    groups.sort(key=lambda g: (
        -g[0]["year"],
        g[0].get("exam_session") or "",
        g[0].get("exam_type") or "",
        g[0].get("exam_part") or "",
        g[0]["problem_number"],
    ))

    return groups


# ---------------------------------------------------------------------------
# Per-row session state helpers
# ---------------------------------------------------------------------------

def _key(pid: str, field: str) -> str:
    return f"{field}_{pid}"


def init_sub_form(problem: dict) -> None:
    """Populate session-state form keys for one sub-part row (only if not yet set)."""
    pid = problem["id"]
    if _key(pid, "tags") not in st.session_state:
        st.session_state[_key(pid, "tags")]  = problem.get("topic_tags") or []
        st.session_state[_key(pid, "diff")]  = problem.get("difficulty_level") or ""
        st.session_state[_key(pid, "num")]   = int(problem.get("problem_number") or 1)
        st.session_state[_key(pid, "sub")]   = problem.get("sub_part") or ""
        st.session_state[_key(pid, "notes")] = problem.get("notes") or ""


def init_group(group: list[dict]) -> None:
    for p in group:
        init_sub_form(p)


# ---------------------------------------------------------------------------
# Supabase write actions
# ---------------------------------------------------------------------------

def approve_sub(problem: dict, reviewer: str) -> None:
    pid = problem["id"]
    now = datetime.now(timezone.utc).isoformat()
    get_supabase().table("problems").update({
        "topic_tags":       st.session_state[_key(pid, "tags")],
        "difficulty_level": st.session_state[_key(pid, "diff")] or None,
        "problem_number":   st.session_state[_key(pid, "num")],
        "sub_part":         st.session_state[_key(pid, "sub")] or None,
        "notes":            st.session_state[_key(pid, "notes")],
        "human_reviewed":   True,
        "reviewed_by":      reviewer or "ismeretlen",
        "reviewed_at":      now,
        "updated_at":       now,
    }).eq("id", pid).execute()
    problem["human_reviewed"] = True


def flag_sub(problem: dict, note: str) -> None:
    pid = problem["id"]
    existing = problem.get("notes", "")
    new_notes = f"[MEGJELÖLVE] {note}\n{existing}".strip()
    get_supabase().table("problems").update({
        "notes":      new_notes,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", pid).execute()
    problem["notes"] = new_notes
    st.session_state[_key(pid, "notes")] = new_notes


# ---------------------------------------------------------------------------
# Sub-part form (rendered inside a tab or directly)
# ---------------------------------------------------------------------------

def render_sub_form(problem: dict, reviewer: str, groups: list[list[dict]]) -> None:
    pid  = problem["id"]
    init_sub_form(problem)

    reviewed = problem.get("human_reviewed", False)
    if reviewed:
        st.success("✓ Jóváhagyva")
    else:
        st.info("⏳ Felülvizsgálatra vár")

    # Problem number correction
    num_col, sub_col = st.columns([2, 1])
    with num_col:
        new_num = st.number_input(
            "Feladatszám",
            min_value=1, max_value=50,
            value=st.session_state[_key(pid, "num")],
            step=1,
            key=_key(pid, "num_widget"),
            help="Javítsd, ha a szegmentáló rossz számot rendelt.",
        )
        st.session_state[_key(pid, "num")] = int(new_num)
    with sub_col:
        new_sub = st.text_input(
            "Alrész",
            value=st.session_state[_key(pid, "sub")],
            max_chars=4,
            placeholder="pl. a",
            key=_key(pid, "sub_widget"),
            help="Hagyd üresen, ha nincs alrész.",
        )
        st.session_state[_key(pid, "sub")] = new_sub.strip().lower()

    # Topic tags
    tag_options = list(TOPIC_LABELS.keys())
    tag_labels  = [TOPIC_LABELS[t] for t in tag_options]
    current_labels = [TOPIC_LABELS[t] for t in st.session_state[_key(pid, "tags")] if t in TOPIC_LABELS]

    selected_labels = st.multiselect(
        "Témakörök",
        options=tag_labels,
        default=current_labels,
        placeholder="Válassz témakört...",
        key=_key(pid, "tags_widget"),
    )
    st.session_state[_key(pid, "tags")] = [LABEL_TO_SLUG[l] for l in selected_labels if l in LABEL_TO_SLUG]

    # Difficulty
    diff_keys   = list(DIFFICULTY_OPTIONS.keys())
    diff_labels = list(DIFFICULTY_OPTIONS.values())
    current_diff = st.session_state[_key(pid, "diff")]
    diff_idx = diff_keys.index(current_diff) if current_diff in diff_keys else 0
    chosen = st.selectbox(
        "Nehézségi szint",
        options=diff_labels,
        index=diff_idx,
        key=_key(pid, "diff_widget"),
    )
    st.session_state[_key(pid, "diff")] = diff_keys[diff_labels.index(chosen)]

    # Notes
    new_notes = st.text_area(
        "Megjegyzés (belső)",
        value=st.session_state[_key(pid, "notes")],
        height=60,
        placeholder="Opcionális.",
        key=_key(pid, "notes_widget"),
    )
    st.session_state[_key(pid, "notes")] = new_notes

    st.divider()

    btn_flag, btn_approve = st.columns([1, 1])

    with btn_flag:
        with st.popover("⚠️ Megjelölés", use_container_width=True):
            flag_note = st.text_input("Miért?", key=_key(pid, "flag_note"))
            if st.button("Mentés", type="secondary", key=_key(pid, "flag_btn")):
                flag_sub(problem, flag_note)
                st.success("Megjelölve.")

    with btn_approve:
        if not reviewer:
            st.button(
                "✓ Jóváhagyás", type="primary", disabled=True,
                help="Add meg a neved a bal oldali panelen.",
                use_container_width=True,
                key=_key(pid, "approve_btn_disabled"),
            )
        else:
            if st.button("✓ Jóváhagyás", type="primary",
                         use_container_width=True, key=_key(pid, "approve_btn")):
                approve_sub(problem, reviewer)
                # Invalidate cached problem list so progress updates
                load_all_problems.clear()
                st.success("Jóváhagyva!")
                # Auto-advance if all sub-parts in the group are now reviewed
                gidx = st.session_state.current_group_idx
                group = groups[gidx]
                if all(p.get("human_reviewed") for p in group):
                    next_gidx = gidx + 1
                    while next_gidx < len(groups) and all(p.get("human_reviewed") for p in groups[next_gidx]):
                        next_gidx += 1
                    if next_gidx < len(groups):
                        st.session_state.current_group_idx = next_gidx
                        init_group(groups[next_gidx])
                st.rerun()


# ---------------------------------------------------------------------------
# Main app
# ---------------------------------------------------------------------------

def main() -> None:
    st.set_page_config(
        page_title="Feladat Felülvizsgáló",
        page_icon="📐",
        layout="wide",
    )

    # ── Sidebar ──────────────────────────────────────────────────────────────
    with st.sidebar:
        st.title("📐 Feladat Felülvizsgáló")
        st.divider()

        reviewer = st.text_input(
            "Felülvizsgáló neve",
            placeholder="pl. Kiss Péter",
            key="reviewer_name",
        )

        unreviewed_only = st.checkbox("Csak felülvizsgálatlanok", value=True)

        filter_exam = st.selectbox(
            "Szint",
            options=["Mind", "Középszint", "Emelt szint"],
        )

        st.divider()

        if st.button("🔄 Frissítés", use_container_width=True):
            load_all_problems.clear()
            for k in list(st.session_state.keys()):
                if k not in ("reviewer_name",):
                    del st.session_state[k]
            st.rerun()

    # ── Load & group ──────────────────────────────────────────────────────────
    filter_key = f"{unreviewed_only}_{filter_exam}"
    if st.session_state.get("_last_filter") != filter_key:
        for k in ["groups", "current_group_idx", "_last_filter"]:
            st.session_state.pop(k, None)
        st.session_state["_last_filter"] = filter_key

    if "groups" not in st.session_state:
        with st.spinner("Feladatok betöltése..."):
            all_problems = load_all_problems()

        # Exam-level filter
        if filter_exam == "Középszint":
            all_problems = [p for p in all_problems if p["exam_type"] == "kozep"]
        elif filter_exam == "Emelt szint":
            all_problems = [p for p in all_problems if p["exam_type"] == "emelt"]

        all_groups = build_groups(all_problems)

        # Unreviewed filter: keep groups with at least one unreviewed sub-part
        if unreviewed_only:
            all_groups = [g for g in all_groups if any(not p["human_reviewed"] for p in g)]

        st.session_state.groups = all_groups
        st.session_state.current_group_idx = 0

    groups: list[list[dict]] = st.session_state.groups
    total_groups = len(groups)

    if total_groups == 0:
        if unreviewed_only:
            st.success("🎉 Minden feladat jóváhagyva!")
        else:
            st.warning("Nem találhatók feladatok az adatbázisban.")
        return

    gidx = st.session_state.get("current_group_idx", 0)
    gidx = max(0, min(gidx, total_groups - 1))
    st.session_state.current_group_idx = gidx

    group = groups[gidx]
    init_group(group)

    # Representative problem for header info
    rep = group[0]

    # ── Progress (sidebar) ────────────────────────────────────────────────────
    with st.sidebar:
        reviewed_n, total_n = get_counts()
        st.metric("Sorok jóváhagyva", f"{reviewed_n} / {total_n}")
        st.progress(reviewed_n / total_n if total_n else 0)
        st.caption(f"Aktuális lista: {total_groups} feladat")

    # ── Navigation bar ────────────────────────────────────────────────────────
    nav_cols = st.columns([1, 5, 1])
    with nav_cols[0]:
        if st.button("← Előző", disabled=(gidx == 0), use_container_width=True):
            st.session_state.current_group_idx = gidx - 1
            init_group(groups[gidx - 1])
            st.rerun()
    with nav_cols[1]:
        exam_type_hu = "Középszint" if rep["exam_type"] == "kozep" else "Emelt szint"
        session_hu   = {"majus": "május", "oktober": "október", "februar": "február"}.get(
            rep.get("exam_session", ""), rep.get("exam_session", "")
        )
        n_parts = len(group)
        parts_label = f" ({n_parts} alrész)" if n_parts > 1 else ""
        st.markdown(
            f"**{gidx + 1} / {total_groups}** — "
            f"{rep['year']} {session_hu} · {exam_type_hu} · "
            f"{rep.get('exam_part', '?')}. rész · "
            f"**{rep['problem_number']}. feladat**{parts_label}"
            + (" · 🔬 OCR" if rep.get("ocr_used") else "")
        )
    with nav_cols[2]:
        if st.button("Következő →", disabled=(gidx == total_groups - 1), use_container_width=True):
            st.session_state.current_group_idx = gidx + 1
            init_group(groups[gidx + 1])
            st.rerun()

    st.divider()

    # ── Two-column layout ─────────────────────────────────────────────────────
    col_img, col_form = st.columns([3, 2], gap="large")

    # ── Left: crop image (shared by all sub-parts) ────────────────────────────
    with col_img:
        st.subheader("📷 Feladat képe")
        img_url = rep.get("problem_image_url")
        if img_url:
            st.image(img_url, use_container_width=True)
        else:
            st.warning("Nincs elérhető kép ehhez a feladathoz.")

    # ── Right: sub-part tabs ──────────────────────────────────────────────────
    with col_form:
        st.subheader("✏️ Felülvizsgálat")

        if len(group) == 1:
            # No sub-parts — render form directly
            render_sub_form(group[0], reviewer, groups)
        else:
            # Multiple sub-parts — one tab each
            tab_labels = []
            for p in group:
                sub = p.get("sub_part") or "–"
                check = " ✓" if p.get("human_reviewed") else ""
                tab_labels.append(f"{sub}{check}")

            tabs = st.tabs(tab_labels)
            for tab, problem in zip(tabs, group):
                with tab:
                    render_sub_form(problem, reviewer, groups)


if __name__ == "__main__":
    main()
