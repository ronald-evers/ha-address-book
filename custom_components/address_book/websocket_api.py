"""What the panel needs: the people, one person in full, saving and removing.

A change is worked out on a copy of the address book and only then put in
place, so a refused change leaves nothing half done.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from .const import CONF_UPCOMING_DAYS, DEFAULT_UPCOMING_DAYS, DOMAIN
from .core.dates import age_on, next_occurrence
from .core.kinship import kinship
from .core.labels import kinship_label
from .core.model import (
    AddressBook,
    Household,
    Person,
    Relationship,
    RelationshipType,
    new_id,
)
from .core.overview import entries
from .entity import today
from .store import AddressBookData

ERR_NOT_SET_UP = "not_set_up"
ERR_NOT_FOUND = "not_found"
ERR_INVALID = "invalid"

ADDRESS_KEEP = "keep"
ADDRESS_NONE = "none"
ADDRESS_EXISTING = "existing"
ADDRESS_NEW = "new"
ADDRESS_UPDATE = "update"

# How the new person relates to someone already in the address book.
FAMILY_CHILD_OF = "child_of"
FAMILY_PARENT_OF = "parent_of"
FAMILY_SPOUSE_OF = "spouse_of"
FAMILY_PARTNER_OF = "partner_of"

_PERSON_FIELDS = {
    vol.Optional("given_name"): str,
    vol.Optional("family_name_prefix"): str,
    vol.Optional("family_name"): str,
    vol.Optional("nickname"): str,
    vol.Optional("gender"): vol.Any(None, "male", "female", "other"),
    vol.Optional("birth_date"): vol.Any(None, str),
    vol.Optional("emails"): [{vol.Required("value"): str, vol.Optional("label"): str}],
    vol.Optional("phones"): [{vol.Required("value"): str, vol.Optional("label"): str}],
    vol.Optional("send_birthday_card"): bool,
    vol.Optional("notes"): str,
}
_HOUSEHOLD_FIELDS = {
    vol.Optional("street"): str,
    vol.Optional("house_number"): str,
    vol.Optional("house_number_addition"): str,
    vol.Optional("street2"): str,
    vol.Optional("postal_code"): str,
    vol.Optional("city"): str,
    vol.Optional("region"): str,
    vol.Optional("country"): str,
    vol.Optional("send_seasonal_card"): bool,
}


@callback
def async_setup_websocket_api(hass: HomeAssistant) -> None:
    """Register the commands; they exist as long as Home Assistant runs."""
    websocket_api.async_register_command(hass, ws_overview)
    websocket_api.async_register_command(hass, ws_person)
    websocket_api.async_register_command(hass, ws_save_person)
    websocket_api.async_register_command(hass, ws_delete_person)


def _loaded(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> tuple[AddressBookData, int] | None:
    """Return the address book and its settings, or answer that there is none."""
    loaded = hass.config_entries.async_loaded_entries(DOMAIN)
    if not loaded:
        connection.send_error(msg["id"], ERR_NOT_SET_UP, "The address book is not set up")
        return None
    entry = loaded[0]
    return entry.runtime_data, entry.options.get(CONF_UPCOMING_DAYS, DEFAULT_UPCOMING_DAYS)


def _person_row(book: AddressBook, person: Person, on: date) -> dict[str, Any]:
    """One line in the list of people."""
    birth = person.birth_date
    birthday = next_occurrence(birth, on) if birth is not None else None
    if person.is_deceased:
        birthday = None
    household = (
        book.households[person.household_id] if person.household_id is not None else None
    )
    return {
        "id": person.id,
        "name": person.full_name,
        "given_name": person.given_name,
        "family_name": person.family_name,
        "nickname": person.nickname,
        "sort": list(person.sort_key),
        "birth_date": str(birth) if birth is not None else None,
        "age": age_on(birth, on) if birth is not None and not person.is_deceased else None,
        "deceased": person.is_deceased,
        "next_birthday": birthday.isoformat() if birthday is not None else None,
        "days_until_birthday": (birthday - on).days if birthday is not None else None,
        "household_id": person.household_id,
        "address": household.address_line if household is not None else "",
        "street_line": household.street_line if household is not None else "",
        "city": household.city if household is not None else "",
    }


def _household_row(book: AddressBook, household: Household) -> dict[str, Any]:
    return {
        **household.to_dict(),
        "address": household.address_line,
        "street_line": household.street_line,
        "members": [
            {"id": member.id, "name": member.full_name, "given_name": member.given_name}
            for member in book.household_members(household.id)
        ],
    }


@websocket_api.websocket_command({vol.Required("type"): "address_book/overview"})
@callback
def ws_overview(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Everyone, every address, and the dates that are coming up."""
    if (loaded := _loaded(hass, connection, msg)) is None:
        return
    data, upcoming_days = loaded
    book, on = data.book, today()
    people = sorted(book.people.values(), key=lambda p: p.sort_key)
    connection.send_result(
        msg["id"],
        {
            "today": on.isoformat(),
            "upcoming_days": upcoming_days,
            "people": [_person_row(book, person, on) for person in people],
            "households": [_household_row(book, h) for h in book.households.values()],
            "upcoming": [
                entry.as_dict(on)
                for entry in entries(book, on, on + timedelta(days=upcoming_days))
            ],
        },
    )


