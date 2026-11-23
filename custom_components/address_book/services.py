"""Services to add, change, remove and look up records.

``set_*`` without an ``id`` creates a record and returns its id; with an ``id``
it changes only the fields that are given. The rules themselves live in
``core``: a service only translates between Home Assistant and the model.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

import voluptuous as vol

from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .core.calendar_import import CalendarEntry, plan_import
from .core.model import (
    Event,
    Gender,
    Group,
    Household,
    Person,
    Relationship,
    RelationshipType,
    new_id,
)
from .store import AddressBookData

ATTR_ID = "id"
ATTR_QUERY = "query"
SERVICE_FIND_PEOPLE = "find_people"
SERVICE_IMPORT_CALENDAR = "import_calendar"
ATTR_ENTITY_ID = "entity_id"
ATTR_DRY_RUN = "dry_run"
# Four years ahead, so a birthday on 29 February is seen as well.
_IMPORT_WINDOW = timedelta(days=4 * 366)

_NULLABLE_TEXT = vol.Any(None, cv.string)
_ID_LIST = vol.All(cv.ensure_list, [cv.string])
_CONTACT_POINTS = vol.All(
    cv.ensure_list,
    [
        vol.Schema(
            {
                vol.Required("value"): cv.string,
                vol.Optional("label", default=""): cv.string,
            }
        )
    ],
)


@dataclass(frozen=True)
class _Kind:
    """One kind of record and the fields its services accept."""

    name: str  # "person": gives set_person, remove_person, put_person
    record: type
    collection: str  # the dict on AddressBook
    fields: dict[str, Any]
    required: tuple[str, ...] = ()  # needed when creating
    nullable: frozenset[str] = frozenset()  # an empty text clears these


KINDS: tuple[_Kind, ...] = (
    _Kind(
        name="person",
        record=Person,
        collection="people",
        fields={
            "given_name": cv.string,
            "family_name_prefix": cv.string,
            "family_name": cv.string,
            "nickname": cv.string,
            "gender": vol.Any(None, "", vol.In([g.value for g in Gender])),
            "birth_date": _NULLABLE_TEXT,
            "death_date": _NULLABLE_TEXT,
            "deceased": cv.boolean,
            "emails": _CONTACT_POINTS,
            "phones": _CONTACT_POINTS,
            "household_id": _NULLABLE_TEXT,
            "group_ids": _ID_LIST,
            "send_birthday_card": cv.boolean,
            "notes": cv.string,
        },
        required=("given_name",),
        nullable=frozenset({"gender", "birth_date", "death_date", "household_id"}),
    ),
    _Kind(
        name="household",
        record=Household,
        collection="households",
        fields={
            "name": cv.string,
            "street": cv.string,
            "house_number": cv.string,
            "house_number_addition": cv.string,
            "street2": cv.string,
            "postal_code": cv.string,
            "city": cv.string,
            "region": cv.string,
            "country": cv.string,
            "address_verified_on": _NULLABLE_TEXT,
            "send_seasonal_card": cv.boolean,
            "notes": cv.string,
        },
        nullable=frozenset({"address_verified_on"}),
    ),
    _Kind(
        name="group",
        record=Group,
        collection="groups",
        fields={"name": cv.string, "description": cv.string},
        required=("name",),
    ),
    _Kind(
        name="relationship",
        record=Relationship,
        collection="relationships",
        fields={
            "type": vol.In([t.value for t in RelationshipType]),
            "from_id": cv.string,
            "to_id": cv.string,
            "start_date": _NULLABLE_TEXT,
            "end_date": _NULLABLE_TEXT,
            "ended": cv.boolean,
            "label": cv.string,
            "notes": cv.string,
        },
        required=("type", "from_id", "to_id"),
        nullable=frozenset({"start_date", "end_date"}),
    ),
    _Kind(
        name="event",
        record=Event,
        collection="events",
        fields={
            "title": cv.string,
            "date": cv.string,
            "yearly": cv.boolean,
            "person_ids": _ID_LIST,
            "notes": cv.string,
        },
        required=("title", "date"),
    ),
)


def _loaded(hass: HomeAssistant) -> AddressBookData:
    """Return the address book, or explain that there is none."""
    entries = hass.config_entries.async_loaded_entries(DOMAIN)
    if not entries:
        raise ServiceValidationError("The address book is not set up")
    return entries[0].runtime_data


def _set_handler(kind: _Kind):
    async def handle(call: ServiceCall) -> ServiceResponse:
        data = _loaded(call.hass)
        records = getattr(data.book, kind.collection)
        fields = {
            key: None if key in kind.nullable and value == "" else value
            for key, value in call.data.items()
            if key != ATTR_ID
        }
        record_id = call.data.get(ATTR_ID)
        if record_id is None:
            if missing := [name for name in kind.required if name not in fields]:
                raise ServiceValidationError(
                    f"A new {kind.name} needs: {', '.join(missing)}"
                )
            merged = {ATTR_ID: new_id(), **fields}
        elif record_id in records:
            merged = {**records[record_id].to_dict(), **fields}
        else:
            raise ServiceValidationError(f"Unknown {kind.name}: {record_id}")

        try:
            record = kind.record.from_dict(merged)
            getattr(data.book, f"put_{kind.name}")(record)
        except (ValueError, TypeError) as err:
            raise ServiceValidationError(str(err)) from err

        data.async_schedule_save()
        return {ATTR_ID: record.id} if call.return_response else None

    return handle


def _remove_handler(kind: _Kind):
    async def handle(call: ServiceCall) -> None:
        data = _loaded(call.hass)
        record_id = call.data[ATTR_ID]
        if record_id not in getattr(data.book, kind.collection):
            raise ServiceValidationError(f"Unknown {kind.name}: {record_id}")
        getattr(data.book, f"remove_{kind.name}")(record_id)
        data.async_schedule_save()

    return handle


async def _find_people(call: ServiceCall) -> ServiceResponse:
    book = _loaded(call.hass).book
    return {
        "people": [
            {**person.to_dict(), "full_name": person.full_name}
            for person in book.find_people(call.data[ATTR_QUERY])
        ]
    }


async def _import_calendar(call: ServiceCall) -> ServiceResponse:
    """Read a birthday calendar; the calendar itself is never changed."""
    data = _loaded(call.hass)
    entity_id = call.data[ATTR_ENTITY_ID]
    if call.hass.states.get(entity_id) is None:
        raise ServiceValidationError(f"Unknown calendar: {entity_id}")
    start = dt_util.start_of_local_day()
    answer = await call.hass.services.async_call(
        "calendar",
        "get_events",
        {
            ATTR_ENTITY_ID: entity_id,
            "start_date_time": start,
            "end_date_time": start + _IMPORT_WINDOW,
        },
        blocking=True,
        return_response=True,
        context=call.context,
    )
    entries = []
    for item in (answer or {}).get(entity_id, {}).get("events", []):
        day = date.fromisoformat(str(item["start"])[:10])
        entries.append(
            CalendarEntry(
                title=item.get("summary") or "",
                month=day.month,
                day=day.day,
                location=item.get("location") or "",
                description=item.get("description") or "",
            )
        )

    plan = plan_import(data.book, entries)
    dry_run = call.data[ATTR_DRY_RUN]
    summary = plan.summary(data.book)
    if not dry_run:
        plan.apply(data.book)
        data.async_schedule_save()
    return {ATTR_DRY_RUN: dry_run, **summary}


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register the services; they exist as long as Home Assistant runs."""
    for kind in KINDS:
        hass.services.async_register(
            DOMAIN,
            f"set_{kind.name}",
            _set_handler(kind),
            schema=vol.Schema(
                {
                    vol.Optional(ATTR_ID): cv.string,
                    **{vol.Optional(key): rule for key, rule in kind.fields.items()},
                }
            ),
            supports_response=SupportsResponse.OPTIONAL,
        )
        hass.services.async_register(
            DOMAIN,
            f"remove_{kind.name}",
            _remove_handler(kind),
            schema=vol.Schema({vol.Required(ATTR_ID): cv.string}),
        )
    hass.services.async_register(
        DOMAIN,
        SERVICE_FIND_PEOPLE,
        _find_people,
        schema=vol.Schema({vol.Required(ATTR_QUERY): cv.string}),
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_IMPORT_CALENDAR,
        _import_calendar,
        schema=vol.Schema(
            {
                vol.Required(ATTR_ENTITY_ID): cv.entity_domain("calendar"),
                vol.Optional(ATTR_DRY_RUN, default=True): cv.boolean,
            }
        ),
        supports_response=SupportsResponse.ONLY,
    )
