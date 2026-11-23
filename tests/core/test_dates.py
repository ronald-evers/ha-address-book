"""Tests for date arithmetic."""

from __future__ import annotations

from datetime import date

from custom_components.address_book.core.dates import (
    LeapDayRule,
    OccurrenceKind,
    add_months,
    age_on,
    next_occurrence,
    occurrence_in_year,
    occurrences,
    upcoming,
)
from custom_components.address_book.core.model import (
    AddressBook,
    Event,
    PartialDate,
)


def test_next_occurrence_counts_today_and_wraps() -> None:
    """Today is still "next"; yesterday rolls over to next year."""
    birthday = PartialDate.parse("1980-05-17")
    assert next_occurrence(birthday, date(2026, 5, 17)) == date(2026, 5, 17)
    assert next_occurrence(birthday, date(2026, 5, 18)) == date(2027, 5, 17)
    assert next_occurrence(PartialDate.parse("--12-31"), date(2026, 1, 1)) == date(2026, 12, 31)
    assert next_occurrence(PartialDate.parse("1980"), date(2026, 1, 1)) is None


def test_leap_day() -> None:
    """29 February moves in ordinary years, by the chosen rule."""
    leapling = PartialDate.parse("1988-02-29")
    assert occurrence_in_year(leapling, 2028) == date(2028, 2, 29)
    assert occurrence_in_year(leapling, 2027) == date(2027, 2, 28)
    assert occurrence_in_year(leapling, 2027, LeapDayRule.MAR_1) == date(2027, 3, 1)
    # ... and a 29 February without a year is a valid date.
    assert occurrence_in_year(PartialDate.parse("--02-29"), 2027) == date(2027, 2, 28)


def test_age_on() -> None:
    """Age is whole years, and unknown without a full birth date."""
    born = PartialDate.parse("1980-05-17")
    assert age_on(born, date(2026, 5, 16)) == 45
    assert age_on(born, date(2026, 5, 17)) == 46
    assert age_on(born, date(1979, 1, 1)) is None
    assert age_on(PartialDate.parse("--05-17"), date(2026, 5, 17)) is None
    assert age_on(PartialDate.parse("1980"), date(2026, 5, 17)) is None
    # A leapling turns a year older on 28 February in an ordinary year.
    assert age_on(PartialDate.parse("1988-02-29"), date(2027, 2, 27)) == 38
    assert age_on(PartialDate.parse("1988-02-29"), date(2027, 2, 28)) == 39


def test_add_months_clamps() -> None:
    """Half a year after 31 August is the last day of February."""
    assert add_months(date(2018, 8, 24), 150) == date(2031, 2, 24)
    assert add_months(date(2018, 8, 31), 150) == date(2031, 2, 28)
    assert add_months(date(2020, 11, 15), 2) == date(2021, 1, 15)


def test_birthdays_in_range(family: AddressBook) -> None:
    """Birthdays carry the age, flag milestones and work without a year."""
    found = {
        (o.source_id, o.date): o
        for o in occurrences(family, date(2028, 1, 1), date(2028, 12, 31))
        if o.kind is OccurrenceKind.BIRTHDAY
    }
    tom = found[("tom", date(2028, 2, 29))]
    assert tom.years == 40 and tom.milestone
    eva = found[("eva", date(2028, 12, 5))]
    assert eva.years == 38 and not eva.milestone
    lot = found[("lot", date(2028, 6, 21))]
    assert lot.years is None and not lot.milestone
    # People without a birth date simply have no birthday.
    assert not any(source == "wim" for source, _ in found)


def test_no_birthday_after_death(family: AddressBook) -> None:
    """A birthday stops with a death; a day of remembrance takes its place."""
    family.people["henk"].death_date = PartialDate.parse("2027-04-10")
    in_2027 = occurrences(family, date(2027, 1, 1), date(2027, 12, 31))
    in_2028 = occurrences(family, date(2028, 1, 1), date(2028, 12, 31))

    def kinds(found, person_id):
        return [o.kind for o in found if o.person_ids == (person_id,)]

    # Born 2 March, died 10 April 2027: that last birthday still happened.
    assert kinds(in_2027, "henk") == [OccurrenceKind.BIRTHDAY]
    assert kinds(in_2028, "henk") == [OccurrenceKind.DEATH_ANNIVERSARY]
    remembered = next(o for o in in_2028 if o.person_ids == ("henk",))
    assert (remembered.date, remembered.years) == (date(2028, 4, 10), 1)

    # Died, date unknown: no birthdays at all.
    family.people["truus"].deceased = True
    assert kinds(occurrences(family, date(2028, 1, 1), date(2028, 12, 31)), "truus") == []


