"""
Moderne CLI für Revit Familie XML Extractor.
Konvertiert .rfa Dateien zu JSON mit schöner Konsolen-Ausgabe.
"""

import logging
from datetime import datetime
from pathlib import Path

import typer
from json_repository import RevitFamilyJSONRepository
from rich import box
from rich.align import Align
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from rfa2json.service import RevitFamilyService

# Rich Console Setup
console = Console()
app = typer.Typer(
    name="rvt2json",
    help="🏗️  Moderner Revit Familie XML Extractor",
    rich_markup_mode="rich",
)


# Logging Setup
def setup_logging(verbose: bool = False, log_file: Path | None = None) -> None:
    """Konfiguriert Logging mit Rich Handler."""
    level = logging.DEBUG if verbose else logging.INFO

    handlers = [RichHandler(console=console, rich_tracebacks=True)]

    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"),
        )
        handlers.append(file_handler)

    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=handlers,
    )


logger = logging.getLogger(__name__)


class ProcessingStats:
    """Klasse für Verarbeitungsstatistiken mit Rich-Integration."""

    def __init__(self):
        self.processed = 0
        self.failed = 0
        self.skipped = 0
        self.backups_filtered = 0
        self.new_elements = []
        self.start_time = datetime.now()
        self.errors = []

    def add_processed(self) -> None:
        """Fügt eine erfolgreich verarbeitete Datei hinzu."""
        self.processed += 1

    def add_failed(self, filename: str, error: str) -> None:
        """Fügt eine fehlgeschlagene Datei hinzu."""
        self.failed += 1
        self.errors.append((filename, error))

    def add_skipped(self) -> None:
        """Fügt eine übersprungene Datei hinzu."""
        self.skipped += 1

    def add_backup_filtered(self) -> None:
        """Fügt eine gefilterte Backup-Datei hinzu."""
        self.backups_filtered += 1

    def add_new_element(self, element: str) -> None:
        """Fügt ein neues XML-Element hinzu."""
        if element not in self.new_elements:
            self.new_elements.append(element)

    def get_duration(self) -> str:
        """Gibt die Verarbeitungsdauer zurück."""
        duration = datetime.now() - self.start_time
        return f"{duration.total_seconds():.1f}s"

    def create_summary_table(self) -> Table:
        """Erstellt eine Zusammenfassungstabelle."""
        table = Table(title="📊 Verarbeitungsstatistik", box=box.ROUNDED)

        table.add_column("Kategorie", style="cyan", no_wrap=True)
        table.add_column("Anzahl", style="magenta", justify="right")
        table.add_column("Status", style="green")

        total = self.processed + self.failed + self.skipped
        success_rate = (self.processed / total * 100) if total > 0 else 0

        table.add_row("✅ Erfolgreich", str(self.processed), f"{success_rate:.1f}%")
        table.add_row(
            "❌ Fehlgeschlagen",
            str(self.failed),
            "🔴" if self.failed > 0 else "🟢",
        )
        table.add_row("⏭️  Übersprungen", str(self.skipped), "ℹ️")

        # Zeige Backup-Statistik nur wenn Backups gefiltert wurden
        if self.backups_filtered > 0:
            table.add_row("🔄 Backups gefiltert", str(self.backups_filtered), "📁")

        table.add_row("⏱️  Dauer", self.get_duration(), "")

        return table


def create_header() -> Panel:
    """Erstellt einen schönen Header."""
    header_text = Text()
    header_text.append("🏗️  REVIT FAMILIE EXTRACTOR  🏗️", style="bold blue")
    header_text.append("\n")
    header_text.append("Konvertiert .rfa Dateien zu JSON", style="dim")

    return Panel(Align.center(header_text), box=box.DOUBLE, style="blue")


def create_file_tree(files: list[Path], base_path: Path) -> Tree:
    """Erstellt einen Dateibaum zur Anzeige."""
    tree = Tree(f"📁 {base_path.name}", style="bold blue")

    # Gruppiere Dateien nach Ordnern
    folders = {}
    for file in files:
        try:
            rel_path = file.relative_to(base_path)
            folder = rel_path.parent
            if folder not in folders:
                folders[folder] = []
            folders[folder].append(file.name)
        except ValueError:
            # Datei ist nicht relativ zu base_path
            tree.add(f"📄 {file.name}")

    # Füge Ordner und Dateien hinzu
    for folder, file_names in folders.items():
        if str(folder) == ".":
            for name in file_names:
                tree.add(f"📄 {name}")
        else:
            folder_node = tree.add(f"📁 {folder}")
            for name in file_names:
                folder_node.add(f"📄 {name}")

    return tree


