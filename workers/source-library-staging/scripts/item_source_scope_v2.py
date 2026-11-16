"""Bound explicit multi-textbook scope without weakening authenticated ownership.

IDs select candidates only. Retrieval and persistence must separately enforce
the authenticated owner and ready state in SQL for every referenced textbook.
"""
from uuid import UUID


def source_scope(primary, textbook_ids=None):
    if textbook_ids is None:
        return None  # Preserve the existing single-book contract.
    if (not isinstance(textbook_ids, list) or not 1 <= len(textbook_ids) <= 8
            or any(not isinstance(value, str) for value in textbook_ids)):
        raise ValueError('One to eight distinct textbook UUIDs required')
    try:
        books = [str(UUID(value)) for value in textbook_ids]
        anchor = str(UUID(primary))
    except (ValueError, TypeError, AttributeError):
        raise ValueError('Canonical textbook UUIDs required') from None
    if books != textbook_ids or len(set(books)) != len(books) or anchor not in books:
        raise ValueError('Distinct canonical textbook IDs including primary required')
    return [anchor] + sorted(book for book in books if book != anchor)
