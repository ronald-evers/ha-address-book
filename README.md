# Address Book — Home Assistant integration

An address book inside Home Assistant: the people you know, where they live, how
they are related, and the dates that matter.

> **Early development.** The data model, its rules, the storage and the services
> are built and tested. There is no calendar, sensor or panel yet: for now the
> address book is filled and read through services only.

## What it is for

- Remembering: "what are the names of Anna's children again?"
- Birthdays, wedding anniversaries and days of remembrance, with ages and
  milestones, as a calendar and as triggers for your own automations.
- Addresses kept once per household, so a move is one change.
- Groups such as "Family", "Friends" or a club, for a guest list or a
  Christmas card run.

## How it works

Three ideas shape everything; [docs/data-model.md](docs/data-model.md) has the
detail.

1. An address belongs to a **household**, not to a person.
2. Only **parent**, **spouse** and **partner** are stored. Sibling, aunt,
   cousin, mother-in-law and so on are worked out from those.
3. People are **records, not entities**: a large address book does not flood
   Home Assistant with sensors.

## Services

Until there is a panel, records are entered with services (Developer tools →
Actions, or from a script).

| Service | What it does |
|---|---|
| `address_book.set_person`, `set_household`, `set_group`, `set_relationship`, `set_event` | Without `id`: adds a record and returns its `id`. With `id`: changes only the fields that are given |
| `address_book.remove_person`, `remove_household`, `remove_group`, `remove_relationship`, `remove_event` | Removes the record with that `id` |
| `address_book.find_people` | Returns the people whose name contains every word of `query`, with their `id` |

```yaml
action: address_book.set_household
data:
  street: Dorpsstraat
  house_number: "2"
  house_number_addition: A
  postal_code: 1234 AB
  city: Ons Dorp
  country: NL
response_variable: household
```

An empty text clears a date or takes a person out of a household. A call that
breaks a rule of the data model is refused with the reason and changes nothing.

## Privacy

An address book holds personal data about other people, including children.
Everything is stored locally in Home Assistant's own storage and is included in
Home Assistant backups. Nothing is sent anywhere.

## Development

```bash
python -m venv .venv
.venv/bin/pip install -r requirements-test.txt
.venv/bin/python -m pytest
```

The code in `custom_components/address_book/core/` has no Home Assistant
imports: the model, the date arithmetic and the family relations can be read and
tested on their own.

## License

MIT
