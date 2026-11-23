"""Data model for the address book.

Pure Python: nothing in ``core`` imports Home Assistant, so the model and its
rules can be tested and reasoned about on their own. See ``docs/data-model.md``.
"""

from __future__ import annotations

import calendar
import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field, fields, is_dataclass
from datetime import date
from enum import StrEnum
from typing import Any, ClassVar, Self

SCHEMA_VERSION = 1


def new_id() -> str:
    """Return a new unique record id."""
    return uuid.uuid4().hex


# --------------------------------------------------------------------------- #
# Partial dates
# --------------------------------------------------------------------------- #

_FULL = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
_NO_YEAR = re.compile(r"^--(\d{2})-(\d{2})$")
_YEAR_ONLY = re.compile(r"^(\d{4})$")


@dataclass(frozen=True, order=True)
class PartialDate:
    """A date of which the year or the day may be unknown.

    Three shapes are allowed, written the way vCard writes them:

    * ``1980-05-17`` – fully known
    * ``--05-17``    – day known, year unknown ("her birthday is 17 May")
    * ``1980``       – only the year known
    """

    year: int | None = None
    month: int | None = None
    day: int | None = None

    def __post_init__(self) -> None:
        if (self.month is None) != (self.day is None):
            raise ValueError("month and day must be given together")
        if self.month is None and self.year is None:
            raise ValueError("a date needs at least a year or a month and day")
        if self.year is not None and not 1 <= self.year <= 9999:
            raise ValueError(f"year out of range: {self.year}")
        if self.month is not None and self.day is not None:
            if not 1 <= self.month <= 12:
                raise ValueError(f"month out of range: {self.month}")
            # Without a year, 29 February is allowed: check against a leap year.
            reference_year = self.year if self.year is not None else 2000
            if not 1 <= self.day <= calendar.monthrange(reference_year, self.month)[1]:
                raise ValueError(f"day out of range: {self}")

    @classmethod
    def parse(cls, value: str) -> PartialDate:
        """Parse ``YYYY-MM-DD``, ``--MM-DD`` or ``YYYY``."""
        text = value.strip()
        if match := _FULL.match(text):
            return cls(int(match[1]), int(match[2]), int(match[3]))
        if match := _NO_YEAR.match(text):
            return cls(None, int(match[1]), int(match[2]))
        if match := _YEAR_ONLY.match(text):
            return cls(int(match[1]))
        raise ValueError(f"not a valid date: {value!r}")

    @classmethod
    def from_date(cls, value: date) -> PartialDate:
        """Build a fully known partial date from a ``date``."""
        return cls(value.year, value.month, value.day)

    @property
    def has_day(self) -> bool:
        """Whether month and day are known (so it can recur yearly)."""
        return self.month is not None

    @property
    def is_full(self) -> bool:
        """Whether year, month and day are all known."""
        return self.year is not None and self.month is not None

    def to_date(self) -> date:
        """Return the exact ``date``; only valid when fully known."""
        if self.year is None or self.month is None or self.day is None:
            raise ValueError(f"{self} is not a fully known date")
        return date(self.year, self.month, self.day)

    def __str__(self) -> str:
        if self.month is None:
            return f"{self.year:04d}"
        if self.year is None:
            return f"--{self.month:02d}-{self.day:02d}"
        return f"{self.year:04d}-{self.month:02d}-{self.day:02d}"


# --------------------------------------------------------------------------- #
# Records
# --------------------------------------------------------------------------- #


def _dump(value: Any) -> Any:
    """Turn a model value into plain JSON-serialisable data."""
    if isinstance(value, PartialDate):
        return str(value)
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, list):
        return [_dump(item) for item in value]
    if is_dataclass(value) and not isinstance(value, type):
        return {f.name: _dump(getattr(value, f.name)) for f in fields(value)}
    return value


