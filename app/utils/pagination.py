import math
from collections.abc import Sequence


class PagedResult[T]:
    def __init__(self, items: Sequence[T], page: int, per_page: int, total_items: int):
        self.items: list[T] = list(items)
        self.page = max(1, page)
        self.per_page = max(1, per_page)
        self.total_items = max(0, total_items)
        self.total_pages = max(1, math.ceil(self.total_items / self.per_page))

    @property
    def has_prev(self) -> bool:
        return self.page > 1

    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages


def paginate[T](items: Sequence[T], page: int = 1, per_page: int = 5) -> PagedResult[T]:
    """Slice in-memory list according to page and per_page."""
    page = max(1, page)
    per_page = max(1, per_page)
    total_items = len(items)
    offset = (page - 1) * per_page
    sliced = items[offset : offset + per_page]
    return PagedResult(items=sliced, page=page, per_page=per_page, total_items=total_items)
