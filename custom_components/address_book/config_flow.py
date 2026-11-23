"""Config flow for Address Book."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import DOMAIN


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
