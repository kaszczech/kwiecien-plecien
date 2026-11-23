"""Ręczna selekcja przysłów pogodowych z pełnej listy (data/przyslowia_wszystkie.json).

Każde przysłowie pogodowe dostaje jedną kategorię:

  warunkowe - JEŚLI pogoda w danym dniu/miesiącu jest taka, TO później będzie taka
              ("gdy w Michała deszcz spadnie, lekka zima"). Test: czy warunek coś przewiduje.
  dzien     - jaka pogoda jest w konkretnym dniu (lub kilku dniach), bez warunku
              ("na dzień świętej Doroty ma być śniega nad płoty", zimni ogrodnicy).
              Test: w ilu latach tego dnia się zgadzało.
  od_dnia   - od danego dnia zmienia się pora roku / pogoda
              ("na świętego Grzegorza zima idzie do morza", "od świętej Anki zimne poranki").
              Test: czy w danych widać przełom w okolicy tej daty.
  okres     - cały miesiąc lub okres bez konkretnego dnia ("kwiecień plecień", "luty w lód okuty").
              Test: statystyka miesiąca na tle innych.
  urodzaj   - pogoda => plony / gospodarka. Nie da się sprawdzić samymi danymi pogodowymi.
  przyroda  - zwierzęta i rośliny jako zwiastun pogody lub pory roku
              (bociany, jaskółki, żołędzie...). Wymagałoby danych fenologicznych.

Pominięte świadomie: przysłowia astronomiczne ("na Tomasza najdłuższa noc"),
metafory ("kto sieje wiatr, ten zbiera burzę") i czysto rolnicze bez pogody.

Wynik: data/przyslowia_pogodowe.json oraz data/przyslowia_pogodowe.csv
"""
import csv
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"

