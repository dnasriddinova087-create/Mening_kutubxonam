import html
import re

from app.core.i18n import t
from app.schemas.book import BookDTO


def escape_html(text: str | None) -> str:
    """Escapes HTML characters for Telegram HTML parse mode."""
    if not text:
        return ""
    return html.escape(str(text))


def clean_html_tags(text: str | None) -> str:
    """Remove raw HTML tags returned by external APIs like Google Books."""
    if not text:
        return ""
    # Strip HTML tags
    clean = re.sub(r"<[^>]+>", "", text)
    # Unescape HTML entities
    clean = html.unescape(clean)
    # Normalize whitespaces
    return re.sub(r"\s+", " ", clean).strip()


def truncate_text(text: str, max_length: int = 1000, suffix: str = "...") -> str:
    """Safely truncate text to max_length respecting word boundaries."""
    if len(text) <= max_length:
        return text
    truncated = text[: max_length - len(suffix)]
    last_space = truncated.rfind(" ")
    if last_space > 0:
        truncated = truncated[:last_space]
    return truncated + suffix


def format_book_caption(book: BookDTO, lang: str = "uz") -> str:
    """Format a compact, beautiful book card suitable for Telegram photo caption (<= 1024 chars)."""
    title_escaped = escape_html(book.title)
    authors_escaped = escape_html(book.authors_display)

    code_str = f" [#{book.code}]" if book.code else ""
    lines = [
        f"📚 <b>{title_escaped}</b>{code_str}",
        f"✍️ <b>{t(lang, 'book.authors', authors=authors_escaped)}</b>",
    ]

    meta_parts = []
    if book.code:
        meta_parts.append(f"🆔 Kod: <b>#{book.code}</b>")
    if book.published_date:
        meta_parts.append(f"📅 {escape_html(book.published_date[:4])}")
    if book.publisher:
        meta_parts.append(f"🏢 {escape_html(truncate_text(book.publisher, 25))}")
    if book.language:
        meta_parts.append(f"🌐 {escape_html(book.language.upper())}")

    if meta_parts:
        lines.append(" | ".join(meta_parts))

    if book.genres:
        lines.append(f"🏷️ <i>{escape_html(', '.join(book.genres[:3]))}</i>")

    media_badges = []
    if getattr(book, "audio_url", None):
        media_badges.append("🎧 Audiokitob")
    if getattr(book, "video_url", None):
        media_badges.append("🎬 Video sharh")
    if getattr(book, "file_url", None):
        fmt = getattr(book, "file_format", "PDF") or "PDF"
        media_badges.append(f"📥 {fmt}")
    if media_badges:
        lines.append("⚡ " + " • ".join(media_badges))

    lines.append("")

    # Clean description
    raw_desc = clean_html_tags(book.description or "")
    if raw_desc:
        short_desc = truncate_text(raw_desc, 300)
        lines.append(f"📖 <b>{t(lang, 'book.about_header')}</b>\n{escape_html(short_desc)}")
    else:
        lines.append(f"📖 <i>{t(lang, 'book.no_description')}</i>")

    if book.access_type:
        access_label = t(lang, f"book.access_{book.access_type}")
        lines.append(f"\n{access_label}")

    result = "\n".join(lines)
    # Ensure strict adherence to Telegram caption limit of 1024
    if len(result) > 1000:
        return truncate_text(result, 1000)
    return result


def format_book_details(book: BookDTO, lang: str = "uz") -> str:
    """Format full detailed message of the book (<= 4096 chars)."""
    title_escaped = escape_html(book.title)
    authors_escaped = escape_html(book.authors_display)

    code_str = f" [#{book.code}]" if book.code else ""
    lines = [
        f"📚 <b>{title_escaped}</b>{code_str}",
        "",
        f"✍️ {t(lang, 'book.authors', authors=authors_escaped)}",
    ]

    if book.code:
        lines.append(f"🆔 <b>Kitob kodi:</b> <code>#{book.code}</code> (Qidiruv kodi)")
    if book.published_date:
        lines.append(f"📅 {t(lang, 'book.year', year=escape_html(book.published_date))}")
    if book.publisher:
        lines.append(f"🏢 {t(lang, 'book.publisher', publisher=escape_html(book.publisher))}")
    if book.isbn:
        lines.append(f"🔢 {t(lang, 'book.isbn', isbn=escape_html(book.isbn))}")
    if getattr(book, "pages", None):
        lines.append(f"📄 <b>Sahifalar soni:</b> {book.pages} bet")
    if book.genres:
        lines.append(f"🏷️ {t(lang, 'book.genres', genres=escape_html(', '.join(book.genres)))}")
    if book.language:
        lines.append(f"🌐 {t(lang, 'book.language', language=escape_html(book.language.upper()))}")
    lines.append(f"🏛️ {t(lang, 'book.source', source=escape_html(book.source.replace('_', ' ').title()))}")

    # Media materials block
    media_lines = []
    if getattr(book, "audio_url", None):
        duration = f" ({book.audio_duration})" if getattr(book, "audio_duration", None) else ""
        media_lines.append(f"🎧 <a href=\"{escape_html(book.audio_url)}\"><b>Audiokitobni tinglash</b></a>{duration}")
    if getattr(book, "video_url", None):
        media_lines.append(f"🎬 <a href=\"{escape_html(book.video_url)}\"><b>Video sharhni tomosha qilish</b></a>")
    if getattr(book, "file_url", None):
        fmt = getattr(book, "file_format", "PDF") or "PDF"
        media_lines.append(f"📥 <a href=\"{escape_html(book.file_url)}\"><b>Elektron kitobni yuklab olish ({fmt})</b></a>")
    if media_lines:
        lines.append("")
        lines.append("⚡ <b>Multimedia va elektron materiallar:</b>")
        lines.extend(media_lines)

    lines.append("")
    lines.append(f"📖 <b>{t(lang, 'book.about_header')}</b>")
    raw_desc = clean_html_tags(book.description or "")
    if raw_desc:
        lines.append(escape_html(truncate_text(raw_desc, 1800)))
    else:
        lines.append(f"<i>{t(lang, 'book.no_description')}</i>")

    if book.source_url:
        lines.append("")
        lines.append(f"🌐 <a href=\"{escape_html(book.source_url)}\">{t(lang, 'book.reading_sources_header')}</a>")

    result = "\n".join(lines)
    return truncate_text(result, 4000)
