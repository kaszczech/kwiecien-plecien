# Metodologia – przysłowia pogodowe

Dziennik decyzji metodologicznych. Każda decyzja ma datę i uzasadnienie, żeby analizę dało się
odtworzyć i ocenić.

## 1. Źródło przysłów

- Źródło: pl.wiktionary.org, `Kategoria:Polskie przysłowia`, pobrane przez MediaWiki API
  (`fetch_proverbs.py`). Data pobrania i numery rewizji haseł: `data/pobranie_meta.json`,
  `data/przyslowia_wszystkie.json` (`lastrevid`).
- Wynik: 1064 hasła (tylko przestrzeń główna, bez stron „Aneks:”).

## 2. Selekcja i klasyfikacja (2026-11-23)

Ręczna klasyfikacja wszystkich 1064 haseł (`select_weather_proverbs.py`), przejrzana przez autora
projektu (`data/przeglad.xlsx`), bez poprawek.

| Kategoria  | Liczba | Znaczenie |
|------------|-------:|-----------|
| warunkowe  | 104 | JEŚLI pogoda w terminie A, TO pogoda w terminie B |
| dzien      | 22  | pogoda w konkretnym dniu (dniach), bez warunku |
| od_dnia    | 36  | od danego dnia zmienia się pora roku / pogoda |
| okres      | 16  | cały miesiąc lub okres, bez konkretnego dnia |
| urodzaj    | 27  | pogoda → plony; **odłożone** (nietestowalne danymi pogodowymi) |
| przyroda   | 27  | zwierzęta/rośliny jako znak; **odłożone** (wymaga danych fenologicznych) |
| pominięte  | 832 | bez związku z pogodą; 42 przypadki graniczne mają zapisany powód |

## 3. Reguły (2026-11-23)

### 3.1 Grupowanie wariantów
Warianty przysłowia o **identycznym znaczeniu** (te same terminy, te same zjawiska, ten sam kierunek)
tworzą jedną regułę. Warianty różniące się terminem lub kierunkiem to **osobne reguły**
(np. „Barbara po wodzie → Boże Narodzenie po lodzie” i „Barbara po lodzie → Boże Narodzenie
po wodzie”). Dzięki temu jedna myśl nie liczy się wielokrotnie w statystyce.

### 3.2 Przewidywanie dotyczy każdego dnia okna
Przewidywanie reguły to stwierdzenie o **każdym dniu** okna przewidywania, osobno dla każdej
zmiennej (temperatura, opad, pokrywa śnieżna, wiatr, zachmurzenie, burza).
„Łagodna zima” = każdy dzień XII–II ma temperaturę powyżej normy dla tego dnia.

Warunek obejmujący więcej niż jeden dzień (np. „październik ciepło trzyma”) jest oceniany na
**wartości zagregowanej okna** (średnia / suma okresu względem normy tego okresu).

### 3.3 Moc reguły
`moc = 1 / liczba dni okna przewidywania` (liczy się okno, którego dotyczy przewidywanie,
nie okno warunku). Moc służy **wyłącznie do szeregowania** reguł dotyczących tego samego dnia
i tej samej zmiennej; nie jest wagą w obliczeniach.

### 3.4 Remisy i wiele reguł na ten sam dzień
**Żadna reguła nie jest wykluczana.** Wszystkie reguły aktywne dla danego dnia są zachowywane
i raportowane – mogą się wzajemnie wzmacniać albo sobie przeczyć. Sposób łączenia
(np. wybór po mocy) zostanie ustalony później, po przygotowaniu wszystkich reguł.

### 3.5 Okna czasowe
- Pory roku meteorologiczne: zima XII–II, wiosna III–V, lato VI–VIII, jesień IX–XI.
- Miesiąc = rzeczywista liczba dni (luty 28/29), rok = 365 dni.
- Święto = jeden dzień (np. Boże Narodzenie = 25 XII).
- Święta ruchome (Wielkanoc) – data liczona osobno dla każdego roku (kalendarz gregoriański).
- Okno przewidywania to **pierwsze wystąpienie** danego okresu zaczynające się w dniu warunku
  lub po nim (np. Michał 29 IX → najbliższa zima XII–II).
- Reguły „od dnia” bez podanego końca: okno trwa **do końca bieżącej pory roku meteorologicznej**.

### 3.6 Słownik pojęć
Każde ludowe określenie („po wodzie”, „słota”, „łagodna zima”) jest przypisane do mierzalnego
zjawiska z uzasadnieniem (`reguly/slownik.toml`). Tam, gdzie to możliwe, używane są definicje
klimatologiczne IMGW (dzień mroźny, przymrozek, dzień z opadem, pokrywa śnieżna).

### 3.7 Norma klimatyczna i anomalie
- Okres normy: 1991–2020 (standard WMO).
- Anomalie w trzech klasach (tercyle): poniżej normy / w normie / powyżej normy. Każda klasa
  zdarza się w 1/3 przypadków, co daje punkt odniesienia (zgadywanie = 33%).
- Norma dobowa = **wygładzona krzywa sezonowa** (np. kilka harmonicznych), a nie surowa średnia
  z danego dnia kalendarzowego. Powód: przysłowia typu „dzień” twierdzą, że konkretne dni są
  nietypowe (zimni ogrodnicy). Gdyby norma była liczona osobno dla 12 V, ewentualny chłodny
  epizod wszedłby do normy tego dnia i test stałby się tautologią. Szczegóły – na etapie danych.

### 3.8 Twierdzenia o klimacie
Część przysłów nie mówi o konkretnym roku, tylko o klimacie („kwiecień plecień” = kwiecień jest
zmienniejszy niż inne miesiące). Porównanie z normą samego kwietnia byłoby tautologią, więc są
one testowane raz, na całym zbiorze, przez porównanie okresów (rodzaj `porownanie_okresow`).
Nie dają rekomendacji na konkretne dni i nie biorą udziału w szeregowaniu po mocy.

### 3.9 Lata, w których reguła nie ma sensu
Jeśli okno przewidywania wypadałoby przed oknem warunku (np. Wielkanoc przed 25 III dla
„jakie Zwiastowanie, takie Zmartwychwstanie”), rok jest pomijany dla tej reguły i odnotowany
w raporcie (`rules.py`).

## 4. Implementacja reguł

- `reguly/kalendarz.toml` – terminy ze źródłem daty,
- `reguly/slownik.toml` – zjawiska mierzalne + ludowe określenia z uzasadnieniem i pewnością,
- `reguly/reguly.toml` – reguły,
- `rules.py` – walidacja (m.in. czy każdy wariant istnieje w źródle i ma zgodną kategorię,
  czy każde ludowe określenie faktycznie występuje w tekście wariantu, czy wariant nie jest
  w dwóch regułach), liczba dni i moc, eksport do `data/reguly_przeglad.xlsx`.
- **Trend klimatyczny**: anomalie liczone względem trendu, aby ocieplenie nie tworzyło
  fałszywych korelacji. Metoda – do ustalenia na etapie danych.

## 5. Otwarte kwestie

- Kalendarz juliański: część przysłów może pochodzić sprzed reformy gregoriańskiej (1582),
  więc daty mogą być przesunięte o ok. 10 dni. Do rozważenia analiza wrażliwości (± dni).
- Wybór zbioru danych (kandydat: dane synoptyczne IMGW-PIB) i stacji.
