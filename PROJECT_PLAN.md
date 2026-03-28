# Érettségi Matematika Feladatbank — Project Plan

> **Status:** Pre-coding architectural plan. Decisions confirmed. Ready to build.
> **Audience:** Developer reference + teacher stakeholder.
> **Last updated:** 2026-03-28

---

## Confirmed Decisions

| # | Decision | Confirmed Choice |
|---|---|---|
| 1 | Formula handling | **Image-only.** Formula regions are cropped as PNGs and displayed as images. No LaTeX entry required from the teacher. |
| 2 | Pipeline frequency | **Manual, twice a year** (May + October sessions), wrapped in a one-click launcher so the teacher can run it herself. |
| 3 | Authentication | **Google OAuth + email magic link** (via NextAuth.js + Resend free tier). |
| 4 | Problem granularity | **Split by sub-part.** Each a)/b)/c) is a separate database row. |
| 5 | LaTeX delimiters | **`$...$` inline, `$$...$$` display.** Standard convention for any manually-entered LaTeX in text descriptions. |

---

## A note on plain text

Hungarian érettségi problems consist overwhelmingly of **plain Hungarian prose** — sentences like *"Egy háromszög oldalainak hossza 5 cm, 12 cm és 13 cm. Számítsa ki a háromszög területét!"* — interspersed with formula images and occasionally a diagram. PyMuPDF extracts this prose with very high accuracy from digital PDFs, preserving word order and Hungarian accented characters (á, é, í, ó, ö, ő, ú, ü, ű) correctly. The full problem statement — including all surrounding explanatory text, given data, and the question itself — is stored in `statement_text` as plain text, with `{{formula:fig_name.png}}` placeholders marking where formula images sit inline. The app reassembles this into a readable, correctly-ordered display. Plain text is the easy part of this pipeline; it requires no human correction in the vast majority of cases.

---

## 1. Tech Stack Recommendation

### Frontend: **Next.js 14 (App Router)**

Next.js delivers server-side rendering (SSR) and static site generation (SSG) in a single framework. SSG means the browse-by-topic pages are pre-rendered as static HTML — they load instantly on mobile and require zero server runtime for reads. The App Router's React Server Components keep JavaScript payloads small. Vercel (made by the same team) deploys Next.js with zero configuration, and the free Hobby tier covers this project's entire traffic profile indefinitely.

### Backend / API: **Next.js API Routes (built-in)**

All data-fetching logic (search, filters, bookmarks) lives in Next.js route handlers. This avoids running a separate API server. For teacher admin functions (marking problems reviewed, hiding solutions) the same API routes handle authentication with NextAuth.js. Everything lives in one deployable unit.

### Database: **Supabase (PostgreSQL)**

Supabase's free tier gives 500 MB PostgreSQL storage, 2 GB bandwidth, and row-level security — permanently free, not a trial. PostgreSQL's `tsvector`/`tsquery` full-text search handles Hungarian text correctly with the built-in `hungarian` stemming dictionary. Supabase also provides a browser-based table editor so the teacher can view and manually correct problem records without touching code. Supabase Storage hosts all formula and figure PNG images.

### Math Rendering: **KaTeX**

Used only for any LaTeX that appears in plain-text portions of the problem statement (e.g. variable names like $x$, units like $\text{cm}^2$, or manually-entered corrections). Formula images are displayed as `<img>` tags. KaTeX is kept in the stack because it handles these inline cases and remains available as an upgrade path.

### PDF Parsing (Extraction Pipeline): **PyMuPDF (`fitz`)**

Python binding to the MuPDF engine. Extracts text with precise bounding-box coordinates, extracts embedded raster and vector images per-page, and preserves reading order of text blocks. Runs entirely locally with no API key or internet access. Handles encoding issues common in older Hungarian exam PDFs. No alternative matches it on completeness for this use case.

### OCR Fallback: **Tesseract 5 + `pytesseract`**

For pre-2010 scanned PDFs. Free, local, includes `hun.traineddata` for correct Hungarian character handling.

### Pipeline Launcher: **Streamlit**

The entire pipeline — download, extract, segment, review — is wrapped in a Streamlit web app that the teacher launches with one double-click. She never touches the command line.

### Hosting: **Vercel (free Hobby tier)**

Unlimited deployments, 100 GB bandwidth/month, automatic HTTPS, CDN-served static pages with no cold-start latency.

### Summary Table

