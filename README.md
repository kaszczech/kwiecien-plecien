# Przysłowia pogodowe

Czy polskie przysłowia pogodowe sprawdzają się w rzeczywistych danych meteorologicznych?
Projekt zamienia przysłowia na formalne, sprawdzalne reguły i porównuje je z danymi
z ostatnich dziesięcioleci.

Wszystkie decyzje metodologiczne (klasyfikacja, interpretacja ludowych określeń, okna czasowe,
norma klimatyczna) są opisane w [METODOLOGIA.md](METODOLOGIA.md).

## Etapy

| Etap | Stan |
|------|------|
| 1. Pobranie przysłów z Wikisłownika | gotowe (1064 hasła) |
| 2. Wybór i klasyfikacja przysłów pogodowych | gotowe (232, przejrzane) |
| 3. Formalizacja reguł | pilotaż: 10 reguł / 22 przysłowia |
| 4. Dane meteorologiczne i norma | do zrobienia |
| 5. Weryfikacja reguł | do zrobienia |

## Struktura

```
fetch_proverbs.py            pobiera Kategoria:Polskie przysłowia (MediaWiki API)
select_weather_proverbs.py   ręczna klasyfikacja + walidacja względem źródła
export_review.py             arkusz do przeglądu klasyfikacji (data/przeglad.xlsx)
rules.py                     walidacja reguł, liczba dni, moc, eksport do przeglądu
reguly/kalendarz.toml        terminy (święta) ze źródłem daty
reguly/slownik.toml          mierzalne zjawiska + ludowe określenia z uzasadnieniem
reguly/reguly.toml           reguły
data/                        pobrane dane, wyniki klasyfikacji, arkusze przeglądu
```

## Uruchomienie

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe rules.py
```

Pełne odtworzenie od zera (kolejno): `fetch_proverbs.py` → `select_weather_proverbs.py` →
`export_review.py` → `rules.py`. Uwaga: `fetch_proverbs.py` pobiera aktualny stan Wikisłownika,
który mógł się zmienić od daty zapisanej w `data/pobranie_meta.json`.

## Licencja danych

Teksty przysłów pochodzą z [Wikisłownika](https://pl.wiktionary.org/wiki/Kategoria:Polskie_przys%C5%82owia)
i są dostępne na licencji [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/deed.pl).
Każde hasło w `data/` ma link do źródła i numer rewizji (`lastrevid`).