@websocket_api.websocket_command(
    {vol.Required("type"): "address_book/person", vol.Required("person_id"): str}
)
@callback
def ws_person(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """One person with their address, housemates and family."""
    if (loaded := _loaded(hass, connection, msg)) is None:
        return
    book, on = loaded[0].book, today()
    person = book.people.get(msg["person_id"])
    if person is None:
        connection.send_error(msg["id"], ERR_NOT_FOUND, "Unknown person")
        return
    language = hass.config.language

    def short(other: Person) -> dict[str, Any]:
        birth = other.birth_date
        return {
            "id": other.id,
            "name": other.full_name,
            "age": age_on(birth, on) if birth is not None and not other.is_deceased else None,
            "deceased": other.is_deceased,
        }

    couples = []
    for relationship in book.couple_relationships(person.id, current_only=False):
        other = book.people[relationship.other(person.id)]
        start = relationship.start_date
        couples.append(
            {
                **short(other),
                "relationship_id": relationship.id,
                "type": relationship.type.value,
                "ended": relationship.ended,
                "since": str(start) if start is not None else None,
                "years": age_on(start, on) if start is not None else None,
            }
        )

    direct = {person.id, *book.parent_ids(person.id), *book.child_ids(person.id)}
    direct.update(book.partner_ids(person.id, current_only=False))
    derived = []
    for other in sorted(book.people.values(), key=lambda p: p.sort_key):
        if other.id in direct:
            continue
        relation = kinship(book, person.id, other.id)
        if relation is None:
            continue
        derived.append(
            {
                **short(other),
                "kin": relation.kin.value,
                "label": kinship_label(relation, other.gender, language),
                "distance": relation.up + relation.down,
            }
        )
    derived.sort(key=lambda item: item["distance"])

    household = None
    if person.household_id is not None:
        household = _household_row(book, book.households[person.household_id])

    connection.send_result(
        msg["id"],
        {
            "person": {**person.to_dict(), **_person_row(book, person, on)},
            "household": household,
            "couples": couples,
            "children": [short(child) for child in book.children_of(person.id)],
            "parents": [short(parent) for parent in book.parents_of(person.id)],
            "derived": derived,
        },
    )


def _prune_household(book: AddressBook, household_id: str | None) -> None:
    """Remove an address nobody lives at any more."""
    if household_id is not None and household_id in book.households:
        if not book.household_members(household_id):
            book.remove_household(household_id)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "address_book/save_person",
        vol.Optional("person_id"): str,
        vol.Required("person"): _PERSON_FIELDS,
        vol.Optional("address", default={"mode": ADDRESS_KEEP}): vol.Any(
            {vol.Required("mode"): vol.Any(ADDRESS_KEEP, ADDRESS_NONE)},
            {vol.Required("mode"): ADDRESS_EXISTING, vol.Required("household_id"): str},
            {
                vol.Required("mode"): vol.Any(ADDRESS_NEW, ADDRESS_UPDATE),
                vol.Required("household"): _HOUSEHOLD_FIELDS,
            },
        ),
        vol.Optional("family", default=list): [
            {
                vol.Required("relation"): vol.Any(
                    FAMILY_CHILD_OF, FAMILY_PARENT_OF, FAMILY_SPOUSE_OF, FAMILY_PARTNER_OF
                ),
                vol.Required("person_id"): str,
            }
        ],
    }
)
@callback
def ws_save_person(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Add a person, or change one; with where they live and whose family they are."""
    if (loaded := _loaded(hass, connection, msg)) is None:
        return
    data = loaded[0]
    book = AddressBook.from_dict(data.book.to_dict())  # work on a copy
    person_id = msg.get("person_id")
    address = msg["address"]

    try:
        if person_id is None:
            fields = {"id": new_id(), **msg["person"]}
            if "given_name" not in fields:
                raise ValueError("a person needs a given name")
            previous_household = None
        elif person_id in book.people:
            previous_household = book.people[person_id].household_id
            fields = {**book.people[person_id].to_dict(), **msg["person"]}
        else:
            connection.send_error(msg["id"], ERR_NOT_FOUND, "Unknown person")
            return
        if fields.get("birth_date") == "":
            fields["birth_date"] = None

        mode = address["mode"]
        if mode == ADDRESS_NONE:
            fields["household_id"] = None
        elif mode == ADDRESS_EXISTING:
            fields["household_id"] = address["household_id"]
        elif mode == ADDRESS_NEW:
            household = Household.from_dict({"id": new_id(), **address["household"]})
            if not household.address_line:
                raise ValueError("a new address needs at least a street or a city")
            book.put_household(household)
            fields["household_id"] = household.id
        elif mode == ADDRESS_UPDATE:
            if previous_household is None:
                raise ValueError("this person has no address to change")
            current = book.households[previous_household]
            book.put_household(
                Household.from_dict({**current.to_dict(), **address["household"]})
            )

        person = book.put_person(Person.from_dict(fields))

        for link in msg["family"]:
            relation, other_id = link["relation"], link["person_id"]
            if relation == FAMILY_CHILD_OF:
                kind, from_id, to_id = RelationshipType.PARENT, other_id, person.id
            elif relation == FAMILY_PARENT_OF:
                kind, from_id, to_id = RelationshipType.PARENT, person.id, other_id
            elif relation == FAMILY_SPOUSE_OF:
                kind, from_id, to_id = RelationshipType.SPOUSE, person.id, other_id
            else:
                kind, from_id, to_id = RelationshipType.PARTNER, person.id, other_id
            book.put_relationship(
                Relationship(id=new_id(), type=kind, from_id=from_id, to_id=to_id)
            )

        if previous_household != person.household_id:
            _prune_household(book, previous_household)
    except (ValueError, TypeError) as err:
        connection.send_error(msg["id"], ERR_INVALID, str(err))
        return

    data.book = book
    data.async_schedule_save()
    connection.send_result(msg["id"], {"id": person.id})


@websocket_api.websocket_command(
    {vol.Required("type"): "address_book/delete_person", vol.Required("person_id"): str}
)
@callback
def ws_delete_person(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Remove a person with their relationships; an address left empty goes too."""
    if (loaded := _loaded(hass, connection, msg)) is None:
        return
    data = loaded[0]
    book = AddressBook.from_dict(data.book.to_dict())
    person = book.people.get(msg["person_id"])
    if person is None:
        connection.send_error(msg["id"], ERR_NOT_FOUND, "Unknown person")
        return
    book.remove_person(person.id)
    _prune_household(book, person.household_id)
    data.book = book
    data.async_schedule_save()
    connection.send_result(msg["id"], {})
