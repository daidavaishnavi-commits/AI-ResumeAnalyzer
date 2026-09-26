# ResumeIQ — AI Resume Analyzer & Job Matcher

An explainable resume analyzer and job matcher built with Flask. Every number the app
shows is computed from the documents themselves, with the matching text kept as evidence —
no invented scores.

**Current stage: Stage 1 — resume PDF text extraction.**
Upload a PDF, get the cleaned text back with page and line numbers. Section detection,
skill extraction, job-description parsing and match scoring come in later stages.

## Quick start

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements-dev.txt

cp .env.example .env              # set FLASK_CONFIG=development and SECRET_KEY
FLASK_CONFIG=development python run.py    # http://127.0.0.1:5000
```

`FLASK_CONFIG` must be one of `development`, `testing` or `production`. An unknown value is
rejected and an unset value means `production`, so a typo can never start the app with debug
settings. `production` refuses to start unless `SECRET_KEY` is set in the environment, and
never enables Flask's interactive debugger.

Extract text from a PDF without starting the server:

```bash
python scripts/analyze_cli.py path/to/resume.pdf --lines 40
python scripts/analyze_cli.py path/to/resume.pdf --json
```

## Tests

```bash
pytest                                  # 65 tests
pytest --cov=app --cov-report=term-missing
ruff check . && ruff format --check .
```

## How extraction works (Stage 1)

```
upload  →  validate  →  store  →  extract  →  clean  →  ExtractionResult
```

1. **Validate** (`app/services/upload_service.py`): extension must be `.pdf`, size must be
   under 5 MB, and the bytes must actually start with `%PDF-`, because the filename and the
   browser-supplied content type can both lie.
2. **Store**: saved as `<uuid>.pdf` inside `instance/uploads/` via `secure_filename`, so an
   uploaded name can never escape the upload folder. The original name is kept only as
   metadata, together with a SHA-256 hash for later de-duplication.
3. **Extract** (`app/core/extraction.py`): password-protected files are detected up front and
   reported as such; then `pdfplumber` runs first, with `pypdf` as a fallback when pdfplumber
   raises or finds almost no text.
4. **Clean** (`app/core/cleaning.py`): unicode/ligature normalization, bullet characters and
   unmapped `(cid:NNN)` glyphs turned into `- `, hyphenated line wraps rejoined, whitespace
   squeezed, bare page numbers dropped, and running headers/footers dropped only when the
   same header-like text repeats in the same slot at the top or bottom of several pages — a
   repeated skill such as `Python` is kept as evidence. One input line stays one output line,
   and `page_line_index` keeps pointing at the original line even when lines are dropped.
5. **Result** (`app/core/schemas.py`): `ExtractionResult` with the full text, a list of
   `Line(text, original_text, page, index, page_line_index)`, per-page text, the extractor
   used, counts, a `is_probably_scanned` flag and human-readable warnings.

A structurally valid PDF that contains almost no extractable text (a scan or an image-only
export) is not an error: the result comes back with `is_probably_scanned = True` and a warning
saying that ResumeIQ does not run OCR. Nothing pretends text was read. Pass `strict=True` to
`extract_text` (or `--strict` on the CLI) to raise `EmptyDocumentError` instead.

## Layout

```
app/
  __init__.py        application factory + error handlers
  config.py          Dev/Test/Prod config, 5 MB upload limit
  extensions.py      CSRF protection
  core/              pure Python, no Flask: extraction, cleaning, schemas, errors
  routes/            main + analyze blueprints (thin: validate → service → template)
  services/          upload_service: validate, store, extract, delete the file afterwards
  templates/         Bootstrap 5 pages, error pages, partials
  static/            theme.css, upload.js (drag & drop)
scripts/analyze_cli.py   run the pipeline from the terminal
tests/unit/              cleaning, extraction, upload service
tests/integration/       Flask routes (PDFs generated with reportlab)
```

The rule that keeps this maintainable: **`app/core` never imports Flask and never touches the
database.** That is what makes the analysis engine testable and runnable from the CLI.

## Roadmap

| Stage | Scope | Status |
|---|---|---|
| 0 | Project skeleton, app factory | done |
| 1 | PDF text extraction + cleaning | done |
| 2 | Section detection, skill extraction | next |
| 3 | Job-description parsing, explainable match score | planned |
| 4 | SQLite persistence (SQLAlchemy) | planned |
| 5 | Report UI | planned |
| 6 | Dashboard, history, charts | planned |
| 7 | Hardening: rate limiting, security headers, CI | planned |

## Privacy

Resumes contain personal data. Stage 1 only needs the extracted text, so an uploaded PDF is
deleted as soon as it has been read — whether extraction succeeded or not — and anything a
crash leaves behind in the gitignored `instance/uploads/` is purged at startup.
