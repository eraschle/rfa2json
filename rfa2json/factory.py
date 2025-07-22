from datetime import datetime
from typing import Any

from pydantic import BaseModel, field_validator

from .models import (
    Category,
    DesignFile,
    Family,
    FamilyPart,
    Feature,
    Link,
    Parameter,
    ParameterGroup,
    RevitFamilyEntry,
    Taxonomy,
)


class RevitFamilyFactory:
    """
    Factory-Klasse für die Erstellung von Revit Family-Instanzen aus JSON-Daten.

    Diese Klasse ist die zentrale Instanz für die Erstellung von Elementen aus JSON-Daten,
    die durch den XMLToJSONExtractor bereitgestellt werden.
    """

    @staticmethod
    def create_revit_family_entry(data: dict[str, Any]) -> RevitFamilyEntry:
        """
        Erstellt eine RevitFamilyEntry-Instanz aus JSON-Daten.

        Args:
            data: Strukturierte JSON-Daten aus dem XMLToJSONExtractor

        Returns:
            RevitFamilyEntry-Instanz
        """
        return RevitFamilyEntry(
            name=data.get("name", ""),
            id=data.get("id", ""),
            updated=RevitFamilyFactory._parse_datetime(data.get("updated")),
            taxonomies=RevitFamilyFactory._create_taxonomies(data.get("taxonomies", [])),
            categories=RevitFamilyFactory._create_categories(data.get("categories", [])),
            links=RevitFamilyFactory._create_links(data.get("links", [])),
            features=RevitFamilyFactory._create_features(data.get("features", [])),
            family=RevitFamilyFactory._create_family(data.get("family")),
        )

    @staticmethod
    def _parse_datetime(date_str: str | None) -> datetime:
        """Parst einen Datetime-String oder gibt aktuelle Zeit zurück."""
        if not date_str:
            return datetime.now()

        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return datetime.now()

    @staticmethod
    def _create_taxonomies(taxonomies_data: list[dict[str, str]]) -> list[Taxonomy]:
        """Erstellt Taxonomy-Instanzen aus JSON-Daten."""
        return [
            Taxonomy(
                term=tax_data.get("term", ""),
                label=tax_data.get("label", ""),
            )
            for tax_data in taxonomies_data
        ]

    @staticmethod
    def _create_categories(categories_data: list[dict[str, str]]) -> list[Category]:
        """Erstellt Category-Instanzen aus JSON-Daten."""
        return [Category(name=cat_data.get("name", "")) for cat_data in categories_data]

    @staticmethod
    def _create_links(links_data: list[dict[str, Any]]) -> list[Link]:
        """Erstellt Link-Instanzen aus JSON-Daten."""
        links = []
        for link_data in links_data:
            design_file = None
            if link_data.get("design_file"):
                design_file = RevitFamilyFactory._create_design_file(link_data["design_file"])

            links.append(
                Link(
                    rel=link_data.get("rel", ""),
                    type=link_data.get("type", ""),
                    href=link_data.get("href", ""),
                    design_file=design_file,
                )
            )
        return links

    @staticmethod
    def _create_design_file(design_file_data: dict[str, Any]) -> DesignFile:
        """Erstellt eine DesignFile-Instanz aus JSON-Daten."""
        return DesignFile(
            name=design_file_data.get("name", ""),
            product=design_file_data.get("product", ""),
            product_version=design_file_data.get("product_version", ""),
            updated=RevitFamilyFactory._parse_datetime(design_file_data.get("updated")),
        )

    @staticmethod
    def _create_features(features_data: list[dict[str, Any]]) -> list[Feature]:
        """Erstellt Feature-Instanzen aus JSON-Daten."""
        features = []
        for feature_data in features_data:
            groups = RevitFamilyFactory._create_parameter_groups(feature_data.get("groups", []))
            features.append(
                Feature(
                    name=feature_data.get("name", ""),
                    groups=groups,
                )
            )
        return features

    @staticmethod
    def _create_parameter_groups(groups_data: list[dict[str, Any]]) -> list[ParameterGroup]:
        """Erstellt ParameterGroup-Instanzen aus JSON-Daten."""
        groups = []
        for group_data in groups_data:
            parameters = RevitFamilyFactory._create_parameters(group_data.get("parameters", []))
            groups.append(
                ParameterGroup(
                    name=group_data.get("name", ""),
                    parameters=parameters,
                )
            )
        return groups

    @staticmethod
    def _create_parameters(parameters_data: list[dict[str, Any]]) -> list[Parameter]:
        """Erstellt Parameter-Instanzen aus JSON-Daten."""
        parameters = []
        for param_data in parameters_data:
            # Filtere None-Werte für optionale Felder
            filtered_data = {k: v for k, v in param_data.items() if v is not None}

            parameters.append(
                Parameter(
                    name=filtered_data.get("name", ""),
                    display_name=filtered_data.get("display_name"),
                    type=filtered_data.get("type", "custom"),
                    type_of_parameter=filtered_data.get("type_of_parameter"),
                    units=filtered_data.get("units"),
                    value=filtered_data.get("value"),
                )
            )
        return parameters

    @staticmethod
    def _create_family(family_data: dict[str, Any] | None) -> Family | None:
        """Erstellt eine Family-Instanz aus JSON-Daten."""
        if not family_data:
            return None

        parts = RevitFamilyFactory._create_family_parts(family_data.get("parts", []))

        return Family(
            type=family_data.get("type", "user"),
            variation_count=family_data.get("variation_count", 0),
            parts=parts,
        )

    @staticmethod
    def _create_family_parts(parts_data: list[dict[str, Any]]) -> list[FamilyPart]:
        """Erstellt FamilyPart-Instanzen aus JSON-Daten."""
        parts = []
        for part_data in parts_data:
            parameters = RevitFamilyFactory._create_parameters(part_data.get("parameters", []))
            parts.append(
                FamilyPart(
                    name=part_data.get("name", ""),
                    type=part_data.get("type", "user"),
                    parameters=parameters,
                )
            )
        return parts


