"""
Revit Family XML Parser Package

Dieses Package bietet eine saubere, professionelle Implementation
für das Verwalten von Revit Family XML-Daten.
"""

from .analyzer import FamilyDataAnalyzer
from .config import (
    KNOWN_NAMESPACES,
    KNOWN_PARAMETER_TYPES,
    KNOWN_REVIT_CATEGORIES,
    KNOWN_TAXONOMY_TERMS,
    KNOWN_TYPE_OF_PARAMETERS,
)
from .repo.json_repo import RevitFamilyJSONRepository
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
from .extract import RevitFamilyReader
from .repo import RevitFamilyRepository
from .service import RevitFamilyService
from .extract.xml_reader import RevitFamilyXMLReader

__all__ = [
    "KNOWN_NAMESPACES",
    "KNOWN_PARAMETER_TYPES",
    "KNOWN_REVIT_CATEGORIES",
    "KNOWN_TAXONOMY_TERMS",
    "KNOWN_TYPE_OF_PARAMETERS",
    "Category",
    "DesignFile",
    "Family",
    "FamilyDataAnalyzer",
    "FamilyPart",
    "Feature",
    "Link",
    "Parameter",
    "ParameterGroup",
    "RevitFamilyEntry",
    "RevitFamilyJSONRepository",
    "RevitFamilyReader",
    "RevitFamilyRepository",
    "RevitFamilyService",
    "RevitFamilyXMLReader",
]

__version__ = "1.0.0"
