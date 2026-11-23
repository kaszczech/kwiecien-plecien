"""Eksportuje testowalne przysłowia pogodowe do przeglądu.

Tworzy:
  data/przeglad_<kategoria>.csv  - po jednym pliku na kategorię (separator ';')
  data/przeglad.xlsx             - arkusz na kategorię z kolumnami:
                                   Zostaw (PRAWDA/FAŁSZ), Przysłowie, Zmień kategorię, Uwagi, link

Jeśli data/przeglad.xlsx już istnieje, zaznaczenia (Zostaw, Zmień kategorię, Uwagi)
są z niego odczytywane i przenoszone do nowej wersji – dopasowanie po tekście przysłowia.
"""
import csv
import json
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

DATA_DIR = Path(__file__).parent / "data"
XLSX_PATH = DATA_DIR / "przeglad.xlsx"
FONT = "Arial"

# klucz kategorii -> (nazwa arkusza, opis)
CATEGORIES = {
    "warunkowe": ("Warunkowe", "JEŚLI pogoda w dniu X taka, TO później taka"),
    "dzien": ("Dzień", "pogoda w konkretnym dniu, bez warunku"),
    "od_dnia": ("Od dnia", "od danego dnia zmienia się pora roku / pogoda"),
    "okres": ("Okres", "cały miesiąc lub okres, bez konkretnego dnia"),
    "urodzaj": ("Urodzaj", "pogoda => plony (nietestowalne samymi danymi pogodowymi)"),
    "przyroda": ("Przyroda", "zwierzęta/rośliny jako znak pogody (wymaga danych fenologicznych)"),
}
HEADERS = ["Zostaw", "Przysłowie", "Zmień kategorię", "Uwagi", "Wikisłownik"]


def read_previous_marks() -> dict[str, dict]:
    """Zwraca {przysłowie: {zostaw, zmien, uwagi}} z istniejącego arkusza (dowolnej wersji)."""
    if not XLSX_PATH.exists():
        return {}
    wb = load_workbook(XLSX_PATH)
    marks: dict[str, dict] = {}
    for ws in wb.worksheets:
        header = [c.value for c in ws[1]]
        if "Przysłowie" not in header or ("Zostaw" not in header and "Dodać" not in header):
            continue
        col = {name: header.index(name) for name in header if name}
        if "Dodać" in col:  # arkusz 'Pominięte'
            for row in ws.iter_rows(min_row=2, values_only=True):
                text = row[col["Przysłowie"]]
                if text:
                    marks[text] = {
                        "dodac": row[col["Dodać"]] is True,
                        "zmien": row[col["Do kategorii"]],
                        "uwagi": row[col["Uwagi"]],
                    }
            continue
        for row in ws.iter_rows(min_row=2, values_only=True):
            text = row[col["Przysłowie"]]
            if not text:
                continue
            marks[text] = {
                "zostaw": row[col["Zostaw"]] is not False,
                "zmien": row[col["Zmień kategorię"]] if "Zmień kategorię" in col else None,
                "uwagi": row[col["Uwagi"]] if "Uwagi" in col else None,
            }
    return marks


def write_csv(path: Path, rows: list[dict], marks: dict[str, dict]) -> None:
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(["zostaw", "przyslowie", "zmien_kategorie", "uwagi", "url"])
        for r in rows:
            m = marks.get(r["tytul"], {})
            writer.writerow([
                "TAK" if m.get("zostaw", True) else "NIE",
                r["tytul"],
                m.get("zmien") or "",
                m.get("uwagi") or "",
                r["url"],
            ])


def add_instruction_sheet(wb: Workbook) -> None:
    ws = wb.active
    ws.title = "Instrukcja"
    lines = [
        ("Przegląd przysłów pogodowych", True),
        ("", False),
        ("Kategorie (osobny arkusz dla każdej):", True),
        *[(f"• {name} – {desc}", False) for name, desc in CATEGORIES.values()],
        ("", False),
        ("Kolumny do edycji:", True),
        ("• Zostaw – PRAWDA (domyślnie) albo FAŁSZ = to w ogóle nie jest przysłowie pogodowe;", False),
        ("  odrzucony wiersz robi się szary i przekreślony.", False),
        ("• Zmień kategorię – wybierz z listy, jeśli przysłowie pasuje do innej kategorii.", False),
        ("• Uwagi – dowolny komentarz.", False),
        ("Przykład: FAŁSZ | …przysłowie… | (puste) | 'to metafora, nie pogoda'", False),
        ("Strzałki w nagłówkach pozwalają filtrować, np. tylko PRAWDA lub tylko FAŁSZ.", False),
        ("", False),
        ("Arkusz 'Pominięte' – wszystkie przysłowia NIE zakwalifikowane jako pogodowe:", True),
        ("• Na górze przypadki graniczne z powodem pominięcia (astronomia, metafora, kalendarz prac…).", False),
        ("• Jeśli coś powinno trafić do analizy: Dodać = PRAWDA i wybierz 'Do kategorii'.", False),
        ("", False),
        ("Prawdziwe pola wyboru (Excel 365):", True),
        ("Zaznacz komórki od A2 w dół → Wstawianie → Pole wyboru.", False),
        ("", False),
        ("Po przeglądzie zapisz plik – odczytam z niego Twoje decyzje.", False),
    ]
    for i, (text, bold) in enumerate(lines, start=1):
        ws.cell(row=i, column=1, value=text).font = Font(name=FONT, bold=bold, size=14 if i == 1 else 11)
    ws.column_dimensions["A"].width = 100