| Layer | Choice | Why |
|---|---|---|
| Frontend framework | Next.js 14 (App Router) | SSG + SSR, Vercel-native, mobile-first |
| API layer | Next.js API Routes | Single deployable, no separate server |
| Database | Supabase (PostgreSQL) | Free forever, Hungarian FTS, browser editor |
| Formula display | PNG image crops | Zero teacher effort, no LaTeX knowledge needed |
| Inline math (text) | KaTeX (`react-katex`) | Handles simple inline cases, upgrade path |
| PDF parsing | PyMuPDF (`fitz`) | Local, layout-aware, image extraction |
| OCR fallback | Tesseract 5 | Free, Hungarian language support |
| Pipeline UI | Streamlit | One-click launcher for non-developer teacher |
| Auth | NextAuth.js (Google + magic link) | Confirmed choice |
| Email (magic link) | Resend free tier | 3,000 emails/month, zero cost |
| Hosting | Vercel Hobby | Free CDN, zero-config Next.js |

---

## 2. Data Model

### Primary Table: `problems`

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | `uuid` DEFAULT `gen_random_uuid()` | NO | Primary key |
| `created_at` | `timestamptz` DEFAULT `now()` | NO | Row creation timestamp |
| `updated_at` | `timestamptz` | YES | Last human edit timestamp |
| `year` | `smallint` | NO | Exam year, e.g. 2023 |
| `exam_type` | `enum('közép','emelt')` | NO | Középszint or emelt szint |
| `exam_part` | `enum('I','II')` | NO | Part I (short answer) or Part II (long answer) |
| `problem_number` | `smallint` | NO | Official number within the exam |
| `sub_part` | `varchar(4)` | YES | Sub-label: 'a', 'b', 'c' — NULL for single-part problems |
| `problem_image_url` | `text` | YES | Supabase Storage URL for the full-problem region crop PNG. This is the primary display artifact — the website shows this image, not rendered text. |
| `statement_text` | `text` | NO | Raw extracted text from PyMuPDF/OCR. Not displayed on the website. Kept for potential future full-text search. Quality varies — no manual correction required. |
| `solution_text` | `text` | YES | Official solution text (future use) |
| `max_points` | `smallint` | YES | Official maximum point value |
| `difficulty_level` | `enum('könnyű','közepes','nehéz')` | YES | Reviewer-assigned difficulty |
| `topic_tags` | `text[]` | NO | Array of canonical témakör slugs, assigned per sub-part during review |
| `has_figure` | `boolean` DEFAULT false | NO | True if problem includes a diagram |
| `formula_image_urls` | `text[]` | YES | Reserved for future use — not currently populated |
| `figure_urls` | `text[]` | YES | Reserved for future use |
| `source_pdf_filename` | `varchar(255)` | NO | Original PDF filename, e.g. `mat_kozep_2023_maj_fl.pdf` |
| `source_pdf_page` | `smallint` | NO | Page number in source PDF (1-indexed) |
| `source_pdf_url` | `text` | YES | Direct link to the source PDF on oktatas.hu |
| `parsing_confidence` | `numeric(4,3)` | YES | 0.000–1.000; pipeline confidence score |
| `ocr_used` | `boolean` DEFAULT false | NO | True if Tesseract OCR was applied |
| `human_reviewed` | `boolean` DEFAULT false | NO | True once the teacher has verified and approved this problem |
| `reviewed_by` | `varchar(255)` | YES | Email of reviewer |
| `reviewed_at` | `timestamptz` | YES | Timestamp of review |
| `notes` | `text` | YES | Internal notes (parsing issues, known errors) |
| `fts_vector` | `tsvector` | YES | Auto-maintained full-text search index on `statement_text` |

**Indexes:**
- `UNIQUE (source_key)` — prevents duplicate imports
- `GIN(topic_tags)` — fast topic filtering
- `(human_reviewed)` — review queue filtering
- `(year, exam_type)` — year/type filter queries

**Note on display:** The website displays `problem_image_url` as an `<img>` tag — the full problem region rendered directly from the source PDF at 2× scale. No text rendering, no formula reassembly. What you see in the app is pixel-identical to the original exam paper.

**Task group filtering** (derived, no manual tagging needed):
- Problems 1–4 → "Rövid feladatok" (short answer, always Part I)
- Problems 5+ → "Hosszabb feladatok" (longer problems, Part I/II depending on exam type)
This grouping is computed at query time from `problem_number` — no extra column needed.

---

### Secondary Table: `user_progress`

| Column | Type | Description |
|---|---|---|
| `id` | `uuid` | Primary key |
| `user_id` | `uuid` | FK → Supabase auth.users |
| `problem_id` | `uuid` | FK → problems.id |
| `status` | `enum('bookmarked','solved','skipped')` | |
| `created_at` | `timestamptz` | |

### Secondary Table: `exam_sessions`

