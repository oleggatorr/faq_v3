"""
Сервис сохранения файлов на диск.

Отвечает за:
- сохранение загруженных файлов;
- генерацию уникального stored_filename;
- валидацию размера и типа.
"""
from __future__ import annotations

import hashlib
import uuid
from pathlib import Path
from typing import BinaryIO

from app.core.config import settings


class FileStorageError(Exception):
    """Ошибка при работе с файлами."""


class FileStorageService:
    """
    Сохранение файлов в директорию uploads.
    stored_filename = uuid + сохранённое расширение.
    """

    def __init__(self, *, base_dir: Path | str | None = None):
        self.base_dir = Path(base_dir or settings.UPLOAD_DIR)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _safe_extension(self, filename: str) -> str:
        """Извлекает расширение, ограничивает до 20 символов."""
        ext = Path(filename).suffix
        if not ext or len(ext) > 20:
            return ""
        return ext.lower()

    def _make_stored_filename(self, original_filename: str) -> str:
        """Уникальное имя: uuid + расширение."""
        ext = self._safe_extension(original_filename)
        return f"{uuid.uuid4().hex}{ext}"

    def save(
        self,
        *,
        content: bytes,
        original_filename: str,
        mime_type: str,
        max_size: int | None = None,
    ) -> dict:
        """
        Сохраняет файл. Возвращает метаданные для Attachment:
        - original_filename
        - stored_filename
        - file_path (относительный от base_dir или полный)
        - file_size
        - mime_type
        - file_hash (sha256 hex, опционально)
        """
        max_size = max_size or settings.UPLOAD_MAX_SIZE
        if len(content) > max_size:
            raise FileStorageError(
                f"Файл слишком большой. Максимум: {max_size} байт"
            )

        stored_filename = self._make_stored_filename(original_filename)
        rel_path = stored_filename
        full_path = self.base_dir / rel_path

        full_path.write_bytes(content)
        file_hash = hashlib.sha256(content).hexdigest()

        return {
            "original_filename": original_filename[:255],
            "stored_filename": stored_filename[:100],
            "file_path": str(rel_path),
            "file_size": len(content),
            "mime_type": mime_type[:100],
            "file_hash": file_hash,
        }

    def get_path(self, file_path: str) -> Path:
        """Возвращает полный путь к файлу."""
        return self.base_dir / file_path

    def exists(self, file_path: str) -> bool:
        return self.get_path(file_path).is_file()
