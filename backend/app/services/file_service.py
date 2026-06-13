import logging
import os
import uuid
from pathlib import Path

import aiofiles
from fastapi import HTTPException, UploadFile, status

from app.config import get_settings

logger = logging.getLogger(__name__)

try:
    import magic

    _HAS_LIBMAGIC = True
except (ImportError, OSError):
    magic = None  # type: ignore[assignment]
    _HAS_LIBMAGIC = False
    logger.warning(
        "python-magic libmagic not available; falling back to signature-based MIME checks"
    )

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}

EXTENSION_MIME_MAP: dict[str, set[str]] = {
    ".pdf": {"application/pdf"},
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
    ".png": {"image/png"},
}

FILE_SIGNATURES: dict[str, bytes] = {
    ".pdf": b"%PDF",
    ".jpg": b"\xff\xd8\xff",
    ".jpeg": b"\xff\xd8\xff",
    ".png": b"\x89PNG\r\n\x1a\n",
}


def _detect_mime(content: bytes, extension: str) -> str:
    if _HAS_LIBMAGIC and magic is not None:
        return magic.from_buffer(content, mime=True)

    signature = FILE_SIGNATURES.get(extension)
    if signature and content.startswith(signature):
        return next(iter(EXTENSION_MIME_MAP[extension]))

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"File content does not match extension '{extension}'",
    )


async def validate_file(file: UploadFile) -> None:
    settings = get_settings()

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    extension = Path(file.filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Accepted: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    content = await file.read()
    await file.seek(0)

    max_size_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if len(content) > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File exceeds maximum size of {settings.MAX_FILE_SIZE_MB} MB",
        )

    detected_mime = _detect_mime(content, extension)
    allowed_mimes = EXTENSION_MIME_MAP[extension]
    if detected_mime not in allowed_mimes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"MIME type '{detected_mime}' does not match extension '{extension}'",
        )


async def save_file(
    file: UploadFile,
    upload_dir: str,
) -> tuple[str, str, int]:
    extension = Path(file.filename).suffix.lower()
    stored_filename = f"{uuid.uuid4()}{extension}"
    file_path = os.path.join(upload_dir, stored_filename)

    os.makedirs(upload_dir, exist_ok=True)

    content = await file.read()
    async with aiofiles.open(file_path, "wb") as output:
        await output.write(content)

    file_size_kb = max(1, len(content) // 1024)
    return stored_filename, file_path, file_size_kb


def delete_file(file_path: str) -> None:
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except OSError:
        logger.exception("Failed to delete file: %s", file_path)
        raise