| Column | Type | Description |
|---|---|---|
| `id` | `uuid` | Primary key |
| `source_pdf_filename` | `varchar(255)` | Unique — one row per source PDF |
| `year` | `smallint` | |
| `exam_type` | `enum('közép','emelt')` | |
| `is_solution_pdf` | `boolean` | True for megoldások PDFs |
| `downloaded_at` | `timestamptz` | |
| `problem_count` | `smallint` | Expected number of problems |
| `fully_extracted` | `boolean` | |
| `pipeline_run_at` | `timestamptz` | When this PDF was last processed |

---

### Canonical Topic Taxonomy (`topic_tags` values)

| Slug | Hungarian Label | Notes |
|---|---|---|
| `halmazok` | Halmazok | Set operations, Venn diagrams |
| `logika` | Matematikai logika | Propositions, quantifiers |
| `kombinatorika` | Kombinatorika | Permutations, combinations |
| `valoszinuseg` | Valószínűség-számítás | Classical, geometric probability |
| `statisztika` | Statisztika | Mean, median, standard deviation |
| `szamok-muveletek` | Számok és műveletek | Number properties, divisibility, primes |
| `szamelmelet` | Számelmélet | Modular arithmetic, Diophantine problems |
| `algebra` | Algebra | Polynomials, factoring, identities |
| `egyenletek` | Egyenletek és egyenlőtlenségek | Linear, quadratic, absolute value |
| `fuggvenyek` | Függvények és grafikonok | Definition, transformation, graphing |
| `exponencialis` | Exponenciális és logaritmikus függvények | exp/log equations |
| `trigonometria` | Trigonometria | sin/cos/tan, exact values, equations |
| `sorozatok` | Sorozatok | Arithmetic, geometric, limits of sequences |
| `geometria-sik` | Síkgeometria | Triangles, circles, polygons, area |
| `geometria-ter` | Térgeometria | Solids, volume, surface area |
| `koordinata-geometria` | Koordinátageometria | Line, circle, parabola in the plane |
| `vektorok` | Vektorok | Vector operations, scalar product |
| `transzformacio` | Geometriai transzformációk | Symmetry, rotation, dilation |
| `hatarertek` | Határérték és folytonosság | Emelt szint only |
| `differencialszamitas` | Differenciálszámítás | Derivatives, monotonicity, extrema |
| `integralszamitas` | Integrálszámítás | Indefinite/definite integrals, area |
| `komplex-szamok` | Komplex számok | Emelt szint only |
| `matrixok` | Mátrixok | Emelt szint only |
| `szovegfeladas` | Szöveges feladat | Cross-cutting secondary tag for word problems |

---

## 3. PDF Extraction Pipeline Design

### Design Principles

- Runs **locally** on the teacher's or developer's computer — no cloud service required.
- Wrapped in a **Streamlit launcher app** (`scripts/pipeline_app.py`). The teacher opens it by double-clicking a shortcut. She sees a simple interface with buttons: "Új feladatok letöltése", "Szerkesztés / Jóváhagyás", "Feltöltés az adatbázisba". No terminal, no command line.
- **Idempotent:** every script can be re-run safely. Already-processed files are skipped based on the manifest. Already-imported problems are upserted, not duplicated.
- **Twice-yearly cadence:** after the May and October exam sessions, the teacher clicks "Új feladatok letöltése" and the pipeline detects only the new PDFs.

---

### Step 1 — Discover & Download PDFs

**Tool:** Python `requests` + `BeautifulSoup`
**Input:** oktatas.hu archive index page
**Output:** `scripts/data/raw_pdfs/{year}/{közép|emelt}/` — all feladatsor and megoldások PDFs
**Script:** `scripts/01_download_pdfs.py` (called by the Streamlit launcher)

Scrapes the oktatas.hu exam archive, collects all PDF links matching `*feladatsor*` and `*megoldas*`, downloads only files not already in the manifest. On subsequent runs (new exam season), only the 2–4 new PDFs are downloaded. Progress is shown in the Streamlit UI as a progress bar.

**Human review:** None required. The Streamlit UI shows a summary: "23 PDF letöltve, 2 új fájl" so the teacher can confirm at a glance.

---

### Step 2 — PDF Classification & Manifest Update

**Tool:** Pure Python filename parsing + regex
**Input:** All files in `raw_pdfs/`
**Output:** Manifest rows with `year`, `exam_type`, `is_solution_pdf`
**Script:** `scripts/02_classify_pdfs.py`

Filenames follow predictable patterns (e.g. `mat_kozep_2023_maj_fl.pdf`). Unmatched filenames are listed in the UI with a text field for manual year/type entry — the teacher can fill these in herself without knowing any code.

