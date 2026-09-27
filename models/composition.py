"""Музыкальная композиция."""

from pathlib import Path


class Composition:
    """Музыкальная композиция: путь к файлу и название."""

    def __init__(self, file_path: str) -> None:
        """Создать композицию из пути к аудиофайлу."""
        self.file_path = file_path

    @property
    def title(self) -> str:
        """Название: имя файла без папки и расширения."""
        return Path(self.file_path).stem

    def __str__(self) -> str:
        """Название для показа в интерфейсе."""
        return self.title
