from __future__ import annotations

from pathlib import Path

import pytest

from app.core import extraction
from app.core.errors import CorruptPdfError, EmptyDocumentError


def test_is_pdf_bytes():
    assert extraction.is_pdf_bytes(b"%PDF-1.7 ...")
    assert not extraction.is_pdf_bytes(b"PK\x03\x04 zip file")
    assert not extraction.is_pdf_bytes(b"")


def test_extract_text_reads_content_and_metadata(sample_pdf: Path):
    result = extraction.extract_text(sample_pdf)

    assert result.method == "pdfplumber"
    assert result.page_count == 2
    assert result.word_count > 20
    assert "SKILLS" in result.text
    assert "EDUCATION" in result.text
    assert not result.is_probably_scanned


def test_extract_text_preserves_page_and_line_numbers(sample_pdf: Path):
    result = extraction.extract_text(sample_pdf)

    assert {line.page for line in result.lines} == {1, 2}
    assert [line.index for line in result.lines] == list(range(result.line_count))

    education = next(line for line in result.lines if line.text == "EDUCATION")
    assert education.page == 2
    assert result.lines_on_page(2)[0].text == "EDUCATION"


def test_extract_text_normalizes_bullets(sample_pdf: Path):
    result = extraction.extract_text(sample_pdf)
    bullets = [line.text for line in result.lines if line.text.startswith("- ")]
    assert any("Python, Flask" in line for line in bullets)


def test_extract_text_rejects_non_pdf(fake_pdf: Path):
    with pytest.raises(CorruptPdfError):
        extraction.extract_text(fake_pdf)


def test_extract_text_rejects_missing_file(tmp_path: Path):
    with pytest.raises(CorruptPdfError):
        extraction.extract_text(tmp_path / "nope.pdf")


def test_extract_text_flags_scanned_pdf(empty_pdf: Path):
    with pytest.raises(EmptyDocumentError):
        extraction.extract_text(empty_pdf)

    result = extraction.extract_text(empty_pdf, allow_empty=True)
    assert result.is_probably_scanned
    assert result.warnings


def test_extract_pages_falls_back_to_pypdf(monkeypatch, sample_pdf: Path):
    def boom(_path):
        raise RuntimeError("pdfplumber exploded")

    monkeypatch.setattr(extraction, "_read_with_pdfplumber", boom)

    pages, method, warnings = extraction.extract_pages(sample_pdf)

    assert method == "pypdf"
    assert len(pages) == 2
    assert warnings


def test_to_dict_is_json_serializable(sample_pdf: Path):
    import json

    result = extraction.extract_text(sample_pdf)
    payload = json.loads(json.dumps(result.to_dict()))

    assert payload["page_count"] == 2
    assert payload["lines"][0]["page"] == 1
