from app.core.i18n import _TRANSLATIONS, SUPPORTED_LOCALES, load_translations, t


def test_locales_load():
    load_translations()
    for lang in SUPPORTED_LOCALES:
        assert lang in _TRANSLATIONS
        assert len(_TRANSLATIONS[lang]) > 0


def test_i18n_translation():
    uz_welcome = t("uz", "welcome", name="Alisher")
    assert "Alisher" in uz_welcome
    assert "KITOBXON AI" in uz_welcome

    ru_welcome = t("ru", "welcome", name="Алишер")
    assert "Алишер" in ru_welcome
    assert "KITOBXON AI" in ru_welcome

    en_welcome = t("en", "welcome", name="Alisher")
    assert "Alisher" in en_welcome
    assert "KITOBXON AI" in en_welcome


def test_i18n_keys_parity():
    load_translations()
    uz_data = _TRANSLATIONS["uz"]
    ru_data = _TRANSLATIONS["ru"]
    en_data = _TRANSLATIONS["en"]

    def extract_keys(d, prefix=""):
        keys = set()
        for k, v in d.items():
            full = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                keys.update(extract_keys(v, full))
            else:
                keys.add(full)
        return keys

    uz_keys = extract_keys(uz_data)
    ru_keys = extract_keys(ru_data)
    en_keys = extract_keys(en_data)

    missing_in_ru = uz_keys - ru_keys
    missing_in_en = uz_keys - en_keys

    assert not missing_in_ru, f"Missing keys in ru.json: {missing_in_ru}"
    assert not missing_in_en, f"Missing keys in en.json: {missing_in_en}"
