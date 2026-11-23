/* Address Book panel: the people, one person, and a form to add or change one.
 *
 * One file, no build step. Everything shown comes from the integration over
 * the websocket commands in websocket_api.py; text from the address book is
 * always escaped before it goes into the page.
 */

const TEXT = {
  en: {
    title: "Address Book",
    add: "Add person",
    search: "Search by name, nickname or place",
    searchHint: "For example: noor",
    soon: "Coming up",
    inDays: (n) => (n === 0 ? "Today" : n === 1 ? "Tomorrow" : `In ${n} days`),
    turns: (name, n) => `${name} turns ${n}`,
    birthdayOf: (name) => `${name} has a birthday`,
    wedding: (name, n) => `Wedding anniversary of ${name}${n ? ` (${n} years)` : ""}`,
    memorial: (name) => `In memory of ${name}`,
    nobody: "Nobody in the address book yet. Start with “Add person”.",
    noMatch: "Nobody found.",
    years: (n) => `${n} years old`,
    yearUnknown: "year unknown",
    listHint: "Sorted by family name, without the prefix. Choose someone to see everything about them.",
    all: "Everyone",
    edit: "Change",
    remove: "Remove",
    removeAsk: (name) => `Remove ${name} from the address book? Their family links go too.`,
    removeYes: "Yes, remove",
    cancel: "Cancel",
    livesAt: "Lives at",
    noAddress: "No address known.",
    with: "Together with",
    copy: "Copy address",
    copied: "Copied",
    reach: "Contact",
    phone: "Phone",
    email: "Email",
    notes: "Note",
    family: "Family",
    marriedTo: "Married to",
    partner: "Partner",
    ex: "Former partner",
    children: "Children",
    parents: "Parents",
    derived: "Worked out by the address book",
    noFamily: "No family linked yet.",
    since: "since",
    birthdayLine: (date, days, turns) =>
      `birthday on ${date}${days === 0 ? ", today" : `, in ${days} days`}${turns ? ` (turns ${turns})` : ""}`,
    deceased: "deceased",
    addTitle: "Add person",
    editTitle: (name) => `Change ${name}`,
    onlyGiven: "Only the given name is required. You can fill in the rest later.",
    who: "1. Who is it?",
    given: "Given name",
    prefix: "Prefix",
    familyName: "Family name",
    nickname: "Nickname",
    birthday: "Birthday",
    day: "Day",
    month: "Month",
    year: "Year (may be empty)",
    unknown: "unknown",
    noYear: "Without a year the birthday is on the calendar, but without an age.",
    gender: "For words like uncle or aunt",
    male: "Man",
    female: "Woman",
    other: "Other",
    notSaid: "Not filled in",
    card: "Send a birthday card",
    where: (name) => `2. Where does ${name || "this person"} live?`,
    keep: "Leave as it is",
    existing: "With someone already in the address book",
    existingHint: "Type a name or street",
    newAddress: "At a new address",
    updateAddress: "Correct this address (for everyone living there)",
    none: "Unknown, or fill in later",
    street: "Street",
    number: "Number",
    addition: "Addition",
    postal: "Postal code",
    city: "City",
    country: "Country (two letters)",
    familyStep: "3. Family of someone?",
    skip: "(you may skip this)",
    is: (name) => `${name || "This person"} is`,
    child_of: "child of",
    parent_of: "parent of",
    spouse_of: "married to",
    partner_of: "partner of",
    pick: "Search for someone in the address book",
    familyHint: "Grandparents, aunts, cousins and the rest follow by themselves.",
    save: "Save",
    needGiven: "Fill in a given name.",
    needDay: "Fill in both day and month, or leave both empty.",
    needHousehold: "Choose an address from the list.",
    failed: "That did not work:",
    loading: "Loading…",
  },
  nl: {
    title: "Adresboek",
    add: "Persoon toevoegen",
    search: "Zoek op naam, roepnaam of plaats",
    searchHint: "Bijvoorbeeld: noor",
    soon: "Binnenkort",
    inDays: (n) => (n === 0 ? "Vandaag" : n === 1 ? "Morgen" : `Over ${n} dagen`),
    turns: (name, n) => `${name} wordt ${n}`,
    birthdayOf: (name) => `${name} is jarig`,
    wedding: (name, n) => `Trouwdag van ${name}${n ? ` (${n} jaar)` : ""}`,
    memorial: (name) => `Gedenkdag van ${name}`,
    nobody: "Nog niemand in het adresboek. Begin met ‘Persoon toevoegen’.",
    noMatch: "Niemand gevonden.",
    years: (n) => `${n} jaar`,
    yearUnknown: "jaar onbekend",
    listHint: "Op achternaam, zonder tussenvoegsel. Kies iemand om alles over die persoon te zien.",
    all: "Alle mensen",
    edit: "Wijzigen",
    remove: "Verwijderen",
    removeAsk: (name) => `${name} uit het adresboek verwijderen? De familiebanden van deze persoon gaan ook weg.`,
    removeYes: "Ja, verwijderen",
    cancel: "Annuleren",
    livesAt: "Woont op",
    noAddress: "Geen adres bekend.",
    with: "Samen met",
    copy: "Adres kopiëren",
    copied: "Gekopieerd",
    reach: "Bereikbaar",
    phone: "Telefoon",
    email: "E-mail",
    notes: "Notitie",
    family: "Familie",
    marriedTo: "Getrouwd met",
    partner: "Partner",
    ex: "Ex-partner",
    children: "Kinderen",
    parents: "Ouders",
    derived: "Vanzelf afgeleid door het adresboek",
    noFamily: "Nog geen familie gekoppeld.",
    since: "sinds",
    birthdayLine: (date, days, turns) =>
      `jarig op ${date}${days === 0 ? ", vandaag" : `, over ${days} dagen`}${turns ? ` (wordt ${turns})` : ""}`,
    deceased: "overleden",
    addTitle: "Persoon toevoegen",
    editTitle: (name) => `${name} wijzigen`,
    onlyGiven: "Alleen de voornaam is verplicht. De rest kun je later aanvullen.",
    who: "1. Wie is het?",
    given: "Voornaam",
    prefix: "Tussenvoegsel",
    familyName: "Achternaam",
    nickname: "Roepnaam",
    birthday: "Jarig op",
    day: "Dag",
    month: "Maand",
    year: "Jaar (mag leeg)",
    unknown: "onbekend",
    noYear: "Zonder jaar staat de verjaardag wel op de kalender, maar zonder leeftijd.",
    gender: "Voor woorden als oom of tante",
    male: "Man",
    female: "Vrouw",
    other: "Anders",
    notSaid: "Niet ingevuld",
    card: "Verjaardagskaart sturen",
    where: (name) => `2. Waar woont ${name || "deze persoon"}?`,
    keep: "Laten zoals het is",
    existing: "Bij iemand die al in het adresboek staat",
    existingHint: "Typ een naam of straat",
    newAddress: "Op een nieuw adres",
    updateAddress: "Dit adres verbeteren (voor iedereen die er woont)",
    none: "Weet ik niet, of later invullen",
    street: "Straat",
    number: "Huisnummer",
    addition: "Toevoeging",
    postal: "Postcode",
    city: "Plaats",
    country: "Land (twee letters)",
    familyStep: "3. Familie van iemand?",
    skip: "(mag je overslaan)",
    is: (name) => `${name || "Deze persoon"} is`,
    child_of: "kind van",
    parent_of: "ouder van",
    spouse_of: "getrouwd met",
    partner_of: "partner van",
    pick: "Zoek iemand uit het adresboek",
    familyHint: "Opa, oma, tante, neef en nicht volgen daarna vanzelf.",
    save: "Opslaan",
    needGiven: "Vul een voornaam in.",
    needDay: "Vul dag en maand allebei in, of laat ze allebei leeg.",
    needHousehold: "Kies een adres uit de lijst.",
    failed: "Dat is niet gelukt:",
    loading: "Laden…",
  },
};

