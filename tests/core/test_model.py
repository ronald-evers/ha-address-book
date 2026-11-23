"""Tests for the records and the rules that keep them consistent."""

from __future__ import annotations

import json

import pytest

from custom_components.address_book.core.model import (
    AddressBook,
    ContactPoint,
    Event,
    Gender,
    Group,
    Household,
    PartialDate,
    Person,
    Relationship,
    RelationshipType,
)


@pytest.mark.parametrize(
    "text", ["1980-05-17", "--05-17", "1980", "--02-29", "2024-02-29"]
)
def test_partial_date_round_trip(text: str) -> None:
    """Every accepted shape is written back exactly as it was read."""
    assert str(PartialDate.parse(text)) == text


@pytest.mark.parametrize(
    "text", ["", "17-05-1980", "1980-05", "1980-13-01", "2023-02-29", "--04-31", "abc"]
)
def test_partial_date_rejects(text: str) -> None:
    """Dates that cannot exist are refused."""
    with pytest.raises(ValueError):
        PartialDate.parse(text)


def test_names_and_sorting() -> None:
    """A family-name prefix is spoken but not sorted on."""
    people = [
        Person(id="1", given_name="Jan", family_name_prefix="van der", family_name="Berg"),
        Person(id="2", given_name="Anna", family_name="Evers"),
        Person(id="3", given_name="Koen", family_name_prefix="de", family_name="Aalst"),
        Person(id="4", given_name="Mila"),
    ]
    assert people[0].full_name == "Jan van der Berg"
    assert people[3].full_name == "Mila"
    ordered = [p.full_name for p in sorted(people, key=lambda p: p.sort_key)]
    assert ordered == ["Mila", "Koen de Aalst", "Jan van der Berg", "Anna Evers"]


def _small_book() -> AddressBook:
    book = AddressBook()
    book.put_group(Group(id="g-family", name="Family"))
    book.put_group(Group(id="g-friends", name="Friends"))
    book.put_household(
        Household(
            id="h1",
            street="Dorpsstraat 12A",
            postal_code="1234 AB",
            city="Ons Dorp",
            country="NL",
            address_verified_on="2026-11-01",
            send_seasonal_card=True,
        )
    )
    book.put_person(
        Person(
            id="p-mother",
            given_name="Sanne",
            family_name_prefix="de",
            family_name="Wit",
            gender=Gender.FEMALE,
            birth_date=PartialDate.parse("1985-03-04"),
            emails=[ContactPoint("sanne@example.org", "home")],
            phones=[ContactPoint("+31 6 0000 0000", "mobile")],
            household_id="h1",
            group_ids=["g-family", "g-friends"],
            send_birthday_card=True,
        )
    )
    # A toddler: no e-mail, no phone, and that is fine.
    book.put_person(
        Person(
            id="p-child",
            given_name="Pim",
            family_name_prefix="de",
            family_name="Wit",
            birth_date=PartialDate.parse("2024-06-30"),
            household_id="h1",
            group_ids=["g-family"],
        )
    )
    book.put_relationship(
        Relationship(
            id="r1", type=RelationshipType.PARENT, from_id="p-mother", to_id="p-child"
        )
    )
    book.put_event(
        Event(
            id="e1",
            title="First day of school",
            date=PartialDate.parse("2028-07-03"),
            yearly=False,
            person_ids=["p-child"],
        )
    )
    return book


def test_book_round_trip() -> None:
    """Saving and loading gives back the same address book, as plain JSON."""
    book = _small_book()
    data = json.loads(json.dumps(book.to_dict()))
    assert data["people"][0]["birth_date"] == "1985-03-04"
    assert data["people"][0]["gender"] == "female"
    assert data["people"][1]["emails"] == []
    assert data["relationships"][0]["type"] == "parent"
    assert AddressBook.from_dict(data).to_dict() == book.to_dict()


def test_unknown_keys_are_ignored() -> None:
    """Data written by a newer version still loads."""
    data = _small_book().to_dict()
    data["people"][0]["favourite_colour"] = "green"
    book = AddressBook.from_dict(data)
    assert book.people["p-mother"].given_name == "Sanne"


def test_household_and_group_members() -> None:
    """A household lists its members oldest first; a group by name."""
    book = _small_book()
    assert [p.given_name for p in book.household_members("h1")] == ["Sanne", "Pim"]
    assert [p.given_name for p in book.people_in_group("g-family")] == ["Pim", "Sanne"]
    assert [p.given_name for p in book.people_in_group("g-friends")] == ["Sanne"]