def collect_rfa_without_backup(input_path: Path, recursive: bool, include_backups: bool) -> list[Path]:
    """
    Sammelt .rfa Dateien mit optionalem Backup-Filter.

    Args:
        input_path: Pfad zu Datei oder Ordner
        recursive: Rekursive Suche
        include_backups: Ob Backup-Dateien eingeschlossen werden sollen

    Returns:
        Liste der gefilterten .rfa Dateien
    """
    rfa_files = []
    backup_files = []

    if input_path.is_file():
        if input_path.suffix.lower() == ".rfa":
            if _is_backup_file(input_path):
                if include_backups:
                    rfa_files.append(input_path)
                else:
                    backup_files.append(input_path)
                    console.print(
                        f"⏭️  [yellow]Überspringe Backup-Datei:[/yellow] {input_path.name}",
                    )
            else:
                rfa_files.append(input_path)
        else:
            console.print(f"❌ [red]Datei ist keine .rfa Datei:[/red] {input_path}")

    elif input_path.is_dir():
        pattern = "**/*.rfa" if recursive else "*.rfa"
        all_rfa_files = list(input_path.glob(pattern))

        # Filtere Backup-Dateien
        for file in all_rfa_files:
            if _is_backup_file(file):
                if include_backups:
                    rfa_files.append(file)
                else:
                    backup_files.append(file)
            else:
                rfa_files.append(file)

    # Zeige Backup-Statistiken
    if backup_files and not include_backups:
        console.print(
            f"ℹ️  [dim]{len(backup_files)} Backup-Datei(en) übersprungen[/dim]",
        )
        logger.info(f"Backup-Dateien übersprungen: {len(backup_files)}")

        if len(backup_files) <= 5:  # Zeige Details für wenige Dateien
            for backup in backup_files:
                logger.debug(f"Übersprungen: {backup.name}")

    return sorted(rfa_files)


def _is_backup_file(file_path: Path) -> bool:
    """
    Prüft, ob eine Datei eine Revit Backup-Datei ist.

    Revit Backup-Dateien haben das Format: filename.0001.rfa, filename.0002.rfa, etc.

    Args:
        file_path: Pfad zur zu prüfenden Datei

    Returns:
        True wenn es eine Backup-Datei ist, False sonst

    Examples:
        >>> _is_backup_file(Path("Familie.0001.rfa"))
        True
        >>> _is_backup_file(Path("Familie.rfa"))
        False
        >>> _is_backup_file(Path("Familie.0123.rfa"))
        True
    """
    import re

    # Pattern für Backup-Dateien: .NNNN.rfa (wobei NNNN eine 4-stellige Zahl ist)
    backup_pattern = r"\.(\d{4})\.rfa$"

    return bool(re.search(backup_pattern, file_path.name, re.IGNORECASE))


def collect_rfa_files(input_path: Path, recursive: bool) -> list[Path]:
    """Sammelt alle .rfa Dateien im angegebenen Pfad."""
    rfa_files = []

    if input_path.is_file():
        if input_path.suffix.lower() == ".rfa":
            rfa_files.append(input_path)
        else:
            console.print(f"❌ [red]Datei ist keine .rfa Datei:[/red] {input_path}")

    elif input_path.is_dir():
        pattern = "**/*.rfa" if recursive else "*.rfa"
        rfa_files = list(input_path.glob(pattern))

    return sorted(rfa_files)


def determine_output_path(
    rfa_file: Path,
    input_base: Path,
    output_base: Path | None,
) -> Path:
    """Bestimmt den Ausgabepfad für die JSON-Datei."""
    json_filename = rfa_file.stem + ".json"

    if output_base is None:
        # Speichere neben der .rfa Datei
        return rfa_file.parent / json_filename

    # Behalte Ordnerstruktur bei
    if input_base.is_file():
        # Wenn input_base eine Datei ist, speichere direkt in output_base
        return output_base / json_filename
    # Behalte relative Pfadstruktur bei
    relative_path = rfa_file.parent.relative_to(input_base)
    output_dir = output_base / relative_path
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / json_filename


