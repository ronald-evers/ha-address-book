"""The dates of the address book as a calendar.

The title is the name, the location the postal address on one line and the
description the age (when known) followed by the note.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .core.labels import occurrence_detail, occurrence_title
from .core.overview import Entry, entries
from .entity import AddressBookEntity, today
from .store import AddressBookData

ENTITY_ID = "calendar.address_book"
_LOOK_AHEAD = timedelta(days=366)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[AddressBookData],
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add the one calendar."""
    async_add_entities([AddressBookCalendar(entry)])


class AddressBookCalendar(AddressBookEntity, CalendarEntity):
    """Birthdays, wedding anniversaries, days of remembrance and events."""

    _attr_name = None  # the calendar is called after the address book itself

    def __init__(self, entry: ConfigEntry[AddressBookData]) -> None:
        super().__init__(entry, "calendar")
        self.entity_id = ENTITY_ID
        self._event: CalendarEvent | None = None

    @property
    def event(self) -> CalendarEvent | None:
        """Return the date of today, or else the next one."""
        return self._event

    @callback
    def _refresh(self) -> None:
        start = today()
        found = entries(self._data.book, start, start + _LOOK_AHEAD)
        self._event = self._calendar_event(found[0]) if found else None

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Return the dates in a period."""
        first = dt_util.as_local(start_date).date()
        last = (dt_util.as_local(end_date) - timedelta(microseconds=1)).date()
        return [
            self._calendar_event(entry)
            for entry in entries(self._data.book, first, max(first, last))
        ]

    def _calendar_event(self, entry: Entry) -> CalendarEvent:
        language = self.hass.config.language
        occurrence = entry.occurrence
        day: date = occurrence.date
        detail = occurrence_detail(occurrence.kind, occurrence.years, language)
        return CalendarEvent(
            start=day,
            end=day + timedelta(days=1),
            summary=occurrence_title(occurrence.kind, entry.name, language),
            description="\n".join(part for part in (detail, entry.notes) if part) or None,
            location=entry.address or None,
            uid=f"{occurrence.kind.value}:{occurrence.source_id}:{day.isoformat()}",
        )
