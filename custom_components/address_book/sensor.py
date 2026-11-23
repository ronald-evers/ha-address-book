"""Summary sensors: the dates of today and of the coming period.

The state is the number of dates; the attribute ``occurrences`` lists them.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CONF_UPCOMING_DAYS, DEFAULT_UPCOMING_DAYS
from .core.overview import entries
from .entity import AddressBookEntity, today
from .store import AddressBookData

ATTR_OCCURRENCES = "occurrences"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[AddressBookData],
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add the two sensors."""
    upcoming_days = entry.options.get(CONF_UPCOMING_DAYS, DEFAULT_UPCOMING_DAYS)
    async_add_entities(
        [
            OccurrencesSensor(entry, "today", days=0, icon="mdi:cake-variant"),
            OccurrencesSensor(
                entry, "upcoming", days=upcoming_days, icon="mdi:calendar-heart"
            ),
        ]
    )


class OccurrencesSensor(AddressBookEntity, SensorEntity):
    """The dates from today up to and including a number of days ahead."""

    # Names, addresses and notes do not belong in the history database.
    _unrecorded_attributes = frozenset({ATTR_OCCURRENCES})

    def __init__(
        self, entry: ConfigEntry[AddressBookData], key: str, *, days: int, icon: str
    ) -> None:
        super().__init__(entry, key)
        self.entity_id = f"sensor.address_book_{key}"
        self._attr_translation_key = key
        self._attr_icon = icon
        self._days = days
        self._occurrences: list[dict[str, Any]] = []

    @callback
    def _refresh(self) -> None:
        start = today()
        found = entries(self._data.book, start, start + timedelta(days=self._days))
        self._occurrences = [entry.as_dict(start) for entry in found]

    @property
    def native_value(self) -> int:
        """Return the number of dates."""
        return len(self._occurrences)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the dates themselves."""
        return {ATTR_OCCURRENCES: self._occurrences}
