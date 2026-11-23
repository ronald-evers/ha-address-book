"""Date arithmetic: when is the next birthday, how old does someone turn.

Pure Python: no Home Assistant imports.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum

from .model import AddressBook, PartialDate, RelationshipType


class LeapDayRule(StrEnum):
    """When to celebrate a 29 February date in a year without one."""

    FEB_28 = "feb_28"
    MAR_1 = "mar_1"


class OccurrenceKind(StrEnum):
    """What kind of date an occurrence is."""

    BIRTHDAY = "birthday"
    WEDDING_ANNIVERSARY = "wedding_anniversary"
    DEATH_ANNIVERSARY = "death_anniversary"
    EVENT = "event"


BIRTHDAY_MILESTONES = frozenset(
    {1, 18, 21, 30, 40, 50, 60, 65, 70, 75, 80, 85, 90, 95, 100}
)
# 12.5 years is the Dutch "koperen bruiloft"; it falls half a year off the wedding day.
WEDDING_MILESTONES = frozenset({12.5, 25, 40, 50, 60, 65, 70})
_HALF_ANNIVERSARY_MONTHS = 150  # 12.5 years


@dataclass(frozen=True)
class Occurrence:
    """One date on the calendar."""

    date: date
    kind: OccurrenceKind
    source_id: str  # the person, relationship or event it comes from
    person_ids: tuple[str, ...]
    years: float | None = None  # age turned / years married; None when unknown
    milestone: bool = False
    title: str = ""  # only set for custom events


def occurrence_in_year(
    value: PartialDate, year: int, rule: LeapDayRule = LeapDayRule.FEB_28
) -> date | None:
    """Return the day a yearly date falls on in the given year."""
    if value.month is None or value.day is None:
        return None
    if value.month == 2 and value.day == 29 and not calendar.isleap(year):
        return date(year, 2, 28) if rule is LeapDayRule.FEB_28 else date(year, 3, 1)
    return date(year, value.month, value.day)


def next_occurrence(
    value: PartialDate, today: date, rule: LeapDayRule = LeapDayRule.FEB_28
) -> date | None:
    """Return the next day a yearly date falls on; today counts."""
    this_year = occurrence_in_year(value, today.year, rule)
    if this_year is None:
        return None
    if this_year >= today:
        return this_year
    return occurrence_in_year(value, today.year + 1, rule)


def age_on(
    born: PartialDate, on: date, rule: LeapDayRule = LeapDayRule.FEB_28
) -> int | None:
    """Return the age in whole years on a given day; None unless fully known."""
    if born.year is None:
        return None
    birthday = occurrence_in_year(born, on.year, rule)
    if birthday is None:
        return None
    age = on.year - born.year - (1 if on < birthday else 0)
    return age if age >= 0 else None


def add_months(value: date, months: int) -> date:
    """Add calendar months, clamping to the last day of the month."""
    index = value.year * 12 + (value.month - 1) + months
    year, month = divmod(index, 12)
    month += 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _yearly(
    value: PartialDate, start: date, end: date, rule: LeapDayRule
) -> list[tuple[date, int | None]]:
    """Return (day, years since the original date) for every hit in a range."""
    hits: list[tuple[date, int | None]] = []
    for year in range(start.year, end.year + 1):
        day = occurrence_in_year(value, year, rule)
        if day is None or not start <= day <= end:
            continue
        hits.append((day, None if value.year is None else year - value.year))
    return hits


def occurrences(
    book: AddressBook,
    start: date,
    end: date,
    rule: LeapDayRule = LeapDayRule.FEB_28,
) -> list[Occurrence]:
    """Return every date in the address book that falls in ``start``..``end``."""
    found: list[Occurrence] = []

    for person in book.people.values():
        if person.birth_date is not None:
            died = person.death_date.to_date() if (
                person.death_date is not None and person.death_date.is_full
            ) else None
            for day, years in _yearly(person.birth_date, start, end, rule):
                if years is not None and years < 1:
                    continue
                # No birthdays after someone has died.
                if person.is_deceased and (died is None or day > died):
                    continue
                found.append(
                    Occurrence(
                        date=day,
                        kind=OccurrenceKind.BIRTHDAY,
                        source_id=person.id,
                        person_ids=(person.id,),
                        years=years,
                        milestone=years in BIRTHDAY_MILESTONES,
                    )
                )
        if person.death_date is not None:
            for day, years in _yearly(person.death_date, start, end, rule):
                if years is not None and years < 1:
                    continue
                found.append(
                    Occurrence(
                        date=day,
                        kind=OccurrenceKind.DEATH_ANNIVERSARY,
                        source_id=person.id,
                        person_ids=(person.id,),
                        years=years,
                    )
                )

    for relationship in book.relationships.values():
        wedding = relationship.start_date
        if (
            relationship.type is not RelationshipType.SPOUSE
            or relationship.ended
            or wedding is None
        ):
            continue
        couple = (relationship.from_id, relationship.to_id)
        # An anniversary is for the two of them: not after one has died.
        if any(book.people[person_id].is_deceased for person_id in couple):
            continue
        for day, years in _yearly(wedding, start, end, rule):
            if years is not None and years < 1:
                continue
            found.append(
                Occurrence(
                    date=day,
                    kind=OccurrenceKind.WEDDING_ANNIVERSARY,
                    source_id=relationship.id,
                    person_ids=couple,
                    years=years,
                    milestone=years in WEDDING_MILESTONES,
                )
            )
        if wedding.is_full:
            half = add_months(wedding.to_date(), _HALF_ANNIVERSARY_MONTHS)
            if start <= half <= end:
                found.append(
                    Occurrence(
                        date=half,
                        kind=OccurrenceKind.WEDDING_ANNIVERSARY,
                        source_id=relationship.id,
                        person_ids=couple,
                        years=12.5,
                        milestone=True,
                    )
                )

    for event in book.events.values():
        if event.yearly:
            for day, years in _yearly(event.date, start, end, rule):
                if years is not None and years < 0:
                    continue
                found.append(
                    Occurrence(
                        date=day,
                        kind=OccurrenceKind.EVENT,
                        source_id=event.id,
                        person_ids=tuple(event.person_ids),
                        years=years or None,
                        title=event.title,
                    )
                )
        elif start <= event.date.to_date() <= end:
            found.append(
                Occurrence(
                    date=event.date.to_date(),
                    kind=OccurrenceKind.EVENT,
                    source_id=event.id,
                    person_ids=tuple(event.person_ids),
                    title=event.title,
                )
            )

    return sorted(found, key=lambda o: (o.date, o.kind, o.source_id))


def upcoming(
    book: AddressBook,
    today: date,
    days: int,
    rule: LeapDayRule = LeapDayRule.FEB_28,
) -> list[Occurrence]:
    """Return the dates from today up to and including ``days`` days ahead."""
    return occurrences(book, today, today + timedelta(days=days), rule)
