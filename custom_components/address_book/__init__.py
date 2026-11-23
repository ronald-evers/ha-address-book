"""Address Book: people, households, family relations and the dates that matter."""

from __future__ import annotations

from datetime import datetime

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN
from .panel import async_register_panel, async_remove_panel, async_setup_static_path
from .reminder import async_setup_reminders
from .services import async_setup_services
from .store import AddressBookData, AddressBookLoadError
from .websocket_api import async_setup_websocket_api

type AddressBookConfigEntry = ConfigEntry[AddressBookData]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
PLATFORMS = [Platform.CALENDAR, Platform.SENSOR]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the services and what the panel needs."""
    async_setup_services(hass)
    async_setup_websocket_api(hass)
    await async_setup_static_path(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: AddressBookConfigEntry) -> bool:
    """Set up Address Book from a config entry."""
    data = AddressBookData(hass)
    try:
        await data.async_load()
    except AddressBookLoadError as err:
        raise ConfigEntryError(str(err)) from err
    entry.runtime_data = data

    @callback
    def new_day(now: datetime) -> None:
        """Yesterday's birthday is over: let the entities look again."""
        data.async_notify()

    entry.async_on_unload(
        async_track_time_change(hass, new_day, hour=0, minute=0, second=0)
    )
    entry.async_on_unload(async_setup_reminders(hass, entry))
    entry.async_on_unload(entry.add_update_listener(_async_options_changed))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await async_register_panel(hass)
    return True


async def _async_options_changed(hass: HomeAssistant, entry: AddressBookConfigEntry) -> None:
    """Start again with the new settings."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: AddressBookConfigEntry) -> bool:
    """Unload the config entry, writing any change that is still waiting."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        async_remove_panel(hass)
        await entry.runtime_data.async_flush()
    return unloaded


async def async_remove_entry(hass: HomeAssistant, entry: AddressBookConfigEntry) -> None:
    """Delete the stored address book together with the integration.

    It holds personal data about other people, so nothing is left behind.
    Home Assistant backups made earlier still contain it.
    """
    await AddressBookData(hass).async_remove()
