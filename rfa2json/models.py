from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Parameter:
    """Repräsentiert einen einzelnen Parameter mit seinen Eigenschaften."""

    name: str
    display_name: str | None = None
    type: str = "custom"
    type_of_parameter: str | None = None
    units: str | None = None
    value: Any = None


@dataclass
class ParameterGroup:
    """Gruppiert verwandte Parameter zusammen."""

    name: str
    parameters: list[Parameter] = field(default_factory=list)


@dataclass
class Feature:
    """Repräsentiert ein Feature mit seinen Parametergruppen."""

    name: str
    groups: list[ParameterGroup] = field(default_factory=list)


@dataclass
class FamilyPart:
    """Repräsentiert eine Variante/Teil einer Familie."""

    name: str
    type: str = "user"
    parameters: list[Parameter] = field(default_factory=list)


@dataclass
class DesignFile:
    """Informationen über die Design-Datei."""

    name: str
    product: str
    product_version: str
    updated: datetime


@dataclass
class Link:
    """Link zu einer Design-Datei."""

    rel: str
    type: str
    href: str
    design_file: DesignFile | None = None


@dataclass
class Taxonomy:
    """Taxonomie-Information."""

    term: str
    label: str


@dataclass
class Category:
    """Kategorie-Information."""

    name: str


@dataclass
class Family:
    """Repräsentiert eine komplette Revit Familie."""

    type: str = "user"
    variation_count: int = 0
    parts: list[FamilyPart] = field(default_factory=list)


@dataclass
class RevitFamilyEntry:
    """Hauptklasse für einen kompletten Revit Family Entry."""

    name: str
    id: str
    updated: datetime
    taxonomies: list[Taxonomy] = field(default_factory=list)
    categories: list[Category] = field(default_factory=list)
    links: list[Link] = field(default_factory=list)
    features: list[Feature] = field(default_factory=list)
    family: Family | None = None