**Human review:** Optional — only for irregularly named older PDFs. Shown as a list in the Streamlit UI.

---

### Step 3 — PDF Text & Image Extraction

**Tool:** PyMuPDF (`fitz`)
**Input:** One PDF file
**Output:** Per-page JSON (`page_{n}.json`) with `text_blocks`, `image_blocks`, dimensions. Figure/formula PNGs saved to `extracted/{pdf_stem}/figures/`.
**Script:** `scripts/03_extract_pages.py`

PyMuPDF extracts full layout trees per page: all text blocks with their bounding boxes, font sizes, bold flags, and all embedded images. Hungarian plain text (the dominant content of every problem) extracts cleanly at this step. Formula regions are identified as image blocks or as text blocks with abnormal character composition (mixed Unicode math symbols, unusual font sizes).

For **scanned PDFs** (no extractable text — rare, mostly pre-2008): Tesseract OCR is applied automatically. The `ocr_used` flag is set on all resulting problems.

**Human review:** None at this step. Pipeline logs which files used OCR.

**Estimated runtime:** 1–3 seconds per digital PDF; 15–30 seconds per page for OCR mode.

---

### Step 4 — Problem Segmentation

**Tool:** Custom Python heuristics
**Input:** Per-page JSON from Step 3
**Output:** Per-problem JSON in `scripts/data/problems/{pdf_stem}/`
**Script:** `scripts/04_segment_problems.py`

⚠️ **This is the hardest step in the pipeline.**

The segmentation heuristic detects problem boundaries using four signals, in priority order:

1. **Bold large-font number** at left margin matching `^\d+\.` — primary boundary signal
2. **Vertical gap** exceeding 1.5× the median line height — secondary boundary signal
3. **Sub-part labels** matching `^[a-c]\)` — triggers splitting into separate sub-part rows
4. **Page-break continuation** — a problem starting near the bottom of a page is merged with the next page until a new problem boundary is found

Plain text paragraphs (task explanation, given data, the question) are assembled in reading order and joined into `statement_text`. Figure and formula image references are inserted as `{{formula:filename.png}}` placeholders at the position where they appeared in the page layout.

**Why this is the hardest step:** The PDFs have no machine-readable structure. Problem boundaries must be inferred from visual layout alone, which varies significantly between years. Expect a 5–15% raw error rate (wrong split, missed merge) on first run, falling to 1–2% after tuning — which is why Step 5 (review) is mandatory.

---

### Step 5 — Problem Region Cropping

**Tool:** PyMuPDF
**Input:** Problem JSON files + original PDFs (re-runs step 4 segmentation to obtain y-ranges)
**Output:** One PNG per problem number saved to `scripts/data/problems/{pdf_stem}/crops/`
**Script:** `scripts/05_crop_images.py`

For each unique problem number in a PDF, this step renders the full problem region (from the first detected line of the problem to the last) as a high-resolution PNG at 2× scale. All sub-parts (a/b/c) of a problem share the same crop — you see the full problem in context when reviewing any sub-part.

The crop covers the horizontal full width of the text area (excluding page margins) and the vertical extent of the entire problem. This produces a pixel-perfect image identical to the original exam paper — equations, diagrams, and formatting all preserved exactly.

**Why image-only (not text):** PyMuPDF text extraction is reliable for plain Hungarian prose but breaks down for equations, superscripts, and diagrams. Rather than requiring manual text correction for every problem, the image is the primary display artifact. The extracted `statement_text` (imperfect) is stored in the DB for potential future search use but never displayed.

**Human review:** None at this step.

---

### Step 6 — Supabase Import

**Tool:** Python `supabase-py`
**Input:** All problem JSON files + crop PNG files from Step 5
**Output:** All problems upserted to Supabase `problems` table with `human_reviewed = false`; crop PNGs uploaded to Supabase Storage (`problem-images` bucket)
**Script:** `scripts/06_import_to_db.py`

Uploads every crop PNG to `{pdf_stem}/crops/{filename}` in Supabase Storage, then upserts each problem row with `problem_image_url` pointing to the public CDN URL. Re-running is safe (upsert on `source_key`). Rows already reviewed (`human_reviewed = true`) are skipped to protect review work.

Importing before review enables **multi-user review**: once the data is in Supabase, any reviewer opens the Step 7 UI in a browser — no local files needed.

**Human review:** None at this step.

---

### Step 7 — Review UI (Streamlit, Supabase-backed)

**Tool:** Streamlit app reading/writing directly from Supabase
**Input:** Unreviewed rows in Supabase (`human_reviewed = false`)
**Output:** Approved rows with `human_reviewed = true`, topic tags, difficulty, verified problem number/sub-part — written back to Supabase
**Script:** `scripts/07_review_app.py`

