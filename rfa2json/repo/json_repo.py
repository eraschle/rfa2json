import json
from datetime import datetime
from pathlib import Path
from typing import Any

from models import (
    Category,
    DesignFile,
    Family,
    FamilyPart,
    Feature,
    Link,
    Parameter,
    ParameterGroup,
    RevitFamilyEntry,
)


class RevitFamilyJSONRepository:
    """JSON-basierte Repository Implementation für RevitFamilyEntry."""

    def save(self, entry: RevitFamilyEntry, file_path: Path) -> None:
        """Speichert RevitFamilyEntry als JSON."""
        data = self._to_dict(entry)

        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=2, ensure_ascii=False, default=str)

    def load(self, file_path: Path) -> RevitFamilyEntry:
        """Lädt RevitFamilyEntry aus JSON."""
        if not file_path.exists():
            raise FileNotFoundError(f"Datei nicht gefunden: {file_path}")

        with open(file_path, encoding="utf-8") as file:
            data = json.load(file)

        return self._from_dict(data)

    def _to_dict(self, entry: RevitFamilyEntry) -> dict[str, Any]:
        """Konvertiert RevitFamilyEntry zu Dictionary."""
        return {
            "name": entry.name,
            "id": entry.id,
            "updated": entry.updated.isoformat(),
            "categories": [{"name": c.name} for c in entry.categories],
            "links": [
                {
                    "rel": l.rel,
                    "type": l.type,
                    "href": l.href,
                    "design_file": {
                        "name": l.design_file.name,
                        "product": l.design_file.product,
                        "product_version": l.design_file.product_version,
                        "updated": l.design_file.updated.isoformat(),
                    }
                    if l.design_file
                    else None,
                }
                for l in entry.links
            ],
            "features": [
                {
                    "name": f.name,
                    "groups": [
                        {
                            "name": g.name,
                            "parameters": [
                                {
                                    "name": p.name,
                                    "display_name": p.display_name,
                                    "type": p.type,
                                    "type_of_parameter": p.type_of_parameter,
                                    "units": p.units,
                                    "value": p.value,
                                }
                                for p in g.parameters
                            ],
                        }
                        for g in f.groups
                    ],
                }
                for f in entry.features
            ],
            "family": {
                "type": entry.family.type,
                "variation_count": entry.family.variation_count,
                "parts": [
                    {
                        "name": p.name,
                        "type": p.type,
                        "parameters": [
                            {
                                "name": param.name,
                                "display_name": param.display_name,
                                "type": param.type,
                                "type_of_parameter": param.type_of_parameter,
                                "units": param.units,
                                "value": param.value,
                            }
                            for param in p.parameters
                        ],
                    }
                    for p in entry.family.parts
                ],
            }
            if entry.family
            else None,
        }

    def _from_dict(self, data: dict[str, Any]) -> RevitFamilyEntry:
        """Konvertiert Dictionary zu RevitFamilyEntry."""
        # Parse datetime
        updated = datetime.fromisoformat(data["updated"])

        # taxonomies werden nicht mehr geladen - leere Liste
        taxonomies = []

        # Parse categories (ohne scheme)
        categories = [Category(name=c["name"]) for c in data.get("categories", [])]

        # Parse links
        links = []
        for l in data.get("links", []):
            design_file = None
            if l.get("design_file"):
                df_data = l["design_file"]
                design_file = DesignFile(
                    name=df_data["name"],
                    product=df_data["product"],
                    product_version=df_data["product_version"],
                    updated=datetime.fromisoformat(df_data["updated"]),
                )

            links.append(
                Link(
                    rel=l["rel"],
                    type=l["type"],
                    href=l["href"],
                    design_file=design_file,
                ),
            )

        # Parse features
        features = []
        for f in data.get("features", []):
            groups = []
            for g in f.get("groups", []):
                parameters = [
                    Parameter(
                        name=p["name"],
                        display_name=p.get("display_name"),
                        type=p.get("type", "custom"),
                        type_of_parameter=p.get("type_of_parameter"),
                        units=p.get("units"),
                        value=p.get("value"),
                    )
                    for p in g.get("parameters", [])
                ]
                groups.append(ParameterGroup(name=g["name"], parameters=parameters))

            features.append(Feature(name=f["name"], groups=groups))

        # Parse family
        family = None
        if data.get("family"):
            f_data = data["family"]
            parts = []
            for p in f_data.get("parts", []):
                parameters = [
                    Parameter(
                        name=param["name"],
                        display_name=param.get("display_name"),
                        type=param.get("type", "custom"),
                        type_of_parameter=param.get("type_of_parameter"),
                        units=param.get("units"),
                        value=param.get("value"),
                    )
                    for param in p.get("parameters", [])
                ]
                parts.append(
                    FamilyPart(
                        name=p["name"],
                        type=p.get("type", "user"),
                        parameters=parameters,
                    ),
                )

            family = Family(
                type=f_data.get("type", "user"),
                variation_count=f_data.get("variation_count", 0),
                parts=parts,
            )

        return RevitFamilyEntry(
            name=data["name"],
            id=data["id"],
            updated=updated,
            taxonomies=taxonomies,
            categories=categories,
            links=links,
            features=features,
            family=family,
        )
