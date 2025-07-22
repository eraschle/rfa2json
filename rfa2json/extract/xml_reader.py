import logging
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from ..factory import RevitFamilyFactory
from ..models import RevitFamilyEntry
from .json_extractor import XMLToJSONExtractor

logger = logging.getLogger(__name__)


class RevitFamilyXMLReader:
    """Implementierung für das Lesen von Revit Family XML Daten aus .rfa Dateien."""

    def __init__(self):
        """Initialisiert den Reader mit JSON-Extraktor und Factory."""
        self.json_extractor = XMLToJSONExtractor()
        self.factory = RevitFamilyFactory()

    # XML Start- und End-Pattern für die Suche in binären Daten
    XML_START_PATTERN = rb'<\?xml\s+version="1\.0"[^>]*\?>'
    XML_END_PATTERN = rb"</entry>"

    # Alternative Patterns falls das erste nicht funktioniert
    ENTRY_START_PATTERN = rb"<entry[^>]*>"
    ENTRY_END_PATTERN = rb"</entry>"

    def read_from_file(self, file_path: Path) -> RevitFamilyEntry:
        """
        Liest XML Daten aus einer .rfa Datei.

        .rfa Dateien sind binäre Dateien, die XML-Metadaten enthalten.
        Diese Methode extrahiert die XML-Daten aus der binären Datei.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Datei nicht gefunden: {file_path}")

        # Lese die gesamte Datei als binäre Daten
        with Path.open(file_path, mode="rb") as file:
            binary_content = file.read()

        # Extrahiere XML aus den binären Daten
        xml_content = self._extract_xml_from_binary(binary_content)

        if not xml_content:
            raise ValueError(f"Keine XML-Daten in der .rfa Datei gefunden: {file_path}")

        return self.read_from_xml_string(xml_content)

    def _extract_xml_from_binary(self, binary_data: bytes) -> str:
        """
        Extrahiert XML-Daten aus binären .rfa Daten.

        Sucht nach XML-Start und -End-Markern und extrahiert den dazwischenliegenden Inhalt.
        """
        # Methode 1: Suche nach vollständigem XML-Dokument (<?xml ... </entry>)
        xml_content = self._find_complete_xml_document(binary_data)
        if xml_content:
            return xml_content

        # Methode 2: Suche nur nach <entry> ... </entry>
        xml_content = self._find_entry_block(binary_data)
        if xml_content:
            # Füge XML-Deklaration hinzu, falls sie fehlt
            if not xml_content.startswith("<?xml"):
                xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_content
            return xml_content

        # Methode 3: Suche nach allen XML-ähnlichen Blöcken
        xml_content = self._find_any_xml_block(binary_data)
        if xml_content:
            return xml_content

        return ""

    def _find_complete_xml_document(self, binary_data: bytes) -> str:
        """Sucht nach einem vollständigen XML-Dokument mit Deklaration."""
        try:
            # Suche nach XML-Deklaration
            start_match = re.search(self.XML_START_PATTERN, binary_data)
            if not start_match:
                return ""

            start_pos = start_match.start()

            # Suche nach </entry> nach der XML-Deklaration
            end_match = re.search(self.XML_END_PATTERN, binary_data[start_pos:])
            if not end_match:
                return ""

            end_pos = start_pos + end_match.end()

            # Extrahiere XML-Inhalt
            xml_bytes = binary_data[start_pos:end_pos]

            # Versuche verschiedene Encodings
            for encoding in ["utf-8", "utf-16", "latin-1", "cp1252"]:
                try:
                    xml_content = xml_bytes.decode(encoding)
                    # Validiere, dass es gültiges XML ist
                    ET.fromstring(xml_content)
                    return xml_content
                except (UnicodeDecodeError, ET.ParseError):
                    continue

        except Exception:
            pass

        return ""

    def _find_entry_block(self, binary_data: bytes) -> str:
        """Sucht nach <entry> ... </entry> Block."""
        try:
            # Suche nach <entry> Tag
            start_match = re.search(self.ENTRY_START_PATTERN, binary_data)
            if not start_match:
                return ""

            start_pos = start_match.start()

            # Suche nach </entry>
            end_match = re.search(self.ENTRY_END_PATTERN, binary_data[start_pos:])
            if not end_match:
                return ""

            end_pos = start_pos + end_match.end()

            # Extrahiere XML-Inhalt
            xml_bytes = binary_data[start_pos:end_pos]

            # Versuche verschiedene Encodings
            for encoding in ["utf-8", "utf-16", "latin-1", "cp1252"]:
                try:
                    xml_content = xml_bytes.decode(encoding)
                    # Teste, ob es gültiges XML ist (mit hinzugefügter Deklaration)
                    test_xml = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_content
                    ET.fromstring(test_xml)
                    return xml_content
                except (UnicodeDecodeError, ET.ParseError):
                    continue

        except Exception:
            pass

        return ""

    def _find_any_xml_block(self, binary_data: bytes) -> str:
        """
        Fallback-Methode: Sucht nach beliebigen XML-ähnlichen Strukturen.

        Diese Methode versucht, XML-Daten zu finden, auch wenn sie nicht
        dem erwarteten Format entsprechen.
        """
        try:
            patterns = [
                rb"<entry[^>]*xmlns[^>]*>",  # Entry mit Namespace
                rb"<\w+[^>]*xmlns[^>]*>",  # Beliebiges Tag mit Namespace
                rb"<entry[^>]*>",  # Einfaches Entry-Tag
            ]

            for pattern in patterns:
                matches = list(re.finditer(pattern, binary_data))

                for match in matches:
                    start_pos = match.start()

                    # Suche nach passendem End-Tag
                    # Extrahiere Tag-Name aus dem Start-Tag
                    tag_match = re.match(rb"<(\w+)", binary_data[start_pos:])
                    if not tag_match:
                        continue

                    tag_name = tag_match.group(1)
                    end_pattern = rb"</" + tag_name + rb">"

                    end_match = re.search(end_pattern, binary_data[start_pos:])
                    if not end_match:
                        continue

                    end_pos = start_pos + end_match.end()
                    xml_bytes = binary_data[start_pos:end_pos]

                    # Versuche zu dekodieren
                    for encoding in ["utf-8", "utf-16", "latin-1", "cp1252"]:
                        try:
                            xml_content = xml_bytes.decode(encoding)

                            # Füge XML-Deklaration hinzu, falls nötig
                            if not xml_content.startswith("<?xml"):
                                xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_content

                            # Validiere XML
                            ET.fromstring(xml_content)
                            return xml_content
                        except (UnicodeDecodeError, ET.ParseError):
                            continue
        except Exception:
            pass

        return ""

    def read_from_xml_string(self, xml_content: str | bytes) -> RevitFamilyEntry:
        """
        Parst XML String zu RevitFamilyEntry.

        Verwendet die neue JSON-Extraktion und Factory-Pattern.
        """
        # Extrahiere JSON-Daten aus XML
        json_data = self.json_extractor.extract_from_xml_string(xml_content)

        # Erstelle RevitFamilyEntry über Factory
        entry = self.factory.create_revit_family_entry(json_data)

        # Validiere, dass keine Namespace-Prefixes verbleiben
        self._validate_cleaned_data(entry)

        return entry

    def _validate_cleaned_data(self, entry: RevitFamilyEntry) -> None:
        """
        Validiert, dass keine Namespace-Prefixes in den Daten verbleiben.

        Loggt Warnungen, falls noch Namespace-URIs gefunden werden.
        """
        namespace_patterns = [
            "{http://www.w3.org/2005/Atom}",
            "{urn:schemas-autodesk-com:partatom}",
        ]
        # Prüfe Parameter in Features
        for feature in entry.features:
            for group in feature.groups:
                for param in group.parameters:
                    message = f"Namespace-Prefix in Parameter gefunden: {param.name}"
                    for pattern in namespace_patterns:
                        if pattern in param.name:
                            logger.warning(message)
        # Prüfe Parameter in Family Parts
        if entry.family:
            for part in entry.family.parts:
                for param in part.parameters:
                    message = f"Namespace-Prefix in Family Part Parameter gefunden: {param.name}"
                    for pattern in namespace_patterns:
                        if pattern in param.name:
                            logger.warning(message)