def test_find_people() -> None:
    """Search matches every word, in any order, ignoring case."""
    book = _small_book()
    book.people["p-child"].nickname = "Pimmie"
    assert [p.id for p in book.find_people("wit")] == ["p-child", "p-mother"]
    assert [p.id for p in book.find_people("WIT sanne")] == ["p-mother"]
    assert [p.id for p in book.find_people("pimmie")] == ["p-child"]
    assert book.find_people("   ") == []
    assert book.find_people("nobody") == []


def test_removing_keeps_the_book_consistent() -> None:
    """Nothing is left pointing at a record that is gone."""
    book = _small_book()
    book.remove_group("g-friends")
    assert book.people["p-mother"].group_ids == ["g-family"]

    book.remove_household("h1")
    assert book.people["p-mother"].household_id is None
    assert book.people["p-child"].household_id is None

    book.remove_person("p-child")
    assert book.relationships == {}
    assert book.events["e1"].person_ids == []
    # ... and the result still loads.
    assert AddressBook.from_dict(book.to_dict()).to_dict() == book.to_dict()


def test_dangling_references_are_refused() -> None:
    """You cannot point at a household, group or person that does not exist."""
    book = _small_book()
    with pytest.raises(ValueError, match="unknown household"):
        book.put_person(Person(id="x", given_name="X", household_id="nope"))
    with pytest.raises(ValueError, match="unknown group"):
        book.put_person(Person(id="x", given_name="X", group_ids=["nope"]))
    with pytest.raises(ValueError, match="only once"):
        book.put_person(Person(id="x", given_name="X", group_ids=["g-family", "g-family"]))
    with pytest.raises(ValueError, match="unknown person"):
        book.put_relationship(
            Relationship(
                id="r2", type=RelationshipType.FRIEND, from_id="p-mother", to_id="nope"
            )
        )
    with pytest.raises(ValueError, match="unknown person"):
        book.put_event(
            Event(id="e2", title="T", date=PartialDate.parse("--01-01"), person_ids=["nope"])
        )
    assert "x" not in book.people


def test_relationship_rules() -> None:
    """No duplicates, no relationship with yourself, no circular ancestry."""
    book = _small_book()
    parent, friend = RelationshipType.PARENT, RelationshipType.FRIEND

    with pytest.raises(ValueError, match="two different people"):
        Relationship(id="r", type=friend, from_id="p-child", to_id="p-child")
    with pytest.raises(ValueError, match="already exists"):
        book.put_relationship(
            Relationship(id="r2", type=parent, from_id="p-mother", to_id="p-child")
        )
    with pytest.raises(ValueError, match="own ancestor"):
        book.put_relationship(
            Relationship(id="r2", type=parent, from_id="p-child", to_id="p-mother")
        )

    book.put_relationship(
        Relationship(id="r3", type=friend, from_id="p-mother", to_id="p-child")
    )
    # Friendship has no direction, so the mirror image is the same relationship.
    with pytest.raises(ValueError, match="already exists"):
        book.put_relationship(
            Relationship(id="r4", type=friend, from_id="p-child", to_id="p-mother")
        )
    # Replacing a relationship by its own id is an update, not a duplicate.
    book.put_relationship(
        Relationship(id="r3", type=friend, from_id="p-mother", to_id="p-child", notes="x")
    )
    assert book.relationships["r3"].notes == "x"


def test_record_validation() -> None:
    """Records refuse to be created half-empty."""
    with pytest.raises(ValueError):
        Person(id="x", given_name="  ")
    with pytest.raises(ValueError):
        Group(id="x", name="")
    with pytest.raises(ValueError):
        Event(id="x", title="Yearly", date=PartialDate.parse("2020"))
    with pytest.raises(ValueError):
        Event(id="x", title="Once", date=PartialDate.parse("--05-01"), yearly=False)
    with pytest.raises(ValueError):
        Household.from_dict({"id": "h", "address_verified_on": "01-11-2026"})


def test_deceased() -> None:
    """Someone has died when there is a date, or when the flag says so."""
    assert not Person(id="a", given_name="A").is_deceased
    assert Person(id="a", given_name="A", deceased=True).is_deceased
    assert Person(id="a", given_name="A", death_date=PartialDate.parse("2020")).is_deceased