The interface is designed for speed. Each screen shows:

- **Problem image** (full-width): the crop PNG loaded directly from the Supabase CDN — pixel-perfect replica of the exam paper. No text editing needed.
- **Metadata form** (compact, below or beside the image):
  - **Témakörök** — multi-select from the canonical topic taxonomy (auto-suggested from keyword scan of extracted text)
  - **Nehézségi szint** — könnyű / közepes / nehéz
  - **Feladatszám** — editable number (pre-filled, for correcting segmentation mistakes)
  - **Alrész** — editable field: a / b / c / empty (for correcting sub-part detection)
  - **Jóváhagyás (✓)** / **Kihagyás** / **Megjelölés** buttons
- **Sidebar:** reviewer name, progress counter ("142 / 1454 jóváhagyva"), filter toggle

Because `problem_image_url` is a public CDN URL, remote reviewers see the exact same image as local reviewers — no PDF files required on their machine.

Multiple reviewers work simultaneously — state is in Supabase, not local. Each reviewer opens the app URL, enters their name, and starts tagging.

**Estimated time per problem: 10–20 seconds.** No text correction, just look at the image and assign tags.

**Human review:** Yes — this is the quality gate. The reviewer verifies the problem crop looks correct, assigns topic tags and difficulty, and approves.

---

### Step 8 — Go Live (ISR Revalidation)

After enough problems are approved in Step 7, trigger a Next.js ISR revalidation webhook so the live site updates within seconds. This can be done from the Streamlit UI with a single button click.

**Human review:** None.

---

### Pipeline Flow Summary

```
[Streamlit Launcher — teacher double-clicks shortcut]
         │
         ▼
[01] Download new PDFs from oktatas.hu
         │
         ▼
[02] Classify filenames → manifest
         │ (teacher fills in any unmatched files in UI)
         ▼
[03] Extract text + images per page (PyMuPDF / Tesseract)
         │
         ▼
[04] Segment into individual problems + sub-parts
         │
         ▼
[05] Crop full problem regions → one PNG per problem number
         │
         ▼
[06] Upload crop PNGs + upsert rows to Supabase (human_reviewed = false)
         │
         ▼
[07] ★ REVIEW ★ — show crop image, assign tags, approve (10–20 s/problem)
         │
         ▼
[08] Trigger ISR revalidation → approved problems go live on site
```

---

## 4. Feature Specification

### F1 — Browse Problems by Topic (Témakör szerinti böngészés)

**User story:** As a teacher, I want to browse all problems tagged under "Kombinatorika" so I can find every kombinatorika problem across all exam years.

**Complexity:** Low

Next.js generates topic pages statically at build time via `generateStaticParams` — zero server latency. Each problem card shows: year, exam type, problem number, max points, difficulty badge, and the first 150 characters of plain text. Formula images appearing in the first 150 characters are replaced with "[képlet]" in the preview.

---

### F2 — Full-Text Search (Teljes szöveg keresés)

**User story:** As a student, I want to search for "pitagorasz" and find every problem that mentions the Pythagorean theorem.

**Complexity:** Medium

PostgreSQL `tsvector` full-text search with the `hungarian` dictionary handles stemming. The `fts_vector` column is maintained by a Postgres trigger on `INSERT`/`UPDATE` of `statement_text`. Note: formula images are not searchable by their mathematical content (a known limitation of the image-only approach). The search bar sits in the global navigation with 300 ms debounce.

---

### F3 — Filter by Year, Difficulty, Exam Type (Szűrés)

**User story:** As a teacher, I want to see only emelt szint problems from 2018–2022 tagged as "nehéz".

**Complexity:** Low

Filter state lives in URL query parameters so filtered views are shareable. The API route builds dynamic `WHERE` clauses. Filter controls collapse into a drawer on mobile.

---

### F4 — Bookmark / Favourite Problems (Kedvencek)

**User story:** As a student, I want to bookmark problems I find interesting and return to them from any device.

**Complexity:** Medium

Requires authentication. Stored in `user_progress` with `status = 'bookmarked'`. A star icon on every problem card; unauthenticated users are prompted to log in on click.

---

### F5 — Teacher: Hide / Show Solutions (Megoldás elrejtése)

**User story:** As a teacher showing problems on a projector, I want to toggle solution visibility for the whole class session.

**Complexity:** Low

A global React context toggle collapses all `<SolutionPanel>` components. State is not persisted — it resets on page reload, which is correct for classroom use. No authentication required.

---

### F6 — Export Selected Problems to PDF (Feladatlap generálás)