def add_category_sheet(wb: Workbook, title: str, rows: list[dict], marks: dict[str, dict]) -> None:
    ws = wb.create_sheet(title)
    header_fill = PatternFill("solid", start_color="1F4E78")
    for col, h in enumerate(HEADERS, start=1):
        c = ws.cell(row=1, column=col, value=h)
        c.font = Font(name=FONT, bold=True, color="FFFFFF")
        c.fill = header_fill

    for i, r in enumerate(rows, start=2):
        m = marks.get(r["tytul"], {})
        values = [m.get("zostaw", True), r["tytul"], m.get("zmien"), m.get("uwagi")]
        for col, v in enumerate(values, start=1):
            c = ws.cell(row=i, column=col, value=v)
            c.font = Font(name=FONT)
            c.alignment = Alignment(wrap_text=True, vertical="top", horizontal="center" if col == 1 else None)
        link = ws.cell(row=i, column=5, value="otwórz")
        link.hyperlink = r["url"]
        link.font = Font(name=FONT, color="0563C1", underline="single")

    last = len(rows) + 1
    other = [name for name, _ in CATEGORIES.values() if name != title]
    dv = DataValidation(type="list", formula1='"' + ",".join(other) + '"', allow_blank=True)
    ws.add_data_validation(dv)
    dv.add(f"C2:C{last}")

    grey = PatternFill("solid", start_color="D9D9D9", end_color="D9D9D9")
    ws.conditional_formatting.add(
        f"A2:E{last}",
        FormulaRule(formula=["$A2=FALSE"], fill=grey, font=Font(color="808080", strike=True)),
    )
    ws.auto_filter.ref = f"A1:E{last}"
    ws.freeze_panes = "A2"
    for letter, width in zip("ABCDE", (10, 85, 18, 35, 13)):
        ws.column_dimensions[letter].width = width


def add_excluded_sheet(wb: Workbook, rows: list[dict], marks: dict[str, dict]) -> None:
    """Wszystkie odrzucone przysłowia – do wyłapania pominiętych pogodowych."""
    ws = wb.create_sheet("Pominięte")
    headers = ["Dodać", "Przysłowie", "Do kategorii", "Powód pominięcia", "Uwagi", "Wikisłownik"]
    header_fill = PatternFill("solid", start_color="7F6000")
    for col, h in enumerate(headers, start=1):
        c = ws.cell(row=1, column=col, value=h)
        c.font = Font(name=FONT, bold=True, color="FFFFFF")
        c.fill = header_fill

    # graniczne (z konkretnym powodem) na górze
    rows = sorted(rows, key=lambda r: r["powod"] == "brak związku z pogodą")
    for i, r in enumerate(rows, start=2):
        m = marks.get(r["tytul"], {})
        values = [m.get("dodac", False), r["tytul"], m.get("zmien"), r["powod"], m.get("uwagi")]
        for col, v in enumerate(values, start=1):
            c = ws.cell(row=i, column=col, value=v)
            c.font = Font(name=FONT)
            c.alignment = Alignment(wrap_text=True, vertical="top", horizontal="center" if col == 1 else None)
        link = ws.cell(row=i, column=6, value="otwórz")
        link.hyperlink = r["url"]
        link.font = Font(name=FONT, color="0563C1", underline="single")

    last = len(rows) + 1
    names = [name for name, _ in CATEGORIES.values()]
    dv = DataValidation(type="list", formula1='"' + ",".join(names) + '"', allow_blank=True)
    ws.add_data_validation(dv)
    dv.add(f"C2:C{last}")
    green = PatternFill("solid", start_color="C6EFCE", end_color="C6EFCE")
    ws.conditional_formatting.add(f"A2:F{last}", FormulaRule(formula=["$A2=TRUE"], fill=green))
    ws.auto_filter.ref = f"A1:F{last}"
    ws.freeze_panes = "A2"
    for letter, width in zip("ABCDEF", (10, 75, 16, 40, 30, 13)):
        ws.column_dimensions[letter].width = width


def main() -> None:
    proverbs = json.loads((DATA_DIR / "przyslowia_pogodowe.json").read_text(encoding="utf-8"))
    excluded = json.loads((DATA_DIR / "przyslowia_pominiete.json").read_text(encoding="utf-8"))
    marks = read_previous_marks()
    carried = sum(
        1 for m in marks.values()
        if m.get("zostaw") is False or m.get("dodac") or m.get("zmien") or m.get("uwagi")
    )
    print(f"Przeniesione zaznaczenia ze starego arkusza: {carried}")

    for old in DATA_DIR.glob("przeglad_*.csv"):
        old.unlink()

    wb = Workbook()
    add_instruction_sheet(wb)
    for key, (title, _) in CATEGORIES.items():
        rows = [p for p in proverbs if p["kategoria"] == key]
        write_csv(DATA_DIR / f"przeglad_{key}.csv", rows, marks)
        add_category_sheet(wb, title, rows, marks)
        print(f"{title}: {len(rows)}")
    add_excluded_sheet(wb, excluded, marks)
    print(f"Pominięte: {len(excluded)}")
    wb.save(XLSX_PATH)
    print(f"Zapisano do {DATA_DIR}")


if __name__ == "__main__":
    main()
