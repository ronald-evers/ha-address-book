"""What the calendar and the sensors have in common."""

from __future__ import annotations

from datetime import date

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .store import AddressBookData


def today() -> date:
    """Return the current day in Home Assistant's time zone."""
    return dt_util.now().date()


class AddressBookEntity(Entity):
    """An entity that shows the address book and follows its changes.

    There are only a few of these: people are records, not entities.
    """

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, entry: ConfigEntry[AddressBookData], key: str) -> None:
        self._data = entry.runtime_data
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Address Book",
            entry_type=DeviceEntryType.SERVICE,
        )

    async def async_added_to_hass(self) -> None:
        """Follow the address book from now on."""
        self._refresh()
        self.async_on_remove(self._data.async_add_listener(self._changed))

    @callback
    def _changed(self) -> None:
        self._refresh()
        self.async_write_ha_state()

    @callback
    def _refresh(self) -> None:
        """Work out again what to show; called on a change and on a new day."""
        raise NotImplementedError