**User story:** As a teacher, I want to select 8 problems and download a formatted PDF worksheet with my school name and the date.

**Complexity:** High

Problem selection is managed in a Zustand store (persists across page navigation). The "Feladatlap összeállítása" button opens a configuration modal: school name, class, date, include/exclude solutions. The export API route uses `@react-pdf/renderer` for layout. Formula images are fetched from Supabase Storage and embedded directly as PNGs in the PDF. Plain text is rendered with the PDF library's `<Text>` component. KaTeX is used server-side only for any `$...$` spans in plain text.

---

### F7 — Progress Tracker (Megoldottság jelölése)

**User story:** As a student, I want to mark problems as "solved" and see my completion percentage per topic.

**Complexity:** Medium

Requires authentication. Stored in `user_progress` with `status = 'solved'`. Per-topic dashboard shows a progress bar: total / solved / percentage. Checkmark icon on each problem card reflects the user's personal status.

---

### F8 — Random Problem Generator (Véletlenszerű feladat)

**User story:** As a student, I want a random unsolved problem from "Valószínűség-számítás" to practise without choosing one myself.

**Complexity:** Low

API route: `SELECT id FROM problems WHERE topic_tags @> ARRAY[$topic] AND human_reviewed = true ORDER BY RANDOM() LIMIT 1`. If authenticated, additionally excludes already-solved problems. A "Véletlenszerű feladat" button appears on every topic page.

---

## 5. Project File Structure

```
veglesine-web/
│
├── app/                              # Next.js App Router — all pages and API routes
│   ├── layout.tsx                    # Root layout: nav, KaTeX CSS, fonts, auth provider
│   ├── page.tsx                      # Homepage: search bar, topic grid, stats
│   ├── feladatok/
│   │   ├── page.tsx                  # All problems, paginated, with filters
│   │   ├── [id]/
│   │   │   └── page.tsx             # Single problem detail: text + formula images + solution
│   │   └── temakör/
│   │       └── [slug]/
│   │           └── page.tsx         # Problems filtered by topic (statically generated)
│   ├── kereses/
│   │   └── page.tsx                 # Full-text search results
│   ├── kedvencek/
│   │   └── page.tsx                 # User's bookmarked problems (auth required)
│   ├── haladas/
│   │   └── page.tsx                 # Per-topic progress dashboard (auth required)
│   ├── feladatlap/
│   │   └── page.tsx                 # Worksheet builder: problem selection + PDF export UI
│   ├── admin/
│   │   ├── layout.tsx               # Admin layout with teacher-only auth guard
│   │   └── page.tsx                 # Problem list with review status; inline edit
│   └── api/
│       ├── problems/
│       │   ├── route.ts             # GET: list/filter/search problems
│       │   └── [id]/route.ts        # GET single problem; PATCH: admin edits
│       ├── random/route.ts          # GET: random problem by topic (excludes solved if authed)
│       ├── progress/route.ts        # GET/POST: user bookmark & solved status
│       ├── export/route.ts          # POST: assemble and stream worksheet PDF
│       └── auth/[...nextauth]/route.ts  # NextAuth.js: Google OAuth + email magic link
│
├── components/
│   ├── ProblemCard.tsx              # Compact problem card for list views
│   ├── ProblemDetail.tsx            # Full problem view with solution toggle
│   ├── ProblemRenderer.tsx          # ★ Core: parses statement_text, renders text + formula images inline
│   ├── FormulaImage.tsx             # Lazy-loaded, retina-aware formula PNG display
│   ├── FigureImage.tsx              # Lazy-loaded diagram/figure with lightbox on click
│   ├── SolutionToggle.tsx           # Global show/hide solutions toggle (React context)
│   ├── TopicSidebar.tsx             # Témakör navigation list with problem counts
│   ├── FilterPanel.tsx              # Year/type/difficulty filter controls (URL-synced)
│   ├── SearchBar.tsx                # Debounced full-text search input
│   ├── BookmarkButton.tsx           # Star icon; auth-gated
│   ├── SolvedCheckbox.tsx           # Mark-as-solved; auth-gated
│   ├── ProgressBar.tsx              # Per-topic completion bar
│   ├── WorksheetBuilder.tsx         # Problem selection interface + export modal
│   └── ui/                          # Primitive UI: Button, Badge, Modal, Spinner, Drawer
│
├── lib/
│   ├── supabase/
│   │   ├── client.ts                # Browser-side Supabase client
│   │   └── server.ts                # Server-side Supabase client (for API routes + RSC)
│   ├── auth.ts                      # NextAuth.js config: Google provider + Resend email
│   ├── topics.ts                    # Canonical témakör taxonomy: slug → Hungarian label map
│   ├── problem-renderer.ts          # Utility: parse `{{formula:...}}` tokens from statement_text
│   └── types.ts                     # TypeScript interfaces: Problem, UserProgress, ExamSession
│
├── scripts/                          # Python PDF extraction pipeline — runs locally
│   ├── pipeline_app.py              # ★ Streamlit launcher: one-click UI for the teacher
│   ├── 01_download_pdfs.py         # Scrape + download PDFs from oktatas.hu
│   ├── 02_classify_pdfs.py         # Filename parsing → manifest metadata
│   ├── 03_extract_pages.py         # PyMuPDF text + image extraction per page
│   ├── 04_segment_problems.py      # Heuristic problem + sub-part boundary detection
│   ├── 05_crop_images.py           # Render PDF regions to high-res formula/figure PNGs
│   ├── 06_import_to_db.py          # Upload all problems + images to Supabase (human_reviewed=false)
│   ├── 07_review_app.py            # Streamlit review UI — reads/writes Supabase directly
│   ├── config.py                    # Paths, Supabase URL/key (reads from .env)
│   ├── requirements.txt             # Python deps: pymupdf, pytesseract, streamlit, supabase
│   ├── PIPELINE_GUIDE.md           # Step-by-step guide for the teacher (Hungarian)
│   └── data/                        # Local working data — git-ignored
│       ├── raw_pdfs/               # Downloaded PDFs: raw_pdfs/{year}/{kozep|emelt}/
│       ├── extracted/              # Per-page JSON + figure PNGs from Step 3
│       ├── problems/               # Per-problem JSON from Step 4 onwards
│       ├── manifest.db             # SQLite: tracks downloaded & processed files
│       └── unmatched_files.txt     # Files needing manual year/type entry
│
├── public/
│   ├── favicon.ico
│   └── logo.svg
│
├── styles/
│   └── globals.css                  # Tailwind base + KaTeX CSS
│
├── supabase/
│   ├── migrations/
│   │   ├── 001_create_problems.sql         # problems table + all indexes
│   │   ├── 002_create_user_progress.sql    # user_progress table
│   │   ├── 003_create_exam_sessions.sql    # exam_sessions table
│   │   ├── 004_fts_trigger.sql            # tsvector auto-update trigger
│   │   └── 005_rls_policies.sql           # Row-level security policies
│   └── seed.sql                            # ~10 sample problems for local dev
│
├── .env.local                        # Secrets: Supabase keys, NextAuth secret, Resend key (git-ignored)
├── .env.example                      # Template showing all required env vars
├── .gitignore                        # Excludes: node_modules, .env.local, scripts/data/
├── next.config.ts                    # Image domains (Supabase Storage CDN), ISR config
├── tailwind.config.ts
├── tsconfig.json
└── package.json
```

