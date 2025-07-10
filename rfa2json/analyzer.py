"""
Analyse-Modul für Revit Familie Daten.
Bietet Funktionen für Datenanalyse, Visualisierung und Queries.
"""

import logging
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from models import RevitFamilyEntry
from rich import box
from rich.console import Console
from rich.table import Table
from service import RevitFamilyService

logger = logging.getLogger(__name__)
console = Console()

# Matplotlib für bessere Darstellung konfigurieren
plt.style.use("seaborn-v0_8")
sns.set_palette("husl")


class FamilyDataAnalyzer:
    """Analysiert und visualisiert Revit Familie Daten."""

    def __init__(self):
        self.service = RevitFamilyService()
        self.families: list[RevitFamilyEntry] = []
        self.df_parameters: pd.DataFrame | None = None
        self.df_families: pd.DataFrame | None = None

    def load_families_from_directory(
        self,
        directory: Path,
        recursive: bool = True,
    ) -> None:
        """Lädt alle JSON-Dateien aus einem Verzeichnis."""
        pattern = "**/*.json" if recursive else "*.json"
        json_files = list(directory.glob(pattern))

        console.print(f"🔍 Lade {len(json_files)} JSON-Dateien...")

        self.families = []
        for json_file in json_files:
            try:
                family = self.service.load_from_json(json_file)
                self.families.append(family)
            except Exception as e:
                logger.warning(f"Fehler beim Laden von {json_file}: {e}")

        console.print(f"✅ {len(self.families)} Familien erfolgreich geladen")
        self._create_dataframes()

    def _create_dataframes(self) -> None:
        """Erstellt Pandas DataFrames für die Analyse."""
        # DataFrame für Parameter
        param_data = []
        family_data = []

        for family in self.families:
            # Familie-Daten
            family_data.append(
                {
                    "family_name": family.name,
                    "family_id": family.id,
                    "family_type": family.family.type if family.family else "unknown",
                    "variation_count": family.family.variation_count if family.family else 0,
                    "parts_count": len(family.family.parts) if family.family else 0,
                    "features_count": len(family.features),
                    "categories": ", ".join([cat.name for cat in family.categories]),
                    "updated": family.updated,
                },
            )

            # Parameter aus Features
            for feature in family.features:
                for group in feature.groups:
                    for param in group.parameters:
                        param_data.append(
                            {
                                "family_name": family.name,
                                "family_id": family.id,
                                "source": "feature",
                                "feature_name": feature.name,
                                "group_name": group.name,
                                "param_name": param.name,
                                "param_display_name": param.display_name,
                                "param_type": param.type,
                                "param_type_of_parameter": param.type_of_parameter,
                                "param_units": param.units,
                                "param_value": param.value,
                            },
                        )

            # Parameter aus Family Parts
            if family.family:
                for part in family.family.parts:
                    for param in part.parameters:
                        param_data.append(
                            {
                                "family_name": family.name,
                                "family_id": family.id,
                                "source": "part",
                                "feature_name": None,
                                "group_name": part.name,
                                "param_name": param.name,
                                "param_display_name": param.display_name,
                                "param_type": param.type,
                                "param_type_of_parameter": param.type_of_parameter,
                                "param_units": param.units,
                                "param_value": param.value,
                            },
                        )

        self.df_parameters = pd.DataFrame(param_data)
        self.df_families = pd.DataFrame(family_data)

        console.print(
            f"📊 DataFrames erstellt: {len(self.df_families)} Familien, {len(self.df_parameters)} Parameter",
        )

    def query_data(self, query_string: str) -> pd.DataFrame:
        """
        Führt eine Query auf den Daten aus.

        Unterstützte Query-Formate:
        - Param:name=Width
        - Param:type=custom
        - Param:type_of_parameter=Länge
        - Cat:name=Allgemeines Modell
        - Family:type=user
        - Group:name=Bemaßungen
        """
        if self.df_parameters is None:
            raise ValueError(
                "Keine Daten geladen. Verwende load_families_from_directory() zuerst.",
            )

        parts = query_string.split(":")
        if len(parts) != 2:
            raise ValueError("Query-Format: 'Typ:Feld=Wert' (z.B. 'Param:name=Width')")

        query_type, condition = parts

        if "=" not in condition:
            raise ValueError("Query-Format: 'Typ:Feld=Wert' (z.B. 'Param:name=Width')")

        field, value = condition.split("=", 1)

        if query_type.lower() == "param":
            return self._query_parameters(field, value)
        if query_type.lower() == "cat":
            return self._query_categories(field, value)
        if query_type.lower() == "family":
            return self._query_families(field, value)
        if query_type.lower() == "group":
            return self._query_groups(field, value)
        raise ValueError(
            f"Unbekannter Query-Typ: {query_type}. Unterstützt: Param, Cat, Family, Group",
        )

    def _query_parameters(self, field: str, value: str) -> pd.DataFrame:
        """Query für Parameter."""
        field_mapping = {
            "name": "param_name",
            "type": "param_type",
            "type_of_parameter": "param_type_of_parameter",
            "units": "param_units",
            "value": "param_value",
            "display_name": "param_display_name",
        }

        if field not in field_mapping:
            raise ValueError(
                f"Unbekanntes Parameter-Feld: {field}. Unterstützt: {list(field_mapping.keys())}",
            )

        df_field = field_mapping[field]
        return self.df_parameters[
            self.df_parameters[df_field].astype(str).str.contains(value, case=False, na=False)
        ]

    def _query_categories(self, field: str, value: str) -> pd.DataFrame:
        """Query für Kategorien."""
        if field != "name":
            raise ValueError("Für Kategorien ist nur 'name' unterstützt")

        # Filtere Familien nach Kategorie
        matching_families = self.df_families[
            self.df_families["categories"].str.contains(value, case=False, na=False)
        ]["family_name"].tolist()

        return self.df_parameters[self.df_parameters["family_name"].isin(matching_families)]

    def _query_families(self, field: str, value: str) -> pd.DataFrame:
        """Query für Familien."""
        field_mapping = {
            "name": "family_name",
            "type": "family_type",
            "id": "family_id",
        }

        if field not in field_mapping:
            raise ValueError(
                f"Unbekanntes Familie-Feld: {field}. Unterstützt: {list(field_mapping.keys())}",
            )

        df_field = field_mapping[field]
        matching_families = self.df_families[
            self.df_families[df_field].astype(str).str.contains(value, case=False, na=False)
        ]["family_name"].tolist()

        return self.df_parameters[self.df_parameters["family_name"].isin(matching_families)]

    def _query_groups(self, field: str, value: str) -> pd.DataFrame:
        """Query für Gruppen."""
        if field != "name":
            raise ValueError("Für Gruppen ist nur 'name' unterstützt")

        return self.df_parameters[
            self.df_parameters["group_name"].astype(str).str.contains(value, case=False, na=False)
        ]

    def create_parameter_type_chart(self, output_path: Path | None = None) -> None:
        """Erstellt ein Diagramm der Parameter-Typen."""
        if self.df_parameters is None:
            raise ValueError("Keine Daten geladen")

        # Zähle Parameter-Typen
        type_counts = self.df_parameters["param_type"].value_counts()

        plt.figure(figsize=(10, 6))
        ax = type_counts.plot(
            kind="bar",
            color=sns.color_palette("husl", len(type_counts)),
        )
        plt.title("Verteilung der Parameter-Typen", fontsize=16, fontweight="bold")
        plt.xlabel("Parameter-Typ", fontsize=12)
        plt.ylabel("Anzahl", fontsize=12)
        plt.xticks(rotation=45)
        plt.grid(axis="y", alpha=0.3)

        # Werte auf Balken anzeigen
        for i, v in enumerate(type_counts.values):
            ax.text(i, v + 0.1, str(v), ha="center", va="bottom", fontweight="bold")

        plt.tight_layout()

        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches="tight")
            console.print(f"📊 Diagramm gespeichert: {output_path}")
        else:
            plt.show()

    def create_family_parts_distribution(
        self,
        output_path: Path | None = None,
    ) -> None:
        """Erstellt ein Diagramm der Familie-Teile-Verteilung."""
        if self.df_families is None:
            raise ValueError("Keine Daten geladen")

        plt.figure(figsize=(12, 6))

        # Subplot 1: Parts Count Distribution
        plt.subplot(1, 2, 1)
        parts_counts = self.df_families["parts_count"].value_counts().sort_index()
        plt.bar(
            parts_counts.index,
            parts_counts.values,
            color=sns.color_palette("viridis", len(parts_counts)),
        )
        plt.title("Verteilung der Anzahl Familie-Teile", fontweight="bold")
        plt.xlabel("Anzahl Teile")
        plt.ylabel("Anzahl Familien")
        plt.grid(axis="y", alpha=0.3)

        # Subplot 2: Variation Count Distribution
        plt.subplot(1, 2, 2)
        var_counts = self.df_families["variation_count"].value_counts().sort_index()
        plt.bar(
            var_counts.index,
            var_counts.values,
            color=sns.color_palette("plasma", len(var_counts)),
        )
        plt.title("Verteilung der Varianten-Anzahl", fontweight="bold")
        plt.xlabel("Anzahl Varianten")
        plt.ylabel("Anzahl Familien")
        plt.grid(axis="y", alpha=0.3)

        plt.tight_layout()

        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches="tight")
            console.print(f"📊 Diagramm gespeichert: {output_path}")
        else:
            plt.show()

    def create_parameter_units_chart(self, output_path: Path | None = None) -> None:
        """Erstellt ein Diagramm der Parameter-Einheiten."""
        if self.df_parameters is None:
            raise ValueError("Keine Daten geladen")

        # Filtere nur Parameter mit Einheiten
        units_data = self.df_parameters[self.df_parameters["param_units"].notna()]
        units_counts = units_data["param_units"].value_counts().head(15)  # Top 15

        plt.figure(figsize=(12, 8))
        ax = units_counts.plot(
            kind="barh",
            color=sns.color_palette("Set2", len(units_counts)),
        )
        plt.title("Top 15 Parameter-Einheiten", fontsize=16, fontweight="bold")
        plt.xlabel("Anzahl Parameter", fontsize=12)
        plt.ylabel("Einheit", fontsize=12)
        plt.grid(axis="x", alpha=0.3)

        # Werte auf Balken anzeigen
        for i, v in enumerate(units_counts.values):
            ax.text(v + 0.1, i, str(v), ha="left", va="center", fontweight="bold")

        plt.tight_layout()

        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches="tight")
            console.print(f"📊 Diagramm gespeichert: {output_path}")
        else:
            plt.show()

    def create_category_distribution(self, output_path: Path | None = None) -> None:
        """Erstellt ein Diagramm der Kategorie-Verteilung."""
        if self.df_families is None:
            raise ValueError("Keine Daten geladen")

        # Extrahiere alle Kategorien (können mehrere pro Familie sein)
        all_categories = []
        for categories_str in self.df_families["categories"]:
            if pd.notna(categories_str):
                cats = [cat.strip() for cat in categories_str.split(",")]
                all_categories.extend(cats)

        cat_counts = Counter(all_categories)

        plt.figure(figsize=(12, 8))
        categories, counts = zip(*cat_counts.most_common(10), strict=False)

        plt.pie(counts, labels=categories, autopct="%1.1f%%", startangle=90)
        plt.title("Top 10 Revit Kategorien", fontsize=16, fontweight="bold")
        plt.axis("equal")

        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches="tight")
            console.print(f"📊 Diagramm gespeichert: {output_path}")
        else:
            plt.show()

    def create_comprehensive_dashboard(self, output_dir: Path) -> None:
        """Erstellt ein umfassendes Dashboard mit allen Diagrammen."""
        output_dir.mkdir(parents=True, exist_ok=True)

        console.print("📊 Erstelle umfassendes Dashboard...")

        # Einzelne Diagramme erstellen
        self.create_parameter_type_chart(output_dir / "parameter_types.png")
        self.create_family_parts_distribution(output_dir / "family_parts.png")
        self.create_parameter_units_chart(output_dir / "parameter_units.png")
        self.create_category_distribution(output_dir / "categories.png")

        # Zusammenfassendes Dashboard
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))

        # Parameter Types
        type_counts = self.df_parameters["param_type"].value_counts()
        ax1.bar(
            type_counts.index,
            type_counts.values,
            color=sns.color_palette("husl", len(type_counts)),
        )
        ax1.set_title("Parameter-Typen", fontweight="bold")
        ax1.tick_params(axis="x", rotation=45)

        # Parts Distribution
        parts_counts = self.df_families["parts_count"].value_counts().sort_index()
        ax2.bar(
            parts_counts.index,
            parts_counts.values,
            color=sns.color_palette("viridis", len(parts_counts)),
        )
        ax2.set_title("Familie-Teile Verteilung", fontweight="bold")

        # Top Units
        units_data = self.df_parameters[self.df_parameters["param_units"].notna()]
        units_counts = units_data["param_units"].value_counts().head(8)
        ax3.barh(
            units_counts.index,
            units_counts.values,
            color=sns.color_palette("Set2", len(units_counts)),
        )
        ax3.set_title("Top Parameter-Einheiten", fontweight="bold")

        # Categories
        all_categories = []
        for categories_str in self.df_families["categories"]:
            if pd.notna(categories_str):
                cats = [cat.strip() for cat in categories_str.split(",")]
                all_categories.extend(cats)

        cat_counts = Counter(all_categories)
        categories, counts = zip(*cat_counts.most_common(6), strict=False)
        ax4.pie(counts, labels=categories, autopct="%1.1f%%", startangle=90)
        ax4.set_title("Top Kategorien", fontweight="bold")

        plt.suptitle("Revit Familie Daten - Dashboard", fontsize=20, fontweight="bold")
        plt.tight_layout()

        dashboard_path = output_dir / "dashboard.png"
        plt.savefig(dashboard_path, dpi=300, bbox_inches="tight")
        console.print(f"📊 Dashboard gespeichert: {dashboard_path}")

        plt.show()

    def print_summary_statistics(self) -> None:
        """Zeigt zusammenfassende Statistiken an."""
        if not self.families:
            console.print("❌ Keine Daten geladen")
            return

        # Basis-Statistiken
        stats_table = Table(title="📊 Zusammenfassende Statistiken", box=box.ROUNDED)
        stats_table.add_column("Metrik", style="cyan")
        stats_table.add_column("Wert", style="magenta", justify="right")

        total_families = len(self.families)
        total_parameters = len(self.df_parameters) if self.df_parameters is not None else 0
        avg_parts = self.df_families["parts_count"].mean() if self.df_families is not None else 0
        avg_features = self.df_families["features_count"].mean() if self.df_families is not None else 0

        stats_table.add_row("Gesamt Familien", str(total_families))
        stats_table.add_row("Gesamt Parameter", str(total_parameters))
        stats_table.add_row("Ø Teile pro Familie", f"{avg_parts:.1f}")
        stats_table.add_row("Ø Features pro Familie", f"{avg_features:.1f}")

        if self.df_parameters is not None:
            unique_param_types = self.df_parameters["param_type"].nunique()
            unique_units = self.df_parameters["param_units"].nunique()
            stats_table.add_row("Verschiedene Parameter-Typen", str(unique_param_types))
            stats_table.add_row("Verschiedene Einheiten", str(unique_units))

        console.print(stats_table)

        # Top Parameter-Namen
        if self.df_parameters is not None:
            top_params = self.df_parameters["param_name"].value_counts().head(10)

            params_table = Table(title="🔝 Top 10 Parameter-Namen", box=box.ROUNDED)
            params_table.add_column("Parameter", style="green")
            params_table.add_column("Anzahl", style="magenta", justify="right")

            for param, count in top_params.items():
                params_table.add_row(param, str(count))

            console.print(params_table)