def check_for_new_elements(entry, stats: ProcessingStats) -> None:
    """Prüft auf neue XML-Elemente, die Code-Updates erfordern könnten."""
    from config import KNOWN_PARAMETER_TYPES, KNOWN_TYPE_OF_PARAMETERS

    # Prüfe Features
    for feature in entry.features:
        for group in feature.groups:
            for param in group.parameters:
                if param.type and param.type not in KNOWN_PARAMETER_TYPES:
                    stats.add_new_element(f"Neuer Parameter-Typ: {param.type}")

                if param.type_of_parameter and param.type_of_parameter not in KNOWN_TYPE_OF_PARAMETERS:
                    stats.add_new_element(
                        f"Neuer typeOfParameter: {param.type_of_parameter}",
                    )

    # Prüfe Family Parts
    if entry.family:
        for part in entry.family.parts:
            for param in part.parameters:
                if param.type and param.type not in KNOWN_PARAMETER_TYPES:
                    stats.add_new_element(f"Neuer Part-Parameter-Typ: {param.type}")


@app.command("extract")
def extract_families(
    input_path: Path = typer.Argument(..., help="📂 Pfad zu .rfa Datei oder Ordner"),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="📤 Ausgabepfad für JSON-Dateien",
    ),
    recursive: bool = typer.Option(
        False,
        "--recursive",
        "-r",
        help="🔄 Rekursive Suche in Unterordnern",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="💪 Überschreibt existierende JSON-Dateien",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="🔍 Ausführliche Ausgabe",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="👀 Zeigt nur an, was verarbeitet würde",
    ),
    log_file: Path | None = typer.Option(
        None,
        "--log-file",
        help="📝 Pfad zur Log-Datei",
    ),
    include_backups: bool = typer.Option(
        False,
        "--include-backups",
        help="🔄 Verarbeitet auch Backup-Dateien (.0001.rfa, etc.)",
    ),
):
    """
    🚀 Extrahiert XML-Daten aus Revit Familie (.rfa) Dateien zu JSON.

    Moderne, benutzerfreundliche Verarbeitung mit schöner Ausgabe! ✨

    Backup-Dateien (.0001.rfa, .0002.rfa, etc.) werden standardmäßig übersprungen.
    """

    # Setup Logging
    setup_logging(verbose, log_file)

    # Header anzeigen
    console.print(create_header())
    console.print()

    # Validierung
    if not input_path.exists():
        console.print(f"❌ [red]Pfad existiert nicht:[/red] {input_path}")
        logger.error(f"Pfad existiert nicht: {input_path}")
        raise typer.Exit(1)

    # Sammle Dateien
    with console.status("[bold green]🔍 Suche nach .rfa Dateien..."):
        rfa_files = collect_rfa_files_with_backup_filter(
            input_path,
            recursive,
            include_backups,
        )

    if not rfa_files:
        console.print("❌ [red]Keine .rfa Dateien gefunden![/red]")
        logger.warning("Keine .rfa Dateien gefunden")
        raise typer.Exit(1)

    # Zeige gefundene Dateien
    console.print(f"✅ [green]{len(rfa_files)} .rfa Datei(en) gefunden[/green]")
    logger.info(f"Gefunden: {len(rfa_files)} .rfa Datei(en)")

    if verbose or len(rfa_files) <= 10:
        console.print("\n📋 Gefundene Dateien:")
        tree = create_file_tree(
            rfa_files,
            input_path if input_path.is_dir() else input_path.parent,
        )
        console.print(tree)
        console.print()

    # Setup
    stats = ProcessingStats()
    service = RevitFamilyService(
        reader=RevitFamilyXMLReader(),
        repository=RevitFamilyJSONRepository(),
    )

    # Verarbeitung mit Progress Bar
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TextColumn("[blue]{task.fields[current_file]}"),
        console=console,
        transient=False,
    ) as progress:
        task = progress.add_task(
            "🔄 Verarbeite Familien...",
            total=len(rfa_files),
            current_file="",
        )

        for rfa_file in rfa_files:
            progress.update(task, current_file=rfa_file.name)

            try:
                json_path = determine_output_path(rfa_file, input_path, output)

                # Prüfe ob überspringen
                if json_path.exists() and not force:
                    stats.add_skipped()
                    logger.info(f"Überspringe: {rfa_file.name} (existiert bereits)")
                    progress.advance(task)
                    continue

                if dry_run:
                    console.print(
                        f"👀 [cyan][DRY-RUN][/cyan] {rfa_file.name} → {json_path.name}",
                    )
                    logger.info(f"[DRY-RUN] Würde verarbeiten: {rfa_file.name}")
                    stats.add_processed()
                else:
                    # Tatsächliche Verarbeitung
                    entry = service.extract_and_save(rfa_file, json_path)
                    check_for_new_elements(entry, stats)
                    stats.add_processed()
                    logger.info(f"Verarbeitet: {rfa_file.name}")

            except Exception as e:
                error_msg = str(e)
                stats.add_failed(rfa_file.name, error_msg)
                console.print(f"❌ [red]Fehler bei {rfa_file.name}:[/red] {error_msg}")
                logger.error(f"Fehler bei {rfa_file.name}: {error_msg}")

                if verbose:
                    logger.exception("Detaillierter Fehler:")

            progress.advance(task)

    # Zusammenfassung anzeigen
    console.print("\n" + "=" * 60)
    console.print(stats.create_summary_table())

    # Zeige Fehler Details
    if stats.errors and verbose:
        console.print("\n❌ [red]Fehler Details:[/red]")
        error_table = Table(title="🔍 Fehler", box=box.ROUNDED)
        error_table.add_column("Datei", style="yellow")
        error_table.add_column("Fehler", style="red")

        for filename, error in stats.errors:
            error_table.add_row(
                filename,
                error[:80] + "..." if len(error) > 80 else error,
            )

        console.print(error_table)

    # Warnungen für neue Elemente
    if stats.new_elements:
        console.print(
            "\n⚠️  [bold yellow]ACHTUNG: Neue XML-Elemente entdeckt![/bold yellow]",
        )
        warning_table = Table(title="🔍 Neue Elemente", box=box.ROUNDED)
        warning_table.add_column("Element", style="yellow")
        warning_table.add_column("Aktion erforderlich", style="red")

        for element in stats.new_elements:
            warning_table.add_row(element, "Code-Update prüfen")

        console.print(warning_table)
        logger.warning(f"Neue XML-Elemente gefunden: {stats.new_elements}")

    # Log Zusammenfassung
    logger.info(
        f"Verarbeitung abgeschlossen: {stats.processed} erfolgreich, {stats.failed} fehlgeschlagen, {stats.skipped} übersprungen",
    )

    # Exit Code
    if stats.failed > 0:
        console.print("\n❌ [red]Verarbeitung mit Fehlern abgeschlossen[/red]")
        raise typer.Exit(1)
    console.print("\n🎉 [green]Verarbeitung erfolgreich abgeschlossen![/green]")


