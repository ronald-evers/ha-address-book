"""Tests for keeping the address book in Home Assistant's storage."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.address_book.const import DOMAIN
from custom_components.address_book.core.model import AddressBook, Person
from custom_components.address_book.store import (
    SAVE_DELAY,
    STORAGE_KEY,
    STORAGE_MINOR_VERSION,
    STORAGE_VERSION,
)


def _stored(
    data: dict[str, Any],
    *,
    version: int = STORAGE_VERSION,
    minor_version: int = STORAGE_MINOR_VERSION,
) -> dict[str, Any]:
    return {
        "version": version,
        "minor_version": minor_version,
        "key": STORAGE_KEY,
        "data": data,
    }


async def _setup(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, title="Address Book")
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_starts_empty(hass: HomeAssistant, hass_storage: dict[str, Any]) -> None:
    """Without a file there is an empty address book, and nothing is written."""
    entry = await _setup(hass)
    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data.book.people == {}
    assert STORAGE_KEY not in hass_storage


async def test_loads_what_was_stored(
    hass: HomeAssistant, hass_storage: dict[str, Any], family: AddressBook
) -> None:
    """A stored address book comes back complete."""
    hass_storage[STORAGE_KEY] = _stored(family.to_dict())
    entry = await _setup(hass)
    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data.book.to_dict() == family.to_dict()


async def test_change_is_written_after_a_delay(
    hass: HomeAssistant, hass_storage: dict[str, Any]
) -> None:
    """A change is on disk shortly after it is made, not immediately."""
    entry = await _setup(hass)
    data = entry.runtime_data
    data.book.put_person(Person(id="noor", given_name="Noor"))
    data.async_schedule_save()
    assert STORAGE_KEY not in hass_storage

    async_fire_time_changed(
        hass, dt_util.utcnow() + timedelta(seconds=SAVE_DELAY + 1)
    )
    await hass.async_block_till_done()

    saved = hass_storage[STORAGE_KEY]
    assert saved["version"] == STORAGE_VERSION
    assert saved["minor_version"] == STORAGE_MINOR_VERSION
    assert [p["given_name"] for p in saved["data"]["people"]] == ["Noor"]


async def test_unload_writes_a_waiting_change(
    hass: HomeAssistant, hass_storage: dict[str, Any]
) -> None:
    """Nothing is lost when the entry unloads before the delay has passed."""
    entry = await _setup(hass)
    entry.runtime_data.book.put_person(Person(id="noor", given_name="Noor"))
    entry.runtime_data.async_schedule_save()

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert len(hass_storage[STORAGE_KEY]["data"]["people"]) == 1


async def test_survives_a_reload(
    hass: HomeAssistant, hass_storage: dict[str, Any]
) -> None:
    """What was entered is there again after a reload."""
    entry = await _setup(hass)
    entry.runtime_data.book.put_person(Person(id="noor", given_name="Noor"))
    entry.runtime_data.async_schedule_save()

    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.runtime_data.book.people["noor"].given_name == "Noor"


async def test_broken_reference_is_refused(
    hass: HomeAssistant, hass_storage: dict[str, Any]
) -> None:
    """A file pointing at a missing household is refused and left as it is."""
    broken = {
        "people": [{"id": "noor", "given_name": "Noor", "household_id": "gone"}]
    }
    hass_storage[STORAGE_KEY] = _stored(broken)
    entry = await _setup(hass)
    assert entry.state is ConfigEntryState.SETUP_ERROR
    assert hass_storage[STORAGE_KEY]["data"] == broken


async def test_newer_minor_version_opens(
    hass: HomeAssistant, hass_storage: dict[str, Any]
) -> None:
    """Data with fields from a newer minor version still opens."""
    newer = {"people": [{"id": "noor", "given_name": "Noor", "shoe_size": 24}]}
    hass_storage[STORAGE_KEY] = _stored(
        newer, minor_version=STORAGE_MINOR_VERSION + 1
    )
    entry = await _setup(hass)
    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data.book.people["noor"].given_name == "Noor"


async def test_newer_major_version_is_refused(
    hass: HomeAssistant, hass_storage: dict[str, Any]
) -> None:
    """Data from a newer schema is refused and left as it is."""
    newer = {"persons": []}
    hass_storage[STORAGE_KEY] = _stored(newer, version=STORAGE_VERSION + 1)
    entry = await _setup(hass)
    assert entry.state is ConfigEntryState.SETUP_ERROR
    assert hass_storage[STORAGE_KEY]["version"] == STORAGE_VERSION + 1
    assert hass_storage[STORAGE_KEY]["data"] == newer


async def test_removing_the_integration_deletes_the_data(
    hass: HomeAssistant, hass_storage: dict[str, Any], family: AddressBook
) -> None:
    """No personal data is left behind, also not a change still waiting."""
    hass_storage[STORAGE_KEY] = _stored(family.to_dict())
    entry = await _setup(hass)
    entry.runtime_data.book.put_person(Person(id="extra", given_name="Extra"))
    entry.runtime_data.async_schedule_save()

    assert await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    async_fire_time_changed(
        hass, dt_util.utcnow() + timedelta(seconds=SAVE_DELAY + 1)
    )
    await hass.async_block_till_done()
    assert STORAGE_KEY not in hass_storage
