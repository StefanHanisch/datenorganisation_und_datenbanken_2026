#!/usr/bin/env python
"""Baut die Hotel-Analytics-Notebooks aus den Quellen in notebooks/src/.

Aufruf (im Projektordner):

    python scripts/build_notebooks.py            # beide Notebooks schreiben
    python scripts/build_notebooks.py --check    # nur prüfen, ob sie aktuell sind

Ergebnis:
    notebooks/hotel_analytics.ipynb          für Studierende, mit Lücken ___
    notebooks/hotel_analytics_loesung.ipynb  Lösung

Die Quellen sind Python-Dateien im "percent"-Format (wie jupytext). Den
verbindlichen Vertrag beschreibt notebooks/src/README.md. Kurz:

    # %% [markdown]             Markdown-Zelle, jede Zeile beginnt mit "# " oder ist "#"
    # %% [markdown] [loesung]   Markdown-Zelle, die nur im Lösungs-Notebook steht
    # %%                        Code-Zelle
    # %% [setup]                Code-Zelle, die Colab einklappt (erste Zeile "# @title ...")
    # %% [checks]               Platzhalter: hier landen alle Dateien aus checks/*.py

In Code-Zellen trennen die Marker-Zeilen "### LÖSUNG", "### LÜCKE" und
"### ENDE" die beiden Varianten. In Markdown-Zellen ersetzt der Generator
die Platzhalter {{ZEITTABELLE}} und {{COLAB_BADGE}}.

Nur Standardbibliothek, läuft ab Python 3.9.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SRC = PROJECT_ROOT / "notebooks" / "src"
DEFAULT_OUT = PROJECT_ROOT / "notebooks"

STUDENT_FILE = "hotel_analytics.ipynb"
SOLUTION_FILE = "hotel_analytics_loesung.ipynb"

GITHUB_PATH = "StefanHanisch/datenorganisation_und_datenbanken_2026/blob/main/notebooks"
COLAB_BADGE = (
    "[![In Colab öffnen](https://colab.research.google.com/assets/colab-badge.svg)]"
    "(https://colab.research.google.com/github/" + GITHUB_PATH + "/{file_name})"
)
CHECKS_TITLE = "# @title Prüf-Funktionen laden – einfach ausführen"

GAP = "___"
MAX_GAPS_PER_CELL = 3

MARKER_SOLUTION = "### LÖSUNG"
MARKER_GAP = "### LÜCKE"
MARKER_END = "### ENDE"

# "# %%" plus optionale Tags, z. B. "# %% [markdown] [loesung]"
CELL_HEADER = re.compile(r"^# %%(.*)$")
BLOCK_HEADING = re.compile(r"^##\s+Block\s+([^:\s]+)\s*:\s*(.+?)\s*$")
TASK_HEADING = re.compile(r"^###\s+Aufgabe\b.*⏱\s*ca\.\s*(\d+)\s*Min\.")


class BuildError(Exception):
    """Fehler in einer Quelldatei, die Meldung nennt Datei und Zeile."""


class SourceCell:
    """Eine Zelle aus einer Quelldatei, noch vor der Aufteilung in die Varianten.

    kind:  "markdown", "code", "setup" oder "checks"
    lines: Liste von (Zeilennummer, Text) aus der Quelldatei
    """

    def __init__(self, kind: str, file_name: str, line_number: int, solution_only: bool = False):
        self.kind = kind
        self.file_name = file_name
        self.line_number = line_number
        self.solution_only = solution_only
        self.lines: list = []

    def where(self, line_number: int | None = None) -> str:
        return f"{self.file_name}:{line_number or self.line_number}"


# ---------------------------------------------------------------------------
# 1. Quelldateien lesen
# ---------------------------------------------------------------------------

def parse_header(tags_text: str, location: str):
    """Übersetzt die Tags hinter "# %%" in (kind, solution_only)."""
    tags = re.findall(r"\[([^\]]*)\]", tags_text)
    rest = re.sub(r"\[[^\]]*\]", "", tags_text).strip()
    if rest:
        raise BuildError(f"{location}: Unbekannter Text im Zellkopf: {tags_text.strip()!r}")
    if tags == []:
        return "code", False
    if tags == ["markdown"]:
        return "markdown", False
    if tags == ["markdown", "loesung"]:
        return "markdown", True
    if tags == ["setup"]:
        return "setup", False
    if tags == ["checks"]:
        return "checks", False
    raise BuildError(f"{location}: Unbekannter Zellkopf '# %%{tags_text}'")


def read_source_file(path: Path) -> list:
    """Zerlegt eine Quelldatei in SourceCell-Objekte."""
    cells = []
    current = None
    text_lines = path.read_text(encoding="utf-8").splitlines()
    for number, raw_line in enumerate(text_lines, start=1):
        line = raw_line.rstrip()
        header = CELL_HEADER.match(line)
        if header:
            kind, solution_only = parse_header(header.group(1), f"{path.name}:{number}")
            current = SourceCell(kind, path.name, number, solution_only)
            cells.append(current)
            continue
        if current is None:
            if line.strip():
                raise BuildError(f"{path.name}:{number}: Text vor der ersten Zelle ('# %%').")
            continue
        current.lines.append((number, line))
    return cells


def strip_blank_edges(lines: list) -> list:
    """Entfernt leere Zeilen am Anfang und am Ende einer Zelle."""
    start, end = 0, len(lines)
    while start < end and not lines[start][1].strip():
        start += 1
    while end > start and not lines[end - 1][1].strip():
        end -= 1
    return lines[start:end]


def markdown_text(cell: SourceCell) -> list:
    """Entfernt das führende "# " bzw. "#" jeder Markdown-Zeile."""
    result = []
    for number, line in cell.lines:
        if line == "" or line == "#":
            result.append((number, ""))
        elif line.startswith("# "):
            result.append((number, line[2:]))
        else:
            raise BuildError(
                f"{cell.where(number)}: Markdown-Zeile muss mit '# ' beginnen oder genau '#' sein."
            )
    return strip_blank_edges(result)


# ---------------------------------------------------------------------------
# 2. LÖSUNG / LÜCKE / ENDE aufteilen
# ---------------------------------------------------------------------------

def split_variants(cell: SourceCell):
    """Teilt eine Code-Zelle in (Lösungszeilen, Lückenzeilen)."""
    solution, student = [], []
    state = "both"  # "both" -> "solution" -> "gap" -> "both"
    group_start = 0
    group_gap_lines = []
    for number, line in cell.lines:
        marker = line.strip()
        if marker == MARKER_SOLUTION:
            if state != "both":
                raise BuildError(
                    f"{cell.where(number)}: '{MARKER_SOLUTION}' ohne vorheriges "
                    f"'{MARKER_END}' (Marker dürfen nicht verschachtelt sein)."
                )
            state, group_start, group_gap_lines = "solution", number, []
        elif marker == MARKER_GAP:
            if state != "solution":
                raise BuildError(f"{cell.where(number)}: '{MARKER_GAP}' ohne vorheriges '{MARKER_SOLUTION}'.")
            state = "gap"
        elif marker == MARKER_END:
            if state != "gap":
                raise BuildError(f"{cell.where(number)}: '{MARKER_END}' ohne vorheriges '{MARKER_GAP}'.")
            if not any(GAP in text for _, text in group_gap_lines):
                raise BuildError(
                    f"{cell.where(group_start)}: Der LÜCKE-Teil dieser Gruppe enthält keine Lücke '{GAP}'."
                )
            state = "both"
        elif state == "solution":
            solution.append((number, line))
        elif state == "gap":
            student.append((number, line))
            group_gap_lines.append((number, line))
        else:
            solution.append((number, line))
            student.append((number, line))
    if state != "both":
        missing = f"{MARKER_GAP} … {MARKER_END}" if state == "solution" else MARKER_END
        raise BuildError(
            f"{cell.where(group_start)}: Marker-Gruppe ab hier wird nicht mit '{missing}' abgeschlossen."
        )
    return strip_blank_edges(solution), strip_blank_edges(student)


def count_gaps(lines: list) -> int:
    """Zählt die Lücken ___ in Codezeilen (Kommentarzeilen zählen nicht)."""
    return sum(text.count(GAP) for _, text in lines if not text.strip().startswith("#"))


def check_syntax(lines: list, cell: SourceCell, variant: str) -> None:
    """Meldet Syntaxfehler mit der Zeilennummer aus der Quelldatei."""
    code = "\n".join(
        "" if text.strip().startswith(("%", "!")) else text for _, text in lines
    )
    try:
        ast.parse(code)
    except SyntaxError as error:
        index = max((error.lineno or 1) - 1, 0)
        number = lines[index][0] if index < len(lines) else cell.line_number
        raise BuildError(f"{cell.where(number)}: Syntaxfehler im {variant}-Notebook: {error.msg}")


# ---------------------------------------------------------------------------
# 3. Zeittabelle aus den Überschriften
# ---------------------------------------------------------------------------

def format_minutes(minutes: int) -> str:
    """75 -> 'ca. 1 h 15 Min.', 40 -> 'ca. 40 Min.', 120 -> 'ca. 2 h'."""
    hours, rest = divmod(minutes, 60)
    if hours == 0:
        return f"ca. {rest} Min."
    if rest == 0:
        return f"ca. {hours} h"
    return f"ca. {hours} h {rest} Min."


def build_time_table(markdown_cells: list) -> str:
    """Erzeugt | Block | Thema | Zeit | aus '## Block …' und '### Aufgabe … ⏱ ca. N Min.'."""
    blocks = []  # Liste von [Block-Kennung, Titel, Minuten]
    for cell, lines in markdown_cells:
        for number, text in lines:
            block = BLOCK_HEADING.match(text)
            task = TASK_HEADING.match(text)
            if block:
                blocks.append([block.group(1), block.group(2), 0])
            elif task:
                if not blocks:
                    raise BuildError(f"{cell.where(number)}: Aufgabe steht vor dem ersten '## Block …'.")
                blocks[-1][2] += int(task.group(1))
            elif text.startswith("### Aufgabe") and "⏱" in text:
                raise BuildError(
                    f"{cell.where(number)}: Zeitangabe nicht lesbar, Format: "
                    "'### Aufgabe 1.2: Titel · ⏱ ca. 10 Min.'"
                )
    rows = ["| Block | Thema | Zeit |", "|---|---|---|"]
    for name, title, minutes in blocks:
        time_text = format_minutes(minutes) if minutes else "–"
        rows.append(f"| {name} | {title} | {time_text} |")
    total = sum(minutes for _, _, minutes in blocks)
    rows.append(f"| | **Gesamt** | **{format_minutes(total)}** |")
    return "\n".join(rows)


# ---------------------------------------------------------------------------
# 4. Notebook zusammenbauen
# ---------------------------------------------------------------------------

def to_source(texts: list) -> list:
    """Zeilen für .ipynb: jede mit "\\n", die letzte ohne."""
    return [text + "\n" for text in texts[:-1]] + texts[-1:]


def read_checks(checks_dir: Path) -> list:
    """Hängt alle checks/*.py in Namensreihenfolge aneinander."""
    texts = [CHECKS_TITLE]
    for path in sorted(checks_dir.glob("*.py")):
        content = path.read_text(encoding="utf-8").strip("\n").splitlines()
        try:
            ast.parse("\n".join(content))
        except SyntaxError as error:
            raise BuildError(f"checks/{path.name}:{error.lineno}: Syntaxfehler: {error.msg}")
        texts += ["", "", f"# ---- {path.name} ----"] + [line.rstrip() for line in content]
    return texts


def make_cell(cell_type: str, texts: list, collapsed: bool = False) -> dict:
    cell = {"cell_type": cell_type, "id": "", "metadata": {"cellView": "form"} if collapsed else {}}
    if cell_type == "code":
        cell["execution_count"] = None
        cell["outputs"] = []
    cell["source"] = to_source(texts)
    return cell


def build_variant(source_cells: list, checks_dir: Path, solution: bool, time_table: str):
    """Baut ein Notebook (dict) und zählt die Lücken."""
    file_name = SOLUTION_FILE if solution else STUDENT_FILE
    variant = "Lösungs" if solution else "Studierenden"
    cells = []
    gaps = 0
    title_done = False
    for cell in source_cells:
        if cell.kind == "markdown":
            if cell.solution_only and not solution:
                continue
            texts = [text for _, text in markdown_text(cell)]
            text = "\n".join(texts)
            text = text.replace("{{ZEITTABELLE}}", time_table)
            text = text.replace("{{COLAB_BADGE}}", COLAB_BADGE.format(file_name=file_name))
            texts = text.split("\n")
            if solution and not title_done and texts and texts[0].startswith("# "):
                texts[0] += " – Lösung"
            title_done = True
            if text.strip():
                cells.append(make_cell("markdown", texts))
        elif cell.kind == "checks":
            cells.append(make_cell("code", read_checks(checks_dir), collapsed=True))
        else:
            solution_lines, student_lines = split_variants(cell)
            lines = solution_lines if solution else student_lines
            if not lines:
                continue
            if cell.kind == "setup" and not lines[0][1].startswith("# @title"):
                raise BuildError(f"{cell.where()}: Eine [setup]-Zelle muss mit '# @title …' beginnen.")
            if solution and count_gaps(lines):
                raise BuildError(f"{cell.where()}: Lücke '{GAP}' steht auch im Lösungs-Notebook.")
            check_syntax(lines, cell, variant)
            cell_gaps = count_gaps(lines)
            if cell_gaps > MAX_GAPS_PER_CELL:
                print(f"Warnung {cell.where()}: {cell_gaps} Lücken in einer Zelle (höchstens {MAX_GAPS_PER_CELL}).")
            gaps += cell_gaps
            texts = [text for _, text in lines]
            cells.append(make_cell("code", texts, collapsed=(cell.kind == "setup")))

    for index, cell in enumerate(cells, start=1):
        cell["id"] = f"cell-{index:03d}"

    notebook = {
        "cells": cells,
        "metadata": {
            "colab": {"provenance": []},
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    return notebook, gaps


def build_all(src_dir: Path) -> dict:
    """Liest alle Quellen und gibt {Dateiname: (JSON-Text, Zellen, Lücken)} zurück."""
    paths = sorted(src_dir.glob("*.py"))
    if not paths:
        raise BuildError(f"Keine Quelldateien (*.py) in {src_dir} gefunden.")
    source_cells = []
    for path in paths:
        source_cells += read_source_file(path)

    checks_count = sum(1 for cell in source_cells if cell.kind == "checks")
    if checks_count > 1:
        raise BuildError("'# %% [checks]' darf nur einmal vorkommen.")
    checks_dir = src_dir / "checks"
    if checks_count == 0 and list(checks_dir.glob("*.py")):
        print("Warnung: checks/*.py vorhanden, aber keine Zelle '# %% [checks]'.")

    # Zeittabelle aus den Markdown-Zellen, die auch Studierende sehen
    markdown_cells = [
        (cell, markdown_text(cell))
        for cell in source_cells
        if cell.kind == "markdown" and not cell.solution_only
    ]
    time_table = build_time_table(markdown_cells)

    results = {}
    for solution in (False, True):
        notebook, gaps = build_variant(source_cells, checks_dir, solution, time_table)
        text = json.dumps(notebook, indent=1, ensure_ascii=False) + "\n"
        file_name = SOLUTION_FILE if solution else STUDENT_FILE
        results[file_name] = (text, len(notebook["cells"]), gaps)
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Baut die Hotel-Analytics-Notebooks aus notebooks/src/.")
    parser.add_argument("--src", type=Path, default=DEFAULT_SRC, help="Ordner mit den Quellen (Standard: notebooks/src)")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Zielordner (Standard: notebooks)")
    parser.add_argument("--check", action="store_true", help="Nichts schreiben, nur prüfen, ob die Notebooks aktuell sind")
    args = parser.parse_args()

    try:
        results = build_all(args.src)
    except BuildError as error:
        print(f"Fehler: {error}", file=sys.stderr)
        return 1

    outdated = []
    for file_name, (text, cell_count, gaps) in results.items():
        path = args.out / file_name
        print(f"{file_name}: {cell_count} Zellen, {gaps} Lücken")
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                outdated.append(file_name)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8", newline="\n") as file:
                file.write(text)

    if outdated:
        print(
            "Fehler: veraltet: " + ", ".join(outdated) + ". Bitte 'python scripts/build_notebooks.py' ausführen.",
            file=sys.stderr,
        )
        return 1
    if args.check:
        print("Alle Notebooks sind aktuell.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
