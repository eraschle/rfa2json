from pathlib import Path

from json_repository import RevitFamilyJSONRepository
from models import RevitFamilyEntry
from protocols import RevitFamilyReader, RevitFamilyRepository
from xml_reader import RevitFamilyXMLReader


class RevitFamilyService:
    """Service für das Verwalten von Revit Family Daten."""

    def __init__(
        self,
        reader: RevitFamilyReader = None,
        repository: RevitFamilyRepository = None,
    ):
        self.reader = reader or RevitFamilyXMLReader()
        self.repository = repository or RevitFamilyJSONRepository()

    def extract_and_save(
        self,
        rfa_file_path: Path,
        json_output_path: Path,
    ) -> RevitFamilyEntry:
        """
        Extrahiert Daten aus .rfa Datei und speichert als JSON.

        Args:
            rfa_file_path: Pfad zur .rfa Datei
            json_output_path: Pfad für JSON Output

        Returns:
            Extrahierte RevitFamilyEntry
        """
        entry = self.reader.read_from_file(rfa_file_path)
        self.repository.save(entry, json_output_path)
        return entry

    def load_from_json(self, json_file_path: Path) -> RevitFamilyEntry:
        """Lädt RevitFamilyEntry aus JSON Datei."""
        return self.repository.load(json_file_path)

    def extract_from_xml_string(self, xml_content: str) -> RevitFamilyEntry:
        """Extrahiert Daten direkt aus XML String."""
        return self.reader.read_from_xml_string(xml_content)

    def get_family_parts(self, entry: RevitFamilyEntry) -> list:
        """Gibt alle Family Parts zurück."""
        if entry.family:
            return entry.family.parts
        return []

    def get_parameters_by_group(self, entry: RevitFamilyEntry, group_name: str) -> list:
        """Gibt alle Parameter einer bestimmten Gruppe zurück."""
        parameters = []
        for feature in entry.features:
            for group in feature.groups:
                if group.title == group_name:
                    parameters.extend(group.parameters)
        return parameters