class ValidationError(Exception):
    """Exception für Validierungsfehler in der Factory."""

    pass


class ValidatedRevitFamilyFactory(RevitFamilyFactory):
    """
    Erweiterte Factory mit Pydantic-Validierung.

    Diese Klasse bietet zusätzliche Validierung der JSON-Daten
    bevor die Instanzen erstellt werden.
    """

    class RevitFamilyEntrySchema(BaseModel):
        """Pydantic-Schema für RevitFamilyEntry Validierung."""

        name: str
        id: str
        updated: str
        taxonomies: list[dict[str, str]] = []
        categories: list[dict[str, str]] = []
        links: list[dict[str, Any]] = []
        features: list[dict[str, Any]] = []
        family: dict[str, Any] | None = None

        @field_validator("name")
        @classmethod
        def name_must_not_be_empty(cls, v):
            if not v.strip():
                raise ValueError("Name darf nicht leer sein")
            return v

        @field_validator("updated")
        @classmethod
        def validate_updated_format(cls, v):
            try:
                datetime.fromisoformat(v.replace("Z", "+00:00"))
            except ValueError:
                raise ValueError("Invalid datetime format")
            return v

    @staticmethod
    def create_revit_family_entry_validated(data: dict[str, Any]) -> RevitFamilyEntry:
        """
        Erstellt eine validierte RevitFamilyEntry-Instanz aus JSON-Daten.

        Args:
            data: Strukturierte JSON-Daten aus dem XMLToJSONExtractor

        Returns:
            RevitFamilyEntry-Instanz

        Raises:
            ValidationError: Wenn die Validierung fehlschlägt
        """
        try:
            # Validiere die Daten mit Pydantic
            schema = ValidatedRevitFamilyFactory.RevitFamilyEntrySchema(**data)
            # Erstelle die Instanz mit der Basis-Factory
            return RevitFamilyFactory.create_revit_family_entry(schema.model_dump())
        except Exception as e:
            raise ValidationError(f"Validierung fehlgeschlagen: {e}") from e
