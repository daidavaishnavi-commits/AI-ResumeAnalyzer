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

cp .env.example .env              # set SECRET_KEY
python run.py                     # http://127.0.0.1:5000
```

Extract text from a PDF without starting the server:

```bash
python scripts/analyze_cli.py path/to/resume.pdf --lines 40
python scripts/analyze_cli.py path/to/resume.pdf --json
```

## Tests

```bash
pytest                                  # 40 tests
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
3. **Extract** (`app/core/extraction.py`): `pdfplumber` first; `pypdf` is used as a fallback
   when pdfplumber raises or finds almost no text.
4. **Clean** (`app/core/cleaning.py`): unicode/ligature normalization, bullet characters and
   unmapped `(cid:NNN)` glyphs turned into `- `, hyphenated line wraps rejoined, whitespace
   squeezed, repeated running headers/footers and bare page numbers dropped. One input line
   stays one output line, so line numbers remain meaningful.
5. **Result** (`app/core/schemas.py`): `ExtractionResult` with the full text, a list of
   `Line(text, original_text, page, index, page_line_index)`, per-page text, the extractor
   used, counts, a `is_probably_scanned` flag and human-readable warnings.

A PDF with almost no extractable text raises `EmptyDocumentError` instead of being passed on
as an empty resume — scanned resumes are reported, not silently accepted.

## Layout

```
app/
  __init__.py        application factory + error handlers
  config.py          Dev/Test/Prod config, 5 MB upload limit
  extensions.py      CSRF protection
  core/              pure Python, no Flask: extraction, cleaning, schemas, errors
  routes/            main + analyze blueprints (thin: validate → service → template)
  services/          upload_service: validate, store, extract, clean up on failure
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

Resumes contain personal data. Uploaded files stay in `instance/uploads/`, which is
gitignored, and are deleted automatically if extraction fails.
