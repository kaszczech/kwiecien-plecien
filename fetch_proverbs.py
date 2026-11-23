"""Pobiera wszystkie hasła z kategorii 'Kategoria:Polskie przysłowia' z pl.wiktionary.org.

Korzysta z MediaWiki API (generator=categorymembers + prop=info), które zwraca do 500 pozycji
na zapytanie i obsługuje paginację przez parametr 'continue'. Dla każdego hasła zapisujemy
identyfikator rewizji (lastrevid), żeby dało się odtworzyć dokładnie ten stan Wikisłownika.

Wynik:
  data/przyslowia_wszystkie.json  - lista haseł (tytuł, pageid, lastrevid, url)
  data/przyslowia_wszystkie.txt   - same tytuły, po jednym w wierszu
  data/pobranie_meta.json         - data i parametry pobrania
"""
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API_URL = "https://pl.wiktionary.org/w/api.php"
CATEGORY = "Kategoria:Polskie przysłowia"
USER_AGENT = "przyslowiaPogoda/0.1 (research project; python-urllib)"
DATA_DIR = Path(__file__).parent / "data"

# Kolejność polskiego alfabetu – do sortowania wyników (API przy generatorze nie gwarantuje kolejności)
_PL_ALPHABET = "aąbcćdeęfghijklłmnńoóprsśtuvwxyzźż"
_PL_ORDER = {ch: i for i, ch in enumerate(_PL_ALPHABET)}


def pl_sort_key(text: str) -> list[tuple[int, str]]:
    return [(_PL_ORDER.get(ch, len(_PL_ALPHABET)), ch) for ch in text.lower()]


def api_get(params: dict) -> dict:
    url = API_URL + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_category_pages(category: str) -> list[dict]:
    params = {
        "action": "query",
        "generator": "categorymembers",
        "gcmtitle": category,
        "gcmlimit": "500",
        "gcmtype": "page",
        "gcmnamespace": "0",  # tylko hasła główne (bez stron 'Aneks:')
        "prop": "info",
        "format": "json",
        "formatversion": "2",
    }
    pages: dict[int, dict] = {}
    while True:
        data = api_get(params)
        for p in data.get("query", {}).get("pages", []):
            pages[p["pageid"]] = p
        print(f"Pobrano razem {len(pages)}")
        if "continue" not in data:
            break
        params.update(data["continue"])
        time.sleep(0.5)  # grzecznie wobec serwera
    return list(pages.values())


def main() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    pages = fetch_category_pages(CATEGORY)
    proverbs = sorted(
        (
            {
                "tytul": p["title"],
                "pageid": p["pageid"],
                "lastrevid": p["lastrevid"],
                "url": "https://pl.wiktionary.org/wiki/" + urllib.parse.quote(p["title"].replace(" ", "_")),
            }
            for p in pages
        ),
        key=lambda p: pl_sort_key(p["tytul"]),
    )
    if len({p["tytul"] for p in proverbs}) != len(proverbs):
        raise ValueError("Zduplikowane tytuły w odpowiedzi API")

    (DATA_DIR / "przyslowia_wszystkie.json").write_text(
        json.dumps(proverbs, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (DATA_DIR / "przyslowia_wszystkie.txt").write_text(
        "\n".join(p["tytul"] for p in proverbs) + "\n", encoding="utf-8"
    )
    meta = {
        "zrodlo": API_URL,
        "kategoria": CATEGORY,
        "pobrano_utc": fetched_at,
        "liczba_hasel": len(proverbs),
        "uwagi": "lastrevid w przyslowia_wszystkie.json pozwala odtworzyć dokładną wersję każdego hasła "
                 "(https://pl.wiktionary.org/w/index.php?oldid=<lastrevid>)",
    }
    (DATA_DIR / "pobranie_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Zapisano {len(proverbs)} przysłów do {DATA_DIR}")


if __name__ == "__main__":
    main()
