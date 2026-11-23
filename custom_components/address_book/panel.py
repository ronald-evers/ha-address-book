"""The address book in the sidebar.

The panel is one JavaScript file without a build step, served from this
directory. It talks to the integration through ``websocket_api.py``.
"""

from __future__ import annotations

from pathlib import Path

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import DOMAIN

PANEL_URL_PATH = "address-book"
PANEL_ELEMENT = "address-book-panel"
PANEL_ICON = "mdi:book-account"
PANEL_FILE = "address-book-panel.js"
STATIC_URL = f"/{DOMAIN}_static"
_TITLES = {"en": "Address Book", "nl": "Adresboek"}

_FRONTEND_DIR = Path(__file__).parent / "frontend"


async def async_setup_static_path(hass: HomeAssistant) -> None:
    """Serve the panel's file; done once per run of Home Assistant."""
    if hass.http is None:
        return
    await hass.http.async_register_static_paths(
        [StaticPathConfig(STATIC_URL, str(_FRONTEND_DIR), cache_headers=False)]
    )


def _version() -> str:
    """Change the address when the file changes, so browsers fetch it again."""
    return str(int((_FRONTEND_DIR / PANEL_FILE).stat().st_mtime))


async def async_register_panel(hass: HomeAssistant) -> None:
    """Show the address book in the sidebar, for everyone who logs in."""
    if "frontend" not in hass.config.components:
        return
    version = await hass.async_add_executor_job(_version)
    language = hass.config.language.split("-")[0].lower()
    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=PANEL_URL_PATH,
        webcomponent_name=PANEL_ELEMENT,
        sidebar_title=_TITLES.get(language, _TITLES["en"]),
        sidebar_icon=PANEL_ICON,
        module_url=f"{STATIC_URL}/{PANEL_FILE}?v={version}",
        require_admin=False,
    )


def async_remove_panel(hass: HomeAssistant) -> None:
    """Take the address book out of the sidebar."""
    if "frontend" in hass.config.components:
        frontend.async_remove_panel(hass, PANEL_URL_PATH, warn_if_unknown=False)