@app.command("info")
def show_info(json_file: Path = typer.Argument(..., help="📄 JSON-Datei zum Anzeigen")):
    """📋 Zeigt detaillierte Informationen über eine verarbeitete Familie."""

    if not json_file.exists():
        console.print(f"❌ [red]Datei nicht gefunden:[/red] {json_file}")
        raise typer.Exit(1)

    try:
        service = RevitFamilyService()

        with console.status("[bold green]📖 Lade Familie-Informationen..."):
            entry = service.load_from_json(json_file)

        # Haupt-Info Panel
        info_text = f"""[bold blue]Name:[/bold blue] {entry.name}
[bold blue]ID:[/bold blue] {entry.id}
[bold blue]Aktualisiert:[/bold blue] {entry.updated}
[bold blue]Kategorien:[/bold blue] {len(entry.categories)}"""

        console.print(Panel(info_text, title="📋 Familie Information", box=box.ROUNDED))

        # Familie Details
        if entry.family:
            family_table = Table(title="👨‍👩‍👧‍👦 Familie Details", box=box.ROUNDED)
            family_table.add_column("Eigenschaft", style="cyan")
            family_table.add_column("Wert", style="magenta")

            family_table.add_row("Typ", entry.family.type)
            family_table.add_row("Varianten", str(entry.family.variation_count))
            family_table.add_row("Teile", str(len(entry.family.parts)))

            console.print(family_table)

            # Teile Details
            if entry.family.parts:
                parts_table = Table(title="🧩 Familie Teile", box=box.ROUNDED)
                parts_table.add_column("Nr.", style="dim")
                parts_table.add_column("Name", style="cyan")
                parts_table.add_column("Typ", style="green")
                parts_table.add_column("Parameter", style="magenta", justify="right")

                for i, part in enumerate(entry.family.parts, 1):
                    parts_table.add_row(
                        str(i),
                        part.name,
                        part.type,
                        str(len(part.parameters)),
                    )

                console.print(parts_table)

        # Features
        if entry.features:
            features_table = Table(title="⚙️  Features", box=box.ROUNDED)
            features_table.add_column("Feature", style="cyan")
            features_table.add_column("Gruppen", style="green", justify="right")
            features_table.add_column("Parameter", style="magenta", justify="right")

            for feature in entry.features:
                total_params = sum(len(group.parameters) for group in feature.groups)
                features_table.add_row(
                    feature.name,
                    str(len(feature.groups)),
                    str(total_params),
                )

            console.print(features_table)

    except Exception as e:
        console.print(f"❌ [red]Fehler beim Laden:[/red] {e}")
        raise typer.Exit(1)


