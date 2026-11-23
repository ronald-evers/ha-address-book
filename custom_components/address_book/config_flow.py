"""Config flow for Address Book."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TimeSelector,
)

from .const import (
    CONF_DAYS_AHEAD,
    CONF_REMINDER_TIME,
    CONF_UPCOMING_DAYS,
    DEFAULT_DAYS_AHEAD,
    DEFAULT_REMINDER_TIME,
    DEFAULT_UPCOMING_DAYS,
    DOMAIN,
)


def _days(maximum: int) -> Any:
    return vol.All(
        NumberSelector(
            NumberSelectorConfig(
                min=0, max=maximum, step=1, mode=NumberSelectorMode.BOX
            )
        ),
        vol.Coerce(int),
    )


OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_UPCOMING_DAYS, default=DEFAULT_UPCOMING_DAYS): _days(366),
        vol.Required(CONF_DAYS_AHEAD, default=DEFAULT_DAYS_AHEAD): _days(60),
        vol.Required(CONF_REMINDER_TIME, default=DEFAULT_REMINDER_TIME): TimeSelector(),
    }
)


class AddressBookConfigFlow(ConfigFlow, domain=DOMAIN):
    """There is one address book per Home Assistant; nothing to ask."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm and create the single entry."""
        if user_input is not None:
            return self.async_create_entry(title="Address Book", data={})
        return self.async_show_form(step_id="user")

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the flow for the settings."""
        return AddressBookOptionsFlow()


class AddressBookOptionsFlow(OptionsFlow):
    """How far the sensor looks ahead, and when reminders fire."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the settings."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                OPTIONS_SCHEMA, self.config_entry.options
            ),
        )