WEATHER_PROVERBS: dict[str, list[str]] = {
    "warunkowe": [
        "Adam i Ewa pokazują, jaki styczeń i luty po nich następują",
        "Barbara po wodzie, Boże Narodzenie po lodzie",
        "Bartłomiej zwiastuje, jaka jesień następuje",
        "bój się w styczniu wiosny, bo marzec zazdrosny",
        "Boże Narodzenie po wodzie, Wielkanoc po lodzie",
        "co marzec wypiecze, to kwiecień wysiecze",
        "czerwiec po deszczowym maju często dżdżysty w naszym kraju",
        "czerwiec stały, grudzień doskonały",
        "deszcz na świętego Błażeja, słaba wiosny nadzieja",
        "deszcze Michałowe prawią w zimie powietrze zdrowe",
        "deszcze na lipca pierwszego, drugiego, zapowiedzią deszczu czterdziestodniowego",
        "do Michała przymrozków ile, i w maju tyle",
        "gdy bez wiatrów luty chodzi, w kwietniu wicher nie zawodzi",
        "gdy ciepło w lutym, zimno w marcu bywa, długo trwa zima, to jest niewątpliwa",
        "gdy deszcz w świętego Michała, będzie łagodna zima cała",
        "gdy Franciszka z wichrem po polu hasa, może sypnąć śniegiem powyżej pasa",
        "gdy Halina łąki zrosi, rolnik w wodzie siano kosi",
        "gdy Katarzyna kurzy, wszystka się radość zburzy",
        "gdy mróz w lutym ostro trzyma, tedy jest niedługa zima",
        "gdy na Małgorzaty mróz, jeszcze długo nie pojedzie wóz",
        "gdy na świętą Barbarę gęś chodzi po lodzie, to Boże Narodzenie będzie po wodzie",
        "gdy na świętą Barbarę mróz, sanie na górę włóż, a szykuj dobry wóz",
        "gdy na świętego Prota jest pogoda albo słota, to na świętego Hieronima jest deszcz albo go ni ma",
        "gdy na święty Walek deszcze, mrozy wrócą jeszcze",
        "gdy na Walka są deszcze, będzie ostry mróz jeszcze",
        "gdy na Wincentego i nawrócenie Pawła pogoda świeci, spodziewajcie się dobrego lata, dzieci",
        "gdy noc jasna na Michała, to nastąpi zima trwała",
        "gdy październik ciepło trzyma, zwykle mroźna bywa zima",
        "gdy słońce przygrzewa na Jana Dobrego, spodziewać się można lata pogodnego",
        "gdy styczeń z zimnem nie chodzi, marzec, kwiecień wychłodzi",
        "gdy święta Agata po błocie brodzi, człek w Zmartwychwstanie po lodzie chodzi",
        "gdy święty Andrzej ze śniegiem przybieży, sto dni śnieg na polu leży",
        "gdy Święty Maciej zimę poprawia, to Oblubieniec mrozy zostawia",
        "gdy Trzej Królowie ciepłem darzą, gospodarze o wiośnie gwarzą",
        "gdy w Andrzeja deszcz lub słota, w grudniu drogi bez błota",
        "gdy w Katarzynę lód nie stanie – szykuj sanie, gdy w Katarzynę mróz – szykuj wóz",
        "gdy w Katarzynę zima, śnieg nie poleży, mróz nie potrzyma",
        "gdy w lipcu słońce dopieka, burza niedaleka",
        "gdy w Michała deszcz spadnie, lekka zima będzie snadnie",
        "gdy w Michała wiatr od wschodu lub północy, w zimie mrozy wielkiej mocy",
        "gdy w świętą Barbarę gęś chodzi po lodzie, to Boże Narodzenie będzie po wodzie",
        "gdy w świętą Barbarę gęś po stawie chodzi, w Boże Narodzenie pływać po nim się godzi",
        "gdy w świętą Barbarę ostre mrozy, to na zimę gotuj wozy; a gdy roztajanie, każ opatrzyć sanie",
        "gdy Wawrzyniec i Bartłomiej pogodą dopisują, piękną jesień obiecują",
        "gdy wietrzno w Michała, będzie mroźna zima cała",
        "gdy Zuzanna z pogodą chadza, piękną jesień przyprowadza",
        "im na Krzysztofa większe pogody, tym zimą sroższe nastaną lody",
        "jak na Matkę Gromniczną, tak na święty Józef",
        "jak na święty Maciej ciepło, to się będzie długo wlekło",
        "jak się Katarzyna głosi, tak się Nowy Rok nosi",
        "jak śnieg w świętego Błażeja, pogodna będzie Wielka Niedziela",
        "jak styczeń zachlapany, to lipiec zapłakany",
        "jak święta Agnieszka wypuści śnieg z mieszka, to go nie powstrzyma ani do Franciszka",
        "jaka Gromniczna bracie, taki Święty Maciej",
        "jaka Małgorzatka, takie będzie pół latka",
        "jaki Bartek, taki wrzesień, jaki Marcin, taka zima",
        "jaki dzień Bartłomieja, takiej jesieni nadzieja",
        "jaki Michał, taka wiosna",
        "jakie Zwiastowanie, takie Zmartwychwstanie",
        "jeśli deszcz na Michała, zima będzie nietrwała",
        "jeśli upały w sianokosy i żniwa, to zima ostra i dokuczliwa, a jeżeli słota, to w zimie dużo błota",
        "jeśli w dzień świętego Michała wiatr północny wieje, to na pogodę nie miejmy nadzieję",
        "jeżeli ciepło w dzień świętego Piotra, to zima do Wielkiejnocy potrwa",
        "jeżeli święty Michał deszczem przysłuży, to suchą wiosnę nam wróży",
        "Katarzyny dzień jaki, cały grudzień będzie taki",
        "Katarzyny dzień jaki, cały grudzień taki",
        "kiedy Gromniczna zimę traci, to święty Maciej ją wzbogaci",
        "kiedy Jerzy pogodą częstuje, wnet się pogoda zepsuje",
        "kiedy luty puści, to marzec wypiecze",
        "kiedy na Michała wiatr północny wieje, na ładną pogodę chłop traci nadzieję",
        "kiedy na świętą Łucję mróz, to smaruj wóz",
        "kiedy w świętą Barbarę mróz, to chłopie sanie na górę włóż",
        "kiedy w świętą Barbarę mróz, to szukaj chłopie dobry wóz",
        "kiedy w świętą Barbarę mróz, to szykuj chłopie dobry wóz",
        "kiedy w świętą Katarzynę lód nie stanie, to gotuj sanie",
        "miękko na Andrzeja, oj! niedobra nadzieja",
        "miękko na Jędrzeja, oj! niedobra nadzieja",
        "na Adama pięknie, zima prędko pęknie",
        "na Katarzynę gęś po wodzie, Boże Narodzenie po lodzie",
        "na świętego Walentego bywa zwykle mróz niczego, lecz jak Walek się rozdeszcze, pewne mrozy wrócą jeszcze",
        "na święty Maciej lody wróżą długie chłody, a gdy płyną już strugą, to i zimy niedługo",
        "na Urbana chwile jakie, i lato takie",
        "na Urbana chwile jakie, mówią, że i lato takie",
        "noc jasna na Michała, zima ostra i trwała, gdy noc słotna, zima do końca grudnia lekka i błotna",
        "Nowy Rok jaki, cały rok taki",
        "pogoda na świętego Błażeja, dobra wiosny nadzieja",
        "słota w dzień Adama i Ewy, zabezpiecz od zimna cholewy",
        "styczeń bywa łagodny, gdy październik śnieżny i chłodny",
        "święta Barbara po lodzie, Boże Narodzenie po wodzie",
        "święta Barbara po wodzie, Boże Narodzenie po lodzie",
        "święta Katarzyna po lodzie, Boże Narodzenie po wodzie",
        "święta Katarzyna po wodzie, Boże Narodzenie po lodzie",
        "święta Katarzyna pokazuje, jaką pogodę nam styczeń zgotuje",
        "święta Łucja głosi, jaką pogodę styczeń przynosi",
        "święto Barbary po wodzie, Boże Narodzenie po lodzie",
        "święty Bartłomiej pogodny, jesień pogodna",
        "upały lipcowe wróżą mrozy styczniowe",
        "Urszula jaka, cała zima taka",
        "w dzień świętej Agaty, jeśli słonko przez okienko zajrzy do chaty, to wiosenka na świat podgląda zza zimowej kraty",
        "w Katarzynę z nieba nic nie spadnie, będzie w przyszłym lutym chyba jeszcze ładniej",
        "w lutym gdy zagrzmi od wschodniego boku, burze i wiatry walne są w tym roku",
        "w Narodzenie Panny Marii pogodnie, będzie tak cztery tygodnie",
        "w styczniu grzmoty, częste słoty",
        "Wawrzyniec pokazuje, jaka jesień następuje",
    ],
    "dzien": [
        "na dzień świętej Doroty ma być śniega nad płoty",
        "na Katarzynę schowaj się pod pierzynę",
        "na świętą Agatę wysuszysz na słońcu szmatę",
        "na świętą Agnieszkę wychodzi woda na ścieżkę",
        "na świętego Andrzeja trza kożucha dobrodzieja",
        "na świętego Franciszka nieraz dobrze grzmi i łyska",
        "na świętego Hieronima jest pogoda albo jej ni ma",
        "na święty Józef czasem śniegu wózek",
        "o świętej Dorocie pójdziesz po błocie",
        "Pankracy, Serwacy i Bonifacy – źli na ogrody chłopacy",
        "Pankracy, Serwacy, Bonifacy i Zośka to zimni święci",
        "Pankracy, Serwacy, Bonifacy, każdy swoim zimnem raczy",
        "rzadki dzień świętej Doroty bez mrozu, zawiei, słoty",
        "święta Agata w zimę bogata",
        "święta Dorota suszy chusty u płota",
        "święta Dorota! wyratuj z błota",
        "święta Jagna taje bagna",
        "świętej Agaty uschną szmaty",
        "świętej Agnieszki uschną pieluszki; świętej Agaty uschną i szmaty",
        "święty Józek wiezie trawy wózek, ale czasem smuci, bo śniegiem przyrzuci",
        "w dzień Trzech Króli każdy się do pieca tuli",
        "w święto Trzech Króli człek się w kożuch tuli",
    ],
    "od_dnia": [
        "gromnica – zimy połowica",
        "kiedy Paweł się nawróci, zima na wspak się odwróci",
        "na świętą Barbarę dobądź ze skrzyni czamarę",
        "na świętą Barbarę wyciągnij z kąta czamarę",
        "na świętą Katarzynę szykuj ciepłą pierzynę",
        "na świętego Grzegorza idą rzeki do morza",
        "na świętego Grzegorza idzie zima do morza",
        "na świętego Grzegorza zima idzie do morza",
        "na świętego Kazimierza zima do morza zmierza",
        "na świętego Macieja prędzej wiosny nadzieja",
        "na świętego Pawła połowa zimy przepadła",
        "na świętej Katarzyny szykuj babo pierzyny",
        "o świętej Katarzynie pomyśl o pierzynie",
        "od Grzegorza zima idzie do morza",
        "od świętej Anki chłodne wieczory, poranki",
        "od świętej Anki zimne poranki",
        "od świętej Anki zimne wieczory i ranki",
        "od świętej Anny nie doczeka południa deszcz poranny",
        "od świętej Hanki zimne poranki",
        "od świętej Hanki zimne wieczory i ranki",
        "od świętej Katarzyny szukaj pierzyny",
        "po świętej Agacie wyschną na słońcu gacie",
        "po świętej Agacie wyschnie bielizna na płocie",
        "po świętej Agnieszce napije się wół na ścieżce",
        "po świętej Dorocie wieszaj chusty na płocie",
        "po świętej Dorocie wyschną chusty na płocie",
        "po świętej Katarzynie pomyśl o pierzynie",
        "po świętym Tadeuszu trzeba chodzić w kapeluszu",
        "po Urbanie lato nastanie",
        "przed Pankracym nie ma lata, po Bonifacym mróz ulata",
        "święta Hanna to już jesienna panna",
        "święta Małgorzata zapowiada środek lata",
        "święty Ambroży zimy przysporzy",
        "święty Józef kiwnie brodą, idzie zimno na dół z wodą",
        "w dzień Agaty to dopiero pół zimy rogatej",
        "ze świętą Małgorzatą upał przybiera, kanikułę otwiera",
    ],
    "okres": [
        "choć już w kwietniu słonko grzeje, nieraz pole śnieg zawieje",
        "czasem luty ostro kuty, czasem w luty same pluty",
        "czasem luty się zlituje, że człek niby wiosnę czuje; ale czasem tak się zżyma, że człek prawie nie wytrzyma",
        "grudzień – łudzień",
        "idzie luty, podkuj buty",
        "jeśli ci jeszcze nie dokuczył luty, to pal dobrze w kominie i miej kożuch suty",
        "kiedy luty schodzi, człek po wodzie brodzi",
        "kiedy luty, obuj buty",
        "kwiecień plecień, bo przeplata trochę zimy, trochę lata",
        "kwiecień plecień, bo przeplata: trochę zimy, trochę lata",
        "luty w lód okuty",
        "luty, napije się wół pluty",
        "na stycznie i lute trzeba mieć konie kute",
        "na wiosnę ceber deszczu, łyżka błota; na jesieni łyżka deszczu, ceber błota",
        "spyta cię luty: maszli buty?",
        "w marcu jak w garncu",
    ],
    "urodzaj": [
        "deszcz na świętą Małgorzatę jest orzechom na stratę",
        "deszcze częste w kwietniu wróżą, że owoców będzie dużo",
        "gdy deszcz w świętego Urbana, mały profit z winobrania",
        "gdy na święty Paweł jasno, po żniwach też będzie ciasno",
        "gdy na święty Paweł jasno, po żniwach w stodole ciasno",
        "gdy się grzmot w lipcu od południa poda, drzewom się znaczy szwank i nieuroda",
        "gdy w styczniu deszcz leje, złe robi nadzieje",
        "Gromniczna pogodna, będzie jesień dorodna",
        "grzmoty czerwca rozweselają rolnikom serca",
        "jak w świętą Annę deszcz pada, to robak orzechy zjada",
        "jak w Wiliję gwiazdy świecą, kury dobrze jajka niesą",
        "jeśli w święty Paweł śnieg albo deszcz pada, dobrych się urodzajów spodziewać wypada",
        "jeżeli na Świętego Kazimierza pogoda, to na kartofle uroda",
        "kiedy styczeń najostrzejszy, wtedy roczek najpłodniejszy",
        "kiedy w Małgorzatę kropi, siano się źle kopi",
        "kwiecień, co deszczem rosi, wiele owoców przynosi",
        "mokry czerwiec, chłodny maj – wszystkim gburom prawy raj",
        "na święty Jerzy rosa, nie trzeba koniom owsa",
        "na święty Józef gdy płyną wody, na święty Wojciech rznij trawę dla trzody",
        "na święty Józef pogoda, będzie w polu uroda",
        "Oblubieniec pogodny, rok będzie urodny",
        "Rok Nowy pogodny, zbiór będzie dorodny",
        "styczeń pogodny wróży rok płodny",
        "święty Józef pogodny, będzie roczek urodny",
        "w lutym wody wiele – w lecie głodne nawet cielę",
        "w lutym wody wiele, w lecie głodne i cielę",
        "w świętą Małgorzatę skąd wiatr duje, drogę po zboże toruje",
    ],
    "przyroda": [
        "Agnieszka łaskawa puszcza skowronka z rękawa",
        "gdy na Michała obrodzą żołędzie, dużo śniegów w zimie będzie",
        "gdy na święty Jerzy jeszcze nie rozkwita, niech się cieszy stary, młody, chłop i kobieta",
        "gdy na święty Józef bociek przybędzie, to już śniegu nie będzie",
        "gdy na Wawrzyńca orzechy obrodzą, to w zimie mrozy dogodzą",
        "gdy pająk w lipcu przychodzi, to za sobą deszcz przywodzi, gdy swą pajęczynę snuje, bliską burzę czuje",
        "gdy przyjdzie Agnieszka, rozbije ogonem lód pliszka",
        "gdy przyjdzie święta Agnieszka, przebije lód ogonem pliszka",
        "jak drozdy śpiewają na wierzchołkach drzew, wiosna wnet; a jak między gałęziami, to jeszcze het",
        "jak na święty Józef bocian przyleci, to na skrzydłach resztki śniegu przynosi",
        "jak pszczółki na wiosnę z ula wcześnie wylatują, to pewnie mróz na drzewa w maju nam zwiastują",
        "jaskółka i pszczółka lata, znakiem wiosny to dla świata",
        "jeśli bociany do Michała zostały, nie będzie mrozów przez grudzień cały",
        "jeśli nie odlecą ptaszki do Michała, do Wigilii zima nie nastąpi trwała",
        "jeżeli pszczoła w styczniu z ula wylatuje, rzadko pomyślny rok nam obiecuje",
        "kiedy ptaki w styczniu śpiewają, to im w maju dzioby zamarzają",
        "kiedy się jaskółka zniża, deszcz się do nas zbliża",
        "na świętą Annę mrowiska, szukaj w zimie ogniska",
        "na świętego Franciszka odlatuje pliszka",
        "na świętego Franciszka przylatuje pliszka",
        "na świętego Franciszka zielenią się łany i ze swego zimowiska wracają bociany",
        "na świętego Macieja zniesie gęś pierwsze jejca",
        "na święty Maciej skowronek zapiej",
        "na święty Wojciech zniesie jajko bociek",
        "na świętej Agaty wychodzą muchy zza łaty",
        "święta Agnieszka wypuściła skowronka z mieszka",
        "święta Agnieszka wypuszcza skowronka z mieszka",
    ],
}


