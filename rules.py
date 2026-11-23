"""Wczytuje, waliduje i opisuje reguły przysłów pogodowych.

Pliki wejściowe:
  reguly/kalendarz.toml  - terminy (święta, daty) używane w przysłowiach
  reguly/slownik.toml    - zjawiska mierzalne i ludowe określenia
  reguly/reguly.toml     - reguły
  data/przyslowia_pogodowe.json - przysłowia z kategoriami

Walidacja przerywa działanie przy pierwszej grupie błędów (lista wszystkich znalezionych).
Wynik: raport w konsoli + data/reguly_przeglad.xlsx do przeglądu.

Uruchomienie:  python rules.py
"""
from __future__ import annotations

import json
import re
import tomllib
from calendar import monthrange
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).parent
RULES_DIR = ROOT / "reguly"
DATA_DIR = ROOT / "data"

# lata, dla których sprawdzamy rozwiązywanie okien (zakres typowych danych IMGW)
LATA = range(1951, 2026)

TYPY = {"warunkowe", "dzien", "od_dnia", "okres"}
RODZAJE = {"zdarzenie", "anomalia", "porownanie_okresow"}
KLASY = {"ponizej", "w_normie", "powyzej"}
OPERATORY = {"<", "<=", ">", ">=", "=="}
RELACJE = {"taki_sam", "przeciwny"}
PEWNOSCI = {"wysoka", "srednia", "niska"}
ZMIENNE = {"temperatura", "opad", "pokrywa_sniezna", "wiatr", "zachmurzenie", "burza"}
RZYMSKIE = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"]

RE_DATA = re.compile(r"^(\d{2})-(\d{2})$")
RE_KONIEC = re.compile(r"^(\d{2})-koniec$")


# ------------------------------------------------------------------ kalendarz

