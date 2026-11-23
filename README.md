# Address Book — Home Assistant integration

An address book inside Home Assistant: the people you know, where they live, how
they are related, and the dates that matter.

> **Early development.** Storage, services, a calendar, two sensors and a daily
> reminder event are built and tested. There is no panel yet: the address book
> is filled through services.

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

## In Home Assistant

| What | For |
|---|---|
| `calendar.address_book` | Birthdays, wedding anniversaries, days of remembrance and events. Title: the name. Location: the postal address on one line. Description: the age when known ("Turns 50"), then the note |
| `sensor.address_book_today` | The number of dates today |
| `sensor.address_book_upcoming` | The number of dates in the coming 30 days |
| Event `address_book_reminder` | Fired every day at 09:00 for each date that is 7 days away, and again on the day itself |

Both sensors carry an attribute `occurrences`, a list with for every date:
`name`, `date`, `days` (from today), `kind` (`birthday`, `wedding_anniversary`,
`death_anniversary` or `event`), `years`, `milestone`, `address`, `notes` and
`person_ids`. The reminder event carries the same fields plus `days_ahead`. The
attribute is kept out of the recorder, so names and addresses do not end up in
the history database.

The period of the upcoming sensor, the number of days ahead and the time of the
reminder are settings of the integration (Configure).

```yaml
automation:
  - alias: Birthday reminder
    triggers:
      - trigger: event
        event_type: address_book_reminder
        event_data:
          kind: birthday
    actions:
      - action: notify.notify
        data:
          message: >-
            {% set e = trigger.event.data %}
            {% if e.days_ahead == 0 %}Today: {{ e.name }} has a birthday.
            {% else %}In {{ e.days_ahead }} days: {{ e.name }}{% if e.years %} turns {{ e.years }}{% endif %}.
            {% if e.address %}Address: {{ e.address }}.{% endif %}{% endif %}
```

If Home Assistant is not running at the reminder time, that day's reminders are
not sent later.

## Services

Until there is a panel, records are entered with services (Developer tools →
Actions, or from a script).

| Service | What it does |
|---|---|
| `address_book.set_person`, `set_household`, `set_group`, `set_relationship`, `set_event` | Without `id`: adds a record and returns its `id`. With `id`: changes only the fields that are given |
| `address_book.remove_person`, `remove_household`, `remove_group`, `remove_relationship`, `remove_event` | Removes the record with that `id` |
| `address_book.find_people` | Returns the people whose name contains every word of `query`, with their `id` |
| `address_book.import_calendar` | Turns an existing birthday calendar into people and households. Shows a preview unless `dry_run` is off; see [docs/data-model.md](docs/data-model.md#importing-a-birthday-calendar) |

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
