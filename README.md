# RVT2JSON - Revit Familie XML Extractor

🏗️ Ein moderner, professioneller Extractor für Revit Familie XML-Daten mit schöner Konsolen-Ausgabe.

## 📋 Übersicht

RVT2JSON konvertiert Revit Familie (.rfa) Dateien zu strukturierten JSON-Dateien. Das Tool extrahiert XML-Metadaten aus .rfa Dateien und speichert sie in einem sauberen, lesbaren JSON-Format.

### ✨ Features

- 🚀 **Moderne CLI** mit Rich-basierter Ausgabe
- 📊 **Progress Bars** und schöne Tabellen
- 🔄 **Batch-Verarbeitung** mit rekursiver Ordnersuche
- 📝 **Umfassendes Logging** in Datei und Konsole
- ✅ **JSON-Validierung** für verarbeitete Dateien
- 🎯 **Intelligente Pfad-Verwaltung** mit Ordnerstruktur-Erhaltung
- ⚠️ **Neue Element-Erkennung** für Code-Updates
- 🧪 **Dry-Run Modus** für sicheres Testen

## 🛠️ Installation

### Voraussetzungen

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) für Package-Management

### Setup mit uv

```bash
# Repository klonen
git clone <repository-url>
cd rvt2json

# Virtuelle Umgebung erstellen und Dependencies installieren
uv sync

# Development Dependencies installieren
uv sync --group dev

# CLI installieren
uv pip install -e .
```

## 🚀 Verwendung

### Grundlegende Kommandos

```bash
# Einzelne .rfa Datei verarbeiten
rvt2json extract /pfad/zur/familie.rfa

# Ordner rekursiv verarbeiten
rvt2json extract /pfad/zum/ordner --recursive

# Mit spezifischem Ausgabepfad
rvt2json extract /pfad/zum/ordner --output /ausgabe/pfad --recursive

# Dry-Run (nur anzeigen, was gemacht würde)
rvt2json extract /pfad/zum/ordner --dry-run --recursive

# Mit ausführlicher Ausgabe und Logging
rvt2json extract /pfad/zum/ordner --verbose --log-file verarbeitung.log --recursive

# Existierende Dateien überschreiben
rvt2json extract /pfad/zum/ordner --force --recursive

# Backup-Dateien mit verarbeiten
rvt2json extract /pfad/zum/ordner --include-backups --recursive
```

### Backup-Dateien Filter

Das Tool filtert standardmäßig Revit Backup-Dateien aus, die das Format `.NNNN.rfa` haben (z.B. `Familie.0001.rfa`, `Familie.0002.rfa`).

```bash
# Standardverhalten: Backup-Dateien werden übersprungen
rvt2json extract /pfad/zum/ordner --recursive

# Backup-Dateien mit verarbeiten
rvt2json extract /pfad/zum/ordner --recursive --include-backups
```

**Warum werden Backup-Dateien gefiltert?**
- Backup-Dateien enthalten meist identische Daten wie die Hauptdatei
- Sie würden zu doppelten JSON-Ausgaben führen
- Die Verarbeitung wird schneller und effizienter

### Informationen und Validierung

```bash
# Information über verarbeitete Familie anzeigen
rvt2json info /pfad/zur/familie.json

# JSON-Dateien validieren
rvt2json validate /pfad/zum/json/ordner

# Hilfe anzeigen
rvt2json --help
rvt2json extract --help
```

### Ausgabepfad-Logik

- **Kein `--output` angegeben**: JSON-Dateien werden neben den .rfa Dateien gespeichert
- **Mit `--output`**: JSON-Dateien werden im angegebenen Pfad gespeichert, wobei die Ordnerstruktur beibehalten wird

## 📁 Projektstruktur

```
rvt2json/
├── __init__.py          # Package Initialisierung
├── models.py            # Datenmodelle (dataclasses)
├── protocols.py         # Abstrakte Interfaces
├── xml_reader.py        # XML Parser Implementation
├── json_repository.py   # JSON Persistierung
├── service.py           # Business Logic Service
├── cli.py              # Moderne CLI mit Rich
├── pyproject.toml      # Projekt-Konfiguration
└── README.md           # Diese Dokumentation
```

## 🧪 Development

### Code-Qualität Tools

```bash
# Type Checking mit Pyright
uv run pyright

# Linting und Formatting mit Ruff
uv run ruff check
uv run ruff format

# Tests ausführen
uv run pytest
uv run pytest --cov=. --cov-report=html
```

### Neue Dependencies hinzufügen

```bash
# Runtime Dependency
uv add package-name

# Development Dependency
uv add --group dev package-name
```

## 📊 Datenmodell

Das Tool extrahiert folgende Informationen aus .rfa Dateien:

### RevitFamilyEntry
- **Basis-Informationen**: Titel, ID, Update-Datum
- **Taxonomien**: Autodesk-spezifische Klassifizierungen
- **Kategorien**: Revit-Kategorien
- **Links**: Verweise auf Design-Dateien
- **Features**: Parametergruppen mit Eigenschaften
- **Familie**: Varianten und Teile mit Parametern