---

## 6. Build Sequence

### Milestone 1 — PDF Extraction Pipeline
**Delivers:** Working local pipeline: downloads all historical PDFs, extracts problems into JSON with formula image crops.

**Dependency:** None. This is the data foundation.

**Status:** ✅ Complete (Steps 1–5 done, v0.4.0)

**Estimated hours:** 40–55h
Steps 1–2 (download + classify): 6h. Step 3 (PyMuPDF extraction): 8h. Step 4 (segmentation heuristics): 20h (hardest). Step 5 (image cropping): 5h. Testing across 20+ years of PDFs: 6h.

---

### Milestone 2 — Database Schema & Initial Import (Step 6)
**Delivers:** Supabase project live with full schema, RLS policies, storage bucket, and all ~1454 problems imported as `human_reviewed = false`. Import script (Step 6) validated.

**Dependency:** Milestone 1 must produce problem JSON files and formula PNGs.

**Estimated hours:** 10–15h
Supabase setup + migrations: 4h. RLS policies: 2h. Importer script: 4h. Validation: 3–5h.

---

### Milestone 3 — Core Read-Only Web App (MVP)
**Delivers:** Deployed Next.js app on Vercel with: homepage, browse-by-topic static pages, problem detail page with formula images and solution toggle. Mobile-responsive. No accounts. No search. Teacher can use this for classroom display immediately.

**Dependency:** Milestone 2 must have problems in Supabase.

**Estimated hours:** 25–35h
Project setup (Next.js, Tailwind, Supabase client): 4h. `ProblemRenderer` component (the `{{formula:...}}` parser): 6h. `FormulaImage` + `FigureImage` components: 4h. Topic pages (static generation): 5h. Problem detail page: 4h. Solution toggle: 2h. Mobile layout: 5h. Vercel deploy: 2h. Cross-device testing: 3h.

---

