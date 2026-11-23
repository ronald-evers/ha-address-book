"""Turn a birthday calendar into people and households.

The source is a calendar where the title is a name, the location a postal
address on one line and the description a free note. The import takes over what
is written and guesses nothing: no birth years, no relationships, and nothing is
read out of the note.

Pure Python: no Home Assistant imports.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .model import AddressBook, Event, Household, PartialDate, Person, new_id

# Words that belong to a family name but are not sorted on.
_PREFIXES = frozenset(
    "van de der den het 't te ten ter in op aan bij uit voor la le du von vom zu".split()
)
_SEVERAL_NAMES = re.compile(r"\s+(?:en|and)\s+|\s*[&+]\s*", re.IGNORECASE)
# "Dorpsstraat 12", "Dorpsstraat 12A", "Dorpsstraat 12-A", "Dorpsstraat 12 bis", "Laan 12-2"
_STREET = re.compile(
    r"^(?P<street>.+)\s+(?P<number>\d+)"
    r"(?:\s*-\s*(?P<hyphenated>[A-Za-z0-9]+)|\s*(?P<letters>[A-Za-z]+))?$"
)
_DUTCH_POSTAL_CODE = re.compile(r"^(\d{4})\s?([A-Za-z]{2})\s+(.+)$")
_COUNTRIES = {
    "nederland": "NL",
    "the netherlands": "NL",
    "netherlands": "NL",
    "belgië": "BE",
    "belgie": "BE",
    "belgium": "BE",
    "duitsland": "DE",
    "germany": "DE",
    "deutschland": "DE",
    "frankrijk": "FR",
    "france": "FR",
    "verenigd koninkrijk": "GB",
    "engeland": "GB",
    "united kingdom": "GB",
    "spanje": "ES",
    "italië": "IT",
    "italie": "IT",
    "oostenrijk": "AT",
    "zwitserland": "CH",
    "luxemburg": "LU",
    "denemarken": "DK",
    "zweden": "SE",
    "noorwegen": "NO",
    "verenigde staten": "US",
    "canada": "CA",
    "australië": "AU",
    "australie": "AU",
}

ATTENTION_SEVERAL_NAMES = "several_names"
ATTENTION_ADDRESS = "address_not_recognised"
ATTENTION_COUNTRY = "country_not_recognised"
ATTENTION_NO_NAME = "no_name"


@dataclass(frozen=True)
class CalendarEntry:
    """One yearly date from the calendar."""

    title: str
    month: int
    day: int
    location: str = ""
    description: str = ""


def split_names(title: str) -> list[str]:
    """Split "Jan en Marie" into its names; one name stays one name."""
    return [part.strip() for part in _SEVERAL_NAMES.split(title.strip()) if part.strip()]


def parse_name(name: str) -> tuple[str, str, str]:
    """Return given name, family name prefix and family name.

    The first word is the given name; "van", "de", "van der" and the like
    after it are the prefix; the rest is the family name.
    """
    words = name.split()
    if not words:
        return ("", "", "")
    given, rest = words[0], words[1:]
    count = 0
    while count < len(rest) - 1 and rest[count].casefold() in _PREFIXES:
        count += 1
    return (given, " ".join(rest[:count]), " ".join(rest[count:]))


def parse_address(location: str) -> tuple[dict[str, str], list[str]]:
    """Read "street number[-addition], postal code city[, country]".

    Returns the household fields and what needs attention. An address that
    does not have this shape is kept whole in ``street``.
    """
    parts = [part.strip() for part in re.split(r"[,\n]", location) if part.strip()]
    street = _STREET.match(parts[0]) if parts else None
    if street is None or not 2 <= len(parts) <= 3:
        return ({"street": ", ".join(parts)}, [ATTENTION_ADDRESS])

    fields = {
        "street": street["street"].strip(),
        "house_number": street["number"],
        "house_number_addition": street["hyphenated"] or street["letters"] or "",
    }
    if dutch := _DUTCH_POSTAL_CODE.match(parts[1]):
        fields["postal_code"] = f"{dutch[1]} {dutch[2].upper()}"
        fields["city"] = dutch[3].strip()
    else:
        first, _, rest = parts[1].partition(" ")
        if rest and any(char.isdigit() for char in first):
            fields["postal_code"], fields["city"] = first, rest.strip()
        else:
            fields["city"] = parts[1]

    attention: list[str] = []
    if len(parts) == 3:
        country = parts[2]
        if len(country) == 2 and country.isalpha():
            fields["country"] = country.upper()
        elif country.casefold() in _COUNTRIES:
            fields["country"] = _COUNTRIES[country.casefold()]
        else:
            fields["country"] = country
            attention.append(ATTENTION_COUNTRY)
    return (fields, attention)


def _address_key(household: Household) -> tuple[str, ...]:
    return tuple(
        value.casefold()
        for value in (
            household.street,
            household.house_number,
            household.house_number_addition,
            household.postal_code,
            household.city,
            household.country,
        )
    )


@dataclass
class ImportPlan:
    """What an import adds; nothing changes until ``apply``."""

    households: list[Household] = field(default_factory=list)
    people: list[Person] = field(default_factory=list)
    events: list[Event] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)  # titles already present
    attention: list[tuple[str, str]] = field(default_factory=list)  # (title, reason)

    def apply(self, book: AddressBook) -> None:
        """Add everything to the address book."""
        for household in self.households:
            book.put_household(household)
        for person in self.people:
            book.put_person(person)
        for event in self.events:
            book.put_event(event)

    def summary(self, book: AddressBook) -> dict[str, Any]:
        """Describe the plan in plain data, for a preview."""
        addresses = {h.id: h for h in (*book.households.values(), *self.households)}

        def address(household_id: str | None) -> str:
            if household_id is None:
                return ""
            household = addresses[household_id]
            town = " ".join(p for p in (household.postal_code, household.city) if p)
            parts = (household.street_line, town, household.country)
            return ", ".join(part for part in parts if part)

        return {
            "households": [address(h.id) for h in self.households],
            "people": [
                {
                    "name": p.full_name,
                    "birthday": str(p.birth_date) if p.birth_date else "",
                    "address": address(p.household_id),
                }
                for p in self.people
            ],
            "events": [{"title": e.title, "date": str(e.date)} for e in self.events],
            "skipped": list(self.skipped),
            "attention": [
                {"title": title, "reason": reason} for title, reason in self.attention
            ],
        }


def plan_import(book: AddressBook, entries: list[CalendarEntry]) -> ImportPlan:
    """Work out what the calendar adds to the address book.

    * A title with one name becomes a person with a birthday (day and month).
    * A title with several names becomes those people, without a birthday, and
      a yearly event carrying the original title: whose date it is, is not
      guessed.
    * The same address is one household.
    * The description is carried over as a note, unread.
    * What is already there is skipped, so an import can be repeated.
    """
    plan = ImportPlan()
    households = {
        _address_key(h): h for h in book.households.values() if any(_address_key(h))
    }
    by_name: dict[str, Person] = {}
    for existing in book.people.values():
        by_name.setdefault(existing.full_name.casefold(), existing)
    birthdays = {
        (p.full_name.casefold(), p.birth_date.month, p.birth_date.day)
        for p in book.people.values()
        if p.birth_date is not None and p.birth_date.has_day
    }
    events = {(e.title.casefold(), e.date.month, e.date.day) for e in book.events.values()}

    def household_for(entry: CalendarEntry) -> str | None:
        if not entry.location.strip():
            return None
        fields, attention = parse_address(entry.location)
        candidate = Household(id=new_id(), **fields)
        found = households.get(_address_key(candidate))
        if found is None:
            households[_address_key(candidate)] = found = candidate
            plan.households.append(candidate)
            plan.attention.extend((entry.title, reason) for reason in attention)
        return found.id

    for entry in dict.fromkeys(entries):  # the same entry twice counts once
        names = split_names(entry.title)
        date = PartialDate(None, entry.month, entry.day)
        if not names:
            plan.attention.append((entry.title, ATTENTION_NO_NAME))
            continue

        if len(names) == 1:
            given, prefix, family = parse_name(names[0])
            person = Person(
                id=new_id(),
                given_name=given,
                family_name_prefix=prefix,
                family_name=family,
                birth_date=date,
                notes=entry.description,
            )
            key = (person.full_name.casefold(), entry.month, entry.day)
            if key in birthdays:
                plan.skipped.append(entry.title)
                continue
            person.household_id = household_for(entry)
            birthdays.add(key)
            by_name.setdefault(person.full_name.casefold(), person)
            plan.people.append(person)
            continue

        key = (entry.title.strip().casefold(), entry.month, entry.day)
        if key in events:
            plan.skipped.append(entry.title)
            continue
        household_id = household_for(entry)
        person_ids = []
        for name in names:
            given, prefix, family = parse_name(name)
            person = Person(
                id=new_id(),
                given_name=given,
                family_name_prefix=prefix,
                family_name=family,
                household_id=household_id,
            )
            known = by_name.get(person.full_name.casefold())
            if known is None:
                by_name[person.full_name.casefold()] = known = person
                plan.people.append(person)
            person_ids.append(known.id)
        events.add(key)
        plan.events.append(
            Event(
                id=new_id(),
                title=entry.title.strip(),
                date=date,
                person_ids=list(dict.fromkeys(person_ids)),
                notes=entry.description,
            )
        )
        plan.attention.append((entry.title, ATTENTION_SEVERAL_NAMES))

    return plan
