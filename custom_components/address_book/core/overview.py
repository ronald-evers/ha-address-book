"""Dates with what you want to know about them: who, where, and the note.

Pure Python: no Home Assistant imports.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from .dates import LeapDayRule, Occurrence, OccurrenceKind, occurrences
from .model import AddressBook


@dataclass(frozen=True)
class Entry:
    """One date on the calendar, described."""

    occurrence: Occurrence
    name: str  # the person, the couple ("Tom & Iris") or the title of the event
    address: str  # postal address on one line; empty when unknown
    notes: str

    def as_dict(self, today: date) -> dict[str, Any]:
        """Return plain data, with the number of days from ``today``."""
        years = self.occurrence.years
        if years is not None and float(years).is_integer():
            years = int(years)
        return {
            "name": self.name,
            "date": self.occurrence.date.isoformat(),
            "days": (self.occurrence.date - today).days,
            "kind": self.occurrence.kind.value,
            "years": years,
            "milestone": self.occurrence.milestone,
            "address": self.address,
            "notes": self.notes,
            "person_ids": list(self.occurrence.person_ids),
        }


def describe(book: AddressBook, occurrence: Occurrence) -> Entry:
    """Look up the name, address and note that go with a date."""
    people = [book.people[i] for i in occurrence.person_ids if i in book.people]

    if occurrence.kind is OccurrenceKind.EVENT:
        name = occurrence.title
        notes = book.events[occurrence.source_id].notes
    elif occurrence.kind is OccurrenceKind.WEDDING_ANNIVERSARY:
        name = " & ".join(person.full_name for person in people)
        notes = book.relationships[occurrence.source_id].notes
    else:
        name = people[0].full_name
        notes = people[0].notes

    address = ""
    for person in people:
        if person.household_id is not None:
            address = book.households[person.household_id].address_line
            break
    return Entry(occurrence=occurrence, name=name, address=address, notes=notes)


def entries(
    book: AddressBook,
    start: date,
    end: date,
    rule: LeapDayRule = LeapDayRule.FEB_28,
) -> list[Entry]:
    """Return every date from ``start`` up to and including ``end``, described."""
    return [describe(book, found) for found in occurrences(book, start, end, rule)]