### Milestone 4 — Search, Filters & Random Problem
**Delivers:** Full-text search (Hungarian), year/type/difficulty filters with URL state, and the random problem generator. App is fully functional for anonymous student self-study.

**Dependency:** Milestone 3.

**Estimated hours:** 15–20h
FTS trigger + index: 2h. Search API route: 3h. SearchBar + debounce: 3h. FilterPanel + URL sync: 4h. Random problem API route: 2h. UI integration + mobile: 4h.

---

### Milestone 5 — User Accounts, Bookmarks & Progress
**Delivers:** Google + magic link auth, bookmarks, mark-as-solved, per-topic progress dashboard.

**Dependency:** Milestone 4.

**Estimated hours:** 20–25h
NextAuth.js + Google + Resend email: 5h. Supabase auth integration: 3h. Bookmark + solved components: 4h. Progress API + dashboard page: 6h. RLS for `user_progress`: 2h. Auth flow testing: 4h.

---

### Milestone 6 — Worksheet PDF Export
**Delivers:** Problem selection UI, worksheet configuration modal, server-side PDF generation with embedded formula images.

**Dependency:** Milestone 3 (problem pages must exist). Milestone 5 optional.

**Estimated hours:** 20–30h
WorksheetBuilder + Zustand selection store: 5h. Config modal: 3h. `@react-pdf/renderer` layout: 8h. Formula PNG embedding in PDF: 5h. API route streaming: 3h. Mobile selection UX: 4h.

---

### Milestone 7 — Admin Panel, Pipeline Launcher Polish & Documentation
**Delivers:** Protected teacher admin area for editing problems in-browser; polished Streamlit launcher with Hungarian-language guide; full deployment documentation.

**Dependency:** All previous milestones.

**Estimated hours:** 15–20h
Admin auth guard: 2h. Admin problem list + inline edit: 5h. ISR revalidation trigger: 2h. Streamlit launcher polish + error handling: 3h. `PIPELINE_GUIDE.md` in Hungarian for the teacher: 3h. Deployment runbook: 2h.

---

### Milestone Summary

| # | Name | Delivers | Est. Hours |
|---|---|---|---|
| 1 | PDF Extraction Pipeline | Local pipeline + teacher-friendly launcher | 40–55h |
| 2 | Database & Import | Supabase schema + first live data | 10–15h |
| 3 | Core Read-Only Web App | Browseable, deployed MVP | 25–35h |
| 4 | Search, Filters & Random | FTS, filters, random problem | 15–20h |
| 5 | User Accounts & Progress | Auth, bookmarks, progress | 20–25h |
| 6 | Worksheet PDF Export | PDF generation feature | 20–30h |
| 7 | Admin & Documentation | Teacher admin + guides | 15–20h |
| | **Total** | | **145–200h** |

---

## 7. Risk & Decision Log

All 5 decisions are now confirmed. This section is retained as a permanent record.

### Decision 1 — Formula handling ✅ CONFIRMED: Image-only

Formula regions are cropped to PNG and displayed as `<img>` tags in the app. No LaTeX conversion. No teacher formula entry. The `{{formula:filename.png}}` inline token system is the implementation. Known limitation: formula content is not full-text searchable. Acceptable trade-off for zero teacher effort.

---

### Decision 2 — Pipeline frequency ✅ CONFIRMED: Manual twice-yearly, teacher-runnable

The pipeline runs manually after each May and October exam session. It is wrapped in a Streamlit launcher with a Hungarian-language UI so the teacher can run it herself. Step 7 (import) only pushes `human_reviewed: true` problems, maintaining the quality gate. Developer involvement is not required for routine pipeline runs.

---

### Decision 3 — Authentication ✅ CONFIRMED: Google OAuth + email magic link

Implemented via NextAuth.js with Google provider and Resend for email delivery. Resend free tier (3,000 emails/month) is sufficient. Students without school Google accounts can sign in with any email address.

---

### Decision 4 — Problem granularity ✅ CONFIRMED: Split by sub-part

Each a)/b)/c) sub-part is a separate database row with `sub_part = 'a'/'b'/'c'`. Single-part problems have `sub_part = NULL`. Enables: per-sub-part topic tagging, per-sub-part progress tracking, per-sub-part worksheet selection.

---

### Decision 5 — LaTeX delimiters ✅ CONFIRMED: `$...$` inline, `$$...$$` display

Used only for any manually-entered LaTeX in plain-text spans (e.g. variable names, units). Formula images remain the primary display mechanism. The `$...$` convention is standard, supported natively by KaTeX, and the only option that requires no custom parser.

---

*End of project plan. All decisions confirmed. Ready to begin Milestone 1.*
