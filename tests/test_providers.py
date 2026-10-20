from app.providers.google_books import GoogleBooksProvider
from app.providers.open_library import OpenLibraryProvider


def test_google_books_parsing():
    provider = GoogleBooksProvider()

    raw_item = {
        "id": "test_id_123",
        "volumeInfo": {
            "title": "Clean Code",
            "authors": ["Robert C. Martin"],
            "publishedDate": "2008-08-01",
            "description": "A Handbook of Agile Software Craftsmanship",
            "industryIdentifiers": [
                {"type": "ISBN_10", "identifier": "0132350882"},
                {"type": "ISBN_13", "identifier": "9780132350884"},
            ],
            "categories": ["Computers / Programming"],
            "imageLinks": {
                "thumbnail": "http://books.google.com/books/content?id=test&printsec=frontcover&img=1"
            },
            "previewLink": "http://books.google.com/books?id=test",
        },
        "accessInfo": {
            "accessViewStatus": "SAMPLE",
            "publicDomain": False,
        },
        "saleInfo": {
            "saleability": "FOR_SALE",
            "buyLink": "https://play.google.com/store/books/details?id=test",
        },
    }

    dto = provider._parse_volume(raw_item)
    assert dto is not None
    assert dto.title == "Clean Code"
    assert dto.authors == ["Robert C. Martin"]
    assert dto.isbn == "9780132350884"
    assert dto.access_type == "preview"
    # Ensure http is upgraded to https for image
    assert dto.cover_url.startswith("https://")


def test_open_library_parsing():
    provider = OpenLibraryProvider()

    raw_doc = {
        "key": "/works/OL45883W",
        "title": "Fantastic Mr Fox",
        "author_name": ["Roald Dahl"],
        "first_publish_year": 1970,
        "isbn": ["9780140328721"],
        "subject": ["Children's stories", "Foxes"],
        "cover_i": 8225261,
        "has_fulltext": True,
        "lending_edition_s": "OL24199925M",
    }

    dto = provider._parse_doc(raw_doc)
    assert dto is not None
    assert dto.title == "Fantastic Mr Fox"
    assert dto.authors == ["Roald Dahl"]
    assert dto.published_date == "1970"
    assert dto.access_type == "borrow"
    assert "8225261" in dto.cover_url
