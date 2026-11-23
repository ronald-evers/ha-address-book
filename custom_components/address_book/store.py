"""Keep the address book in Home Assistant's own storage.

One JSON file in ``.storage``, so it is part of every Home Assistant backup and
never leaves the system.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.storage import Store

from .const import DOMAIN
from .core.model import SCHEMA_VERSION, AddressBook

STORAGE_KEY = DOMAIN
STORAGE_VERSION = SCHEMA_VERSION
STORAGE_MINOR_VERSION = 1
SAVE_DELAY = 1.0  # seconds; several changes in a row become one write


class AddressBookLoadError(HomeAssistantError):
    """The stored address book cannot be used as it is."""


class _AddressBookStore(Store[dict[str, Any]]):
    """Storage with a migration path between schema versions."""

    async def _async_migrate_func(
        self,
        old_major_version: int,
        old_minor_version: int,
        old_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Bring data written by another version up to this one.

        A newer minor version only adds fields, which are ignored on load. A
        newer major version cannot be read: refuse rather than lose data.
        """
        if old_major_version > STORAGE_VERSION:
            raise AddressBookLoadError(
                f"The address book was saved by a newer version of the integration "
                f"(schema {old_major_version}, this version reads {STORAGE_VERSION})"
            )
        # Migrations from older major versions go here, one step at a time:
        # if old_major_version == 1: old_data = _migrate_1_to_2(old_data)
        return old_data


class AddressBookData:
    """The address book in memory, and its copy on disk."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.book = AddressBook()
        self._store = _AddressBookStore(
            hass,
            STORAGE_VERSION,
            STORAGE_KEY,
            minor_version=STORAGE_MINOR_VERSION,
        )
        self._dirty = False
        self._listeners: list[Callable[[], None]] = []

    async def async_load(self) -> None:
        """Read the address book; start empty when there is none yet.

        Every reference is checked on the way in. A file that does not hold
        together is refused and left untouched.
        """
        data = await self._store.async_load()
        if data is None:
            return
        try:
            self.book = AddressBook.from_dict(data)
        except (ValueError, TypeError, KeyError, AttributeError) as err:
            raise AddressBookLoadError(
                f"The stored address book is not consistent: {err}"
            ) from err

    @callback
    def async_schedule_save(self) -> None:
        """Write the address book shortly; call this after every change.

        Everything that shows the address book is told about the change too.
        """
        self._dirty = True
        self._store.async_delay_save(self._data_to_save, SAVE_DELAY)
        self.async_notify()

    @callback
    def async_add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Call ``listener`` after every change; returns how to stop that."""
        self._listeners.append(listener)

        @callback
        def remove() -> None:
            self._listeners.remove(listener)

        return remove

    @callback
    def async_notify(self) -> None:
        """Tell the listeners to look again: a change, or a new day."""
        for listener in list(self._listeners):
            listener()

    async def async_flush(self) -> None:
        """Write now if a change is still waiting to be written."""
        if self._dirty:
            await self._store.async_save(self._data_to_save())

    async def async_remove(self) -> None:
        """Delete the stored address book."""
        self._dirty = False
        await self._store.async_remove()

    @callback
    def _data_to_save(self) -> dict[str, Any]:
        self._dirty = False
        return self.book.to_dict()
