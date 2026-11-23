"""Shared fixtures."""

from __future__ import annotations

import pytest

from custom_components.address_book.core.model import (
    AddressBook,
    Gender,
    PartialDate,
    Person,
    Relationship,
    RelationshipType,
)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Let Home Assistant load the integration from custom_components."""
    return


def _person(book: AddressBook, name: str, gender: Gender, born: str | None = None) -> None:
    book.put_person(
        Person(
            id=name.lower(),
            given_name=name,
            gender=gender,
            birth_date=PartialDate.parse(born) if born else None,
        )
    )


def _link(
    book: AddressBook,
    kind: RelationshipType,
    from_id: str,
    to_id: str,
    *,
    start: str | None = None,
    ended: bool = False,
) -> None:
    book.put_relationship(
        Relationship(
            id=f"{kind.value}:{from_id}:{to_id}",
            type=kind,
            from_id=from_id,
            to_id=to_id,
            start_date=PartialDate.parse(start) if start else None,
            ended=ended,
        )
    )


@pytest.fixture
def family() -> AddressBook:
    """A fictional family, four generations deep.

    Henk + Truus ──┬── Piet + Maria ──┬── Tom + Iris ── Noor
                   │   (Piet's ex Els │   (Iris's son Finn)
                   │    ── Rik)       └── Eva
                   └── Anna + Kees ───┬── Sam
                                      └── Lot
    Wim + Greet ───┬── Maria
                   └── Bas
    """
    book = AddressBook()
    male, female = Gender.MALE, Gender.FEMALE
    for name, gender, born in (
        ("Henk", male, "1935-03-02"),
        ("Truus", female, "1937-11-20"),
        ("Piet", male, "1960-06-15"),
        ("Maria", female, "1962-01-09"),
        ("Els", female, None),
        ("Anna", female, "1964-09-30"),
        ("Kees", male, "1963-04-04"),
        ("Tom", male, "1988-02-29"),
        ("Eva", female, "1990-12-05"),
        ("Rik", male, "1984-07-07"),
        ("Iris", female, "1989-08-18"),
        ("Finn", male, "2012-05-01"),
        ("Noor", female, "2021-10-10"),
        ("Sam", male, "1992-03-14"),
        ("Lot", female, "--06-21"),
        ("Wim", male, None),
        ("Greet", female, None),
        ("Bas", male, None),
        ("Vreemde", male, None),
    ):
        _person(book, name, gender, born)

    spouse, partner, parent = (
        RelationshipType.SPOUSE,
        RelationshipType.PARTNER,
        RelationshipType.PARENT,
    )
    _link(book, spouse, "henk", "truus", start="1958-05-10")
    _link(book, spouse, "piet", "maria", start="1986-09-12")
    _link(book, partner, "piet", "els", ended=True)
    _link(book, spouse, "anna", "kees", start="1990-06-01")
    _link(book, spouse, "tom", "iris", start="2018-08-24")
    _link(book, spouse, "wim", "greet")

    for parent_id, children in (
        ("henk", ("piet", "anna")),
        ("truus", ("piet", "anna")),
        ("piet", ("tom", "eva", "rik")),
        ("maria", ("tom", "eva")),
        ("els", ("rik",)),
        ("anna", ("sam", "lot")),
        ("kees", ("sam", "lot")),
        ("tom", ("noor",)),
        ("iris", ("noor", "finn")),
        ("wim", ("maria", "bas")),
        ("greet", ("maria", "bas")),
    ):
        for child_id in children:
            _link(book, parent, parent_id, child_id)
    return book