def wielkanoc(rok: int) -> date:
    """Niedziela wielkanocna w kalendarzu gregoriańskim (algorytm Meeusa/Jonesa/Butchera)."""
    a = rok % 19
    b, c = divmod(rok, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    miesiac, dzien = divmod(h + l - 7 * m + 114, 31)
    return date(rok, miesiac, dzien + 1)


RUCHOME = {"wielkanoc_gregorianska": wielkanoc}


def koniec_pory_roku(d: date) -> date:
    """Ostatni dzień meteorologicznej pory roku, w której leży d."""
    if d.month in (12, 1, 2):
        rok = d.year + 1 if d.month == 12 else d.year
        return date(rok, 2, monthrange(rok, 2)[1])
    koniec = {3: 5, 4: 5, 5: 5, 6: 8, 7: 8, 8: 8, 9: 11, 10: 11, 11: 11}[d.month]
    return date(d.year, koniec, monthrange(d.year, koniec)[1])


@dataclass
class Kalendarz:
    wpisy: dict

    def czy_token(self, token: str) -> bool:
        return (token in self.wpisy or bool(RE_DATA.match(token)) or bool(RE_KONIEC.match(token))
                or token == "koniec_pory_roku")

    def czy_ruchomy(self, token: str) -> bool:
        return token in self.wpisy and "ruchome" in self.wpisy[token]

    def w_roku(self, token: str, rok: int) -> date:
        if token in self.wpisy:
            w = self.wpisy[token]
            if "ruchome" in w:
                return RUCHOME[w["ruchome"]](rok)
            token = w["data"]
        if m := RE_DATA.match(token):
            return date(rok, int(m[1]), int(m[2]))
        if m := RE_KONIEC.match(token):
            mies = int(m[1])
            return date(rok, mies, monthrange(rok, mies)[1])
        raise ValueError(f"Nieznany token daty: {token!r}")

    def pierwsze_od(self, token: str, kotwica: date, scisle_po: bool) -> date | None:
        """Pierwsze wystąpienie tokenu w dniu kotwicy lub później (albo ściśle po).
        Dla świąt ruchomych tylko w tym samym roku – inaczej None (rok pomijany)."""
        d = self.w_roku(token, kotwica.year)
        za_wczesnie = d <= kotwica if scisle_po else d < kotwica
        if not za_wczesnie:
            return d
        if self.czy_ruchomy(token):
            return None
        return self.w_roku(token, kotwica.year + 1)

    def okno(self, okno: dict, kotwica: date, scisle_po: bool = False) -> tuple[date, date] | None:
        start = self.pierwsze_od(okno["od"], kotwica, scisle_po)
        if start is None:
            return None
        if okno["do"] == "koniec_pory_roku":
            return start, koniec_pory_roku(start)
        koniec = self.pierwsze_od(okno["do"], start, scisle_po=False)
        if koniec is None:
            return None
        return start, koniec

    def opis_tokenu(self, token: str) -> str:
        if token == "koniec_pory_roku":
            return "koniec pory roku"
        if token in self.wpisy:
            w = self.wpisy[token]
            if "ruchome" in w:
                return f"{w['nazwa']} (święto ruchome)"
            mies, dz = map(int, w["data"].split("-"))
            return f"{w['nazwa']} ({dz} {RZYMSKIE[mies]})"
        if m := RE_DATA.match(token):
            return f"{int(m[2])} {RZYMSKIE[int(m[1])]}"
        if m := RE_KONIEC.match(token):
            return f"koniec {RZYMSKIE[int(m[1])]}"
        return token

    def opis_okna(self, okno: dict) -> str:
        if okno["od"] == okno["do"]:
            return self.opis_tokenu(okno["od"])
        return f"{self.opis_tokenu(okno['od'])} – {self.opis_tokenu(okno['do'])}"


# ------------------------------------------------------------------ wczytywanie

def wczytaj() -> tuple[Kalendarz, dict, list[dict], dict[str, dict]]:
    kal = Kalendarz(tomllib.loads((RULES_DIR / "kalendarz.toml").read_text(encoding="utf-8")))
    slownik = tomllib.loads((RULES_DIR / "slownik.toml").read_text(encoding="utf-8"))
    reguly = tomllib.loads((RULES_DIR / "reguly.toml").read_text(encoding="utf-8")).get("regula", [])
    przyslowia = {p["tytul"]: p for p in json.loads((DATA_DIR / "przyslowia_pogodowe.json").read_text(encoding="utf-8"))}
    return kal, slownik, reguly, przyslowia


def slowa_tekstu(tekst: str) -> set[str]:
    return set(re.findall(r"\w+", tekst.lower()))


# ------------------------------------------------------------------ walidacja

def waliduj(kal: Kalendarz, slownik: dict, reguly: list[dict], przyslowia: dict[str, dict]) -> list[str]:
    bledy: list[str] = []
    zjawiska = slownik.get("zjawisko", {})
    wielkosci = slownik.get("wielkosc", {})
    grupy = slownik.get("grupa", {})
    slowa = {}
    for s in slownik.get("slowo", []):
        if s["tekst"] in slowa:
            bledy.append(f"słownik: zduplikowane słowo {s['tekst']!r}")
        slowa[s["tekst"]] = s

    # --- kalendarz
    for klucz, w in kal.wpisy.items():
        if ("data" in w) == ("ruchome" in w):
            bledy.append(f"kalendarz.{klucz}: wymagane dokładnie jedno z 'data' / 'ruchome'")
        elif "data" in w:
            try:
                kal.w_roku(klucz, 2001)
            except ValueError as e:
                bledy.append(f"kalendarz.{klucz}: niepoprawna data ({e})")
        elif w["ruchome"] not in RUCHOME:
            bledy.append(f"kalendarz.{klucz}: nieznany algorytm {w['ruchome']!r}")
        if "zrodlo" not in w:
            bledy.append(f"kalendarz.{klucz}: brak źródła daty")

    # --- słownik
    for klucz, z in zjawiska.items():
        p = f"zjawisko.{klucz}"
        if z.get("zmienna") not in ZMIENNE:
            bledy.append(f"{p}: nieznana zmienna {z.get('zmienna')!r}")
        if z.get("wielkosc") not in wielkosci:
            bledy.append(f"{p}: nieznana wielkość {z.get('wielkosc')!r}")
        if z.get("rodzaj") not in RODZAJE:
            bledy.append(f"{p}: nieznany rodzaj {z.get('rodzaj')!r}")
        if z.get("rodzaj") == "zdarzenie" and (z.get("operator") not in OPERATORY or "prog" not in z):
            bledy.append(f"{p}: zdarzenie wymaga 'operator' i 'prog'")
        if z.get("rodzaj") == "anomalia" and z.get("klasa") not in KLASY:
            bledy.append(f"{p}: anomalia wymaga 'klasa' z {sorted(KLASY)}")
        if not z.get("uzasadnienie"):
            bledy.append(f"{p}: brak uzasadnienia")
    for klucz, g in grupy.items():
        for zm in g.get("zmienne", []):
            if zm not in ZMIENNE:
                bledy.append(f"grupa.{klucz}: nieznana zmienna {zm!r}")
    for tekst, s in slowa.items():
        if s.get("zjawisko") not in zjawiska:
            bledy.append(f"słowo {tekst!r}: nieznane zjawisko {s.get('zjawisko')!r}")
        if s.get("pewnosc") not in PEWNOSCI:
            bledy.append(f"słowo {tekst!r}: pewność spoza {sorted(PEWNOSCI)}")
        if not s.get("uzasadnienie"):
            bledy.append(f"słowo {tekst!r}: brak uzasadnienia")

    # --- reguły
    ids: set[str] = set()
    uzyte_warianty: dict[str, str] = {}

    def sprawdz_okno(p: str, okno) -> None:
        if not isinstance(okno, dict) or set(okno) != {"od", "do"}:
            bledy.append(f"{p}: okno musi mieć dokładnie 'od' i 'do'")
            return
        for t in ("od", "do"):
            if not kal.czy_token(okno[t]):
                bledy.append(f"{p}: nieznany termin {okno[t]!r}")
        if okno["od"] == "koniec_pory_roku":
            bledy.append(f"{p}: 'koniec_pory_roku' może być tylko końcem okna")

    def sprawdz_zjawisko(p: str, czlon: dict, warianty: list[str]) -> None:
        z = czlon.get("zjawisko")
        if z not in zjawiska:
            bledy.append(f"{p}: nieznane zjawisko {z!r}")
            return
        lista = czlon.get("slowa", [])
        if not lista:
            bledy.append(f"{p}: brak 'slowa' – każde zjawisko musi wskazywać określenie z przysłowia")
        for s in lista:
            if s not in slowa:
                bledy.append(f"{p}: słowo {s!r} nie istnieje w słowniku")
            elif slowa[s]["zjawisko"] != z:
                bledy.append(f"{p}: słowo {s!r} oznacza {slowa[s]['zjawisko']!r}, a nie {z!r}")
            if not any(slowa_tekstu(s) <= slowa_tekstu(w) for w in warianty):
                bledy.append(f"{p}: słowo {s!r} nie występuje w żadnym wariancie")
        for w in warianty:
            if lista and not any(slowa_tekstu(s) <= slowa_tekstu(w) for s in lista):
                bledy.append(f"{p}: wariant {w!r} nie zawiera żadnego z określeń {lista}")

    for r in reguly:
        rid = r.get("id", "<brak id>")
        p = f"reguła {rid}"
        if rid in ids:
            bledy.append(f"{p}: zduplikowane id")
        ids.add(rid)
        typ = r.get("typ")
        if typ not in TYPY:
            bledy.append(f"{p}: nieznany typ {typ!r}")
        if r.get("pewnosc") not in PEWNOSCI:
            bledy.append(f"{p}: pewność spoza {sorted(PEWNOSCI)}")
        if not r.get("interpretacja"):
            bledy.append(f"{p}: brak interpretacji")

        warianty = r.get("warianty", [])
        if not warianty:
            bledy.append(f"{p}: brak wariantów")
        for w in warianty:
            if w not in przyslowia:
                bledy.append(f"{p}: wariant nie istnieje w przyslowia_pogodowe.json: {w!r}")
                continue
            if przyslowia[w]["kategoria"] != typ:
                bledy.append(f"{p}: wariant {w!r} ma kategorię {przyslowia[w]['kategoria']!r}, a reguła typ {typ!r}")
            if w in uzyte_warianty:
                bledy.append(f"{p}: wariant {w!r} jest już w regule {uzyte_warianty[w]}")
            uzyte_warianty[w] = rid

        war = r.get("warunek")
        if typ == "warunkowe" and war is None:
            bledy.append(f"{p}: reguła warunkowa wymaga 'warunek'")
        if typ != "warunkowe" and war is not None:
            bledy.append(f"{p}: tylko reguła warunkowa może mieć 'warunek'")
        if war is not None:
            sprawdz_okno(f"{p} / warunek", war.get("okno"))
            if "grupa" in war:
                if war["grupa"] not in grupy:
                    bledy.append(f"{p} / warunek: nieznana grupa {war['grupa']!r}")
                if war.get("stan") != "dowolny":
                    bledy.append(f"{p} / warunek: grupa wymaga stan = 'dowolny'")
            else:
                sprawdz_zjawisko(f"{p} / warunek", war, warianty)

        przew = r.get("przewidywanie", [])
        if not przew:
            bledy.append(f"{p}: brak przewidywania")
        for i, pr in enumerate(przew, start=1):
            pp = f"{p} / przewidywanie {i}"
            sprawdz_okno(pp, pr.get("okno"))
            if "relacja" in pr:
                if pr["relacja"] not in RELACJE:
                    bledy.append(f"{pp}: nieznana relacja {pr['relacja']!r}")
                if war is None or war.get("grupa") != pr.get("grupa"):
                    bledy.append(f"{pp}: relacja wymaga warunku z tą samą grupą zmiennych")
            else:
                sprawdz_zjawisko(pp, pr, warianty)
    return bledy


# ------------------------------------------------------------------ obliczenia

@dataclass
class OknaReguly:
    dni_min: int | None
    dni_max: int | None
    pominiete_lata: list[int]


def okna_przewidywania(kal: Kalendarz, r: dict, przewidywanie: dict) -> OknaReguly:
    dlugosci: list[int] = []
    pominiete: list[int] = []
    for rok in LATA:
        if "warunek" in r:
            okno_w = kal.okno(r["warunek"]["okno"], date(rok, 1, 1))
            okno_p = kal.okno(przewidywanie["okno"], okno_w[1], scisle_po=True) if okno_w else None
        else:
            okno_p = kal.okno(przewidywanie["okno"], date(rok, 1, 1))
        if okno_p is None:
            pominiete.append(rok)
            continue
        dlugosci.append((okno_p[1] - okno_p[0]).days + 1)
    return OknaReguly(min(dlugosci, default=None), max(dlugosci, default=None), pominiete)


def opis_zjawiska(slownik: dict, klucz: str) -> str:
    z = slownik["zjawisko"][klucz]
    w = slownik["wielkosc"][z["wielkosc"]]
    if z["rodzaj"] == "zdarzenie":
        prog = f"{z['prog']:g}".replace(".", ",")
        return f"{w['opis']} {z['operator']} {prog} {w['jednostka']}"
    if z["rodzaj"] == "anomalia":
        klasa = {"ponizej": "poniżej normy", "w_normie": "w normie", "powyzej": "powyżej normy"}[z["klasa"]]
        return f"{w['opis']} {klasa}"
    return f"porównanie okresów: {w['opis']}"


def opis_czlonu(kal: Kalendarz, slownik: dict, czlon: dict) -> str:
    okno = kal.opis_okna(czlon["okno"])
    if "grupa" in czlon:
        zm = ", ".join(slownik["grupa"][czlon["grupa"]]["zmienne"])
        if "relacja" in czlon:
            rel = "taka sama klasa jak w warunku" if czlon["relacja"] == "taki_sam" else "przeciwna klasa niż w warunku"
            return f"{okno}: {rel} ({zm})"
        return f"{okno}: dowolny stan ({zm})"
    slowa = ", ".join(f"„{s}”" for s in czlon.get("slowa", []))
    return f"{okno}: {opis_zjawiska(slownik, czlon['zjawisko'])}  [{slowa}]"


def zmienne_czlonu(slownik: dict, czlon: dict) -> list[str]:
    if "grupa" in czlon:
        return slownik["grupa"][czlon["grupa"]]["zmienne"]
    return [slownik["zjawisko"][czlon["zjawisko"]]["zmienna"]]


def bierze_udzial_w_rankingu(slownik: dict, czlon: dict) -> bool:
    return "grupa" in czlon or slownik["zjawisko"][czlon["zjawisko"]]["rodzaj"] != "porownanie_okresow"


def zestawienie(kal: Kalendarz, slownik: dict, reguly: list[dict]) -> list[dict]:
    wiersze = []
    for r in reguly:
        for i, pr in enumerate(r["przewidywanie"], start=1):
            okna = okna_przewidywania(kal, r, pr)
            ranking = bierze_udzial_w_rankingu(slownik, pr)
            if okna.dni_min is None:
                dni = "—"
            elif okna.dni_min == okna.dni_max:
                dni = str(okna.dni_min)
            else:
                dni = f"{okna.dni_min}–{okna.dni_max}"
            if not ranking or okna.dni_max is None:
                moc = "nie dotyczy"
            elif okna.dni_min == okna.dni_max:
                moc = f"1/{okna.dni_min}"
            else:
                moc = f"1/{okna.dni_min} – 1/{okna.dni_max}"
            wiersze.append({
                "id": r["id"] + (f" #{i}" if len(r["przewidywanie"]) > 1 else ""),
                "typ": r["typ"],
                "warianty": r["warianty"],
                "warunek": opis_czlonu(kal, slownik, r["warunek"]) if "warunek" in r else "— (bez warunku)",
                "przewidywanie": opis_czlonu(kal, slownik, pr),
                "zmienne": ", ".join(zmienne_czlonu(slownik, pr)),
                "dni": dni,
                "moc": moc,
                "pominiete_lata": okna.pominiete_lata,
                "pewnosc": r["pewnosc"],
                "interpretacja": r["interpretacja"],
                "uwagi": r.get("uwagi", []),
            })
    return wiersze


# ------------------------------------------------------------------ eksport

def eksportuj_xlsx(wiersze: list[dict], kal: Kalendarz, slownik: dict, sciezka: Path) -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill

    font = "Arial"
    wb = Workbook()

    def arkusz(ws, naglowki, dane, szerokosci):
        for c, h in enumerate(naglowki, start=1):
            k = ws.cell(row=1, column=c, value=h)
            k.font = Font(name=font, bold=True, color="FFFFFF")
            k.fill = PatternFill("solid", start_color="1F4E78")
            k.alignment = Alignment(wrap_text=True, vertical="center")
        for i, wiersz in enumerate(dane, start=2):
            for c, v in enumerate(wiersz, start=1):
                k = ws.cell(row=i, column=c, value=v)
                k.font = Font(name=font)
                k.alignment = Alignment(wrap_text=True, vertical="top")
        for c, s in enumerate(szerokosci, start=1):
            ws.column_dimensions[ws.cell(row=1, column=c).column_letter].width = s
        ws.freeze_panes = "B2"
        ws.auto_filter.ref = ws.dimensions

    ws = wb.active
    ws.title = "Reguły"
    arkusz(
        ws,
        ["Akceptuję", "ID", "Typ", "Warianty", "Warunek", "Przewidywanie", "Zmienne", "Dni", "Moc",
         "Pewność interpretacji", "Interpretacja", "Uwagi / decyzje", "Pominięte lata", "Twoje uwagi"],
        [
            [True, w["id"], w["typ"], "\n".join(w["warianty"]), w["warunek"], w["przewidywanie"], w["zmienne"],
             w["dni"], w["moc"], w["pewnosc"], w["interpretacja"], "\n".join(f"• {u}" for u in w["uwagi"]),
             ", ".join(map(str, w["pominiete_lata"])) or None, None]
            for w in wiersze
        ],
        [11, 30, 11, 45, 40, 45, 16, 8, 12, 12, 40, 60, 14, 30],
    )
    for row in ws.iter_rows(min_row=2, max_col=1):
        row[0].alignment = Alignment(horizontal="center", vertical="top")

    arkusz(
        wb.create_sheet("Słownik"),
        ["Określenie ludowe", "Zjawisko", "Definicja pomiarowa", "Zmienna", "Pewność", "Uzasadnienie określenia",
         "Uzasadnienie definicji", "Twoje uwagi"],
        [
            [s["tekst"], s["zjawisko"], opis_zjawiska(slownik, s["zjawisko"]),
             slownik["zjawisko"][s["zjawisko"]]["zmienna"], s["pewnosc"], s["uzasadnienie"],
             slownik["zjawisko"][s["zjawisko"]]["uzasadnienie"], None]
            for s in slownik["slowo"]
        ],
        [28, 22, 45, 16, 10, 55, 60, 30],
    )
    arkusz(
        wb.create_sheet("Kalendarz"),
        ["Klucz", "Termin", "Data", "Źródło", "Uwagi", "Twoje uwagi"],
        [
            [k, w["nazwa"], w.get("data") or "ruchome", w["zrodlo"], w.get("uwagi"), None]
            for k, w in kal.wpisy.items()
        ],
        [18, 28, 10, 60, 60, 30],
    )
    wb.save(sciezka)


# ------------------------------------------------------------------ main

def main() -> None:
    kal, slownik, reguly, przyslowia = wczytaj()
    bledy = waliduj(kal, slownik, reguly, przyslowia)
    if bledy:
        print(f"BŁĘDY WALIDACJI ({len(bledy)}):")
        for b in bledy:
            print("  -", b)
        raise SystemExit(1)
    print(f"Walidacja OK: {len(reguly)} reguł, {len(slownik['slowo'])} określeń, {len(kal.wpisy)} terminów")

    wiersze = zestawienie(kal, slownik, reguly)
    print()
    for w in wiersze:
        print(f"{w['id']:40s} dni={w['dni']:7s} moc={w['moc']:14s} zmienne={w['zmienne']}")
        if w["pominiete_lata"]:
            print(f"{'':40s} pominięte lata: {w['pominiete_lata']}")

    testowalne = {t for t, p in przyslowia.items() if p["kategoria"] in TYPY}
    pokryte = {w for r in reguly for w in r["warianty"]}
    print(f"\nPokrycie: {len(pokryte)} z {len(testowalne)} przysłów (warunkowe/dzien/od_dnia/okres)")

    sciezka = DATA_DIR / "reguly_przeglad.xlsx"
    eksportuj_xlsx(wiersze, kal, slownik, sciezka)
    print(f"Zapisano {sciezka}")


if __name__ == "__main__":
    main()
