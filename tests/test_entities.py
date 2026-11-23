"""Tests for the calendar, the sensors, the reminder event and the settings."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pytest
from freezegun.api import FrozenDateTimeFactory

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_capture_events,
    async_fire_time_changed,
)

from custom_components.address_book.const import DOMAIN, EVENT_REMINDER
from custom_components.address_book.core.model import AddressBook, Household
from custom_components.address_book.store import (
    STORAGE_KEY,
    STORAGE_MINOR_VERSION,
    STORAGE_VERSION,
)

CALENDAR = "calendar.address_book"
TODAY = "sensor.address_book_today"
UPCOMING = "sensor.address_book_upcoming"


@pytest.fixture
async def entry(
    hass: HomeAssistant,
    hass_storage: dict[str, Any],
    family: AddressBook,
    freezer: FrozenDateTimeFactory,
) -> MockConfigEntry:
    """The fictional family on Monday 8 June 2026, with an address for Piet."""
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
    family.people["piet"].notes = "Likes sailing"
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


async def _move_to(hass: HomeAssistant, freezer: FrozenDateTimeFactory, when: str) -> None:
    moment = datetime.fromisoformat(when)
    freezer.move_to(moment)
    async_fire_time_changed(hass, moment)
    await hass.async_block_till_done()


async def test_sensors(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """The state counts the dates; the attribute lists them."""
    assert hass.states.get(TODAY).state == "0"
    assert hass.states.get(TODAY).attributes["occurrences"] == []

    upcoming = hass.states.get(UPCOMING)
    assert upcoming.state == "3"
    rows = upcoming.attributes["occurrences"]
    assert [(r["name"], r["date"], r["days"]) for r in rows] == [
        ("Piet", "2026-06-15", 7),
        ("Lot", "2026-06-21", 13),
        ("Rik", "2026-07-07", 29),
    ]
    assert rows[0] == {
        "name": "Piet",
        "date": "2026-06-15",
        "days": 7,
        "kind": "birthday",
        "years": 66,
        "milestone": False,
        "address": "Dorpsstraat 12-A, 1234 AB Ons Dorp",
        "notes": "Likes sailing",
        "person_ids": ["piet"],
    }
    assert rows[1]["years"] is None  # Lot's year of birth is unknown


async def test_sensors_follow_changes(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """A change through a service shows at once."""
    await hass.services.async_call(
        DOMAIN,
        "set_person",
        {"given_name": "Juna", "birth_date": "2016-06-08"},
        blocking=True,
    )
    today = hass.states.get(TODAY)
    assert today.state == "1"
    assert today.attributes["occurrences"][0]["years"] == 10
    assert hass.states.get(UPCOMING).state == "4"
    assert hass.states.get(CALENDAR).state == "on"


async def test_new_day(
    hass: HomeAssistant, entry: MockConfigEntry, freezer: FrozenDateTimeFactory
) -> None:
    """At midnight the sensors and the calendar move on."""
    assert hass.states.get(CALENDAR).state == "off"
    await _move_to(hass, freezer, "2026-06-15 00:00:00+00:00")
    assert hass.states.get(TODAY).state == "1"
    assert hass.states.get(TODAY).attributes["occurrences"][0]["days"] == 0
    assert hass.states.get(CALENDAR).state == "on"
    assert hass.states.get(CALENDAR).attributes["message"] == "Piet"

    await _move_to(hass, freezer, "2026-06-16 00:00:00+00:00")
    assert hass.states.get(TODAY).state == "0"
    assert hass.states.get(CALENDAR).attributes["message"] == "Lot"


async def _events(hass: HomeAssistant, start: str, end: str) -> list[dict[str, Any]]:
    answer = await hass.services.async_call(
        "calendar",
        "get_events",
        {"entity_id": CALENDAR, "start_date_time": start, "end_date_time": end},
        blocking=True,
        return_response=True,
    )
    return answer[CALENDAR]["events"]


async def test_calendar(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Title is the name, location the address, description the age and the note."""
    state = hass.states.get(CALENDAR)
    assert state.attributes["message"] == "Piet"
    assert state.attributes["all_day"] is True
    assert state.attributes["location"] == "Dorpsstraat 12-A, 1234 AB Ons Dorp"

    june = await _events(hass, "2026-06-01 00:00:00", "2026-07-01 00:00:00")
    assert june == [
        {
            "start": "2026-06-01",
            "end": "2026-06-02",
            "summary": "Wedding anniversary: Anna & Kees",
            "description": "36 years married",
        },
        {
            "start": "2026-06-15",
            "end": "2026-06-16",
            "summary": "Piet",
            "description": "Turns 66\nLikes sailing",
            "location": "Dorpsstraat 12-A, 1234 AB Ons Dorp",
        },
        {"start": "2026-06-21", "end": "2026-06-22", "summary": "Lot"},
    ]
    # A period that ends at midnight does not include the day that starts then.
    assert await _events(hass, "2026-06-14 00:00:00", "2026-06-15 00:00:00") == []
    assert len(await _events(hass, "2026-06-15 00:00:00", "2026-06-16 00:00:00")) == 1


