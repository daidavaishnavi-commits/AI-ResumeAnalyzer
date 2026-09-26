"""Exceptions raised by the analysis core.

Each carries a message meant for the user and an optional technical detail that
belongs in the log, never on the page.
"""

from __future__ import annotations


class ResumeIQError(Exception):
    user_message = "Something went wrong while processing the file."

    def __init__(self, user_message: str | None = None, technical_detail: str = ""):
        self.user_message = user_message or type(self).user_message
        self.technical_detail = technical_detail
        super().__init__(self.user_message)


class UnsupportedFileError(ResumeIQError):
    user_message = "Only PDF files are supported right now."


class FileTooLargeError(ResumeIQError):
    user_message = "The file is larger than the 5 MB limit."


class CorruptPdfError(ResumeIQError):
    user_message = "This file could not be opened as a PDF. It may be corrupt."


class EncryptedPdfError(ResumeIQError):
    user_message = "This PDF is password protected. Please upload an unlocked copy."


class EmptyDocumentError(ResumeIQError):
    user_message = (
        "No readable text was found in this PDF. It looks like a scanned image, "
        "so please upload a text-based PDF."
    )
