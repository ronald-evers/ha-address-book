"""Fire an event for every date that is today or a number of days away.

Once a day, at a set time, so an automation needs no template to find out who
has a birthday: it listens for ``address_book_reminder``.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_change
from homeassistant.util import dt as dt_util

from .const import (
    CONF_DAYS_AHEAD,
    CONF_REMINDER_TIME,
    DEFAULT_DAYS_AHEAD,
    DEFAULT_REMINDER_TIME,
    EVENT_REMINDER,
)
from .core.overview import entries
from .entity import today
from .store import AddressBookData

ATTR_DAYS_AHEAD = "days_ahead"


@callback
def async_setup_reminders(
    hass: HomeAssistant, entry: ConfigEntry[AddressBookData]
) -> CALLBACK_TYPE:
    """Start the daily reminder; returns how to stop it."""
    data = entry.runtime_data
    days_ahead = entry.options.get(CONF_DAYS_AHEAD, DEFAULT_DAYS_AHEAD)
    at = dt_util.parse_time(entry.options.get(CONF_REMINDER_TIME, DEFAULT_REMINDER_TIME))
    assert at is not None  # the options flow only stores valid times

    @callback
    def fire(now: datetime) -> None:
        start = today()
        for ahead in dict.fromkeys((days_ahead, 0)):  # early warnings first
            day = start + timedelta(days=ahead)
            for found in entries(data.book, day, day):
                hass.bus.async_fire(
                    EVENT_REMINDER, {**found.as_dict(start), ATTR_DAYS_AHEAD: ahead}
                )

    return async_track_time_change(
        hass, fire, hour=at.hour, minute=at.minute, second=0
    )
