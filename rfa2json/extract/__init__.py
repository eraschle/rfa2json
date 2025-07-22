from pathlib import Path
from typing import Protocol, runtime_checkable

from ..models import RevitFamilyEntry


@runtime_checkable
class RevitFamilyReader(Protocol):
    """Protokoll für das Lesen von Revit Family Daten."""

    def read_from_file(self, file_path: Path) -> RevitFamilyEntry:
        """
        Liest Revit Family Daten aus einer .rfa Datei.

        Args:
            file_path: Pfad zur .rfa Datei

        Returns:
            RevitFamilyEntry mit den gelesenen Daten

        Raises:
            FileNotFoundError: Wenn die Datei nicht existiert
            ValueError: Wenn die Datei kein gültiges XML enthält
        """
        ...

    def read_from_xml_string(self, xml_content: str) -> RevitFamilyEntry:
        """
        Liest Revit Family Daten aus einem XML String.

        Args:
            xml_content: XML Inhalt als String

        Returns:
            RevitFamilyEntry mit den gelesenen Daten
        """
        ...
