import re
import unicodedata

UZ_LATIN_TO_CYRILLIC = {
    "o'": "ў", "oʻ": "ў", "o‘": "ў", "o`": "ў",
    "g'": "ғ", "gʻ": "ғ", "g‘": "ғ", "g`": "ғ",
    "sh": "ш", "ch": "ч", "yo": "ё", "yu": "ю", "ya": "я", "ye": "е",
    "O'": "Ў", "Oʻ": "Ў", "O‘": "Ў", "O`": "Ў",
    "G'": "Ғ", "Gʻ": "Ғ", "G‘": "Ғ", "G`": "Ғ",
    "Sh": "Ш", "Ch": "Ч", "Yo": "Ё", "Yu": "Ю", "Ya": "Я", "Ye": "Е",
    "a": "а", "b": "б", "d": "д", "e": "е", "f": "ф", "g": "г",
    "h": "ҳ", "i": "и", "j": "ж", "k": "к", "l": "л", "m": "м",
    "n": "н", "o": "о", "p": "п", "q": "қ", "r": "р", "s": "с",
    "t": "т", "u": "у", "v": "в", "x": "х", "y": "й", "z": "з",
    "A": "А", "B": "Б", "D": "Д", "E": "Е", "F": "Ф", "G": "Г",
    "H": "Ҳ", "I": "И", "J": "Ж", "K": "К", "L": "Л", "M": "М",
    "N": "Н", "O": "О", "P": "П", "Q": "Қ", "R": "Р", "S": "С",
    "T": "Т", "U": "У", "V": "В", "X": "Х", "Y": "Й", "Z": "З",
}

UZ_CYRILLIC_TO_LATIN = {
    "ў": "o'", "ғ": "g'", "ш": "sh", "ч": "ch", "ё": "yo", "ю": "yu", "я": "ya",
    "Ў": "O'", "Ғ": "G'", "Ш": "Sh", "Ч": "Ch", "Ё": "Yo", "Ю": "Yu", "Я": "Ya",
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ж": "j",
    "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n",
    "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f",
    "х": "x", "ҳ": "h", "ц": "ts", "ы": "i", "э": "e", "қ": "q",
    "А": "A", "Б": "B", "В": "V", "Г": "G", "Д": "D", "Е": "E", "Ж": "J",
    "З": "Z", "И": "I", "Й": "Y", "К": "K", "Л": "L", "М": "M", "Н": "N",
    "О": "O", "П": "P", "Р": "R", "С": "S", "Т": "T", "У": "U", "Ф": "F",
    "Х": "X", "Ҳ": "H", "Ц": "Ts", "Ы": "I", "Э": "E", "Қ": "Q",
    "ъ": "'", "ь": "", "Ъ": "'", "Ь": "",
}


def latin_to_cyrillic(text: str) -> str:
    """Convert Uzbek Latin text to Uzbek Cyrillic."""
    res = text
    # Replace compound characters first
    for lat, cyr in sorted(UZ_LATIN_TO_CYRILLIC.items(), key=lambda x: len(x[0]), reverse=True):
        res = res.replace(lat, cyr)
    return res


def cyrillic_to_latin(text: str) -> str:
    """Convert Uzbek Cyrillic text to Uzbek Latin."""
    res = text
    for cyr, lat in sorted(UZ_CYRILLIC_TO_LATIN.items(), key=lambda x: len(x[0]), reverse=True):
        res = res.replace(cyr, lat)
    return res


def normalize_query(query: str) -> str:
    """Normalize search query: standard apostrophes, trim whitespace, normalize unicode."""
    if not query:
        return ""
    q = unicodedata.normalize("NFKC", query)
    # Standardize all apostrophe varieties to standard single quote
    q = re.sub(r"[ʻ’`‘´‛′]", "'", q)
    q = re.sub(r"\s+", " ", q).strip()
    return q
