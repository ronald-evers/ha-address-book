"""Tests for turning a birthday calendar into people and households."""

from __future__ import annotations

import pytest

from custom_components.address_book.core.calendar_import import (
    ATTENTION_ADDRESS,
    ATTENTION_COUNTRY,
    ATTENTION_NO_NAME,
    ATTENTION_SEVERAL_NAMES,
    CalendarEntry,
    parse_address,
    parse_name,
    plan_import,
    split_names,
)
from custom_components.address_book.core.model import AddressBook


@pytest.mark.parametrize(
    ("title", "names"),
    [
        ("Noor van der Berg", ["Noor van der Berg"]),
        ("Tom en Iris", ["Tom", "Iris"]),
        ("Tom & Iris Akker", ["Tom", "Iris Akker"]),
        ("Tom+Iris", ["Tom", "Iris"]),
        ("Tom and Iris", ["Tom", "Iris"]),
        ("Hendrik", ["Hendrik"]),  # "en" inside a name is not a separator
        ("  ", []),
    ],
)
def test_split_names(title: str, names: list[str]) -> None:
    assert split_names(title) == names


@pytest.mark.parametrize(
    ("name", "parts"),
    [
        ("Noor", ("Noor", "", "")),
        ("Noor Berg", ("Noor", "", "Berg")),
        ("Noor van der Berg", ("Noor", "van der", "Berg")),
        ("Noor Van Der Berg", ("Noor", "Van Der", "Berg")),
        ("Noor de Vries Akker", ("Noor", "de", "Vries Akker")),
        ("Noor de", ("Noor", "", "de")),  # a prefix alone is the family name
        ("", ("", "", "")),
    ],
)
def test_parse_name(name: str, parts: tuple[str, str, str]) -> None:
    assert parse_name(name) == parts


@pytest.mark.parametrize(
    ("location", "fields"),
    [
        (
            "Dorpsstraat 12, 1234 AB Ons Dorp",
            {"street": "Dorpsstraat", "house_number": "12", "house_number_addition": "",
             "postal_code": "1234 AB", "city": "Ons Dorp"},
        ),
        (
            "Dorpsstraat 12-A, 1234ab Ons Dorp, Nederland",
            {"street": "Dorpsstraat", "house_number": "12", "house_number_addition": "A",
             "postal_code": "1234 AB", "city": "Ons Dorp", "country": "NL"},
        ),
        (
            "Dorpsstraat 12A\n1234 AB Ons Dorp",
            {"street": "Dorpsstraat", "house_number": "12", "house_number_addition": "A",
             "postal_code": "1234 AB", "city": "Ons Dorp"},
        ),
        (
            "Lange Laan 12 bis, 1234 AB Ons Dorp",
            {"street": "Lange Laan", "house_number": "12", "house_number_addition": "bis",
             "postal_code": "1234 AB", "city": "Ons Dorp"},
        ),
        (
            "Plein 1945 3, 1234 AB Ons Dorp",
            {"street": "Plein 1945", "house_number": "3", "house_number_addition": "",
             "postal_code": "1234 AB", "city": "Ons Dorp"},
        ),
        (
            "Laan 12-2, 1234 AB Ons Dorp",
            {"street": "Laan", "house_number": "12", "house_number_addition": "2",
             "postal_code": "1234 AB", "city": "Ons Dorp"},
        ),
        (
            "Hauptstrasse 5, 12345 Musterstadt, de",
            {"street": "Hauptstrasse", "house_number": "5", "house_number_addition": "",
             "postal_code": "12345", "city": "Musterstadt", "country": "DE"},
        ),
        (
            "Kerkweg 7, Ons Dorp",
            {"street": "Kerkweg", "house_number": "7", "house_number_addition": "",
             "city": "Ons Dorp"},
        ),
    ],
)
def test_parse_address(location: str, fields: dict[str, str]) -> None:
    assert parse_address(location) == (fields, [])


def test_address_that_is_not_recognised() -> None:
    """Anything else is kept whole, and reported."""
    assert parse_address("Ergens in Ons Dorp") == (
        {"street": "Ergens in Ons Dorp"},
        [ATTENTION_ADDRESS],
    )
    assert parse_address("2 Main Street, Springfield") == (
        {"street": "2 Main Street, Springfield"},
        [ATTENTION_ADDRESS],
    )
    fields, attention = parse_address("Kerkweg 7, 1234 AB Ons Dorp, Verweggistan")
    assert fields["country"] == "Verweggistan"
    assert attention == [ATTENTION_COUNTRY]


