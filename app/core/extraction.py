"""PDF text extraction (Stage 1).

Primary extractor is pdfplumber, which keeps line order and spacing well.
pypdf is the fallback for files pdfplumber cannot handle. Scanned documents are
reported honestly instead of being passed on as an almost empty resume.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pdfplumber
import pypdf

from app.core import cleaning
from app.core.errors import CorruptPdfError, EmptyDocumentError, EncryptedPdfError
from app.core.schemas import ExtractionResult, Page

logger = logging.getLogger(__name__)

PDF_MAGIC = b"%PDF-"
MIN_TEXT_CHARS = 150
MIN_CHARS_PER_PAGE = 100


def is_pdf_bytes(data: bytes) -> bool:
    """A real PDF starts with `%PDF-`, optionally after a little junk."""
    return PDF_MAGIC in data[:1024]


def _read_with_pdfplumber(path: Path) -> list[Page]:
    pages: list[Page] = []
    with pdfplumber.open(str(path)) as pdf:
        for number, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            pages.append(Page(number=number, text=text, char_count=len(text.strip())))
    return pages


def is_encrypted(path: Path) -> bool:
    """Is the PDF password protected in a way that blocks reading?

    Many PDFs are "encrypted" with an empty owner password and open fine, so an
    empty password is tried before declaring the file locked.
    """
    try:
        reader = pypdf.PdfReader(str(path))
    except pypdf.errors.FileNotDecryptedError:
        return True
    except pypdf.errors.PdfReadError:
        return False

    if not reader.is_encrypted:
        return False

    try:
        return reader.decrypt("") == pypdf.PasswordType.NOT_DECRYPTED
    except Exception as exc:
        logger.info("could not decrypt %s: %s", path.name, exc)
        return True


def _read_with_pypdf(path: Path) -> list[Page]:
    reader = pypdf.PdfReader(str(path))
    if reader.is_encrypted:
        try:
            decrypted = reader.decrypt("") != pypdf.PasswordType.NOT_DECRYPTED
        except Exception as exc:
            raise EncryptedPdfError(technical_detail=str(exc)) from exc
        if not decrypted:
            raise EncryptedPdfError(technical_detail="empty password was rejected")

    pages: list[Page] = []
    for number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        pages.append(Page(number=number, text=text, char_count=len(text.strip())))
    return pages


def _total_chars(pages: list[Page]) -> int:
    return sum(page.char_count for page in pages)


def extract_pages(path: str | Path) -> tuple[list[Page], str, list[str]]:
    """Extract raw per-page text, falling back to pypdf when needed."""
    path = Path(path)
    if not path.exists():
        raise CorruptPdfError(technical_detail=f"file not found: {path}")

    with path.open("rb") as handle:
        if not is_pdf_bytes(handle.read(1024)):
            raise CorruptPdfError(technical_detail="missing %PDF- header")

    if is_encrypted(path):
        raise EncryptedPdfError(technical_detail="PDF is password protected")

    warnings: list[str] = []
    pages: list[Page] = []
    method = "pdfplumber"

    try:
        pages = _read_with_pdfplumber(path)
    except EncryptedPdfError:
        raise
    except Exception as exc:
        logger.warning("pdfplumber failed for %s: %s", path.name, exc)
        warnings.append("Primary extractor failed; used the fallback extractor.")
        pages = []

    if not pages or _total_chars(pages) < MIN_TEXT_CHARS:
        try:
            fallback_pages = _read_with_pypdf(path)
        except EncryptedPdfError:
            raise
        except Exception as exc:
            if pages:
                logger.warning("pypdf fallback failed for %s: %s", path.name, exc)
            else:
                raise CorruptPdfError(technical_detail=str(exc)) from exc
        else:
            # An image-only PDF yields zero characters from both extractors; the
            # fallback pages are still used so the document is reported as
            # scanned rather than as unreadable.
            if not pages or _total_chars(fallback_pages) > _total_chars(pages):
                if pages:
                    warnings.append("Primary extractor found little text; used the fallback.")
                pages = fallback_pages
                method = "pypdf"

    if not pages:
        raise CorruptPdfError(technical_detail="no pages could be read")

    return pages, method, warnings


def extract_text(path: str | Path, strict: bool = False) -> ExtractionResult:
    """Extract and clean the text of a resume PDF.

    A structurally valid PDF that holds scanned images rather than text is not
    an error: the result comes back with `is_probably_scanned` set and a
    warning saying OCR is not available, so nothing pretends text was read.
    Pass `strict=True` to raise `EmptyDocumentError` for such a document.
    """
    pages, method, warnings = extract_pages(path)

    lines = cleaning.build_lines(pages)
    text = cleaning.lines_to_text(lines)
    char_count = len(text.strip())
    word_count = len(text.split())

    is_probably_scanned = char_count < MIN_TEXT_CHARS or (
        char_count / max(len(pages), 1) < MIN_CHARS_PER_PAGE
    )

    if is_probably_scanned:
        if strict:
            raise EmptyDocumentError(
                technical_detail=f"only {char_count} characters over {len(pages)} page(s)"
            )
        warnings.append(
            "Almost no text could be read, so this is probably a scanned or image-only "
            "PDF. ResumeIQ does not run OCR, so please upload a text-based PDF."
        )

    if len(pages) > 1 and any(page.char_count == 0 for page in pages):
        warnings.append("Some pages contain no text and may be images.")

    return ExtractionResult(
        text=text,
        lines=lines,
        pages=pages,
        method=method,
        page_count=len(pages),
        char_count=char_count,
        word_count=word_count,
        is_probably_scanned=is_probably_scanned,
        warnings=warnings,
    )