### Parameter
- **Name**: Parameter-Bezeichnung
- **Typ**: system, custom, instance, type
- **Wert**: Aktueller Parameterwert
- **Einheiten**: Maßeinheiten (m, mm, etc.)
- **Typ-Parameter**: Länge, Material, Ja/Nein, etc.

## ⚠️ Neue Element-Erkennung

Das Tool überwacht automatisch neue XML-Strukturen und warnt, wenn:
- Neue Parameter-Typen entdeckt werden
- Unbekannte `typeOfParameter` Werte gefunden werden
- Neue XML-Elemente in der Struktur auftauchen

Diese Warnungen helfen dabei, den Code aktuell zu halten, wenn Autodesk neue Revit-Versionen mit erweiterten XML-Strukturen veröffentlicht.

## 📝 Logging

Das Tool bietet umfassendes Logging:

- **Konsole**: Rich-formatierte Ausgabe mit Farben und Symbolen
- **Datei**: Strukturierte Logs für Debugging und Archivierung
- **Level**: INFO (Standard) oder DEBUG (mit `--verbose`)

Beispiel Log-Ausgabe:
```
2024-12-18 15:30:15 - INFO - Gefunden: 25 .rfa Datei(en)
2024-12-18 15:30:16 - INFO - Verarbeitet: Kabelverteiler.rfa
2024-12-18 15:30:17 - WARNING - Neue XML-Elemente gefunden: ['Neuer Parameter-Typ: advanced']
2024-12-18 15:30:20 - INFO - Verarbeitung abgeschlossen: 24 erfolgreich, 1 fehlgeschlagen, 0 übersprungen
```

## 🤝 Contributing

1. Fork das Repository
2. Erstelle einen Feature Branch (`git checkout -b feature/amazing-feature`)
3. Committe deine Änderungen (`git commit -m 'Add amazing feature'`)
4. Push zum Branch (`git push origin feature/amazing-feature`)
5. Öffne einen Pull Request

### Code-Standards

- **Type Hints**: Alle Funktionen müssen Type Hints haben
- **Docstrings**: Alle öffentlichen Funktionen brauchen Dokumentation
- **Tests**: Neue Features müssen getestet werden
- **Ruff**: Code muss Ruff-konform sein
- **Pyright**: Keine Type-Errors erlaubt

## 📄 Lizenz

[Lizenz hier einfügen]

## 🆘 Support

Bei Problemen oder Fragen:
1. Prüfe die [Issues](link-to-issues)
2. Erstelle ein neues Issue mit detaillierter Beschreibung
3. Füge Log-Dateien und Beispiel-Dateien hinzu

### Datenanalyse und Visualisierung

Das Tool bietet umfassende Analyse- und Visualisierungsfunktionen:

```bash
# Basis-Analyse mit Statistiken
rvt2json analyze /pfad/zu/json/dateien

# Vollständiges Dashboard erstellen
rvt2json analyze /pfad/zu/json/dateien --output /pfad/zu/diagrammen

# Spezifische Diagramme erstellen
rvt2json analyze /pfad/zu/json/dateien --output /pfad/zu/diagrammen --chart param-types
rvt2json analyze /pfad/zu/json/dateien --output /pfad/zu/diagrammen --chart family-parts
rvt2json analyze /pfad/zu/json/dateien --output /pfad/zu/diagrammen --chart units
rvt2json analyze /pfad/zu/json/dateien --output /pfad/zu/diagrammen --chart categories

# Query-basierte Analyse
rvt2json analyze /pfad/zu/json/dateien --query "Param:type=custom"
rvt2json analyze /pfad/zu/json/dateien --query "Param:name=Width"
rvt2json analyze /pfad/zu/json/dateien --query "Cat:name=Möbel"
rvt2json analyze /pfad/zu/json/dateien --query "Group:name=Bemaßungen"
```

#### Unterstützte Query-Formate:

- **Parameter-Queries:**
  - `Param:name=Width` - Parameter nach Name
  - `Param:type=custom` - Parameter nach Typ
  - `Param:type_of_parameter=Länge` - Parameter nach typeOfParameter
  - `Param:units=m` - Parameter nach Einheiten

- **Kategorie-Queries:**
  - `Cat:name=Möbel` - Familien nach Kategorie

- **Familie-Queries:**
  - `Family:type=user` - Familien nach Typ
  - `Family:name=Kabel` - Familien nach Name

- **Gruppen-Queries:**
  - `Group:name=Bemaßungen` - Parameter nach Gruppe

#### Verfügbare Diagramme:

- **dashboard** - Umfassendes Dashboard mit allen Diagrammen
- **param-types** - Verteilung der Parameter-Typen
- **family-parts** - Verteilung der Familie-Teile
- **units** - Top Parameter-Einheiten
- **categories** - Kategorie-Verteilung

## 🔄 Changelog

### v0.1.0
- ✨ Initiale Version
- 🏗️ Moderne CLI mit Rich
- 📊 XML zu JSON Konvertierung
- ✅ Validierung und Logging
- 🔍 Neue Element-Erkennung
- 📈 Datenanalyse und Visualisierung
- 🔍 Query-System für gezielte Datenabfragen
