from app.utils.translit import (
    cyrillic_to_latin,
    latin_to_cyrillic,
    normalize_query,
)


def test_uzbek_transliteration():
    # Latin to Cyrillic
    lat_text = "O'tkan kunlar Abdulla Qodiriy"
    cyr = latin_to_cyrillic(lat_text)
    assert "Ў" in cyr or "ў" in cyr
    assert "Қодирий" in cyr

    # Cyrillic to Latin
    lat_back = cyrillic_to_latin(cyr)
    assert "O'tkan" in lat_back or "o'tkan" in lat_back.lower()
    assert "Qodiriy" in lat_back or "qodiriy" in lat_back.lower()


def test_query_normalization():
    query = "  O‘tkan    kunlar   "
    normalized = normalize_query(query)
    assert normalized == "O'tkan kunlar"

    # Variations of apostrophes
    assert normalize_query("Gʻafur Gʻulom") == "G'afur G'ulom"
    assert normalize_query("O`tkir Hoshimov") == "O'tkir Hoshimov"