# Przysłowia odrzucone, choć dotyczą słońca, deszczu, pór roku lub kalendarza – z uzasadnieniem.
# Pozostałe odrzucone nie mają związku z pogodą (powód: "brak związku z pogodą").
EXCLUDED_BORDERLINE: dict[str, str] = {
    # astronomia: długość dnia zależy od położenia Ziemi, nie od pogody
    "na Nowy Rok przybywa dnia na barani skok": "astronomia (długość dnia)",
    "na święty Tomasz dzień się z nocą sili, mniej nocy, więcej dnia będzie po chwili": "astronomia (długość dnia)",
    "na Tomasza najdłuższa noc nasza": "astronomia (długość dnia)",
    "po świętej Łucji dzień trwa najkrócej": "astronomia (długość dnia)",
    "święta Łucja dnia przyrzuca": "astronomia (długość dnia)",
    "święto Łucji dzień króci": "astronomia (długość dnia)",
    "święto Łucy noc króci": "astronomia (długość dnia)",
    # metafory – słownictwo pogodowe, ale znaczenie przenośne
    "chłop się nie przeżegna, dopóki piorunu nie usłyszy": "metafora",
    "jedna jaskółka nie czyni wiosny": "metafora",
    "jedna jaskółka wiosny nie czyni": "metafora",
    "kto sieje wiatr, ten zbiera burzę": "metafora",
    "kto wiatr sieje, zbiera burzę": "metafora",
    "nie chwal dnia przed zachodem słońca": "metafora",
    "nim słońce wzejdzie, rosa oczy wyje": "metafora",
    "z dużej chmury będzie mały deszcz": "metafora",
    "z dużej chmury mały deszcz": "metafora",
    "człowiek strzela, a wiatr kule nosi": "metafora",
    "biednemu zawsze wiatr w oczy": "metafora",
    "kto latem pracuje, zimą głodu nie czuje": "metafora (o pracowitości)",
    "kto w lipcu patrzy chłodu, nacierpi się w zimie głodu": "metafora (o pracowitości)",
    # zdrowie / obyczaj – pogoda najwyżej pośrednio
    "gdzie nie zagląda słońce, tam zagląda lekarz": "zdrowie, nie prognoza pogody",
    "święty Błażej gardła zagrzej": "zdrowie (Błażej – patron chorób gardła), chłód tylko pośrednio",
    "gdy przyjdzie marzec, umrze niejeden starzec": "zdrowie (przednówek), nie pogoda",
    "do panny Katarzyny nowych butów obłóczyny": "obyczaj, chłód tylko pośrednio",
    # kalendarz prac polowych bez stwierdzenia o pogodzie
    "kto sieje jęczmień na Urbana, będzie pił piwo ze dzbana": "kalendarz prac polowych, bez pogody",
    "w Urbana, miły chłopie, siej len i konopie": "kalendarz prac polowych, bez pogody",
    "na świętego Franciszka chłop w polu nic nie zyska": "kalendarz prac polowych, bez pogody",
    "na święty Dominik, kopy z pola mig, mig": "kalendarz prac polowych, bez pogody",
    "na święty Wawrzyniec, wolny przez pola gościniec": "kalendarz prac polowych, bez pogody",
    "na świętego Wawrzyna śpieszą do młyna": "kalendarz prac polowych, bez pogody",
    "w święto Wawrzyńca śpieszą do młyńca": "kalendarz prac polowych, bez pogody",
    "na świętą Małgorzatę kopa zawsze w polu stanie": "kalendarz prac polowych, bez pogody",
    "w dzień świętej Małgorzaty pierwsze gruszki do chaty": "kalendarz prac polowych, bez pogody",
    "w lipcu się już kłosek korzy, że niesie dar Boży, a najpierwsza Małgorzata sierp w zboże założy":
        "kalendarz prac polowych, bez pogody",
    "czerwiec – przerwiec, bo przerywa gospodarkę aż do żniwa": "kalendarz prac polowych, bez pogody",
    "czerwiec się czerwieni? Będzie dość w kieszeni": "kalendarz prac polowych, bez pogody",
    "na święty Jerzy nie trzeba koniom owsa": "kalendarz prac polowych, bez pogody",
    "od świętej Katarzyny nie wyganiaj już żywiny": "kalendarz prac polowych, chłód tylko pośrednio",
    "od świętej Katarzyny nie prześladuj już zwierzyny": "kalendarz łowiecki, bez pogody",
    "na świętego Franciszka szuka ziarnek w polu myszka": "zachowanie zwierząt bez związku z pogodą",
    "po świętym Pawle i Pietrze muchy tłuste jak wieprze": "zachowanie zwierząt bez związku z pogodą",
    "święta Agata chatę wymiata": "obyczaj, bez pogody",
}


