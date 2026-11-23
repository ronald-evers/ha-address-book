"""Address Book: people, households, family relations and the dates that matter."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError

from .store import AddressBookData, AddressBookLoadError

type AddressBookConfigEntry = ConfigEntry[AddressBookData]


async def async_setup_entry(hass: HomeAssistant, entry: AddressBookConfigEntry) -> bool:
    """Set up Address Book from a config entry."""
    data = AddressBookData(hass)
    try:
        await data.async_load()
    except AddressBookLoadError as err:
        raise ConfigEntryError(str(err)) from err
    entry.runtime_data = data
    return True


async def async_unload_entry(hass: HomeAssistant, entry: AddressBookConfigEntry) -> bool:
    """Unload the config entry, writing any change that is still waiting."""
    await entry.runtime_data.async_flush()
    return True


async def async_remove_entry(hass: HomeAssistant, entry: AddressBookConfigEntry) -> None:
    """Delete the stored address book together with the integration.

    It holds personal data about other people, so nothing is left behind.
    Home Assistant backups made earlier still contain it.
    """
    await AddressBookData(hass).async_remove()
