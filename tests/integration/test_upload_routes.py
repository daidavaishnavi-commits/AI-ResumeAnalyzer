from __future__ import annotations

import io
from pathlib import Path


def post_pdf(client, path: Path, filename: str = "resume.pdf"):
    return client.post(
        "/upload",
        data={"resume": (io.BytesIO(path.read_bytes()), filename)},
        content_type="multipart/form-data",
        follow_redirects=True,
    )


def test_index_and_upload_pages_render(client):
    assert client.get("/").status_code == 200
    assert b"Upload your resume" in client.get("/upload").data


def test_upload_shows_extracted_lines(client, sample_pdf: Path):
    response = post_pdf(client, sample_pdf)

    assert response.status_code == 200
    body = response.data.decode()
    assert "Extracted text" in body
    assert "SKILLS" in body
    assert "EDUCATION" in body


def test_upload_does_not_leave_files_behind(app, client, sample_pdf: Path):
    for _ in range(3):
        post_pdf(client, sample_pdf)
    assert list(Path(app.config["UPLOAD_FOLDER"]).glob("*.pdf")) == []


def test_upload_rejects_non_pdf_extension(client, sample_pdf: Path):
    response = post_pdf(client, sample_pdf, filename="resume.txt")
    assert b"Only PDF files are supported" in response.data


def test_upload_rejects_fake_pdf(client, fake_pdf: Path):
    response = post_pdf(client, fake_pdf)
    assert b"not a real PDF" in response.data


def test_upload_reports_scanned_pdf_without_failing(client, empty_pdf: Path):
    response = post_pdf(client, empty_pdf)

    assert response.status_code == 200
    body = response.data.decode()
    assert "Extracted text" in body
    assert "OCR" in body


def test_upload_reports_image_only_pdf_as_scanned(client, image_only_pdf: Path):
    response = post_pdf(client, image_only_pdf)

    assert response.status_code == 200
    assert "OCR" in response.data.decode()


def test_upload_reports_password_protected_pdf(client, encrypted_pdf: Path):
    response = post_pdf(client, encrypted_pdf)
    assert b"password protected" in response.data


def test_upload_without_file_is_rejected(client):
    response = client.post("/upload", data={}, follow_redirects=True)
    assert b"Please choose a PDF file" in response.data


def test_oversized_upload_returns_413(app, client, sample_pdf: Path):
    app.config["MAX_CONTENT_LENGTH"] = 1024
    response = client.post(
        "/upload",
        data={"resume": (io.BytesIO(sample_pdf.read_bytes()), "resume.pdf")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 413


def test_unknown_page_returns_404(client):
    assert client.get("/does-not-exist").status_code == 404
