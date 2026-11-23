# Data model

This is what the address book stores, what it works out by itself, and why.
The code lives in `custom_components/address_book/core/` and has no Home
Assistant imports; every rule on this page has a test in `tests/core/`.

## Three principles

1. **An address belongs to a household, not to a person.** A couple and their
   two children share one address. When they move, one record changes.
2. **Only three family facts are stored: parent, spouse and partner.** Brother,
   aunt, cousin, mother-in-law and the rest are derived, so they can never
   contradict each other.
3. **People are records, not entities.** Two hundred contacts must not become
   two hundred sensors. Home Assistant gets a few summary entities, a calendar
   and services; the people themselves live in the integration's own storage.

## Records

### Person

| Field | Type | Notes |
|---|---|---|
| `id` | string | Generated, never changes |
| `given_name` | string | The only required field |
| `family_name_prefix` | string | "van der", "de". Spoken, but not sorted on |
| `family_name` | string | |
| `nickname` | string | Also searched |
| `gender` | `male` / `female` / `other` / empty | Only picks a word: "uncle" or "aunt" |
| `birth_date` | partial date | See [Partial dates](#partial-dates) |
| `death_date` | partial date | |
| `deceased` | boolean | For someone who has died on an unknown date |
| `emails` | list of `{value, label}` | Empty for a toddler, and that is fine |
| `phones` | list of `{value, label}` | |
| `household_id` | reference | At most one: where this person lives now |
| `group_ids` | list of references | Any number of groups |
| `send_birthday_card` | boolean | |
| `notes` | string | |

### Household

| Field | Type | Notes |
|---|---|---|
| `id` | string | |
| `name` | string | Optional label; derived from the members when empty |
| `street` | string | The street name only |
| `house_number` | string | Text, e.g. `2` |
| `house_number_addition` | string | e.g. `A` or `bis`; needs a house number |
| `street2` | string | |
| `postal_code`, `city`, `region` | string | |
| `country` | string | ISO 3166-1 alpha-2, e.g. `NL` |
| `address_verified_on` | date | Last time someone confirmed this address |
| `send_seasonal_card` | boolean | One Christmas card per household |
| `notes` | string | |

The house number and its addition are separate fields, as Dutch addresses and
postal lookups need them. Written out they are joined by a hyphen, after the
street: `Dorpsstraat 2-A`. That order is used for every country for now; a
per-country order (`2 Main Street`) comes with vCard export.

### Group

`id`, `name`, `description`. A person can be in any number of groups ("Family
Evers", "Friends", "Lions"). Groups are flat: no groups inside groups.

### Relationship

A link between two people.

| Field | Type | Notes |
|---|---|---|
| `id` | string | |
| `type` | see below | |
| `from_id`, `to_id` | references | Order matters only for `parent` and `godparent` |
| `start_date` | partial date | For `spouse`: the wedding date |
| `end_date` | partial date | |
| `ended` | boolean | Divorced or separated. A death does **not** end a relationship |
| `label` | string | Free text, used with type `other` |
| `notes` | string | |

| Type | Meaning | Feeds the family tree |
|---|---|---|
| `parent` | `from_id` is the parent of `to_id` | yes |
| `spouse` | Married | yes |
| `partner` | Together, not married | yes |
| `godparent` | `from_id` is the godparent of `to_id` | no |
| `friend`, `colleague`, `neighbour`, `other` | | no |

Rules enforced on every change: both people exist; nobody is related to
themselves; the same relationship cannot be stored twice; nobody can be their
own ancestor.

### Event

A date worth remembering that is not a birthday, wedding or death: `id`,
`title`, `date`, `yearly` (default true), `person_ids`, `notes`. A yearly event
needs at least a month and day; a one-off event needs a full date.

## Partial dates

Dates are often half known. Three shapes are accepted, written as vCard does:

| Written | Meaning |
|---|---|
| `1980-05-17` | Fully known |
| `--05-17` | The day is known, the year is not: there is a birthday, but no age |
| `1980` | Only the year is known: no birthday on the calendar |

## What is derived

### Family relations

For any two people the address book answers "what is B to A?". It looks, in
this order, at: the two as a couple; blood relatives through the nearest common
ancestor; the partner of a blood relative; a blood relative of your own partner.

| Stored facts | Derived |
|---|---|
| Shared parent | sibling (half-sibling when both have two known parents and share one) |
| Parent's parent, and further | grandparent, great-grandparent |
| Parent's sibling | aunt / uncle |
| Sibling's child | niece / nephew |
| Parent's sibling's child | cousin |
| Grandparent's sibling, sibling's grandchild | great-aunt / great-uncle, grandniece / grandnephew |
| Any other common ancestor | relative |
| Parent's partner who is not your parent | step-parent |
| Partner's child who is not yours | stepchild |
| Partner's parent, child's partner | parent-in-law, child-in-law |
| Partner's sibling, sibling's partner | sibling-in-law |
| Partner of an aunt, cousin, … or their relation to your partner | the same word, "by marriage" |

The words exist in English and Dutch. Dutch says *neef* / *nicht* for both a
cousin and a nephew or niece, and *aangetrouwde oom* for an uncle by marriage.

Ended relationships give no in-laws: your father's ex-partner is not your
step-mother. Deaths change nothing: your late uncle's wife is still your aunt.

Not derived (yet): step-siblings, and the partner of your partner's sibling.

### Dates on the calendar

| Source | Occurrence | Carries |
|---|---|---|
| `birth_date` with a day | Birthday, every year | Age, when the year is known |
| `death_date` with a day | Day of remembrance, every year | Years since |
| `spouse` relationship with a `start_date` | Wedding anniversary, every year | Years married |
| The same, with a full date | 12½ years married, once | Dutch *koperen bruiloft* |
| Event | On its date, yearly or once | Years since, when known |

Rules:

- No birthdays after someone has died. The last birthday before a known date of
  death still counts; with an unknown date there are none.
- No wedding anniversary once the relationship has ended or one of the two has
  died.
- A date on 29 February falls on 28 February in other years. Setting:
  `feb_28` (default) or `mar_1`.
- Milestones are flagged so they can be announced earlier or differently.
  Birthdays: 1, 18, 21, 30, 40, 50, 60, 65, 70, 75, 80, 85, 90, 95, 100.
  Weddings: 12½, 25, 40, 50, 60, 65, 70.

## Storage

One JSON file in Home Assistant's `.storage` directory, so it is part of every
Home Assistant backup:

```json
{
  "groups": [],
  "households": [],
  "people": [],
  "relationships": [],
  "events": []
}
```

The file is `.storage/address_book`. A change is written about a second after it
is made, so several changes in a row become one write.

Home Assistant's storage helper adds a schema version, which makes later
changes to this model a migration instead of a manual edit. Unknown fields are
ignored on load, so data written by a newer minor version still opens in an
older one. Data from a newer major version is refused.

On load every reference is checked; a file pointing at a person or household
that does not exist is refused rather than silently repaired. A refused file is
left exactly as it is, and the integration reports a setup error.

Removing the integration deletes the file: it holds personal data about other
people, so nothing is left behind. Backups made earlier still contain it.

## Deliberately left out for now

- **Photos** and a link to a Home Assistant `person` entity.
- **More than one address per person** (a child living in two homes).
- **A history of addresses.** Only the current one is kept.
- **Gifts given and gift ideas.** Likely a later record type of its own.

## Open questions

None at the moment. Decided: the house number is its own field; card flags are
per person (birthday) and per household (seasonal); the milestone lists are the
default and become configurable later.
