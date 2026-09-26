"""Upload and extraction routes (Stage 1).

Stage 1 stops at extraction: the preview page shows what was read from the PDF
so the pipeline can be checked with real resumes before section detection and
matching are built on top of it.
"""

from __future__ import annotations

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for

from app.core.errors import ResumeIQError
from app.services import upload_service

analyze_bp = Blueprint("analyze", __name__)

PREVIEW_LINE_LIMIT = 200


@analyze_bp.route("/upload", methods=["GET"])
def upload_form():
    return render_template("upload.html")


@analyze_bp.route("/upload", methods=["POST"])
def upload():
    try:
        result = upload_service.process_upload(
            request.files.get("resume"),
            current_app.config["UPLOAD_FOLDER"],
            current_app.config["MAX_CONTENT_LENGTH"],
            keep_file=current_app.config["KEEP_UPLOADED_FILES"],
        )
    except ResumeIQError as error:
        current_app.logger.info(
            "upload rejected: %s (%s)", error.user_message, error.technical_detail
        )
        flash(error.user_message, "danger")
        return redirect(url_for("analyze.upload_form"))

    extraction = result.extraction
    for warning in extraction.warnings:
        flash(warning, "warning")

    return render_template(
        "extraction_preview.html",
        filename=result.stored_file.original_filename,
        extraction=extraction,
        lines=extraction.lines[:PREVIEW_LINE_LIMIT],
        truncated=extraction.line_count > PREVIEW_LINE_LIMIT,
    )