async def test_calendar_in_dutch(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """The words follow the language of Home Assistant."""
    hass.config.language = "nl"
    june = await _events(hass, "2026-06-01 00:00:00", "2026-06-16 00:00:00")
    assert [(e["summary"], e["description"].split("\n")[0]) for e in june] == [
        ("Trouwdag: Anna & Kees", "36 jaar getrouwd"),
        ("Piet", "Wordt 66"),
    ]


async def test_reminders(
    hass: HomeAssistant, entry: MockConfigEntry, freezer: FrozenDateTimeFactory
) -> None:
    """An event a week ahead and one on the day itself, at nine in the morning."""
    reminders = async_capture_events(hass, EVENT_REMINDER)

    await _move_to(hass, freezer, "2026-06-09 08:59:00+00:00")
    assert reminders == []

    # Tuesday 9 June: nothing today, nothing in a week.
    await _move_to(hass, freezer, "2026-06-09 09:00:00+00:00")
    assert reminders == []

    # Sunday 14 June: Lot has her birthday in a week.
    await _move_to(hass, freezer, "2026-06-14 09:00:00+00:00")
    assert [(e.data["name"], e.data["days_ahead"], e.data["days"]) for e in reminders] == [
        ("Lot", 7, 7)
    ]

    reminders.clear()
    await _move_to(hass, freezer, "2026-06-15 09:00:00+00:00")
    assert len(reminders) == 1
    assert reminders[0].data == {
        "name": "Piet",
        "date": "2026-06-15",
        "days": 0,
        "days_ahead": 0,
        "kind": "birthday",
        "years": 66,
        "milestone": False,
        "address": "Dorpsstraat 12-A, 1234 AB Ons Dorp",
        "notes": "Likes sailing",
        "person_ids": ["piet"],
    }


async def test_milestone_reminder(
    hass: HomeAssistant, entry: MockConfigEntry, freezer: FrozenDateTimeFactory
) -> None:
    """A milestone is flagged, also a week ahead."""
    reminders = async_capture_events(hass, EVENT_REMINDER)
    await _move_to(hass, freezer, "2030-06-08 09:00:00+00:00")
    assert [(e.data["name"], e.data["years"], e.data["milestone"]) for e in reminders] == [
        ("Piet", 70, True)
    ]


async def test_settings(
    hass: HomeAssistant, entry: MockConfigEntry, freezer: FrozenDateTimeFactory
) -> None:
    """The settings change the sensor's period and when reminders fire."""
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"upcoming_days": 10, "days_ahead": 0, "reminder_time": "07:30:00"},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.options == {
        "upcoming_days": 10,
        "days_ahead": 0,
        "reminder_time": "07:30:00",
    }
    assert hass.states.get(UPCOMING).state == "1"

    reminders = async_capture_events(hass, EVENT_REMINDER)
    await _move_to(hass, freezer, "2026-06-14 07:30:00+00:00")
    assert reminders == []  # no early warning any more
    await _move_to(hass, freezer, "2026-06-15 07:30:00+00:00")
    assert [(e.data["name"], e.data["days_ahead"]) for e in reminders] == [("Piet", 0)]
    assert dt_util.now().hour == 7


async def test_unload_removes_entities(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """After unloading, nothing keeps showing the address book."""
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    for entity_id in (CALENDAR, TODAY, UPCOMING):
        assert hass.states.get(entity_id).state == "unavailable"