def main() -> None:
    all_proverbs = json.loads((DATA_DIR / "przyslowia_wszystkie.json").read_text(encoding="utf-8"))
    by_title = {p["tytul"]: p for p in all_proverbs}

    selected = []
    missing = []
    seen = set()
    for category, texts in WEATHER_PROVERBS.items():
        for text in texts:
            if text in seen:
                raise ValueError(f"Duplikat w klasyfikacji: {text!r}")
            seen.add(text)
            if text not in by_title:
                missing.append(text)
                continue
            selected.append({**by_title[text], "kategoria": category})

    for text in EXCLUDED_BORDERLINE:
        if text in seen:
            raise ValueError(f"Przysłowie jednocześnie wybrane i odrzucone: {text!r}")
        if text not in by_title:
            missing.append(text)

    if missing:
        raise ValueError("Teksty nieznalezione w pełnej liście:\n  " + "\n  ".join(missing))

    excluded = [
        {**p, "powod": EXCLUDED_BORDERLINE.get(p["tytul"], "brak związku z pogodą")}
        for p in all_proverbs
        if p["tytul"] not in seen
    ]
    if len(selected) + len(excluded) != len(all_proverbs):
        raise ValueError("Suma wybranych i odrzuconych nie zgadza się z pełną listą")
    (DATA_DIR / "przyslowia_pominiete.json").write_text(
        json.dumps(excluded, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    selected.sort(key=lambda p: (list(WEATHER_PROVERBS).index(p["kategoria"]), p["tytul"].lower()))

    (DATA_DIR / "przyslowia_pogodowe.json").write_text(
        json.dumps(selected, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    with open(DATA_DIR / "przyslowia_pogodowe.csv", "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["kategoria", "tytul", "url", "pageid", "lastrevid"])
        writer.writeheader()
        writer.writerows(selected)

    print(f"Pogodowych: {len(selected)} z {len(all_proverbs)}")
    for category in WEATHER_PROVERBS:
        print(f"  {category:9s} {sum(p['kategoria'] == category for p in selected)}")
    print(f"Pominiętych: {len(excluded)} (w tym graniczne z uzasadnieniem: {len(EXCLUDED_BORDERLINE)})")


if __name__ == "__main__":
    main()
