"""Wczytuje, waliduje i opisuje reguły przysłów pogodowych.

Pliki wejściowe:
  reguly/kalendarz.toml  - terminy (święta, daty) używane w przysłowiach
  reguly/slownik.toml    - zjawiska mierzalne i ludowe określenia
  reguly/reguly.toml     - reguły
  data/przyslowia_pogodowe.json - przysłowia z kategoriami

Walidacja przerywa działanie przy pierwszej grupie błędów (lista wszystkich znalezionych).
Wynik: raport w konsoli + data/reguly_przeglad.xlsx do przeglądu.

Uruchomienie:
  python rules.py                      walidacja + eksport arkusza przeglądu
  python rules.py --rok 2024           dodatkowo konkretne daty okien w 2024 r.
  python rules.py --przesuniecie -2    wszystkie terminy przysłów 2 dni wcześniej
  python rules.py --tolerancja-po 1    warunek sprawdzany w dniu święta i dzień po nim
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
RODZAJE = {"zdarzenie", "anomalia", "porownanie_okresow", "zmiana_wzgledem_poprzedzajacych"}
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


MAX_PRZESUNIECIE = 30  # dni; większe przesunięcie zmieniałoby porę roku, a nie „dzień czy dwa”
MAX_TOLERANCJA = 7     # dni; tolerancja ma oddawać niepewność „który dzień”, nie zamieniać dnia w okres


@dataclass
class Kalendarz:
    """Terminy z kalendarz.toml.

    przesuniecie - liczba dni (ujemna = wcześniej), o którą przesuwane są WSZYSTKIE terminy
    z kalendarza (święta stałe i ruchome), w warunku i w przewidywaniu jednakowo.
    Daty literalne ("MM-DD", "MM-koniec") i "koniec_pory_roku" NIE są przesuwane: oznaczają
    granice miesięcy i pór roku, a nie dni przysłów (METODOLOGIA 3.10).

    tolerancja_przed / tolerancja_po - o ile dni rozszerzyć OKNO WARUNKU przed jego początkiem /
    po jego końcu, jeśli ten koniec okna jest terminem z kalendarza (np. Barbara, po=1 -> 4–5 XII).
    Warunek jest spełniony, jeśli spełnia go którykolwiek dzień rozszerzonego okna (METODOLOGIA 3.11).
    Okno przewidywania nie jest rozszerzane."""
    wpisy: dict
    przesuniecie: int = 0
    tolerancja_przed: int = 0
    tolerancja_po: int = 0

    def __post_init__(self) -> None:
        if (not isinstance(self.przesuniecie, int) or isinstance(self.przesuniecie, bool)
                or abs(self.przesuniecie) > MAX_PRZESUNIECIE):
            raise ValueError(f"przesunięcie musi być liczbą całkowitą z zakresu ±{MAX_PRZESUNIECIE} dni, "
                             f"podano {self.przesuniecie!r}")
        for nazwa in ("tolerancja_przed", "tolerancja_po"):
            t = getattr(self, nazwa)
            if not isinstance(t, int) or isinstance(t, bool) or not 0 <= t <= MAX_TOLERANCJA:
                raise ValueError(f"{nazwa.replace('_', ' ')} musi być liczbą całkowitą z zakresu "
                                 f"0–{MAX_TOLERANCJA} dni, podano {t!r}")

    @property
    def parametry_domyslne(self) -> bool:
        return self.przesuniecie == 0 and self.tolerancja_przed == 0 and self.tolerancja_po == 0

    def czy_przesuwany(self, token: str) -> bool:
        return token in self.wpisy

    def czy_token(self, token: str) -> bool:
        return (token in self.wpisy or bool(RE_DATA.match(token)) or bool(RE_KONIEC.match(token))
                or token == "koniec_pory_roku")

    def czy_ruchomy(self, token: str) -> bool:
        return token in self.wpisy and "ruchome" in self.wpisy[token]

    def w_roku(self, token: str, rok: int, przesun: bool = True) -> date:
        """Data tokenu dla roku 'rok' (święto ruchome: liczone dla tego roku).
        Termin z kalendarza jest przesuwany o self.przesuniecie (chyba że przesun=False),
        więc wynik może wypaść w sąsiednim roku kalendarzowym."""
        if token in self.wpisy:
            w = self.wpisy[token]
            baza = RUCHOME[w["ruchome"]](rok) if "ruchome" in w else self.w_roku(w["data"], rok)
            return baza + timedelta(days=self.przesuniecie if przesun else 0)
        if m := RE_DATA.match(token):
            return date(rok, int(m[1]), int(m[2]))
        if m := RE_KONIEC.match(token):
            mies = int(m[1])
            return date(rok, mies, monthrange(rok, mies)[1])
        raise ValueError(f"Nieznany token daty: {token!r}")

    def pierwsze_od(self, token: str, kotwica: date, scisle_po: bool) -> date | None:
        """Pierwsze wystąpienie tokenu w dniu kotwicy lub później (albo ściśle po).
        Dla świąt ruchomych tylko wystąpienie z roku kotwicy – inaczej None (rok pomijany).
        Sprawdzany jest też rok poprzedni, bo przesunięty termin może przejść przez Nowy Rok."""
        lata = [kotwica.year] if self.czy_ruchomy(token) else [kotwica.year - 1, kotwica.year, kotwica.year + 1]
        kandydaci = [d for d in (self.w_roku(token, r) for r in lata)
                     if (d > kotwica if scisle_po else d >= kotwica)]
        return min(kandydaci, default=None)

    def okno(self, okno: dict, kotwica: date, scisle_po: bool = False) -> tuple[date, date] | None:
        start = self.pierwsze_od(okno["od"], kotwica, scisle_po)
        if start is None:
            return None
        if okno["do"] == "koniec_pory_roku":
            # Pora roku wynika z NIEPRZESUNIĘTEJ daty terminu: przesunięcie zmienia dzień przysłowia,
            # a nie to, o której porze roku przysłowie mówi.
            baza = start - timedelta(days=self.przesuniecie) if self.czy_przesuwany(okno["od"]) else start
            koniec = koniec_pory_roku(baza)
            return (start, koniec) if start <= koniec else None
        koniec = self.pierwsze_od(okno["do"], start, scisle_po=False)
        if koniec is None:
            return None
        return start, koniec

    def okno_warunku(self, okno: dict, kotwica: date) -> tuple[date, date] | None:
        """Okno warunku rozszerzone o tolerancję po stronie terminów z kalendarza.
        Granice miesięcy ("10-01" – "10-koniec") nie są rozszerzane."""
        o = self.okno(okno, kotwica)
        if o is None:
            return None
        start, koniec = o
        if self.czy_przesuwany(okno["od"]):
            start -= timedelta(days=self.tolerancja_przed)
        if self.czy_przesuwany(okno["do"]):
            koniec += timedelta(days=self.tolerancja_po)
        return start, koniec

    def opis_tokenu(self, token: str) -> str:
        if token == "koniec_pory_roku":
            return "koniec pory roku"
        if token in self.wpisy:
            w = self.wpisy[token]
            p = f" {self.przesuniecie:+d} dni" if self.przesuniecie else ""
            if "ruchome" in w:
                return f"{w['nazwa']} (święto ruchome{p})"
            mies, dz = map(int, w["data"].split("-"))
            return f"{w['nazwa']} ({dz} {RZYMSKIE[mies]}{p})"
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

def wczytaj(przesuniecie: int = 0, tolerancja_przed: int = 0,
            tolerancja_po: int = 0) -> tuple[Kalendarz, dict, list[dict], dict[str, dict]]:
    kal = Kalendarz(tomllib.loads((RULES_DIR / "kalendarz.toml").read_text(encoding="utf-8")),
                    przesuniecie, tolerancja_przed, tolerancja_po)
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
        if z.get("rodzaj") in ("anomalia", "zmiana_wzgledem_poprzedzajacych") and z.get("klasa") not in KLASY:
            bledy.append(f"{p}: {z['rodzaj']} wymaga 'klasa' z {sorted(KLASY)}")
        if z.get("rodzaj") == "zmiana_wzgledem_poprzedzajacych":
            n = z.get("dni_odniesienia")
            if not isinstance(n, int) or isinstance(n, bool) or n < 1:
                bledy.append(f"{p}: zmiana_wzgledem_poprzedzajacych wymaga 'dni_odniesienia' (liczba dni ≥ 1)")
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
            okno_w = kal.okno_warunku(r["warunek"]["okno"], date(rok, 1, 1))
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
    if z["rodzaj"] == "zmiana_wzgledem_poprzedzajacych":
        klasa = {"ponizej": "spadek", "w_normie": "bez zmiany", "powyzej": "wzrost"}[z["klasa"]]
        return (f"{klasa} anomalii ({w['opis']}) względem {z['dni_odniesienia']} dni przed oknem "
                f"(tercyl rozkładu takich zmian)")
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

RECZNE_KOLUMNY = ("Akceptuję", "Twoje uwagi")  # wypełniane przez recenzenta, przenoszone między eksportami


def wczytaj_reczne_kolumny(sciezka: Path) -> dict[str, dict[str, dict[str, object]]]:
    """{arkusz: {klucz wiersza: {kolumna: wartość}}} z poprzedniego eksportu.
    Kluczem jest ID reguły (Reguły) albo pierwsza kolumna (Słownik, Kalendarz)."""
    if not sciezka.exists():
        return {}
    from openpyxl import load_workbook

    wb = load_workbook(sciezka)
    wynik: dict[str, dict[str, dict[str, object]]] = {}
    for ws in wb.worksheets:
        naglowki = [c.value for c in ws[1]]
        kol_klucza = naglowki.index("ID") if "ID" in naglowki else 0
        reczne = [naglowki.index(n) for n in RECZNE_KOLUMNY if n in naglowki]
        arkusz: dict[str, dict[str, object]] = {}
        for wiersz in ws.iter_rows(min_row=2, values_only=True):
            if wiersz[kol_klucza] is None:
                continue
            arkusz[str(wiersz[kol_klucza])] = {naglowki[i]: wiersz[i] for i in reczne}
        wynik[ws.title] = arkusz
    return wynik


def eksportuj_xlsx(wiersze: list[dict], kal: Kalendarz, slownik: dict, sciezka: Path) -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill

    font = "Arial"
    poprzednie = wczytaj_reczne_kolumny(sciezka)
    wb = Workbook()

    def arkusz(ws, naglowki, dane, szerokosci):
        # Przeniesienie ręcznych znaczników z poprzedniej wersji pliku (po kluczu wiersza).
        stare = poprzednie.get(ws.title, {})
        kol_klucza = naglowki.index("ID") if "ID" in naglowki else 0
        obecne = set()
        for wiersz in dane:
            klucz = str(wiersz[kol_klucza])
            obecne.add(klucz)
            for nazwa, wartosc in stare.get(klucz, {}).items():
                if nazwa in naglowki:
                    wiersz[naglowki.index(nazwa)] = wartosc
        utracone = [k for k, v in stare.items()
                    if k not in obecne and v.get("Twoje uwagi") not in (None, "")]
        for k in utracone:
            print(f"UWAGA: arkusz {ws.title!r}: wiersz {k!r} z Twoją uwagą już nie istnieje: "
                  f"{stare[k]['Twoje uwagi']!r}")
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

def okna_w_roku(kal: Kalendarz, r: dict, rok: int) -> list[str]:
    """Konkretne daty okien reguły dla jednego roku (do kontroli wzrokowej)."""
    def fmt(o: tuple[date, date] | None) -> str:
        if o is None:
            return "rok pominięty"
        return o[0].isoformat() if o[0] == o[1] else f"{o[0].isoformat()} – {o[1].isoformat()}"

    wynik = []
    okno_w = kal.okno_warunku(r["warunek"]["okno"], date(rok, 1, 1)) if "warunek" in r else None
    if "warunek" in r:
        wynik.append(f"warunek: {fmt(okno_w)}")
    for pr in r["przewidywanie"]:
        if "warunek" in r:
            okno_p = kal.okno(pr["okno"], okno_w[1], scisle_po=True) if okno_w else None
        else:
            okno_p = kal.okno(pr["okno"], date(rok, 1, 1))
        wynik.append(f"przewidywanie: {fmt(okno_p)}")
    return wynik


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--przesuniecie", type=int, default=0, metavar="DNI",
                        help=f"przesuń wszystkie terminy z kalendarza o DNI (ujemne = wcześniej, "
                             f"max ±{MAX_PRZESUNIECIE}); granice miesięcy i pór roku bez zmian")
    parser.add_argument("--tolerancja-przed", type=int, default=0, metavar="DNI",
                        help=f"rozszerz okno warunku o DNI dni przed terminem z kalendarza (0–{MAX_TOLERANCJA})")
    parser.add_argument("--tolerancja-po", type=int, default=0, metavar="DNI",
                        help=f"rozszerz okno warunku o DNI dni po terminie z kalendarza (0–{MAX_TOLERANCJA})")
    parser.add_argument("--rok", type=int, metavar="RRRR",
                        help="pokaż konkretne daty okien każdej reguły w danym roku")
    args = parser.parse_args()
    try:
        kal, slownik, reguly, przyslowia = wczytaj(args.przesuniecie, args.tolerancja_przed, args.tolerancja_po)
    except ValueError as e:
        parser.error(str(e))
    if kal.przesuniecie:
        print(f"PRZESUNIĘCIE TERMINÓW: {kal.przesuniecie:+d} dni")
    if kal.tolerancja_przed or kal.tolerancja_po:
        print(f"TOLERANCJA WARUNKU: {kal.tolerancja_przed} dni przed, {kal.tolerancja_po} dni po terminie")
    if not kal.parametry_domyslne:
        print()
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

    if args.rok:
        print(f"\nOkna w roku {args.rok} (warunek liczony od 1 I {args.rok}):")
        for r in reguly:
            print(f"  {r['id']:40s} " + "; ".join(okna_w_roku(kal, r, args.rok)))

    testowalne = {t for t, p in przyslowia.items() if p["kategoria"] in TYPY}
    pokryte = {w for r in reguly for w in r["warianty"]}
    print(f"\nPokrycie: {len(pokryte)} z {len(testowalne)} przysłów (warunkowe/dzien/od_dnia/okres)")

    if not kal.parametry_domyslne:
        # Arkusz przeglądu opisuje definicje reguł, które nie zależą od przesunięcia ani tolerancji.
        print("Arkusz przeglądu jest zapisywany tylko przy domyślnych parametrach (przesunięcie i tolerancja 0).")
        return
    sciezka = DATA_DIR / "reguly_przeglad.xlsx"
    eksportuj_xlsx(wiersze, kal, slownik, sciezka)
    print(f"Zapisano {sciezka}")


if __name__ == "__main__":
    main()
