from __future__ import annotations

import io
import os
import time
from pathlib import Path

import pytest
from werkzeug.datastructures import FileStorage

from app.core.errors import EncryptedPdfError, FileTooLargeError, UnsupportedFileError
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


def test_process_upload_deletes_the_file_after_a_successful_extraction(
    sample_pdf: Path, tmp_path: Path
):
    upload_folder = tmp_path / "uploads"

    for _ in range(3):
        result = upload_service.process_upload(storage_from(sample_pdf), upload_folder, MAX_BYTES)
        assert result.extraction.page_count == 2

    assert list(upload_folder.glob("*.pdf")) == []
    assert result.file_retained is False


def test_process_upload_can_keep_the_file_when_asked(sample_pdf: Path, tmp_path: Path):
    upload_folder = tmp_path / "uploads"

    result = upload_service.process_upload(
        storage_from(sample_pdf), upload_folder, MAX_BYTES, keep_file=True
    )

    assert result.file_retained is True
    assert result.stored_file.path.exists()


def test_process_upload_deletes_the_file_when_extraction_fails(encrypted_pdf: Path, tmp_path: Path):
    upload_folder = tmp_path / "uploads"

    with pytest.raises(EncryptedPdfError):
        upload_service.process_upload(storage_from(encrypted_pdf), upload_folder, MAX_BYTES)

    assert list(upload_folder.glob("*.pdf")) == []


def test_purge_old_uploads_removes_only_stale_files(tmp_path: Path):
    upload_folder = tmp_path / "uploads"
    upload_folder.mkdir()
    stale = upload_folder / "stale.pdf"
    fresh = upload_folder / "fresh.pdf"
    stale.write_bytes(b"%PDF-1.4")
    fresh.write_bytes(b"%PDF-1.4")
    old = time.time() - 3600
    os.utime(stale, (old, old))

    removed = upload_service.purge_old_uploads(upload_folder, max_age_seconds=60)

    assert removed == 1
    assert not stale.exists()
    assert fresh.exists()
