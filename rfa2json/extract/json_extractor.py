import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any


class XMLToJSONExtractor:
    """Extrahiert JSON-Daten aus XML-Tags für die weitere Verarbeitung durch eine Factory."""

    NAMESPACES = {
        "atom": "http://www.w3.org/2005/Atom",
        "A": "urn:schemas-autodesk-com:partatom",
    }

    def extract_from_xml_string(self, xml_content: str | bytes) -> dict[str, Any]:
        """
        Extrahiert JSON-Daten aus einem XML-String.

        Returns:
            Dict mit strukturierten JSON-Daten für die Factory
        """
        if isinstance(xml_content, bytes):
            for encoding in ["utf-8", "utf-16", "latin-1", "cp1252"]:
                try:
                    xml_content = xml_content.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                raise ValueError("Konnte XML-Inhalt nicht dekodieren")

        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError:
            xml_content = self._repair_xml(xml_content)
            root = ET.fromstring(xml_content)

        return self._extract_entry_data(root)

    def _extract_entry_data(self, root: ET.Element) -> dict[str, Any]:
        """Extrahiert die Hauptdaten des Entry-Elements."""
        return {
            "name": self._extract_title(root),
            "id": self._extract_id(root),
            "updated": self._extract_updated(root),
            "taxonomies": self._extract_taxonomies(root),
            "categories": self._extract_categories(root),
            "links": self._extract_links(root),
            "features": self._extract_features(root),
            "family": self._extract_family(root),
        }

    def _extract_title(self, root: ET.Element) -> str:
        """Extrahiert den Titel."""
        title_elem = root.find("atom:title", self.NAMESPACES)
        return title_elem.text if title_elem is not None and title_elem.text else ""

    def _extract_id(self, root: ET.Element) -> str:
        """Extrahiert die ID."""
        id_elem = root.find("atom:id", self.NAMESPACES)
        return id_elem.text if id_elem is not None and id_elem.text else ""

    def _extract_updated(self, root: ET.Element) -> str:
        """Extrahiert das Update-Datum als ISO-String."""
        updated_elem = root.find("atom:updated", self.NAMESPACES)
        if updated_elem is not None and updated_elem.text:
            try:
                dt = datetime.fromisoformat(updated_elem.text.replace("Z", "+00:00"))
                return dt.isoformat()
            except ValueError:
                pass
        return datetime.now().isoformat()

    def _extract_taxonomies(self, root: ET.Element) -> list[dict[str, str]]:
        """Extrahiert Taxonomien."""
        taxonomies = []
        for taxonomy_elem in root.findall("A:taxonomy", self.NAMESPACES):
            term_elem = taxonomy_elem.find("atom:term", self.NAMESPACES)
            label_elem = taxonomy_elem.find("atom:label", self.NAMESPACES)

            if term_elem is not None and label_elem is not None:
                taxonomies.append(
                    {
                        "term": term_elem.text or "",
                        "label": label_elem.text or "",
                    }
                )
        return taxonomies

    def _extract_categories(self, root: ET.Element) -> list[dict[str, str]]:
        """Extrahiert Kategorien."""
        categories = []
        for category_elem in root.findall("atom:category", self.NAMESPACES):
            term_elem = category_elem.find("atom:term", self.NAMESPACES)
            if term_elem is not None:
                categories.append({"name": term_elem.text or ""})
        return categories

    def _extract_links(self, root: ET.Element) -> list[dict[str, Any]]:
        """Extrahiert Links."""
        links = []
        for link_elem in root.findall("atom:link", self.NAMESPACES):
            link_data = {
                "rel": link_elem.get("rel", ""),
                "type": link_elem.get("type", ""),
                "href": link_elem.get("href", ""),
                "design_file": self._extract_design_file(link_elem),
            }
            links.append(link_data)
        return links

    def _extract_design_file(self, link_elem: ET.Element) -> dict[str, Any] | None:
        """Extrahiert Design File Informationen."""
        design_file_elem = link_elem.find("A:design-file", self.NAMESPACES)
        if design_file_elem is None:
            return None

        title_elem = design_file_elem.find("A:title", self.NAMESPACES)
        product_elem = design_file_elem.find("A:product", self.NAMESPACES)
        version_elem = design_file_elem.find("A:product-version", self.NAMESPACES)
        updated_elem = design_file_elem.find("A:updated", self.NAMESPACES)

        updated = datetime.now().isoformat()
        if updated_elem is not None and updated_elem.text:
            try:
                dt = datetime.fromisoformat(updated_elem.text.replace("Z", "+00:00"))
                updated = dt.isoformat()
            except ValueError:
                pass

        return {
            "name": title_elem.text if title_elem is not None and title_elem.text else "",
            "product": product_elem.text if product_elem is not None and product_elem.text else "",
            "product_version": version_elem.text if version_elem is not None and version_elem.text else "",
            "updated": updated,
        }

    def _extract_features(self, root: ET.Element) -> list[dict[str, Any]]:
        """Extrahiert Features."""
        features = []
        features_elem = root.find("A:features", self.NAMESPACES)
        if features_elem is None:
            return features

        for feature_elem in features_elem.findall("A:feature", self.NAMESPACES):
            title_elem = feature_elem.find("A:title", self.NAMESPACES)
            title = title_elem.text if title_elem is not None and title_elem.text else ""

            groups = self._extract_parameter_groups(feature_elem)
            features.append({"name": title, "groups": groups})

        return features

    def _extract_parameter_groups(self, feature_elem: ET.Element) -> list[dict[str, Any]]:
        """Extrahiert Parametergruppen."""
        groups = []
        for group_elem in feature_elem.findall("A:group", self.NAMESPACES):
            title_elem = group_elem.find("A:title", self.NAMESPACES)
            title = title_elem.text if title_elem is not None and title_elem.text else ""

            parameters = self._extract_parameters_from_group(group_elem)
            groups.append({"name": title, "parameters": parameters})

        return groups

    def _extract_parameters_from_group(self, group_elem: ET.Element) -> list[dict[str, Any]]:
        """Extrahiert Parameter aus einer Gruppe."""
        parameters = []
        for child in group_elem:
            cleaned_tag = self._clean_tag_name(child.tag)

            if child.tag.startswith("{" + self.NAMESPACES["A"] + "}") or cleaned_tag.lower() == "title":
                continue

            param_data = self._extract_parameter_from_element(child)
            if param_data:
                parameters.append(param_data)

        return parameters

    def _extract_parameter_from_element(self, elem: ET.Element) -> dict[str, Any] | None:
        """Extrahiert Parameter-Daten aus einem XML Element."""
        name = self._clean_tag_name(elem.tag)

        return {
            "name": name,
            "display_name": elem.get("displayName"),
            "type": elem.get("type", "custom"),
            "type_of_parameter": elem.get("typeOfParameter"),
            "units": elem.get("units"),
            "value": elem.text,
        }

    def _extract_family(self, root: ET.Element) -> dict[str, Any] | None:
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

        parts = self._extract_family_parts(family_elem)

        return {
            "type": family_type,
            "variation_count": variation_count,
            "parts": parts,
        }

    def _extract_family_parts(self, family_elem: ET.Element) -> list[dict[str, Any]]:
        """Extrahiert Family Parts."""
        parts = []
        for part_elem in family_elem.findall("A:part", self.NAMESPACES):
            title_elem = part_elem.find("atom:title", self.NAMESPACES)
            title = title_elem.text if title_elem is not None and title_elem.text else ""

            part_type = part_elem.get("type", "user")
            parameters = self._extract_parameters_from_part(part_elem)

            parts.append(
                {
                    "name": title,
                    "type": part_type,
                    "parameters": parameters,
                }
            )

        return parts

    def _extract_parameters_from_part(self, part_elem: ET.Element) -> list[dict[str, Any]]:
        """Extrahiert Parameter aus einem Family Part."""
        parameters = []
        for child in part_elem:
            cleaned_tag = self._clean_tag_name(child.tag)

            if child.tag in ["{" + self.NAMESPACES["atom"] + "}title"] or cleaned_tag.lower() == "title":
                continue

            param_data = self._extract_parameter_from_element(child)
            if param_data:
                parameters.append(param_data)

        return parameters

    def _clean_tag_name(self, tag_name: str) -> str:
        """Entfernt Namespace-Prefixes aus Tag-Namen."""
        if tag_name.startswith("{"):
            namespace_end = tag_name.find("}")
            if namespace_end != -1:
                return tag_name[namespace_end + 1 :]
        return tag_name

    def _repair_xml(self, xml_content: str) -> str:
        """Repariert häufige XML-Probleme."""
        import re

        # Entferne Null-Bytes und andere Kontrollzeichen
        xml_content = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", xml_content)

        # Repariere Encoding-Deklaration falls nötig
        if "<?xml" in xml_content and "encoding=" not in xml_content:
            xml_content = xml_content.replace(
                '<?xml version="1.0"?>',
                '<?xml version="1.0" encoding="UTF-8"?>',
            )

        # Escape ungültige XML-Zeichen in Text-Inhalten
        xml_content = xml_content.replace("&", "&amp;")
        xml_content = xml_content.replace("<", "&lt;").replace(">", "&gt;")

        # Repariere die Tags wieder
        return re.sub(r"&lt;(\/?[\w:]+[^&]*?)&gt;", r"<\1>", xml_content)