ENTRIES = [
    CalendarEntry("Noor van der Berg", 10, 10, "Dorpsstraat 12-A, 1234 AB Ons Dorp", "Likes horses"),
    CalendarEntry("Finn van der Berg", 5, 1, "dorpsstraat 12-a, 1234 ab ons dorp"),
    CalendarEntry("Eva", 12, 5),
    CalendarEntry("Tom en Iris", 8, 24, "Kerkweg 7, 1234 AB Ons Dorp", "Card: yes"),
    CalendarEntry("Sam Akker", 2, 29, "Ergens in Ons Dorp"),
]


def test_plan_changes_nothing() -> None:
    """Planning is a preview: the address book stays as it was."""
    book = AddressBook()
    plan = plan_import(book, ENTRIES)
    assert book.to_dict() == AddressBook().to_dict()
    assert len(plan.people) == 6


def test_import() -> None:
    """People, shared households, notes, and events for titles with several names."""
    book = AddressBook()
    plan = plan_import(book, ENTRIES)
    plan.apply(book)
    people = {p.full_name: p for p in book.people.values()}

    noor, finn = people["Noor van der Berg"], people["Finn van der Berg"]
    assert (noor.given_name, noor.family_name_prefix, noor.family_name) == ("Noor", "van der", "Berg")
    assert str(noor.birth_date) == "--10-10"  # never a year
    assert noor.notes == "Likes horses"
    assert noor.household_id == finn.household_id  # same address, written differently
    assert book.households[noor.household_id].street_line == "Dorpsstraat 12-A"
    assert len(book.households) == 3

    assert people["Eva"].household_id is None
    assert str(people["Sam Akker"].birth_date) == "--02-29"

    # Whose date 24 August is, is not guessed.
    tom, iris = people["Tom"], people["Iris"]
    assert tom.birth_date is None and iris.birth_date is None
    assert tom.household_id == iris.household_id is not None
    (event,) = book.events.values()
    assert (event.title, str(event.date), event.yearly) == ("Tom en Iris", "--08-24", True)
    assert event.person_ids == [tom.id, iris.id]
    assert event.notes == "Card: yes"
    assert book.relationships == {}

    assert plan.attention == [
        ("Tom en Iris", ATTENTION_SEVERAL_NAMES),
        ("Sam Akker", ATTENTION_ADDRESS),
    ]
    assert plan.skipped == []


def test_import_can_be_repeated() -> None:
    """A second run adds nothing; a new entry joins the household that is there."""
    book = AddressBook()
    plan_import(book, ENTRIES).apply(book)
    before = book.to_dict()

    again = plan_import(book, ENTRIES + ENTRIES)
    assert (again.people, again.households, again.events) == ([], [], [])
    assert sorted(again.skipped) == sorted(e.title for e in ENTRIES)
    again.apply(book)
    assert book.to_dict() == before

    extra = plan_import(
        book, [CalendarEntry("Lot van der Berg", 6, 21, "Dorpsstraat 12-A, 1234 AB Ons Dorp")]
    )
    assert extra.households == []
    extra.apply(book)
    assert len(book.household_members(extra.people[0].household_id)) == 3


def test_person_named_in_two_entries() -> None:
    """Someone with a birthday of their own is not created again for a shared date."""
    book = AddressBook()
    plan = plan_import(
        book,
        [
            CalendarEntry("Tom", 2, 29),
            CalendarEntry("Tom en Iris", 8, 24),
            CalendarEntry("", 1, 1),
        ],
    )
    plan.apply(book)
    assert sorted(p.full_name for p in book.people.values()) == ["Iris", "Tom"]
    assert ("", ATTENTION_NO_NAME) in plan.attention


def test_summary() -> None:
    """The preview shows names, birthdays and addresses in plain data."""
    book = AddressBook()
    summary = plan_import(book, ENTRIES).summary(book)
    assert summary["people"][0] == {
        "name": "Noor van der Berg",
        "birthday": "--10-10",
        "address": "Dorpsstraat 12-A, 1234 AB Ons Dorp",
    }
    assert summary["people"][2] == {"name": "Eva", "birthday": "--12-05", "address": ""}
    assert summary["households"] == [
        "Dorpsstraat 12-A, 1234 AB Ons Dorp",
        "Kerkweg 7, 1234 AB Ons Dorp",
        "Ergens in Ons Dorp",
    ]
    assert summary["events"] == [{"title": "Tom en Iris", "date": "--08-24"}]
    assert {"title": "Sam Akker", "reason": ATTENTION_ADDRESS} in summary["attention"]
