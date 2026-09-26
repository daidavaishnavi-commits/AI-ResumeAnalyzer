from __future__ import annotations

import io
from pathlib import Path

import pytest
from werkzeug.datastructures import FileStorage

from app.core.errors import EmptyDocumentError, FileTooLargeError, UnsupportedFileError
from app.services import upload_service

MAX_BYTES = 5 * 1024 * 1024


def storage_from(path: Path, filename: str | None = None) -> FileStorage:
    return FileStorage(
        stream=io.BytesIO(path.read_bytes()),
        filename=filename or path.name,
        content_type="application/pdf",
    )


def test_validate_upload_accepts_a_real_pdf(sample_pdf: Path):
    upload_service.validate_upload(storage_from(sample_pdf), MAX_BYTES)


def test_validate_upload_requires_a_file():
    with pytest.raises(UnsupportedFileError):
        upload_service.validate_upload(None, MAX_BYTES)


def test_validate_upload_rejects_wrong_extension(sample_pdf: Path):
    with pytest.raises(UnsupportedFileError):
        upload_service.validate_upload(storage_from(sample_pdf, "resume.docx"), MAX_BYTES)


def test_validate_upload_rejects_fake_pdf(fake_pdf: Path):
    with pytest.raises(UnsupportedFileError):
        upload_service.validate_upload(storage_from(fake_pdf), MAX_BYTES)


def test_validate_upload_rejects_empty_file():
    storage = FileStorage(stream=io.BytesIO(b""), filename="resume.pdf")
    with pytest.raises(UnsupportedFileError):
        upload_service.validate_upload(storage, MAX_BYTES)


def test_validate_upload_enforces_size_limit(sample_pdf: Path):
    with pytest.raises(FileTooLargeError):
        upload_service.validate_upload(storage_from(sample_pdf), 100)


def test_store_upload_uses_a_random_filename(sample_pdf: Path, tmp_path: Path):
    stored = upload_service.store_upload(
        storage_from(sample_pdf, "../../etc/passwd.pdf"), tmp_path / "uploads"
    )

    assert stored.path.parent == tmp_path / "uploads"
    assert stored.stored_filename.endswith(".pdf")
    assert "/" not in stored.original_filename
    assert ".." not in stored.original_filename
    assert stored.path.exists()
    assert len(stored.sha256) == 64


def test_process_upload_returns_extraction(sample_pdf: Path, tmp_path: Path):
    result = upload_service.process_upload(
        storage_from(sample_pdf), tmp_path / "uploads", MAX_BYTES
    )

    assert result.extraction.page_count == 2
    assert result.stored_file.path.exists()


def test_process_upload_deletes_the_file_when_extraction_fails(empty_pdf: Path, tmp_path: Path):
    upload_folder = tmp_path / "uploads"

    with pytest.raises(EmptyDocumentError):
        upload_service.process_upload(storage_from(empty_pdf), upload_folder, MAX_BYTES)

    assert list(upload_folder.glob("*.pdf")) == []
