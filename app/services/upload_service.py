"""Upload handling: validate, store and extract an uploaded resume.

This is the only place that touches both the filesystem and `app.core`.
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from dataclasses import dataclass
from pathlib import Path

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from app.core import extraction
from app.core.errors import FileTooLargeError, ResumeIQError, UnsupportedFileError
from app.core.schemas import ExtractionResult

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {"pdf"}


@dataclass
class StoredFile:
    path: Path
    original_filename: str
    stored_filename: str
    size: int
    sha256: str

    def delete(self) -> None:
        self.path.unlink(missing_ok=True)


@dataclass
class UploadResult:
    stored_file: StoredFile
    extraction: ExtractionResult


def has_allowed_extension(filename: str) -> bool:
    if "." not in filename:
        return False
    return filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def file_size(storage: FileStorage) -> int:
    storage.stream.seek(0, 2)
    size = storage.stream.tell()
    storage.stream.seek(0)
    return size


def validate_upload(storage: FileStorage | None, max_bytes: int) -> None:
    """Reject anything that is not a plausible PDF within the size limit.

    The extension is checked first because it is cheap, then the magic bytes,
    because a browser-supplied content type can say anything.
    """
    if storage is None or not storage.filename:
        raise UnsupportedFileError("Please choose a PDF file to upload.")

    if not has_allowed_extension(storage.filename):
        raise UnsupportedFileError()

    size = file_size(storage)
    if size == 0:
        raise UnsupportedFileError("The uploaded file is empty.")
    if size > max_bytes:
        raise FileTooLargeError(
            f"The file is {size / (1024 * 1024):.1f} MB, which is over the "
            f"{max_bytes // (1024 * 1024)} MB limit."
        )

    header = storage.stream.read(1024)
    storage.stream.seek(0)
    if not extraction.is_pdf_bytes(header):
        raise UnsupportedFileError("That file is not a real PDF, even though it is named like one.")


def store_upload(storage: FileStorage, upload_folder: str | Path) -> StoredFile:
    """Save the upload under a random name; the original name is only metadata."""
    upload_folder = Path(upload_folder)
    upload_folder.mkdir(parents=True, exist_ok=True)

    original_filename = secure_filename(storage.filename or "resume.pdf") or "resume.pdf"
    stored_filename = f"{uuid.uuid4().hex}.pdf"
    path = upload_folder / stored_filename

    storage.stream.seek(0)
    data = storage.stream.read()
    path.write_bytes(data)

    return StoredFile(
        path=path,
        original_filename=original_filename,
        stored_filename=stored_filename,
        size=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
    )


def process_upload(
    storage: FileStorage | None, upload_folder: str | Path, max_bytes: int
) -> UploadResult:
    """Validate, store and extract. The file is removed if extraction fails."""
    validate_upload(storage, max_bytes)
    assert storage is not None  # guaranteed by validate_upload

    stored_file = store_upload(storage, upload_folder)
    try:
        result = extraction.extract_text(stored_file.path)
    except ResumeIQError:
        stored_file.delete()
        raise
    except Exception as exc:
        stored_file.delete()
        logger.exception("unexpected extraction failure for %s", stored_file.stored_filename)
        raise ResumeIQError(technical_detail=str(exc)) from exc

    return UploadResult(stored_file=stored_file, extraction=result)
