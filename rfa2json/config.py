"""
Konfigurationsdatei für bekannte Parameter-Typen und XML-Strukturen.

Diese Datei enthält alle bekannten Parameter-Typen und typeOfParameter-Werte,
die in Revit Familie XML-Dateien vorkommen können. Sie wird verwendet, um
neue/unbekannte Elemente zu erkennen, die Code-Updates erfordern könnten.
"""

# Bekannte Parameter-Typen
KNOWN_PARAMETER_TYPES = {"system", "custom", "instance", "type", "shared"}

# Bekannte typeOfParameter Werte
KNOWN_TYPE_OF_PARAMETERS = {
    "Ja/Nein",
    "Yes/No",  # Englische Variante
    "Länge",
    "Material",
    "Text",
    "Zahl",
    "Winkel",
    "Volumen",
    "Fläche",
    "Kraft",
    "Moment",
    "Währung",
    "Masse",
    "Massendichte",
    "URL",
    "Bild",
    "Multiline Text",
    "Familie-Typ",
    "Laden-Familie",
    "Ja/Nein-Parameter",
    "Integer",
    "Nummer",
    "Slope",
    "Speed",
    "Acceleration",
}

# Bekannte XML-Namespaces
KNOWN_NAMESPACES = {
    "atom": "http://www.w3.org/2005/Atom",
    "A": "urn:schemas-autodesk-com:partatom",
}

# Bekannte Revit-Kategorien
KNOWN_REVIT_CATEGORIES = {
    "Allgemeines Modell",
    "Möbel",
    "Beleuchtungskörper",
    "Elektrogeräte",
    "Mechanische Ausrüstung",
    "Rohrleitungsarmaturen",
    "Rohrleitungszubehör",
    "Luftkanäle",
    "Luftkanalzubehör",
    "Luftkanalanschlüsse",
    "Strukturelle Verbindungen",
    "Strukturelle Bewehrung",
    "Strukturelle Fundamente",
    "Strukturelle Rahmen",
    "Strukturelle Säulen",
    "Wände",
    "Türen",
    "Fenster",
    "Dächer",
    "Decken",
    "Böden",
    "Treppen",
    "Geländer",
}

# Bekannte Autodesk Taxonomie-Begriffe
KNOWN_TAXONOMY_TERMS = {
    "adsk:revit",
    "adsk:revit:grouping",
    "adsk:revit:family",
    "adsk:revit:type",
    "adsk:revit:instance",
}
