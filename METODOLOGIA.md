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

Wyjątek (decyzja autora, 2026-11-24): warianty opisujące **to samo zjawisko** różniące się jedynie
zakresem dni lub akcentem mogą zostać połączone, jeśli autor tak zdecyduje; decyzja jest wtedy
zapisana w `uwagi` reguły i w rozdz. 6 (np. zimni ogrodnicy).

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

### 3.10 Przesunięcie terminów (parametr, 2026-11-24)
Przysłowia bywały używane dzień czy dwa przed lub po święcie, a część może pochodzić z kalendarza
juliańskiego (rozdz. 5). Dlatego przesunięcie terminów jest **parametrem analizy**
(`rules.py --przesuniecie DNI`, zakres ±30 dni, domyślnie 0):
- przesuwane są **wszystkie terminy z kalendarza** (`kalendarz.toml`: święta stałe i ruchome),
  w warunku i w przewidywaniu o tyle samo – zachowany jest odstęp między nimi;
- **nie** są przesuwane granice miesięcy i pór roku („MM-DD”, „MM-koniec”, „koniec_pory_roku”):
  „grudzień” czy „zima” to okresy klimatyczne, a nie dni przysłowia;
- pora roku dla „koniec_pory_roku” wynika z daty **nieprzesuniętej** (Grzegorz −13 dni = 27 II,
  ale okno nadal trwa do końca wiosny, 31 V);
- przesunięty termin może przejść przez Nowy Rok (Boże Narodzenie +10 = 4 I).

Wynik główny raportujemy dla przesunięcia 0. Inne przesunięcia służą analizie wrażliwości: czy
trafność przysłowia zależy od dokładnego dnia. Uwaga: przeszukanie wielu przesunięć i wybór
najlepszego to wielokrotne testowanie – raportujemy cały profil (trafność dla każdego przesunięcia),
nie tylko maksimum, a ewentualny wybór najlepszego przesunięcia wymaga korekty istotności.

### 3.11 Tolerancja okna warunku (parametr, 2026-11-24)
Nie zawsze wiadomo, czy przysłowie mówi dokładnie o dniu święta, czy o „okolicy” (np. dzień
św. Barbary i dzień po nim). Dlatego okno warunku można rozszerzyć parametrami
`--tolerancja-przed DNI` i `--tolerancja-po DNI` (0–7, domyślnie 0):
- rozszerzane są tylko te końce okna warunku, które są terminami z kalendarza (Barbara po=1
  → 4–5 XII); warunki-miesiące (październik) i okna przewidywania – **nie**;
- najpierw stosowane jest przesunięcie (3.10), potem tolerancja;
- warunek progowy lub tercylowy jest **spełniony, jeśli spełnia go którykolwiek dzień** okna
  z tolerancją. To jest równoważne „bierzemy najlepiej pasujący dzień”: najlepiej pasujący dzień
  spełnia warunek wtedy i tylko wtedy, gdy spełnia go którykolwiek dzień;
- to wyjątek od zasady agregacji z 3.2: tolerancja wyraża niepewność, **który** dzień jest
  właściwy, a nie twierdzenie o całym okresie;
- warunki „jaki X, taki Y” (grupa, stan dowolny) **nie podlegają tolerancji** – zawsze tylko dzień
  święta (decyzja autora, 2026-11-24). Powód: nie ma czego dopasować, a wybór „najlepiej pasującego
  dnia” musiałby patrzeć na wynik przewidywania, co zawyżałoby trafność. Odrzucona alternatywa:
  stan warunku = wartość zagregowana z okna z tolerancją;
- lata, w których okno przewidywania zaczyna się w oknie warunku z tolerancją lub przed nim,
  są pomijane (3.9). (Zwiastowanie to reguła „jaki X, taki Y”, więc tolerancja go nie zmienia.)

Wpływ na ocenę: szerszy warunek jest spełniony w większej liczbie lat, ale nie zmienia
częstości przewidywanego zjawiska, z którą porównujemy wynik – nie zawyża więc trafności sam
z siebie. Jak przy przesunięciu: wynik główny dla tolerancji 0, inne wartości jako profil
wrażliwości, bez wybierania najlepszej bez korekty na wielokrotne testowanie.

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
  więc daty mogą być przesunięte o ok. 10 dni (od 1700 r. o 11, od 1900 r. o 13). Narzędzie:
  parametr przesunięcia (rozdz. 3.10); zakres przesunięć do analizy – do ustalenia.
- Wybór zbioru danych (kandydat: dane synoptyczne IMGW-PIB) i stacji.
- Potwierdzenie kryterium „intensywne opady śniegu” w aktualnym dokumencie IMGW-PIB (rozdz. 6.2).
- Czy zbiór danych zawiera wysokość świeżo spadłego śniegu, czy trzeba liczyć przyrost pokrywy.

## 6. Decyzje z przeglądu pilotażu (2026-11-24)

### 6.1 Zimni ogrodnicy – jedna reguła, „załamanie pogody”
Trzy reguły (12–14 V chłodniej, 12–15 V chłodniej, 12–14 V przymrozek) połączone w jedną
`zimni_ogrodnicy`, okno 12–15 V. Przysłowie twierdzi, że następuje **załamanie pogody**:
- miara: średnia anomalia Tśr w oknie (względem wygładzonej normy sezonowej) minus średnia
  anomalia z 7 dni przed oknem (5–11 V);
- „załamanie” = dolny tercyl rozkładu tej różnicy dla wszystkich okien 4-dniowych w IV–VI
  w okresie normy;
- punkt odniesienia: losowe okno 4-dniowe spełnia warunek w ok. 1/3 przypadków, więc przysłowie
  jest prawdziwe, jeśli 12–15 V spełnia go istotnie częściej;
- przymrozek nie jest warunkiem – raportowany dodatkowo, opisowo.

Uzasadnienie: porównanie z poprzedzającym tygodniem mierzy to, o czym mówi tradycja (nagły powrót
zimna), a nie samo „chłodno jak na maj”; dodatkowo odporne na błąd normy w danym roku.

### 6.2 Św. Dorota – intensywne opady śniegu
„Śniega nad płoty” = mocne opady śniegu 6 II, a nie grubość pokrywy (dosłowny sens, > 1 m, na nizinach
nie występuje). Definicja: przyrost pokrywy ≥ 15 cm w ciągu doby – kryterium ostrzeżenia IMGW-PIB
„intensywne opady śniegu”, stopień 1, sezon zimowy (15–20 cm / 24 h; 10–15 cm / 12 h).
Próg wzięty ze standardu zewnętrznego, a nie dobrany do danych. Analiza wrażliwości: 10 cm.
Źródło kryterium: „Klasyfikacja stopni groźnych zjawisk meteorologiczno-hydrologicznych”
(kopia: powiatprudnicki.pl/download/attachment/29592/…, bez daty) – **do potwierdzenia** na imgw.pl.

### 6.3 Kwiecień plecień – zostaje jako test klimatyczny
Rozważano usunięcie reguły jako trudnej do sprawdzenia. Decyzja: zostaje w obecnej formie
(rozdz. 3.8) – jednorazowy test, czy zmienność temperatury z dnia na dzień (|ΔTśr|) jest w kwietniu
największa ze wszystkich miesięcy. Nie daje prognoz na konkretne dni.