@app.command("validate")
def validate_json_files(
    directory: Path = typer.Argument(..., help="📁 Verzeichnis mit JSON-Dateien"),
    recursive: bool = typer.Option(
        True,
        "--recursive",
        "-r",
        help="🔄 Rekursive Suche",
    ),
):
    """✅ Validiert alle JSON-Dateien in einem Verzeichnis."""

    if not directory.exists():
        console.print(f"❌ [red]Verzeichnis nicht gefunden:[/red] {directory}")
        raise typer.Exit(1)

    # Sammle JSON-Dateien
    pattern = "**/*.json" if recursive else "*.json"
    json_files = list(directory.glob(pattern))

    if not json_files:
        console.print("❌ [red]Keine JSON-Dateien gefunden![/red]")
        raise typer.Exit(1)

    console.print(f"🔍 [blue]{len(json_files)} JSON-Datei(en) gefunden[/blue]")

    valid_count = 0
    invalid_files = []
    service = RevitFamilyService()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("✅ Validiere JSON-Dateien...", total=len(json_files))

        for json_file in json_files:
            try:
                service.load_from_json(json_file)
                valid_count += 1
            except Exception as e:
                invalid_files.append((json_file, str(e)))

            progress.advance(task)

    # Ergebnisse
    results_table = Table(title="📊 Validierungsergebnisse", box=box.ROUNDED)
    results_table.add_column("Status", style="bold")
    results_table.add_column("Anzahl", justify="right")
    results_table.add_column("Prozent", justify="right")

    total = len(json_files)
    invalid_count = len(invalid_files)

    results_table.add_row(
        "✅ Gültig",
        str(valid_count),
        f"{valid_count / total * 100:.1f}%",
    )
    results_table.add_row(
        "❌ Ungültig",
        str(invalid_count),
        f"{invalid_count / total * 100:.1f}%",
    )

    console.print(results_table)

    # Zeige ungültige Dateien
    if invalid_files:
        console.print("\n❌ [red]Ungültige Dateien:[/red]")
        error_table = Table(box=box.SIMPLE)
        error_table.add_column("Datei", style="yellow")
        error_table.add_column("Fehler", style="red")

        for file, error in invalid_files:
            error_table.add_row(
                file.name,
                error[:50] + "..." if len(error) > 50 else error,
            )

        console.print(error_table)
        raise typer.Exit(1)
    console.print("\n🎉 [green]Alle Dateien sind gültig![/green]")


