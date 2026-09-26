from __future__ import annotations

from pathlib import Path

import pytest
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from app import create_app

SAMPLE_PAGES = [
    [
        "VAISHNAVI DAIDA",
        "vaishnavi@example.com | +91 98765 43210 | github.com/example",
        "",
        "SKILLS",
        "\u2022 Python, Flask, SQLAlchemy",
        "\u2022 SQLite, Git, Bootstrap",
        "",
        "EXPERIENCE",
        "Software Engineering Intern, Acme Corp (Jun 2024 - Aug 2024)",
        "\u2022 Built a report generator in Python that cut manual work by 40%",
    ],
    [
        "EDUCATION",
        "B.Tech Computer Science, 2023 - 2027",
        "",
        "PROJECTS",
        "ResumeIQ - explainable resume and job matcher",
    ],
]


def write_pdf(path: Path, pages: list[list[str]]) -> Path:
    pdf = canvas.Canvas(str(path), pagesize=A4)
    for page_lines in pages:
        text = pdf.beginText(50, 800)
        for line in page_lines:
            text.textLine(line)
        pdf.drawText(text)
        pdf.showPage()
    pdf.save()
    return path


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    return write_pdf(tmp_path / "resume.pdf", SAMPLE_PAGES)


@pytest.fixture
def empty_pdf(tmp_path: Path) -> Path:
    """A valid PDF with a single page and almost no text, like a scan."""
    return write_pdf(tmp_path / "scanned.pdf", [["."]])


@pytest.fixture
def fake_pdf(tmp_path: Path) -> Path:
    path = tmp_path / "not_really.pdf"
    path.write_bytes(b"This is plain text pretending to be a PDF." * 10)
    return path


@pytest.fixture
def app(tmp_path: Path):
    application = create_app("testing")
    application.config["UPLOAD_FOLDER"] = str(tmp_path / "uploads")
    Path(application.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    return application


@pytest.fixture
def client(app):
    return app.test_client()