def test_wedding_anniversaries(family: AddressBook) -> None:
    """Anniversaries, the Dutch 12½ years, and none after a death or divorce."""
    weddings = [
        o
        for o in occurrences(family, date(2031, 1, 1), date(2031, 12, 31))
        if o.kind is OccurrenceKind.WEDDING_ANNIVERSARY
    ]
    by_couple = {(o.person_ids, o.years): o for o in weddings}

    # Tom and Iris married on 24 August 2018.
    half = by_couple[(("tom", "iris"), 12.5)]
    assert half.date == date(2031, 2, 24) and half.milestone
    thirteen = by_couple[(("tom", "iris"), 13)]
    assert thirteen.date == date(2031, 8, 24) and not thirteen.milestone
    # Piet and Maria: 45 years in 2031, not a milestone; Wim and Greet have no date.
    assert not by_couple[(("piet", "maria"), 45)].milestone
    assert not any("wim" in o.person_ids for o in weddings)

    silver = [
        o
        for o in occurrences(family, date(2043, 8, 24), date(2043, 8, 24))
        if o.kind is OccurrenceKind.WEDDING_ANNIVERSARY
    ]
    assert [(o.years, o.milestone) for o in silver] == [(25, True)]

    family.people["henk"].deceased = True
    after = occurrences(family, date(2031, 1, 1), date(2031, 12, 31))
    assert not any(
        o.kind is OccurrenceKind.WEDDING_ANNIVERSARY and "truus" in o.person_ids
        for o in after
    )


def test_custom_events(family: AddressBook) -> None:
    """Yearly events repeat; one-off events happen once."""
    family.put_event(
        Event(id="jubilee", title="Club jubilee", date=PartialDate.parse("2020-11-03"))
    )
    family.put_event(
        Event(
            id="party",
            title="Garden party",
            date=PartialDate.parse("2027-07-04"),
            yearly=False,
            person_ids=["tom", "iris"],
        )
    )
    events = [
        o
        for o in occurrences(family, date(2027, 1, 1), date(2028, 12, 31))
        if o.kind is OccurrenceKind.EVENT
    ]
    assert [(o.title, o.date, o.years) for o in events] == [
        ("Garden party", date(2027, 7, 4), None),
        ("Club jubilee", date(2027, 11, 3), 7),
        ("Club jubilee", date(2028, 11, 3), 8),
    ]
    assert events[0].person_ids == ("tom", "iris")


def test_upcoming_is_sorted_and_inclusive(family: AddressBook) -> None:
    """The window runs from today up to and including the last day."""
    found = upcoming(family, date(2026, 12, 5), 30)
    assert [o.date for o in found] == sorted(o.date for o in found)
    assert found[0].source_id == "eva" and found[0].date == date(2026, 12, 5)
    assert all(date(2026, 12, 5) <= o.date <= date(2027, 1, 4) for o in found)
    # Maria's birthday on 9 January is just outside a 30-day window.
    assert not any(o.source_id == "maria" for o in found)
    assert any(o.source_id == "maria" for o in upcoming(family, date(2026, 12, 5), 35))


def test_no_anniversary_after_divorce(family: AddressBook) -> None:
    """An ended marriage has no anniversaries."""
    marriage = next(
        r for r in family.relationships.values() if r.from_id == "anna" and r.to_id == "kees"
    )
    marriage.ended = True
    found = occurrences(family, date(2031, 1, 1), date(2031, 12, 31))
    assert not any(
        o.kind is OccurrenceKind.WEDDING_ANNIVERSARY and "anna" in o.person_ids
        for o in found
    )
