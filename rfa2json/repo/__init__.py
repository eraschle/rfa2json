from pathlib import Path
from typing import Protocol, runtime_checkable

from models import RevitFamilyEntry


@runtime_checkable
class RevitFamilyRepository(Protocol):
    """Protokoll für das Speichern und Laden von Revit Family Daten."""

    def save(self, entry: RevitFamilyEntry, file_path: Path) -> None:
        """
        Speichert einen RevitFamilyEntry in eine Datei.

        Args:
            entry: Zu speichernder RevitFamilyEntry
            file_path: Zielpfad für die Datei
        """
        ...

    def load(self, file_path: Path) -> RevitFamilyEntry:
        """
        Lädt einen RevitFamilyEntry aus einer Datei.

        Args:
            file_path: Pfad zur zu ladenden Datei

        Returns:
            Geladener RevitFamilyEntry
        """
        ...