const esc = (value) =>
  String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const STYLE = `
:host { display: block; min-height: 100vh; background: var(--primary-background-color, #f3f4f6); color: var(--primary-text-color, #1c1c1e); font-family: var(--paper-font-body1_-_font-family, Roboto, system-ui, sans-serif); }
* { box-sizing: border-box; }
.bar { display: flex; align-items: center; gap: 8px; min-height: 56px; padding: 0 12px; background: var(--app-header-background-color, var(--primary-color, #03a9f4)); color: var(--app-header-text-color, #fff); font-size: 20px; }
.page { max-width: 920px; margin: 0 auto; padding: 20px 16px 64px; display: flex; flex-direction: column; gap: 20px; }
.page.narrow { max-width: 680px; }
.row { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 12px 16px; }
h1 { margin: 0; font-size: 28px; font-weight: 500; }
h2 { margin: 0; font-size: 17px; font-weight: 500; }
h2.cap, .cap { margin: 0; font-size: 13px; font-weight: 700; letter-spacing: .4px; text-transform: uppercase; color: var(--secondary-text-color, #5f6368); }
p { margin: 0; }
.muted { color: var(--secondary-text-color, #5f6368); font-size: 14px; }
.card { background: var(--card-background-color, #fff); border: 1px solid var(--divider-color, #e0e3e7); border-radius: 16px; padding: 20px; display: flex; flex-direction: column; gap: 14px; }
.card.flush { padding: 0; overflow: hidden; gap: 0; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; }
.cols { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px 24px; }
button, .btn { font: inherit; font-size: 15px; font-weight: 500; min-height: 44px; padding: 0 18px; border-radius: 22px; border: 1px solid var(--divider-color, #c4c8ce); background: var(--card-background-color, #fff); color: var(--primary-text-color, #1c1c1e); cursor: pointer; display: inline-flex; align-items: center; gap: 8px; }
button.primary { background: var(--primary-color, #03a9f4); border-color: var(--primary-color, #03a9f4); color: var(--text-primary-color, #fff); }
button.danger { color: var(--error-color, #b3261e); border-color: var(--error-color, #b3261e); }
button.link { border: 0; background: none; padding: 0; min-height: 44px; color: var(--primary-color, #03a9f4); border-radius: 4px; text-align: left; }
button.item { width: 100%; border: 0; border-radius: 0; border-bottom: 1px solid var(--divider-color, #eceef1); padding: 14px 20px; display: flex; flex-wrap: wrap; gap: 4px 16px; text-align: left; font-weight: 400; }
button.item:last-child { border-bottom: 0; }
button.item .name { flex: 1 1 220px; font-size: 16px; font-weight: 500; }
button.item .when { flex: 1 1 150px; }
button.item .where { flex: 2 1 240px; }
button.soon { flex: 1 1 220px; flex-direction: column; align-items: flex-start; gap: 2px; border: 0; border-radius: 12px; padding: 12px 14px; height: auto; background: var(--secondary-background-color, #f3f4f6); }
button.soon.near { background: var(--warning-color, #ffa600); color: #1c1c1e; }
button.soon.near .muted { color: #1c1c1e; }
button.chip { background: var(--secondary-background-color, #f3f4f6); border: 0; font-weight: 400; }
.letter { margin: 0; padding: 8px 20px; font-size: 13px; font-weight: 700; color: var(--secondary-text-color, #5f6368); background: var(--secondary-background-color, #f7f8fa); border-bottom: 1px solid var(--divider-color, #e0e3e7); }
label.field { display: flex; flex-direction: column; gap: 6px; font-size: 13px; color: var(--secondary-text-color, #5f6368); }
input[type=text], input[type=search], input[type=tel], input[type=email], select, textarea { font: inherit; font-size: 16px; min-height: 48px; padding: 0 14px; border: 1px solid var(--secondary-text-color, #8a9099); border-radius: 10px; background: var(--card-background-color, #fff); color: var(--primary-text-color, #1c1c1e); width: 100%; }
textarea { padding: 12px 14px; min-height: 88px; resize: vertical; }
.fields { display: flex; flex-wrap: wrap; gap: 12px; align-items: flex-end; }
.fields > * { flex: 1 1 150px; min-width: 0; }
.fields > .small { flex: 0 1 110px; }
label.choice { display: flex; align-items: flex-start; gap: 12px; padding: 14px; border: 1px solid var(--divider-color, #c4c8ce); border-radius: 12px; cursor: pointer; }
label.choice.on { border: 2px solid var(--primary-color, #03a9f4); padding: 13px; }
label.choice input, label.check input { width: 20px; height: 20px; margin: 2px 0 0; flex: none; }
label.choice .body { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 10px; font-size: 16px; }
label.check { display: flex; align-items: center; gap: 12px; min-height: 44px; font-size: 15px; }
.options { border: 1px solid var(--divider-color, #c4c8ce); border-radius: 10px; overflow: hidden; max-height: 264px; overflow-y: auto; }
.options button { width: 100%; border: 0; border-radius: 0; border-bottom: 1px solid var(--divider-color, #eceef1); flex-direction: column; align-items: flex-start; gap: 2px; padding: 10px 14px; height: auto; font-weight: 400; }
.options button.on { background: var(--primary-color, #03a9f4); color: var(--text-primary-color, #fff); }
.options button.on .muted { color: inherit; }
.options button:last-child { border-bottom: 0; }
.error { color: var(--error-color, #b3261e); font-weight: 500; }
.big { font-size: 18px; line-height: 1.45; }
.end { display: flex; flex-wrap: wrap; gap: 12px; justify-content: flex-end; }
.stack { display: flex; flex-direction: column; gap: 6px; }
.chips { display: flex; flex-wrap: wrap; gap: 8px; }
:focus-visible { outline: 3px solid var(--primary-color, #03a9f4); outline-offset: 2px; }
`;

class AddressBookPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._view = { name: "list" };
    this._query = "";
    this._overview = null;
    this._detail = null;
    this._form = null;
    this._error = "";
    this.shadowRoot.addEventListener("click", (event) => this._onClick(event));
    this.shadowRoot.addEventListener("input", (event) => this._onInput(event));
    this.shadowRoot.addEventListener("change", (event) => this._onInput(event));
    this.shadowRoot.addEventListener("submit", (event) => event.preventDefault());
  }

  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    const menu = this.shadowRoot.querySelector("ha-menu-button");
    if (menu) menu.hass = hass;
    if (first) this._loadOverview();
  }

  set narrow(narrow) {
    this._narrow = narrow;
    const menu = this.shadowRoot.querySelector("ha-menu-button");
    if (menu) menu.narrow = narrow;
  }

  get _t() {
    const code = ((this._hass && this._hass.language) || "en").split("-")[0];
    return TEXT[code] || TEXT.en;
  }

  get _locale() {
    return (this._hass && this._hass.language) || "en";
  }

  /* ---------- data ---------- */

  async _ws(message) {
    return this._hass.callWS(message);
  }

  async _loadOverview() {
    try {
      this._overview = await this._ws({ type: "address_book/overview" });
      this._error = "";
    } catch (err) {
      this._error = err.message || String(err);
    }
    this._render();
  }

  async _open(personId) {
    this._view = { name: "person", id: personId, confirm: false };
    this._detail = null;
    this._render();
    try {
      this._detail = await this._ws({ type: "address_book/person", person_id: personId });
      this._error = "";
    } catch (err) {
      this._error = err.message || String(err);
    }
    this._render();
  }

  /* ---------- formatting ---------- */

  _dayMonth(month, day) {
    const date = new Date(Date.UTC(2000, month - 1, day));
    return new Intl.DateTimeFormat(this._locale, { day: "numeric", month: "long", timeZone: "UTC" }).format(date);
  }

  _partial(text) {
    // "1980-05-17", "--05-17" or "1980"
    if (!text) return { year: "", month: "", day: "" };
    if (text.startsWith("--")) return { year: "", month: String(+text.slice(2, 4)), day: String(+text.slice(5, 7)) };
    if (text.length === 4) return { year: text, month: "", day: "" };
    return { year: text.slice(0, 4), month: String(+text.slice(5, 7)), day: String(+text.slice(8, 10)) };
  }

  _birthdayText(person) {
    const t = this._t;
    const parts = this._partial(person.birth_date);
    if (!parts.month) return parts.year ? parts.year : "";
    const day = this._dayMonth(+parts.month, +parts.day);
    if (person.deceased) return day;
    return person.age === null || person.age === undefined ? `${day} · ${t.yearUnknown}` : `${day} · ${t.years(person.age)}`;
  }

  _months() {
    const format = new Intl.DateTimeFormat(this._locale, { month: "long", timeZone: "UTC" });
    return Array.from({ length: 12 }, (_, i) => format.format(new Date(Date.UTC(2000, i, 1))));
  }

  /* ---------- rendering ---------- */

  _render() {
    const t = this._t;
    let body;
    if (this._error && !this._overview) body = `<div class="page"><p class="error">${esc(this._error)}</p></div>`;
    else if (!this._overview) body = `<div class="page"><p class="muted">${esc(t.loading)}</p></div>`;
    else if (this._view.name === "person") body = this._renderPerson();
    else if (this._view.name === "form") body = this._renderForm();
    else body = this._renderList();

    const active = this.shadowRoot.activeElement;
    const keep = active && active.id ? { id: active.id, start: active.selectionStart, end: active.selectionEnd } : null;
    this.shadowRoot.innerHTML = `<style>${STYLE}</style><div class="bar"><ha-menu-button></ha-menu-button><span>${esc(t.title)}</span></div>${body}`;
    const menu = this.shadowRoot.querySelector("ha-menu-button");
    menu.hass = this._hass;
    menu.narrow = this._narrow;
    if (keep) {
      const again = this.shadowRoot.getElementById(keep.id);
      if (again) {
        again.focus();
        try { again.setSelectionRange(keep.start, keep.end); } catch (err) { /* not a text field */ }
      }
    }
  }

  _matches(person, words) {
    const hay = `${person.name} ${person.nickname} ${person.address}`.toLowerCase();
    return words.every((word) => hay.includes(word));
  }

  _renderList() {
    const t = this._t;
    const { people, upcoming } = this._overview;
    const words = this._query.toLowerCase().split(/\s+/).filter(Boolean);
    const shown = words.length ? people.filter((p) => this._matches(p, words)) : people;

    const soon = upcoming.slice(0, 6).map((item) => {
      let line;
      if (item.kind === "birthday") line = item.years ? t.turns(item.name, item.years) : t.birthdayOf(item.name);
      else if (item.kind === "wedding_anniversary") line = t.wedding(item.name, item.years);
      else if (item.kind === "death_anniversary") line = t.memorial(item.name);
      else line = item.name;
      const date = this._dayMonth(+item.date.slice(5, 7), +item.date.slice(8, 10));
      const target = item.person_ids && item.person_ids.length ? ` data-open="${esc(item.person_ids[0])}"` : "";
      return `<button type="button" class="soon${item.days <= 7 ? " near" : ""}"${target}><span class="muted"><b>${esc(t.inDays(item.days))} · ${esc(date)}</b></span><span>${esc(line)}</span></button>`;
    }).join("");

    let rows = "";
    let letter = null;
    for (const person of shown) {
      const first = ((person.family_name || person.given_name)[0] || "#").toUpperCase();
      if (first !== letter) {
        letter = first;
        rows += `<h2 class="letter">${esc(letter)}</h2>`;
      }
      rows += `<button type="button" class="item" data-open="${esc(person.id)}"><span class="name">${esc(person.name)}</span><span class="when muted">${esc(this._birthdayText(person))}</span><span class="where muted">${esc([person.street_line, person.city].filter(Boolean).join(", "))}</span></button>`;
    }
    if (!people.length) rows = `<p class="muted" style="padding:20px">${esc(t.nobody)}</p>`;
    else if (!shown.length) rows = `<p class="muted" style="padding:20px">${esc(t.noMatch)}</p>`;

    return `<div class="page">
      <div class="row"><h1>${esc(t.title)}</h1><button type="button" class="primary" data-action="add">+ ${esc(t.add)}</button></div>
      <label class="field">${esc(t.search)}<input id="search" type="search" placeholder="${esc(t.searchHint)}" value="${esc(this._query)}" data-bind="query"></label>
      ${soon && !words.length ? `<section class="card"><h2 class="cap">${esc(t.soon)}</h2><div class="chips">${soon}</div></section>` : ""}
      <section class="card flush" aria-label="${esc(t.all)}">${rows}</section>
      ${people.length ? `<p class="muted">${esc(t.listHint)}</p>` : ""}
    </div>`;
  }

  _personLink(person, extra = "") {
    return `<button type="button" class="link" data-open="${esc(person.id)}">${esc(person.name)}${extra ? ` <span class="muted">· ${esc(extra)}</span>` : ""}</button>`;
  }

  _renderPerson() {
    const t = this._t;
    const back = `<button type="button" class="link" data-action="list">‹ ${esc(t.all)}</button>`;
    if (!this._detail) return `<div class="page">${back}<p class="${this._error ? "error" : "muted"}">${esc(this._error || t.loading)}</p></div>`;
    const { person, household, couples, children, parents, derived } = this._detail;

    let sub = "";
    const parts = this._partial(person.birth_date);
    if (person.deceased) sub = t.deceased;
    else if (parts.month && person.next_birthday) {
      const day = this._dayMonth(+parts.month, +parts.day);
      const line = t.birthdayLine(day, person.days_until_birthday, person.age === null ? "" : person.age + (person.days_until_birthday === 0 ? 0 : 1));
      sub = person.age === null ? line : `${t.years(person.age)} · ${line}`;
    } else if (person.age !== null && person.age !== undefined) sub = t.years(person.age);

    const mates = household ? household.members.filter((m) => m.id !== person.id) : [];
    const address = household
      ? `<div class="big">${esc(household.street_line)}${household.street2 ? `<br>${esc(household.street2)}` : ""}<br>${esc([household.postal_code, household.city].filter(Boolean).join(" "))}${household.country ? `<br>${esc(household.country)}` : ""}</div>
         ${mates.length ? `<div class="muted">${esc(t.with)} ${mates.map((m) => this._personLink(m)).join(", ")}</div>` : ""}
         <div><button type="button" data-action="copy" data-text="${esc(household.address)}">${esc(t.copy)}</button></div>`
      : `<p class="muted">${esc(t.noAddress)}</p>`;

    const contact = [
      ...person.phones.map((p) => `<div><span class="muted">${esc(p.label || t.phone)}</span><br><a href="tel:${esc(p.value.replace(/\s+/g, ""))}">${esc(p.value)}</a></div>`),
      ...person.emails.map((e) => `<div><span class="muted">${esc(e.label || t.email)}</span><br><a href="mailto:${esc(e.value)}">${esc(e.value)}</a></div>`),
    ].join("");

    const couple = couples.map((c) => {
      const title = c.ended ? t.ex : c.type === "spouse" ? t.marriedTo : t.partner;
      let since = "";
      if (c.since && !c.ended) {
        const p = this._partial(c.since);
        since = `${t.since} ${p.month ? `${this._dayMonth(+p.month, +p.day)} ` : ""}${p.year}`.trim();
      }
      return `<div class="stack"><div class="cap">${esc(title)}</div>${this._personLink(c)}${since ? `<div class="muted">${esc(since)}</div>` : ""}</div>`;
    }).join("");
    const group = (title, list) => list.length
      ? `<div class="stack"><div class="cap">${esc(title)}</div>${list.map((p) => this._personLink(p, p.age === null ? "" : String(p.age))).join("")}</div>` : "";
    const direct = couple + group(t.children, children) + group(t.parents, parents);
    const more = derived.length
      ? `<div class="stack"><div class="cap">${esc(t.derived)}</div><div class="chips">${derived.map((d) => `<button type="button" class="chip" data-open="${esc(d.id)}">${esc(d.name)} · ${esc(d.label)}</button>`).join("")}</div></div>` : "";

    const confirm = this._view.confirm
      ? `<section class="card"><p>${esc(t.removeAsk(person.name))}</p><div class="end"><button type="button" data-action="remove-no">${esc(t.cancel)}</button><button type="button" class="danger" data-action="remove-yes">${esc(t.removeYes)}</button></div></section>` : "";

    return `<div class="page">
      ${back}
      <div class="row"><div class="stack"><h1>${esc(person.name)}</h1><p class="muted" style="font-size:16px">${esc(sub)}</p></div>
        <div class="chips"><button type="button" data-action="edit">${esc(t.edit)}</button><button type="button" class="danger" data-action="remove">${esc(t.remove)}</button></div></div>
      ${this._error ? `<p class="error">${esc(t.failed)} ${esc(this._error)}</p>` : ""}
      ${confirm}
      <div class="grid">
        <section class="card"><h2 class="cap">${esc(t.livesAt)}</h2>${address}</section>
        <section class="card"><h2 class="cap">${esc(t.reach)}</h2>${contact || `<p class="muted">–</p>`}${person.notes ? `<h2 class="cap">${esc(t.notes)}</h2><p style="white-space:pre-line">${esc(person.notes)}</p>` : ""}</section>
      </div>
      <section class="card"><h2 class="cap">${esc(t.family)}</h2>${direct ? `<div class="cols">${direct}</div>` : `<p class="muted">${esc(t.noFamily)}</p>`}${more}</section>
    </div>`;
  }

  _startForm(detail) {
    const person = detail ? detail.person : null;
    const birth = this._partial(person ? person.birth_date : "");
    const household = detail ? detail.household : null;
    this._form = {
      id: person ? person.id : null,
      original: person,
      given_name: person ? person.given_name : "",
      family_name_prefix: person ? person.family_name_prefix : "",
      family_name: person ? person.family_name : "",
      nickname: person ? person.nickname : "",
      gender: person ? person.gender || "" : "",
      day: birth.day, month: birth.month, year: birth.year,
      phone: person && person.phones[0] ? person.phones[0].value : "",
      email: person && person.emails[0] ? person.emails[0].value : "",
      notes: person ? person.notes : "",
      send_birthday_card: person ? person.send_birthday_card : false,
      mode: person ? "keep" : "none",
      had_household: !!household,
      household_id: "",
      household_query: "",
      street: household ? household.street : "", house_number: household ? household.house_number : "",
      house_number_addition: household ? household.house_number_addition : "",
      postal_code: household ? household.postal_code : "", city: household ? household.city : "",
      country: household ? household.country : "",
      relation: "child_of", family: [], family_query: "",
    };
    this._view = { name: "form" };
    this._error = "";
  }

  _input(id, label, value, extra = "") {
    return `<label class="field">${esc(label)}<input id="f-${id}" type="text" value="${esc(value)}" data-field="${id}" ${extra}></label>`;
  }

  _renderForm() {
    const t = this._t;
    const f = this._form;
    const months = this._months().map((name, i) => `<option value="${i + 1}"${String(i + 1) === f.month ? " selected" : ""}>${esc(name)}</option>`).join("");
    const choice = (mode, label, inner = "") =>
      `<label class="choice${f.mode === mode ? " on" : ""}"><input type="radio" name="mode" value="${mode}" data-field="mode"${f.mode === mode ? " checked" : ""}><span class="body"><span>${esc(label)}</span>${f.mode === mode ? inner : ""}</span></label>`;

    const words = f.household_query.toLowerCase().split(/\s+/).filter(Boolean);
    const households = this._overview.households
      .filter((h) => words.every((w) => `${h.address} ${h.members.map((m) => m.name).join(" ")}`.toLowerCase().includes(w)))
      .map((h) => `<button type="button" class="${h.id === f.household_id ? "on" : ""}" data-household="${esc(h.id)}"><span>${esc(h.address)}</span><span class="muted">${esc(h.members.map((m) => m.name).join(", "))}</span></button>`).join("");
    const existing = `<label class="field">${esc(t.existingHint)}<input id="f-hq" type="search" value="${esc(f.household_query)}" data-field="household_query"></label><div class="options">${households || `<p class="muted" style="padding:12px">${esc(t.noMatch)}</p>`}</div>`;
    const addressFields = `<div class="fields">${this._input("street", t.street, f.street)}<span class="small">${this._input("house_number", t.number, f.house_number, 'inputmode="numeric"')}</span><span class="small">${this._input("house_number_addition", t.addition, f.house_number_addition)}</span></div>
      <div class="fields"><span class="small">${this._input("postal_code", t.postal, f.postal_code)}</span>${this._input("city", t.city, f.city)}<span class="small">${this._input("country", t.country, f.country, 'maxlength="2"')}</span></div>`;

    let familyStep = "";
    if (!f.id) {
      const picked = new Set(f.family.map((x) => x.person_id));
      const fw = f.family_query.toLowerCase().split(/\s+/).filter(Boolean);
      const candidates = fw.length
        ? this._overview.people.filter((p) => !picked.has(p.id) && this._matches(p, fw)).slice(0, 8)
            .map((p) => `<button type="button" data-family-add="${esc(p.id)}"><span>${esc(p.name)}</span><span class="muted">${esc([this._birthdayText(p), p.city].filter(Boolean).join(" · "))}</span></button>`).join("")
        : "";
      const chosen = f.family.map((x, i) => {
        const p = this._overview.people.find((q) => q.id === x.person_id);
        return `<button type="button" class="chip" data-family-remove="${i}" aria-label="${esc(t.remove)}: ${esc(p ? p.name : "")}">${esc(t[x.relation])} ${esc(p ? p.name : "")} ✕</button>`;
      }).join("");
      const relations = ["child_of", "parent_of", "spouse_of", "partner_of"].map((r) => `<option value="${r}"${f.relation === r ? " selected" : ""}>${esc(t[r])}</option>`).join("");
      familyStep = `<section class="card"><h2>${esc(t.familyStep)} <span class="muted">${esc(t.skip)}</span></h2>
        ${chosen ? `<div class="chips">${chosen}</div>` : ""}
        <div class="fields"><label class="field">${esc(t.is(f.given_name))}<select id="f-relation" data-field="relation">${relations}</select></label>
        <label class="field">${esc(t.pick)}<input id="f-fq" type="search" value="${esc(f.family_query)}" data-field="family_query"></label></div>
        ${candidates ? `<div class="options">${candidates}</div>` : ""}
        <p class="muted">${esc(t.familyHint)}</p></section>`;
    }

    return `<form class="page narrow">
      <button type="button" class="link" data-action="cancel">‹ ${esc(t.cancel)}</button>
      <h1>${esc(f.id ? t.editTitle(f.original.name) : t.addTitle)}</h1>
      <p class="muted">${esc(t.onlyGiven)}</p>
      <section class="card"><h2>${esc(t.who)}</h2>
        <div class="fields">${this._input("given_name", t.given, f.given_name)}<span class="small">${this._input("family_name_prefix", t.prefix, f.family_name_prefix)}</span>${this._input("family_name", t.familyName, f.family_name)}</div>
        <div class="fields">${this._input("nickname", t.nickname, f.nickname)}
          <label class="field">${esc(t.gender)}<select id="f-gender" data-field="gender"><option value="">${esc(t.notSaid)}</option>${["male", "female", "other"].map((g) => `<option value="${g}"${f.gender === g ? " selected" : ""}>${esc(t[g])}</option>`).join("")}</select></label></div>
        <div class="cap">${esc(t.birthday)}</div>
        <div class="fields"><span class="small">${this._input("day", t.day, f.day, 'inputmode="numeric" maxlength="2"')}</span>
          <label class="field">${esc(t.month)}<select id="f-month" data-field="month"><option value="">–</option>${months}</select></label>
          <span class="small">${this._input("year", t.year, f.year, `inputmode="numeric" maxlength="4" placeholder="${esc(t.unknown)}"`)}</span></div>
        <p class="muted">${esc(t.noYear)}</p>
        <div class="fields"><label class="field">${esc(t.phone)}<input id="f-phone" type="tel" value="${esc(f.phone)}" data-field="phone"></label><label class="field">${esc(t.email)}<input id="f-email" type="email" value="${esc(f.email)}" data-field="email"></label></div>
        <label class="field">${esc(t.notes)}<textarea id="f-notes" data-field="notes">${esc(f.notes)}</textarea></label>
        <label class="check"><input type="checkbox" data-field="send_birthday_card"${f.send_birthday_card ? " checked" : ""}>${esc(t.card)}</label>
      </section>
      <section class="card"><h2>${esc(t.where(f.given_name))}</h2>
        ${f.id ? choice("keep", t.keep) : ""}
        ${f.id && f.had_household ? choice("update", t.updateAddress, addressFields) : ""}
        ${this._overview.households.length ? choice("existing", t.existing, existing) : ""}
        ${choice("new", t.newAddress, addressFields)}
        ${choice("none", t.none)}
      </section>
      ${familyStep}
      ${this._error ? `<p class="error" role="alert">${esc(this._error)}</p>` : ""}
      <div class="end"><button type="button" data-action="cancel">${esc(t.cancel)}</button><button type="button" class="primary" data-action="save">${esc(t.save)}</button></div>
    </form>`;
  }

  /* ---------- events ---------- */

  _onInput(event) {
    const target = event.target;
    if (target.dataset.bind === "query") {
      this._query = target.value;
      this._render();
      return;
    }
    const field = target.dataset.field;
    if (!field || !this._form) return;
    const f = this._form;
    if (target.type === "checkbox") f[field] = target.checked;
    else f[field] = target.value;
    if (field === "mode" && f.mode === "new" && f.id && event.type === "change") {
      Object.assign(f, { street: "", house_number: "", house_number_addition: "", postal_code: "", city: "", country: "" });
    }
    // Only redraw when the screen has to change; typing in a text field does not.
    if (["mode", "household_query", "family_query", "relation"].includes(field) || (field === "given_name" && event.type === "change")) this._render();
  }

  async _onClick(event) {
    const target = event.target.closest("button");
    if (!target) return;
    const data = target.dataset;
    if (data.open) return this._open(data.open);
    if (data.household) { this._form.household_id = data.household; return this._render(); }
    if (data.familyAdd) {
      this._form.family.push({ relation: this._form.relation, person_id: data.familyAdd });
      this._form.family_query = "";
      return this._render();
    }
    if (data.familyRemove) { this._form.family.splice(+data.familyRemove, 1); return this._render(); }
    switch (data.action) {
      case "list": this._view = { name: "list" }; this._error = ""; return this._loadOverview();
      case "add": this._startForm(null); return this._render();
      case "edit": this._startForm(this._detail); return this._render();
      case "cancel":
        this._error = "";
        if (this._form && this._form.id) return this._open(this._form.id);
        this._view = { name: "list" };
        return this._render();
      case "copy":
        try { await navigator.clipboard.writeText(data.text); target.textContent = this._t.copied; } catch (err) { /* no clipboard */ }
        return undefined;
      case "remove": this._view.confirm = true; return this._render();
      case "remove-no": this._view.confirm = false; return this._render();
      case "remove-yes": return this._remove();
      case "save": return this._save();
      default: return undefined;
    }
  }

  async _remove() {
    try {
      await this._ws({ type: "address_book/delete_person", person_id: this._view.id });
      this._view = { name: "list" };
      this._error = "";
      await this._loadOverview();
    } catch (err) {
      this._error = err.message || String(err);
      this._render();
    }
  }

  async _save() {
    const t = this._t;
    const f = this._form;
    const fail = (message) => { this._error = message; this._render(); };
    if (!f.given_name.trim()) return fail(t.needGiven);
    if (!!f.day.trim() !== !!f.month) return fail(t.needDay);
    const pad = (n, width) => String(n).trim().padStart(width, "0");
    let birth = null;
    if (f.month && f.year.trim()) birth = `${pad(f.year, 4)}-${pad(f.month, 2)}-${pad(f.day, 2)}`;
    else if (f.month) birth = `--${pad(f.month, 2)}-${pad(f.day, 2)}`;
    else if (f.year.trim()) birth = pad(f.year, 4);

    const keepRest = (list, value) => {
      const rest = (list || []).slice(1);
      const first = (list || [])[0];
      return value.trim() ? [{ value: value.trim(), label: first ? first.label : "" }, ...rest] : rest;
    };
    const person = {
      given_name: f.given_name.trim(),
      family_name_prefix: f.family_name_prefix.trim(),
      family_name: f.family_name.trim(),
      nickname: f.nickname.trim(),
      gender: f.gender || null,
      birth_date: birth,
      phones: keepRest(f.original && f.original.phones, f.phone),
      emails: keepRest(f.original && f.original.emails, f.email),
      notes: f.notes,
      send_birthday_card: !!f.send_birthday_card,
    };
    let address = { mode: f.mode };
    if (f.mode === "existing") {
      if (!f.household_id) return fail(t.needHousehold);
      address.household_id = f.household_id;
    } else if (f.mode === "new" || f.mode === "update") {
      address.household = {
        street: f.street.trim(), house_number: f.house_number.trim(),
        house_number_addition: f.house_number_addition.trim(),
        postal_code: f.postal_code.trim(), city: f.city.trim(), country: f.country.trim().toUpperCase(),
      };
    }
    const message = { type: "address_book/save_person", person, address, family: f.family };
    if (f.id) message.person_id = f.id;
    try {
      const result = await this._ws(message);
      this._error = "";
      this._overview = await this._ws({ type: "address_book/overview" });
      return this._open(result.id);
    } catch (err) {
      return fail(`${t.failed} ${err.message || String(err)}`);
    }
  }
}

if (!customElements.get("address-book-panel")) {
  customElements.define("address-book-panel", AddressBookPanel);
}