@app.command("analyze")
def analyze_families(
    directory: Path = typer.Argument(..., help="📁 Verzeichnis mit JSON-Dateien"),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="📤 Ausgabeverzeichnis für Diagramme",
    ),
    query: str | None = typer.Option(
        None,
        "--query",
        "-q",
        help="🔍 Query-String (z.B. 'Param:type=custom' oder 'Cat:name=Möbel')",
    ),
    chart_type: str = typer.Option(
        "dashboard",
        "--chart",
        "-c",
        help="📊 Diagramm-Typ: dashboard, param-types, family-parts, units, categories",
    ),
    recursive: bool = typer.Option(
        True,
        "--recursive",
        "-r",
        help="🔄 Rekursive Suche",
    ),
    show_stats: bool = typer.Option(
        True,
        "--stats",
        help="📈 Zeige Zusammenfassungsstatistiken",
    ),
):
    """
    📊 Analysiert Revit Familie Daten und erstellt Visualisierungen.

    Unterstützte Query-Formate:
    - Param:name=Width (Parameter nach Name)
    - Param:type=custom (Parameter nach Typ)
    - Param:type_of_parameter=Länge (Parameter nach typeOfParameter)
    - Cat:name=Möbel (Familien nach Kategorie)
    - Family:type=user (Familien nach Typ)
    - Group:name=Bemaßungen (Parameter nach Gruppe)
    """

    if not directory.exists():
        console.print(f"❌ [red]Verzeichnis nicht gefunden:[/red] {directory}")
        raise typer.Exit(1)

    # Analyzer initialisieren und Daten laden
    from analyzer import FamilyDataAnalyzer

    analyzer = FamilyDataAnalyzer()

    with console.status("[bold green]📖 Lade Familie-Daten..."):
        analyzer.load_families_from_directory(directory, recursive)

    if not analyzer.families:
        console.print("❌ [red]Keine gültigen Familie-Daten gefunden![/red]")
        raise typer.Exit(1)

    # Statistiken anzeigen
    if show_stats:
        analyzer.print_summary_statistics()

    # Query ausführen falls angegeben
    if query:
        try:
            console.print(f"\n🔍 [blue]Führe Query aus:[/blue] {query}")
            result_df = analyzer.query_data(query)

            if result_df.empty:
                console.print(
                    "❌ [yellow]Keine Ergebnisse für die Query gefunden[/yellow]",
                )
            else:
                console.print(f"✅ [green]{len(result_df)} Ergebnisse gefunden[/green]")

                # Zeige erste 10 Ergebnisse
                query_table = Table(
                    title=f"🔍 Query Ergebnisse: {query}",
                    box=box.ROUNDED,
                )
                query_table.add_column("Familie", style="cyan")
                query_table.add_column("Parameter", style="green")
                query_table.add_column("Typ", style="yellow")
                query_table.add_column("Wert", style="magenta")

                for _, row in result_df.head(10).iterrows():
                    query_table.add_row(
                        row["family_name"][:30] + "..."
                        if len(row["family_name"]) > 30
                        else row["family_name"],
                        row["param_name"],
                        str(row["param_type"]),
                        str(row["param_value"])[:20] + "..."
                        if len(str(row["param_value"])) > 20
                        else str(row["param_value"]),
                    )

                console.print(query_table)

                if len(result_df) > 10:
                    console.print(f"... und {len(result_df) - 10} weitere Ergebnisse")

        except Exception as e:
            console.print(f"❌ [red]Fehler bei Query:[/red] {e}")
            raise typer.Exit(1)

    # Diagramme erstellen
    if output:
        output.mkdir(parents=True, exist_ok=True)

        try:
            if chart_type == "dashboard":
                analyzer.create_comprehensive_dashboard(output)
            elif chart_type == "param-types":
                analyzer.create_parameter_type_chart(output / "parameter_types.png")
            elif chart_type == "family-parts":
                analyzer.create_family_parts_distribution(output / "family_parts.png")
            elif chart_type == "units":
                analyzer.create_parameter_units_chart(output / "parameter_units.png")
            elif chart_type == "categories":
                analyzer.create_category_distribution(output / "categories.png")
            else:
                console.print(f"❌ [red]Unbekannter Diagramm-Typ:[/red] {chart_type}")
                console.print(
                    "Unterstützte Typen: dashboard, param-types, family-parts, units, categories",
                )
                raise typer.Exit(1)

        except Exception as e:
            console.print(f"❌ [red]Fehler beim Erstellen der Diagramme:[/red] {e}")
            raise typer.Exit(1)

    console.print("\n🎉 [green]Analyse abgeschlossen![/green]")


def main():
    """Haupteinstiegspunkt für die CLI."""
    app()


if __name__ == "__main__":
    main()