class _Record:
    """Shared (de)serialisation for the dataclasses below."""

    _converters: ClassVar[dict[str, Callable[[Any], Any]]] = {}

    def to_dict(self) -> dict[str, Any]:
        """Return the record as plain data."""
        return _dump(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Build a record from plain data, ignoring keys it does not know.

        Ignoring unknown keys keeps an older version of the code able to read
        data written by a newer one.
        """
        known = {f.name for f in fields(cls)}  # type: ignore[arg-type]
        kwargs: dict[str, Any] = {}
        for key, value in data.items():
            if key not in known:
                continue
            converter = cls._converters.get(key)
            kwargs[key] = converter(value) if converter and value is not None else value
        return cls(**kwargs)


class Gender(StrEnum):
    """Used only to pick a word: "uncle" or "aunt", "son" or "daughter"."""

    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


@dataclass
class ContactPoint(_Record):
    """An e-mail address or phone number, with an optional label ("work")."""

    value: str
    label: str = ""


def _contact_points(items: list[dict[str, Any]]) -> list[ContactPoint]:
    return [ContactPoint.from_dict(item) for item in items]


@dataclass
class Person(_Record):
    """One person. Everything except the given name is optional."""

    id: str
    given_name: str
    family_name: str = ""
    family_name_prefix: str = ""  # "van der", "de" – kept apart for sorting
    nickname: str = ""
    gender: Gender | None = None
    birth_date: PartialDate | None = None
    death_date: PartialDate | None = None
    deceased: bool = False  # set when someone has died but the date is unknown
    emails: list[ContactPoint] = field(default_factory=list)
    phones: list[ContactPoint] = field(default_factory=list)
    household_id: str | None = None
    group_ids: list[str] = field(default_factory=list)
    send_birthday_card: bool = False
    notes: str = ""

    _converters: ClassVar[dict[str, Callable[[Any], Any]]] = {
        "gender": Gender,
        "birth_date": PartialDate.parse,
        "death_date": PartialDate.parse,
        "emails": _contact_points,
        "phones": _contact_points,
    }

    def __post_init__(self) -> None:
        if not self.given_name.strip():
            raise ValueError("a person needs a given name")

    @property
    def is_deceased(self) -> bool:
        """Whether this person has died (with or without a known date)."""
        return self.deceased or self.death_date is not None

    @property
    def full_name(self) -> str:
        """Name as you would say it: "Jan van der Berg"."""
        parts = (self.given_name, self.family_name_prefix, self.family_name)
        return " ".join(part for part in parts if part)

    @property
    def sort_key(self) -> tuple[str, str, str]:
        """Sort on family name without its prefix, the Dutch way."""
        return (
            self.family_name.casefold(),
            self.given_name.casefold(),
            self.family_name_prefix.casefold(),
        )


def _iso_date(value: str) -> str:
    date.fromisoformat(value)  # raises ValueError when malformed
    return value


@dataclass
class Household(_Record):
    """An address and the people living there.

    The address belongs to the household, not to a person: when a family
    moves, there is one record to change.
    """

    id: str
    name: str = ""  # optional label; derived from the members when empty
    street: str = ""  # the street name only
    house_number: str = ""  # text: "2"
    house_number_addition: str = ""  # "A", "bis"; written after a hyphen
    street2: str = ""
    postal_code: str = ""
    city: str = ""
    region: str = ""
    country: str = ""  # ISO 3166-1 alpha-2, e.g. "NL"
    address_verified_on: str | None = None  # ISO date the address was last confirmed
    send_seasonal_card: bool = False
    notes: str = ""

    _converters: ClassVar[dict[str, Callable[[Any], Any]]] = {
        "address_verified_on": _iso_date,
    }

    def __post_init__(self) -> None:
        if self.house_number_addition.strip() and not self.house_number.strip():
            raise ValueError("a house number addition needs a house number")

    @property
    def house_number_full(self) -> str:
        """House number with its addition: "2-A"."""
        if self.house_number_addition:
            return f"{self.house_number}-{self.house_number_addition}"
        return self.house_number

    @property
    def street_line(self) -> str:
        """Street and house number as written on an envelope: "Dorpsstraat 2-A".

        Street first, then the number, for every country (for now).
        """
        return " ".join(part for part in (self.street, self.house_number_full) if part)


@dataclass
class Group(_Record):
    """A label people can carry: "Family Evers", "Friends", "Lions"."""

    id: str
    name: str
    description: str = ""

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("a group needs a name")


class RelationshipType(StrEnum):
    """How two people are linked.

    Only ``spouse``, ``partner`` and ``parent`` feed the family tree; every
    other family term (uncle, cousin, mother-in-law …) is derived from those.
    """

    SPOUSE = "spouse"  # married; start_date is the wedding date
    PARTNER = "partner"  # together, not married
    PARENT = "parent"  # from_id is the parent, to_id the child
    GODPARENT = "godparent"  # from_id is the godparent
    FRIEND = "friend"
    COLLEAGUE = "colleague"
    NEIGHBOUR = "neighbour"
    OTHER = "other"  # free text in ``label``


COUPLE_TYPES = frozenset({RelationshipType.SPOUSE, RelationshipType.PARTNER})
DIRECTED_TYPES = frozenset({RelationshipType.PARENT, RelationshipType.GODPARENT})


@dataclass
class Relationship(_Record):
    """A link between two people."""

    id: str
    type: RelationshipType
    from_id: str
    to_id: str
    start_date: PartialDate | None = None
    end_date: PartialDate | None = None
    ended: bool = False  # e.g. divorced; a death does not end a relationship
    label: str = ""
    notes: str = ""

    _converters: ClassVar[dict[str, Callable[[Any], Any]]] = {
        "type": RelationshipType,
        "start_date": PartialDate.parse,
        "end_date": PartialDate.parse,
    }

    def __post_init__(self) -> None:
        if self.from_id == self.to_id:
            raise ValueError("a relationship needs two different people")

    def involves(self, person_id: str) -> bool:
        """Whether the given person is one of the two."""
        return person_id in (self.from_id, self.to_id)

    def other(self, person_id: str) -> str:
        """Return the id of the other person in the relationship."""
        return self.to_id if person_id == self.from_id else self.from_id


@dataclass
class Event(_Record):
    """A date worth remembering that is not a birthday, wedding or death."""

    id: str
    title: str
    date: PartialDate
    yearly: bool = True
    person_ids: list[str] = field(default_factory=list)
    notes: str = ""

    _converters: ClassVar[dict[str, Callable[[Any], Any]]] = {
        "date": PartialDate.parse,
    }

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError("an event needs a title")
        if self.yearly and not self.date.has_day:
            raise ValueError("a yearly event needs a month and day")
        if not self.yearly and not self.date.is_full:
            raise ValueError("a one-off event needs a full date")


# --------------------------------------------------------------------------- #
# The address book
# --------------------------------------------------------------------------- #


class AddressBook:
    """All records, with the rules that keep them consistent."""

    def __init__(self) -> None:
        self.people: dict[str, Person] = {}
        self.households: dict[str, Household] = {}
        self.groups: dict[str, Group] = {}
        self.relationships: dict[str, Relationship] = {}
        self.events: dict[str, Event] = {}

    # -- people ------------------------------------------------------------- #

    def put_person(self, person: Person) -> Person:
        """Add a person, or replace the one with the same id."""
        if person.household_id is not None and person.household_id not in self.households:
            raise ValueError(f"unknown household: {person.household_id}")
        for group_id in person.group_ids:
            if group_id not in self.groups:
                raise ValueError(f"unknown group: {group_id}")
        if len(set(person.group_ids)) != len(person.group_ids):
            raise ValueError("a person can be in a group only once")
        self.people[person.id] = person
        return person

    def remove_person(self, person_id: str) -> None:
        """Remove a person together with their relationships."""
        del self.people[person_id]
        for relationship in list(self.relationships.values()):
            if relationship.involves(person_id):
                del self.relationships[relationship.id]
        for event in self.events.values():
            if person_id in event.person_ids:
                event.person_ids.remove(person_id)

    # -- households --------------------------------------------------------- #

    def put_household(self, household: Household) -> Household:
        """Add a household, or replace the one with the same id."""
        self.households[household.id] = household
        return household

    def remove_household(self, household_id: str) -> None:
        """Remove a household; its members stay, without an address."""
        del self.households[household_id]
        for person in self.people.values():
            if person.household_id == household_id:
                person.household_id = None

    def household_members(self, household_id: str) -> list[Person]:
        """Return the people living at a household, oldest first."""
        members = [p for p in self.people.values() if p.household_id == household_id]
        return sorted(members, key=_age_sort_key)

    # -- groups ------------------------------------------------------------- #

    def put_group(self, group: Group) -> Group:
        """Add a group, or replace the one with the same id."""
        self.groups[group.id] = group
        return group

    def remove_group(self, group_id: str) -> None:
        """Remove a group; its members stay."""
        del self.groups[group_id]
        for person in self.people.values():
            if group_id in person.group_ids:
                person.group_ids.remove(group_id)

    def people_in_group(self, group_id: str) -> list[Person]:
        """Return the members of a group, sorted by name."""
        members = [p for p in self.people.values() if group_id in p.group_ids]
        return sorted(members, key=lambda p: p.sort_key)

    # -- relationships ------------------------------------------------------ #

    def put_relationship(self, relationship: Relationship) -> Relationship:
        """Add a relationship, or replace the one with the same id."""
        for person_id in (relationship.from_id, relationship.to_id):
            if person_id not in self.people:
                raise ValueError(f"unknown person: {person_id}")

        directed = relationship.type in DIRECTED_TYPES
        for existing in self.relationships.values():
            if existing.id == relationship.id or existing.type != relationship.type:
                continue
            same_way = (existing.from_id, existing.to_id) == (
                relationship.from_id,
                relationship.to_id,
            )
            reverse = (existing.from_id, existing.to_id) == (
                relationship.to_id,
                relationship.from_id,
            )
            if same_way or (reverse and not directed):
                raise ValueError("this relationship already exists")

        # A child may not also be an ancestor of its parent.
        if (
            relationship.type is RelationshipType.PARENT
            and relationship.from_id
            in self._descendants(relationship.to_id, skip=relationship.id)
        ):
            raise ValueError("a person cannot be their own ancestor")

        self.relationships[relationship.id] = relationship
        return relationship

    def remove_relationship(self, relationship_id: str) -> None:
        """Remove a relationship."""
        del self.relationships[relationship_id]

    def _descendants(self, person_id: str, skip: str | None = None) -> set[str]:
        found: set[str] = set()
        queue = [person_id]
        while queue:
            current = queue.pop()
            for relationship in self.relationships.values():
                if (
                    relationship.type is RelationshipType.PARENT
                    and relationship.id != skip
                    and relationship.from_id == current
                    and relationship.to_id not in found
                ):
                    found.add(relationship.to_id)
                    queue.append(relationship.to_id)
        return found

    def parent_ids(self, person_id: str) -> list[str]:
        """Return the ids of a person's parents."""
        return [
            r.from_id
            for r in self.relationships.values()
            if r.type is RelationshipType.PARENT and r.to_id == person_id
        ]

    def child_ids(self, person_id: str) -> list[str]:
        """Return the ids of a person's children."""
        return [
            r.to_id
            for r in self.relationships.values()
            if r.type is RelationshipType.PARENT and r.from_id == person_id
        ]

    def couple_relationships(
        self, person_id: str, *, current_only: bool = True
    ) -> list[Relationship]:
        """Return the spouse/partner relationships of a person."""
        return [
            r
            for r in self.relationships.values()
            if r.type in COUPLE_TYPES
            and r.involves(person_id)
            and not (current_only and r.ended)
        ]

    def partner_ids(self, person_id: str, *, current_only: bool = True) -> list[str]:
        """Return the ids of a person's partners."""
        return [
            r.other(person_id)
            for r in self.couple_relationships(person_id, current_only=current_only)
        ]

    def parents_of(self, person_id: str) -> list[Person]:
        """Return a person's parents, oldest first."""
        return sorted((self.people[i] for i in self.parent_ids(person_id)), key=_age_sort_key)

    def children_of(self, person_id: str) -> list[Person]:
        """Return a person's children, oldest first."""
        return sorted((self.people[i] for i in self.child_ids(person_id)), key=_age_sort_key)

    def siblings_of(self, person_id: str) -> list[Person]:
        """Return everyone sharing at least one parent, oldest first."""
        sibling_ids: set[str] = set()
        for parent_id in self.parent_ids(person_id):
            sibling_ids.update(self.child_ids(parent_id))
        sibling_ids.discard(person_id)
        return sorted((self.people[i] for i in sibling_ids), key=_age_sort_key)

    # -- events ------------------------------------------------------------- #

    def put_event(self, event: Event) -> Event:
        """Add an event, or replace the one with the same id."""
        for person_id in event.person_ids:
            if person_id not in self.people:
                raise ValueError(f"unknown person: {person_id}")
        self.events[event.id] = event
        return event

    def remove_event(self, event_id: str) -> None:
        """Remove an event."""
        del self.events[event_id]

    # -- search ------------------------------------------------------------- #

    def find_people(self, query: str) -> list[Person]:
        """Find people whose name contains every word of the query."""
        words = query.casefold().split()
        if not words:
            return []
        matches = []
        for person in self.people.values():
            haystack = f"{person.full_name} {person.nickname}".casefold()
            if all(word in haystack for word in words):
                matches.append(person)
        return sorted(matches, key=lambda p: p.sort_key)

    # -- serialisation ------------------------------------------------------ #

    def to_dict(self) -> dict[str, Any]:
        """Return the whole address book as plain data."""
        return {
            "groups": [g.to_dict() for g in self.groups.values()],
            "households": [h.to_dict() for h in self.households.values()],
            "people": [p.to_dict() for p in self.people.values()],
            "relationships": [r.to_dict() for r in self.relationships.values()],
            "events": [e.to_dict() for e in self.events.values()],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AddressBook:
        """Build an address book from plain data, checking every reference."""
        book = cls()
        for item in data.get("groups", []):
            book.put_group(Group.from_dict(item))
        for item in data.get("households", []):
            book.put_household(Household.from_dict(item))
        for item in data.get("people", []):
            book.put_person(Person.from_dict(item))
        for item in data.get("relationships", []):
            book.put_relationship(Relationship.from_dict(item))
        for item in data.get("events", []):
            book.put_event(Event.from_dict(item))
        return book


def _age_sort_key(person: Person) -> tuple[int, int, int, int, str]:
    """Oldest first; people without a birth year come last, by name."""
    birth = person.birth_date
    if birth is None or birth.year is None:
        return (1, 0, 0, 0, person.full_name.casefold())
    return (0, birth.year, birth.month or 0, birth.day or 0, person.full_name.casefold())
