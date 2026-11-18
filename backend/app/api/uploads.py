"""Reading an uploaded file within the limits set in the settings.

MAX_UPLOAD_SIZE and ALLOWED_EXTENSIONS used to exist without being enforced
anywhere: any file of any size and type went through. Every endpoint that
receives a file reads it with read_upload.

The size is checked while reading, after the multipart parser has received the
body; the reverse proxy in front of the API should cap the body size as well.
"""
from pathlib import PurePath
from typing import Iterable, Optional

from fastapi import HTTPException, UploadFile

from app.core.config import settings

_CHUNK_SIZE = 1024 * 1024

# Formats the questionnaire parser reads (services/file_parser.py).
QUESTIONNAIRE_EXTENSIONS = ("xlsx", "xls", "csv", "json")


def file_extension(filename: Optional[str]) -> str:
    """'Report.PDF' -> 'pdf'; '' when there is none."""
    return PurePath(filename or "").suffix.lower().lstrip(".")


async def read_upload(file: UploadFile, allowed_extensions: Optional[Iterable[str]] = None) -> bytes:
    """Return the file's bytes, or refuse it with a 400 (type) or a 413 (size).

    `allowed_extensions` defaults to settings.allowed_extensions.
    """
    allowed = sorted(settings.allowed_extensions if allowed_extensions is None
                     else (ext.lower() for ext in allowed_extensions))
    if file_extension(file.filename) not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Accepted types: {', '.join(allowed)}",
        )

    data = bytearray()
    while chunk := await file.read(_CHUNK_SIZE):
        data.extend(chunk)
        if len(data) > settings.max_upload_size:
            raise HTTPException(
                status_code=413,
                detail=f"File too large (limit: {settings.max_upload_size // (1024 * 1024)} MB)",
            )
    return bytes(data)
