"""Tests for the services that add, change, remove and look up records."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import voluptuous as vol
import yaml

from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import ServiceValidationError
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.address_book.const import DOMAIN
from custom_components.address_book.core.model import AddressBook
from custom_components.address_book.services import KINDS
from custom_components.address_book.store import STORAGE_KEY

COMPONENT = Path(__file__).parent.parent / "custom_components" / "address_book"


@pytest.fixture
async def entry(hass: HomeAssistant, hass_storage: dict[str, Any]) -> MockConfigEntry:
    """An empty address book, set up."""
    config_entry = MockConfigEntry(domain=DOMAIN, title="Address Book")
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry


@pytest.fixture
def book(entry: MockConfigEntry) -> AddressBook:
    return entry.runtime_data.book


async def _call(hass: HomeAssistant, service: str, **data: Any) -> Any:
    wants_answer = service.startswith(("set_", "find_"))
    return await hass.services.async_call(
        DOMAIN, service, data, blocking=True, return_response=wants_answer
    )


async def _add(hass: HomeAssistant, kind: str, **data: Any) -> str:
    return (await _call(hass, f"set_{kind}", **data))["id"]


async def test_add_person(hass: HomeAssistant, book: AddressBook) -> None:
    """A new person gets an id, which is returned."""
    person_id = await _add(
        hass,
        "person",
        given_name="Noor",
        family_name_prefix="van der",
        family_name="Berg",
        gender="female",
        birth_date="2021-10-10",
        emails=[{"value": "noor@example.com"}],
    )
    person = book.people[person_id]
    assert person.full_name == "Noor van der Berg"
    assert str(person.birth_date) == "2021-10-10"
    assert person.emails[0].value == "noor@example.com"
    assert person.emails[0].label == ""


async def test_change_only_what_is_given(hass: HomeAssistant, book: AddressBook) -> None:
    """A change leaves every field alone that is not mentioned."""
    person_id = await _add(
        hass, "person", given_name="Noor", family_name="Berg", birth_date="2021-10-10"
    )
    answer = await _call(hass, "set_person", id=person_id, nickname="Noortje")
    assert answer == {"id": person_id}
    person = book.people[person_id]
    assert person.nickname == "Noortje"
    assert person.family_name == "Berg"
    assert str(person.birth_date) == "2021-10-10"
    assert len(book.people) == 1


@pytest.mark.parametrize("empty", ["", None])
async def test_empty_clears_a_date(
    hass: HomeAssistant, book: AddressBook, empty: str | None
) -> None:
    """An empty value removes a date instead of being read as one."""
    person_id = await _add(
        hass, "person", given_name="Noor", birth_date="2021-10-10", gender="female"
    )
    await _call(hass, "set_person", id=person_id, birth_date=empty, gender=empty)
    assert book.people[person_id].birth_date is None
    assert book.people[person_id].gender is None


async def test_changes_are_saved(
    hass: HomeAssistant, entry: MockConfigEntry, hass_storage: dict[str, Any]
) -> None:
    """What a service changes ends up in storage."""
    await _add(hass, "person", given_name="Noor")
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    people = hass_storage[STORAGE_KEY]["data"]["people"]
    assert [p["given_name"] for p in people] == ["Noor"]


@pytest.mark.parametrize(
    ("service", "data", "message"),
    [
        ("set_person", {"family_name": "Berg"}, "needs: given_name"),
        ("set_group", {"description": "x"}, "needs: name"),
        ("set_relationship", {"type": "parent"}, "needs: from_id, to_id"),
        ("set_event", {"title": "Moved in"}, "needs: date"),
        ("set_person", {"id": "nobody", "nickname": "x"}, "Unknown person"),
        ("set_person", {"given_name": "Noor", "birth_date": "10-10-2021"}, "not a valid date"),
        ("set_person", {"given_name": " "}, "given name"),
        ("set_person", {"given_name": "Noor", "household_id": "gone"}, "unknown household"),
        ("set_person", {"given_name": "Noor", "group_ids": ["gone"]}, "unknown group"),
        ("set_household", {"street": "Kerkweg", "house_number_addition": "A"}, "needs a house number"),
        ("set_household", {"address_verified_on": "01-11-2026"}, "Invalid isoformat"),
        ("set_event", {"title": "Once", "date": "--05-01", "yearly": False}, "full date"),
        ("remove_person", {"id": "nobody"}, "Unknown person"),
        ("remove_household", {"id": "nothing"}, "Unknown household"),
    ],
)
async def test_refused(
    hass: HomeAssistant,
    book: AddressBook,
    service: str,
    data: dict[str, Any],
    message: str,
) -> None:
    """A call that breaks a rule is refused with a reason and changes nothing."""
    with pytest.raises(ServiceValidationError, match=message):
        await _call(hass, service, **data)
    assert book.to_dict() == AddressBook().to_dict()


async def test_unknown_values_are_refused(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """A gender or relationship type that does not exist never reaches the model."""
    with pytest.raises(vol.Invalid):
        await _call(hass, "set_person", given_name="Noor", gender="unknown")
    with pytest.raises(vol.Invalid):
        await _call(hass, "set_person", given_name="Noor", shoe_size=24)


async def test_household_and_members(hass: HomeAssistant, book: AddressBook) -> None:
    """A household takes a house number written as a number, and loses its members when removed."""
    household_id = await _add(
        hass,
        "household",
        street="Dorpsstraat",
        house_number=12,
        house_number_addition="A",
        postal_code="1234 AB",
        city="Ons Dorp",
        country="NL",
        address_verified_on="2026-11-01",
    )
    assert book.households[household_id].street_line == "Dorpsstraat 12-A"
    person_id = await _add(hass, "person", given_name="Noor", household_id=household_id)

    await _call(hass, "set_household", id=household_id, address_verified_on="")
    assert book.households[household_id].address_verified_on is None
    assert book.households[household_id].city == "Ons Dorp"

    await _call(hass, "set_person", id=person_id, household_id="")
    assert book.people[person_id].household_id is None
    await _call(hass, "set_person", id=person_id, household_id=household_id)

    await _call(hass, "remove_household", id=household_id)
    assert book.households == {}
    assert book.people[person_id].household_id is None


async def test_groups(hass: HomeAssistant, book: AddressBook) -> None:
    """Groups can be added, renamed and removed; members stay."""
    group_id = await _add(hass, "group", name="Friends")
    person_id = await _add(hass, "person", given_name="Noor", group_ids=group_id)
    assert book.people[person_id].group_ids == [group_id]

    await _call(hass, "set_group", id=group_id, name="Old friends")
    assert book.groups[group_id].name == "Old friends"

    await _call(hass, "remove_group", id=group_id)
    assert book.groups == {}
    assert book.people[person_id].group_ids == []


async def test_relationships(hass: HomeAssistant, book: AddressBook) -> None:
    """Relationships follow the rules of the model and go when a person goes."""
    tom = await _add(hass, "person", given_name="Tom")
    iris = await _add(hass, "person", given_name="Iris")
    noor = await _add(hass, "person", given_name="Noor")

    wedding = await _add(
        hass, "relationship", type="spouse", from_id=tom, to_id=iris, start_date="2018-08-24"
    )
    await _add(hass, "relationship", type="parent", from_id=tom, to_id=noor)
    assert [p.given_name for p in book.children_of(tom)] == ["Noor"]

    with pytest.raises(ServiceValidationError, match="already exists"):
        await _call(hass, "set_relationship", type="spouse", from_id=iris, to_id=tom)
    with pytest.raises(ServiceValidationError, match="own ancestor"):
        await _call(hass, "set_relationship", type="parent", from_id=noor, to_id=tom)
    with pytest.raises(ServiceValidationError, match="unknown person"):
        await _call(hass, "set_relationship", type="friend", from_id=tom, to_id="nobody")
    assert len(book.relationships) == 2

    await _call(hass, "set_relationship", id=wedding, ended=True, start_date="")
    assert book.relationships[wedding].ended
    assert book.relationships[wedding].start_date is None
    assert book.relationships[wedding].to_id == iris

    await _call(hass, "remove_relationship", id=wedding)
    assert wedding not in book.relationships

    await _call(hass, "remove_person", id=noor)
    assert book.relationships == {}
    assert set(book.people) == {tom, iris}


async def test_events(hass: HomeAssistant, book: AddressBook) -> None:
    """Events can be added, changed and removed."""
    noor = await _add(hass, "person", given_name="Noor")
    event_id = await _add(hass, "event", title="Swimming diploma", date="--06-21", person_ids=[noor])
    assert book.events[event_id].yearly
    assert book.events[event_id].person_ids == [noor]

    with pytest.raises(ServiceValidationError, match="unknown person"):
        await _call(hass, "set_event", id=event_id, person_ids=["nobody"])
    assert book.events[event_id].person_ids == [noor]

    await _call(hass, "set_event", id=event_id, date="2027-06-21", yearly=False)
    assert not book.events[event_id].yearly

    await _call(hass, "remove_event", id=event_id)
    assert book.events == {}


async def test_find_people(hass: HomeAssistant, book: AddressBook) -> None:
    """Searching returns people with their ids, sorted by name."""
    noor = await _add(hass, "person", given_name="Noor", family_name_prefix="van der", family_name="Berg")
    await _add(hass, "person", given_name="Tom", family_name="Akker", nickname="Noordje")
    await _add(hass, "person", given_name="Eva", family_name="Berg")

    answer = await _call(hass, "find_people", query="noor")
    assert [p["given_name"] for p in answer["people"]] == ["Tom", "Noor"]
    assert answer["people"][1]["id"] == noor
    assert answer["people"][1]["full_name"] == "Noor van der Berg"

    assert (await _call(hass, "find_people", query="nobody"))["people"] == []


@pytest.fixture
def birthday_calendar(hass: HomeAssistant) -> list[dict[str, Any]]:
    """A stand-in for a calendar entity; returns the calls it received."""
    calls: list[dict[str, Any]] = []
    events = [
        {"start": "2027-10-10", "end": "2027-10-11", "summary": "Noor van der Berg",
         "location": "Dorpsstraat 12-A, 1234 AB Ons Dorp", "description": "Likes horses"},
        # the same birthday a year later, and one with a time instead of a whole day
        {"start": "2028-10-10", "end": "2028-10-11", "summary": "Noor van der Berg",
         "location": "Dorpsstraat 12-A, 1234 AB Ons Dorp", "description": "Likes horses"},
        {"start": "2027-12-05T09:00:00+01:00", "end": "2027-12-05T10:00:00+01:00", "summary": "Eva"},
        {"start": "2027-08-24", "end": "2027-08-25", "summary": "Tom en Iris"},
    ]

    async def get_events(call: ServiceCall) -> dict[str, Any]:
        calls.append(dict(call.data))
        return {"calendar.birthdays": {"events": events}}

    hass.services.async_register(
        "calendar", "get_events", get_events, supports_response=SupportsResponse.ONLY
    )
    hass.states.async_set("calendar.birthdays", "off")
    return calls


async def _import(hass: HomeAssistant, **data: Any) -> Any:
    return await hass.services.async_call(
        DOMAIN, "import_calendar", data, blocking=True, return_response=True
    )


async def test_import_calendar(
    hass: HomeAssistant, book: AddressBook, birthday_calendar: list[dict[str, Any]]
) -> None:
    """A preview changes nothing; the import adds what the preview showed."""
    preview = await _import(hass, entity_id="calendar.birthdays")
    assert preview["dry_run"] is True
    assert [p["name"] for p in preview["people"]] == ["Noor van der Berg", "Eva", "Tom", "Iris"]
    assert preview["households"] == ["Dorpsstraat 12-A, 1234 AB Ons Dorp"]
    assert preview["events"] == [{"title": "Tom en Iris", "date": "--08-24"}]
    assert preview["attention"] == [{"title": "Tom en Iris", "reason": "several_names"}]
    assert book.to_dict() == AddressBook().to_dict()

    window = birthday_calendar[0]
    assert (window["end_date_time"] - window["start_date_time"]).days > 4 * 365

    done = await _import(hass, entity_id="calendar.birthdays", dry_run=False)
    assert done == {**preview, "dry_run": False}
    assert len(book.people) == 4
    birthdays = {str(p.birth_date) for p in book.people.values() if p.birth_date}
    assert birthdays == {"--10-10", "--12-05"}
    assert len(book.households) == 1
    assert len(book.events) == 1

    again = await _import(hass, entity_id="calendar.birthdays", dry_run=False)
    assert again["people"] == []
    assert len(again["skipped"]) == 3
    assert len(book.people) == 4


async def test_import_from_unknown_calendar(hass: HomeAssistant, book: AddressBook) -> None:
    """A calendar that does not exist is refused."""
    with pytest.raises(ServiceValidationError, match="Unknown calendar"):
        await _import(hass, entity_id="calendar.nothing")
    with pytest.raises(vol.Invalid):
        await _import(hass, entity_id="sensor.nothing")


async def test_without_an_address_book(hass: HomeAssistant) -> None:
    """The services say so when the address book is not set up."""
    assert await async_setup_component(hass, DOMAIN, {})
    with pytest.raises(ServiceValidationError, match="not set up"):
        await _call(hass, "set_person", given_name="Noor")
    with pytest.raises(ServiceValidationError, match="not set up"):
        await _call(hass, "find_people", query="noor")


async def test_services_are_described(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Every service and field is in services.yaml and in each translation."""
    registered = hass.services.async_services()[DOMAIN]
    expected: dict[str, set[str]] = {
        "find_people": {"query"},
        "import_calendar": {"entity_id", "dry_run"},
    }
    for kind in KINDS:
        expected[f"set_{kind.name}"] = {"id", *kind.fields}
        expected[f"remove_{kind.name}"] = {"id"}
    assert set(registered) == set(expected)

    described = yaml.safe_load((COMPONENT / "services.yaml").read_text(encoding="utf-8"))
    assert {name: set(body["fields"]) for name, body in described.items()} == expected

    strings = json.loads((COMPONENT / "strings.json").read_text(encoding="utf-8"))
    english = json.loads((COMPONENT / "translations" / "en.json").read_text(encoding="utf-8"))
    dutch = json.loads((COMPONENT / "translations" / "nl.json").read_text(encoding="utf-8"))
    assert strings == english
    for translation in (english, dutch):
        services = translation["services"]
        assert {name: set(body["fields"]) for name, body in services.items()} == expected
        for body in services.values():
            assert body["name"] and body["description"]
            assert all(f["name"] and f["description"] for f in body["fields"].values())
