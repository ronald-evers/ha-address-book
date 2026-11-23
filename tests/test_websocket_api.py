"""Tests for what the panel asks of the integration."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest
from freezegun.api import FrozenDateTimeFactory

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.typing import WebSocketGenerator

from custom_components.address_book.const import DOMAIN
from custom_components.address_book.core.model import AddressBook, Household
from custom_components.address_book.store import (
    STORAGE_KEY,
    STORAGE_MINOR_VERSION,
    STORAGE_VERSION,
)


@pytest.fixture
async def entry(
    hass: HomeAssistant,
    hass_storage: dict[str, Any],
    family: AddressBook,
    freezer: FrozenDateTimeFactory,
) -> MockConfigEntry:
    """The fictional family on 8 June 2026; Piet and Maria share an address."""
    await hass.config.async_set_time_zone("UTC")
    freezer.move_to("2026-06-08 12:00:00+00:00")
    family.put_household(
        Household(
            id="h-piet",
            street="Dorpsstraat",
            house_number="12",
            house_number_addition="A",
            postal_code="1234 AB",
            city="Ons Dorp",
        )
    )
    family.people["piet"].household_id = "h-piet"
    family.people["maria"].household_id = "h-piet"
    hass_storage[STORAGE_KEY] = {
        "version": STORAGE_VERSION,
        "minor_version": STORAGE_MINOR_VERSION,
        "key": STORAGE_KEY,
        "data": family.to_dict(),
    }
    config_entry = MockConfigEntry(domain=DOMAIN, title="Address Book")
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry


@pytest.fixture
async def ask(entry: MockConfigEntry, hass_ws_client: WebSocketGenerator):
    """Send a command and return the whole answer.

    ``entry`` comes first: it sets the clock, and the login must be made after that.
    """
    client = await hass_ws_client()

    async def _ask(command: str, **data: Any) -> dict[str, Any]:
        await client.send_json_auto_id({"type": f"address_book/{command}", **data})
        return await client.receive_json()

    return _ask


async def test_overview(ask) -> None:
    """Everyone sorted by family name, with birthday, age and address."""
    answer = await ask("overview")
    assert answer["success"]
    result = answer["result"]
    assert result["today"] == "2026-06-08"
    assert len(result["people"]) == 19

    piet = next(p for p in result["people"] if p["id"] == "piet")
    assert piet == {
        "id": "piet",
        "name": "Piet",
        "given_name": "Piet",
        "family_name": "",
        "nickname": "",
        "sort": ["", "piet", ""],
        "birth_date": "1960-06-15",
        "age": 65,
        "deceased": False,
        "next_birthday": "2026-06-15",
        "days_until_birthday": 7,
        "household_id": "h-piet",
        "address": "Dorpsstraat 12-A, 1234 AB Ons Dorp",
        "street_line": "Dorpsstraat 12-A",
        "city": "Ons Dorp",
    }
    lot = next(p for p in result["people"] if p["id"] == "lot")
    assert (lot["birth_date"], lot["age"], lot["next_birthday"]) == ("--06-21", None, "2026-06-21")

    (household,) = result["households"]
    assert household["address"] == "Dorpsstraat 12-A, 1234 AB Ons Dorp"
    assert [m["name"] for m in household["members"]] == ["Piet", "Maria"]
    assert [u["name"] for u in result["upcoming"]] == ["Piet", "Lot", "Rik"]


async def test_person(ask) -> None:
    """One person with housemates, direct family and what follows from it."""
    result = (await ask("person", person_id="piet"))["result"]
    assert result["person"]["name"] == "Piet"
    assert result["person"]["phones"] == []
    assert [m["name"] for m in result["household"]["members"]] == ["Piet", "Maria"]

    couples = {c["name"]: c for c in result["couples"]}
    assert couples["Maria"]["type"] == "spouse"
    assert (couples["Maria"]["since"], couples["Maria"]["years"]) == ("1986-09-12", 39)
    assert couples["Els"]["ended"] is True
    assert [c["name"] for c in result["children"]] == ["Rik", "Tom", "Eva"]
    assert [p["name"] for p in result["parents"]] == ["Henk", "Truus"]

    derived = {d["name"]: d["label"] for d in result["derived"]}
    assert derived["Anna"] == "sister"
    assert derived["Kees"] == "brother-in-law"
    assert derived["Noor"] == "granddaughter"
    assert derived["Iris"] == "daughter-in-law"
    assert derived["Sam"] == "nephew"
    assert "Vreemde" not in derived
    assert not {"Maria", "Tom", "Henk", "Piet"} & derived.keys()

    hidden = await ask("person", person_id="nobody")
    assert hidden["error"]["code"] == "not_found"


async def test_person_in_dutch(hass: HomeAssistant, ask) -> None:
    """Family words follow the language of Home Assistant."""
    hass.config.language = "nl"
    derived = {d["name"]: d["label"] for d in (await ask("person", person_id="piet"))["result"]["derived"]}
    assert derived["Kees"] == "zwager"
    assert derived["Lot"] == "nicht"


async def test_add_person(hass: HomeAssistant, entry: MockConfigEntry, ask) -> None:
    """A new person, at a new address, as the child of two people."""
    answer = await ask(
        "save_person",
        person={
            "given_name": "Juna",
            "family_name_prefix": "van der",
            "family_name": "Berg",
            "birth_date": "--06-08",
            "gender": "female",
            "phones": [{"value": "+31 20 555 0100", "label": ""}],
        },
        address={
            "mode": "new",
            "household": {
                "street": "Molenlaan",
                "house_number": "3",
                "postal_code": "1234 CD",
                "city": "Ons Dorp",
            },
        },
        family=[
            {"relation": "child_of", "person_id": "tom"},
            {"relation": "child_of", "person_id": "iris"},
        ],
    )
    assert answer["success"]
    book = entry.runtime_data.book
    juna = book.people[answer["result"]["id"]]
    assert juna.full_name == "Juna van der Berg"
    assert str(juna.birth_date) == "--06-08"
    assert book.households[juna.household_id].address_line == "Molenlaan 3, 1234 CD Ons Dorp"
    assert sorted(book.parent_ids(juna.id)) == ["iris", "tom"]

    # The sensors show her at once: it is her birthday today.
    assert hass.states.get("sensor.address_book_today").state == "1"

    detail = (await ask("person", person_id=juna.id))["result"]
    derived = {d["name"]: d["label"] for d in detail["derived"]}
    assert derived["Noor"] == "sister"
    assert derived["Piet"] == "grandfather"


async def test_other_family_links(entry: MockConfigEntry, ask) -> None:
    """Parent, spouse and partner are stored the right way round."""
    answer = await ask(
        "save_person",
        person={"given_name": "Mila"},
        family=[
            {"relation": "parent_of", "person_id": "vreemde"},
            {"relation": "spouse_of", "person_id": "bas"},
        ],
    )
    book = entry.runtime_data.book
    mila = answer["result"]["id"]
    assert book.child_ids(mila) == ["vreemde"]
    assert book.partner_ids(mila) == ["bas"]
    assert book.people[mila].household_id is None


@pytest.mark.parametrize(
    ("data", "message"),
    [
        ({"person": {"given_name": " "}}, "given name"),
        ({"person": {"family_name": "Berg"}}, "given name"),
        ({"person": {"given_name": "Juna", "birth_date": "8 juni"}}, "not a valid date"),
        (
            {"person": {"given_name": "Juna"}, "address": {"mode": "existing", "household_id": "gone"}},
            "unknown household",
        ),
        (
            {"person": {"given_name": "Juna"}, "address": {"mode": "new", "household": {}}},
            "needs at least",
        ),
        (
            {
                "person": {"given_name": "Juna"},
                "address": {"mode": "new", "household": {"street": "Kerkweg", "house_number_addition": "A"}},
            },
            "needs a house number",
        ),
        (
            {"person": {"given_name": "Juna"}, "family": [{"relation": "child_of", "person_id": "nobody"}]},
            "unknown person",
        ),
        (
            {"person": {"given_name": "Juna"}, "address": {"mode": "update", "household": {"city": "X"}}},
            "no address to change",
        ),
    ],
)
async def test_refused_changes_nothing(
    entry: MockConfigEntry, ask, data: dict[str, Any], message: str
) -> None:
    """A refused change leaves nothing behind: no person, no address, no link."""
    before = entry.runtime_data.book.to_dict()
    answer = await ask("save_person", **data)
    assert not answer["success"]
    assert answer["error"]["code"] == "invalid"
    assert message in answer["error"]["message"]
    assert entry.runtime_data.book.to_dict() == before


async def test_change_person(entry: MockConfigEntry, ask) -> None:
    """A change keeps what is not mentioned, also the address."""
    answer = await ask("save_person", person_id="piet", person={"nickname": "Pieter", "birth_date": ""})
    assert answer["result"] == {"id": "piet"}
    piet = entry.runtime_data.book.people["piet"]
    assert piet.nickname == "Pieter"
    assert piet.birth_date is None
    assert piet.household_id == "h-piet"
    assert entry.runtime_data.book.partner_ids("piet") == ["maria"]

    missing = await ask("save_person", person_id="nobody", person={"nickname": "x"})
    assert missing["error"]["code"] == "not_found"


async def test_addresses(entry: MockConfigEntry, ask) -> None:
    """Moving in with someone, correcting an address, and leaving one empty."""
    data = entry.runtime_data

    # Tom moves in with his parents.
    await ask("save_person", person_id="tom", person={}, address={"mode": "existing", "household_id": "h-piet"})
    assert data.book.people["tom"].household_id == "h-piet"

    # Correcting the address changes it for everyone living there.
    await ask(
        "save_person",
        person_id="tom",
        person={},
        address={"mode": "update", "household": {"house_number": "14", "house_number_addition": ""}},
    )
    assert data.book.households["h-piet"].address_line == "Dorpsstraat 14, 1234 AB Ons Dorp"
    assert data.book.people["maria"].household_id == "h-piet"

    # Tom moves out to a new address; the old one stays, others live there.
    answer = await ask(
        "save_person",
        person_id="tom",
        person={},
        address={"mode": "new", "household": {"street": "Molenlaan", "house_number": "3", "city": "Ons Dorp"}},
    )
    assert answer["success"]
    molenlaan = data.book.people["tom"].household_id
    assert set(data.book.households) == {"h-piet", molenlaan}

    # Once nobody lives at an address, it goes.
    await ask("save_person", person_id="tom", person={}, address={"mode": "none"})
    assert set(data.book.households) == {"h-piet"}
    assert data.book.people["tom"].household_id is None


async def test_delete_person(entry: MockConfigEntry, ask) -> None:
    """Removing someone removes their links, and an address left empty."""
    data = entry.runtime_data
    assert (await ask("delete_person", person_id="maria"))["success"]
    assert "maria" not in data.book.people
    assert data.book.partner_ids("piet") == []
    assert "h-piet" in data.book.households  # Piet still lives there

    assert (await ask("delete_person", person_id="piet"))["success"]
    assert data.book.households == {}
    assert (await ask("delete_person", person_id="piet"))["error"]["code"] == "not_found"


async def test_changes_are_saved(
    hass: HomeAssistant, entry: MockConfigEntry, hass_storage: dict[str, Any], ask
) -> None:
    """What the panel changes ends up in storage."""
    await ask("save_person", person={"given_name": "Juna"})
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    names = [p["given_name"] for p in hass_storage[STORAGE_KEY]["data"]["people"]]
    assert "Juna" in names


async def test_without_an_address_book(hass: HomeAssistant, hass_ws_client: WebSocketGenerator) -> None:
    """The commands say so when the address book is not set up."""
    assert await async_setup_component(hass, DOMAIN, {})
    client = await hass_ws_client()
    await client.send_json_auto_id({"type": "address_book/overview"})
    answer = await client.receive_json()
    assert answer["error"]["code"] == "not_set_up"


async def test_panel_in_the_sidebar(hass: HomeAssistant, hass_storage: dict[str, Any]) -> None:
    """The panel is for everyone, named after the language, and goes on unload."""
    hass.config.language = "nl"
    hass.config.components.add("frontend")
    config_entry = MockConfigEntry(domain=DOMAIN, title="Address Book")
    config_entry.add_to_hass(hass)
    with (
        patch("custom_components.address_book.panel.panel_custom.async_register_panel") as register,
        patch("custom_components.address_book.panel.frontend.async_remove_panel") as remove,
    ):
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
        register.assert_called_once()
        arguments = register.call_args.kwargs
        assert arguments["frontend_url_path"] == "address-book"
        assert arguments["webcomponent_name"] == "address-book-panel"
        assert arguments["sidebar_title"] == "Adresboek"
        assert arguments["require_admin"] is False
        assert arguments["module_url"].startswith("/address_book_static/address-book-panel.js?v=")

        assert await hass.config_entries.async_unload(config_entry.entry_id)
        await hass.async_block_till_done()
        remove.assert_called_once()


async def test_panel_file_is_served(hass: HomeAssistant, entry: MockConfigEntry, hass_client) -> None:
    """The panel's file can be fetched, and defines the element."""
    client = await hass_client()
    response = await client.get("/address_book_static/address-book-panel.js")
    assert response.status == 200
    assert 'customElements.define("address-book-panel"' in await response.text()
