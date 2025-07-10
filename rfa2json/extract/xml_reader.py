import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

from models import (
    Category,
    DesignFile,
    Family,
    Feature,
    Link,
    Parameter,
    ParameterGroup,
    RevitFamilyEntry,
    Taxonomy,
)

logger = logging.getLogger(__name__)


class RevitFamilyXMLReader:
    """Implementierung für das Lesen von Revit Family XML Daten aus .rfa Dateien."""

    NAMESPACES = {
        "atom": "http://www.w3.org/2005/Atom",
        "A": "urn:schemas-autodesk-com:partatom",
    }

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

        Akzeptiert sowohl String als auch Bytes als Input.
        """
        # Konvertiere Bytes zu String falls nötig
        if isinstance(xml_content, bytes):
            # Versuche verschiedene Encodings
            for encoding in ["utf-8", "utf-16", "latin-1", "cp1252"]:
                try:
                    xml_content = xml_content.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                raise ValueError("Konnte XML-Inhalt nicht dekodieren")

        # Parse XML
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError:
            # Versuche, häufige XML-Probleme zu reparieren
            xml_content = self._repair_xml(xml_content)
            root = ET.fromstring(xml_content)

        entry = RevitFamilyEntry(
            name=self._get_title(root),
            id=self._get_id(root),
            updated=self._get_updated(root),
            taxonomies=self._get_taxonomies(root),
            categories=self._get_categories(root),
            links=self._get_links(root),
            features=self._get_features(root),
            family=self._get_family(root),
        )

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

    def _repair_xml(self, xml_content: str) -> str:
        """
        Versucht, häufige XML-Probleme zu reparieren.

        - Entfernt ungültige Zeichen
        - Repariert kaputte Encoding-Deklarationen
        - Escaped ungültige XML-Zeichen
        """
        # Entferne Null-Bytes und andere Kontrollzeichen
        xml_content = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", xml_content)

        # Repariere Encoding-Deklaration falls nötig
        if "<?xml" in xml_content and "encoding=" not in xml_content:
            xml_content = xml_content.replace(
                '<?xml version="1.0"?>',
                '<?xml version="1.0" encoding="UTF-8"?>',
            )

        # Escape ungültige XML-Zeichen in Text-Inhalten
        # (Dies ist eine vereinfachte Implementierung)
        xml_content = xml_content.replace("&", "&amp;")
        xml_content = xml_content.replace("<", "&lt;").replace(">", "&gt;")

        # Repariere die Tags wieder (sehr einfache Implementierung)
        return re.sub(r"&lt;(\/?[\w:]+[^&]*?)&gt;", r"<\1>", xml_content)

    def _get_title(self, root: ET.Element) -> str:
        """Extrahiert den Titel."""
        title_elem = root.find("atom:title", self.NAMESPACES)
        return title_elem.text if title_elem is not None and title_elem.text else ""

    def _get_id(self, root: ET.Element) -> str:
        """Extrahiert die ID."""
        id_elem = root.find("atom:id", self.NAMESPACES)
        return id_elem.text if id_elem is not None and id_elem.text else ""

    def _get_updated(self, root: ET.Element) -> datetime:
        """Extrahiert das Update-Datum."""
        updated_elem = root.find("atom:updated", self.NAMESPACES)
        if updated_elem is not None and updated_elem.text:
            try:
                return datetime.fromisoformat(updated_elem.text.replace("Z", "+00:00"))
            except ValueError:
                # Fallback für ungültige Datumsformate
                pass
        return datetime.now()

    def _get_taxonomies(self, root: ET.Element) -> list[Taxonomy]:
        """Extrahiert Taxonomien."""
        taxonomies = []
        for taxonomy_elem in root.findall("A:taxonomy", self.NAMESPACES):
            term_elem = taxonomy_elem.find("atom:term", self.NAMESPACES)
            label_elem = taxonomy_elem.find("atom:label", self.NAMESPACES)

            if term_elem is not None and label_elem is not None:
                taxonomies.append(
                    Taxonomy(term=term_elem.text or "", label=label_elem.text or ""),
                )
        return taxonomies

    def _get_categories(self, root: ET.Element) -> list[Category]:
        """Extrahiert Kategorien."""
        categories = []
        for category_elem in root.findall("atom:category", self.NAMESPACES):
            term_elem = category_elem.find("atom:term", self.NAMESPACES)

            if term_elem is not None:
                categories.append(Category(name=term_elem.text or ""))
        return categories

    def _get_links(self, root: ET.Element) -> list[Link]:
        """Extrahiert Links."""
        links = []
        for link_elem in root.findall("atom:link", self.NAMESPACES):
            rel = link_elem.get("rel", "")
            type_attr = link_elem.get("type", "")
            href = link_elem.get("href", "")

            design_file = self._get_design_file(link_elem)

            links.append(
                Link(rel=rel, type=type_attr, href=href, design_file=design_file),
            )
        return links

    def _get_design_file(self, link_elem: ET.Element) -> DesignFile | None:
        """Extrahiert Design File Informationen."""
        design_file_elem = link_elem.find("A:design-file", self.NAMESPACES)
        if design_file_elem is None:
            return None

        title_elem = design_file_elem.find("A:title", self.NAMESPACES)
        product_elem = design_file_elem.find("A:product", self.NAMESPACES)
        version_elem = design_file_elem.find("A:product-version", self.NAMESPACES)
        updated_elem = design_file_elem.find("A:updated", self.NAMESPACES)

        updated = datetime.now()
        if updated_elem is not None and updated_elem.text:
            try:
                updated = datetime.fromisoformat(
                    updated_elem.text.replace("Z", "+00:00"),
                )
            except ValueError:
                pass

        return DesignFile(
            name=title_elem.text if title_elem is not None and title_elem.text else "",
            product=product_elem.text if product_elem is not None and product_elem.text else "",
            product_version=version_elem.text if version_elem is not None and version_elem.text else "",
            updated=updated,
        )

    def _get_features(self, root: ET.Element) -> list[Feature]:
        """Extrahiert Features."""
        features = []
        features_elem = root.find("A:features", self.NAMESPACES)
        if features_elem is None:
            return features

        for feature_elem in features_elem.findall("A:feature", self.NAMESPACES):
            title_elem = feature_elem.find("A:title", self.NAMESPACES)
            title = title_elem.text if title_elem is not None and title_elem.text else ""

            groups = self._get_parameter_groups(feature_elem)
            features.append(Feature(name=title, groups=groups))

        return features

    def _get_parameter_groups(self, feature_elem: ET.Element) -> list[ParameterGroup]:
        """Extrahiert Parametergruppen."""
        groups = []
        for group_elem in feature_elem.findall("A:group", self.NAMESPACES):
            title_elem = group_elem.find("A:title", self.NAMESPACES)
            title = title_elem.text if title_elem is not None and title_elem.text else ""

            parameters = self._get_parameters_from_group(group_elem)
            groups.append(ParameterGroup(name=title, parameters=parameters))

        return groups

    def _get_parameters_from_group(self, group_elem: ET.Element) -> list[Parameter]:
        """Extrahiert Parameter aus einer Gruppe."""
        parameters = []
        for child in group_elem:
            # Skip bekannte Namespace-Elemente
            cleaned_tag = self._clean_tag_name(child.tag)

            # Skip A: namespace elements und title elements
            if child.tag.startswith("{" + self.NAMESPACES["A"] + "}") or cleaned_tag.lower() == "title":
                continue

            param = self._create_parameter_from_element(child)
            if param:
                parameters.append(param)

        return parameters

    def _clean_tag_name(self, tag_name: str) -> str:
        """
        Entfernt Namespace-Prefixes aus Tag-Namen.

        Konvertiert z.B. "{http://www.w3.org/2005/Atom}Material_Family" zu "Material_Family"
        """
        if tag_name.startswith("{"):
            # Finde das Ende des Namespace
            namespace_end = tag_name.find("}")
            if namespace_end != -1:
                return tag_name[namespace_end + 1 :]
        return tag_name

    def _create_parameter_from_element(self, elem: ET.Element) -> Parameter | None:
        """Erstellt einen Parameter aus einem XML Element."""
        # Bereinige den Tag-Namen von Namespace-Prefixes
        name = self._clean_tag_name(elem.tag)
        display_name = elem.get("displayName")
        param_type = elem.get("type", "custom")
        type_of_parameter = elem.get("typeOfParameter")
        units = elem.get("units")
        value = elem.text

        return Parameter(
            name=name,
            display_name=display_name,
            type=param_type,
            type_of_parameter=type_of_parameter,
            units=units,
            value=value,
        )

    def _get_family(self, root: ET.Element) -> Family | None:
        """Extrahiert Family Informationen."""
        family_elem = root.find("A:family", self.NAMESPACES)
        if family_elem is None:
            return None

        family_type = family_elem.get("type", "user")

        variation_count_elem = family_elem.find("A:variationCount", self.NAMESPACES)
        variation_count = 0
        if variation_count_elem is not None and variation_count_elem.text:
            try:
                variation_count = int(variation_count_elem.text)
            except ValueError:
                variation_count = 0

        parts = self._get_family_parts(family_elem)

        return Family(type=family_type, variation_count=variation_count, parts=parts)

    def _get_family_parts(self, family_elem: ET.Element) -> list[FamilyPart]:
        """Extrahiert Family Parts."""
        parts = []
        for part_elem in family_elem.findall("A:part", self.NAMESPACES):
            title_elem = part_elem.find("atom:title", self.NAMESPACES)
            title = title_elem.text if title_elem is not None and title_elem.text else ""

            part_type = part_elem.get("type", "user")
            parameters = self._get_parameters_from_part(part_elem)

            parts.append(FamilyPart(name=title, type=part_type, parameters=parameters))

        return parts

    def _get_parameters_from_part(self, part_elem: ET.Element) -> list[Parameter]:
        """Extrahiert Parameter aus einem Family Part."""
        parameters = []
        for child in part_elem:
            # Skip title elements (mit und ohne Namespace)
            cleaned_tag = self._clean_tag_name(child.tag)

            if child.tag in ["{" + self.NAMESPACES["atom"] + "}title"] or cleaned_tag.lower() == "title":
                continue

            param = self._create_parameter_from_element(child)
            if param:
                parameters.append(param)

        return parameters
