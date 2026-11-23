"""Words for family relations, per language.

Home Assistant's own translation files cover the user interface. These words
are needed in answers ("Anna is your aunt"), so they live with the kinship code.

Pure Python: no Home Assistant imports.
"""

from __future__ import annotations

from .kinship import Kin, Kinship
from .model import Gender

# kin -> (male, female, neutral)
_Words = dict[Kin, tuple[str, str, str]]

_EN: _Words = {
    Kin.SELF: ("self", "self", "self"),
    Kin.SPOUSE: ("husband", "wife", "spouse"),
    Kin.PARTNER: ("partner", "partner", "partner"),
    Kin.EX_PARTNER: ("ex-partner", "ex-partner", "ex-partner"),
    Kin.PARENT: ("father", "mother", "parent"),
    Kin.CHILD: ("son", "daughter", "child"),
    Kin.SIBLING: ("brother", "sister", "sibling"),
    Kin.GRANDPARENT: ("grandfather", "grandmother", "grandparent"),
    Kin.GRANDCHILD: ("grandson", "granddaughter", "grandchild"),
    Kin.GREAT_GRANDPARENT: (
        "great-grandfather",
        "great-grandmother",
        "great-grandparent",
    ),
    Kin.GREAT_GRANDCHILD: (
        "great-grandson",
        "great-granddaughter",
        "great-grandchild",
    ),
    Kin.AUNT_UNCLE: ("uncle", "aunt", "aunt or uncle"),
    Kin.NIECE_NEPHEW: ("nephew", "niece", "niece or nephew"),
    Kin.COUSIN: ("cousin", "cousin", "cousin"),
    Kin.GREAT_AUNT_UNCLE: ("great-uncle", "great-aunt", "great-aunt or great-uncle"),
    Kin.GRAND_NIECE_NEPHEW: ("grandnephew", "grandniece", "grandniece or grandnephew"),
    Kin.RELATIVE: ("relative", "relative", "relative"),
    Kin.STEP_PARENT: ("stepfather", "stepmother", "step-parent"),
    Kin.STEP_CHILD: ("stepson", "stepdaughter", "stepchild"),
    Kin.PARENT_IN_LAW: ("father-in-law", "mother-in-law", "parent-in-law"),
    Kin.CHILD_IN_LAW: ("son-in-law", "daughter-in-law", "child-in-law"),
    Kin.SIBLING_IN_LAW: ("brother-in-law", "sister-in-law", "sibling-in-law"),
}

# Dutch uses "neef"/"nicht" for both a cousin and a nephew/niece.
_NL: _Words = {
    Kin.SELF: ("zelf", "zelf", "zelf"),
    Kin.SPOUSE: ("echtgenoot", "echtgenote", "echtgenoot"),
    Kin.PARTNER: ("partner", "partner", "partner"),
    Kin.EX_PARTNER: ("ex-partner", "ex-partner", "ex-partner"),
    Kin.PARENT: ("vader", "moeder", "ouder"),
    Kin.CHILD: ("zoon", "dochter", "kind"),
    Kin.SIBLING: ("broer", "zus", "broer of zus"),
    Kin.GRANDPARENT: ("opa", "oma", "grootouder"),
    Kin.GRANDCHILD: ("kleinzoon", "kleindochter", "kleinkind"),
    Kin.GREAT_GRANDPARENT: ("overgrootvader", "overgrootmoeder", "overgrootouder"),
    Kin.GREAT_GRANDCHILD: ("achterkleinzoon", "achterkleindochter", "achterkleinkind"),
    Kin.AUNT_UNCLE: ("oom", "tante", "oom of tante"),
    Kin.NIECE_NEPHEW: ("neef", "nicht", "neef of nicht"),
    Kin.COUSIN: ("neef", "nicht", "neef of nicht"),
    Kin.GREAT_AUNT_UNCLE: ("oudoom", "oudtante", "oudoom of oudtante"),
    Kin.GRAND_NIECE_NEPHEW: ("achterneef", "achternicht", "achterneef of achternicht"),
    Kin.RELATIVE: ("familielid", "familielid", "familielid"),
    Kin.STEP_PARENT: ("stiefvader", "stiefmoeder", "stiefouder"),
    Kin.STEP_CHILD: ("stiefzoon", "stiefdochter", "stiefkind"),
    Kin.PARENT_IN_LAW: ("schoonvader", "schoonmoeder", "schoonouder"),
    Kin.CHILD_IN_LAW: ("schoonzoon", "schoondochter", "schoonkind"),
    Kin.SIBLING_IN_LAW: ("zwager", "schoonzus", "zwager of schoonzus"),
}

_WORDS: dict[str, _Words] = {"en": _EN, "nl": _NL}
_HALF: dict[str, str] = {"en": "half-{}", "nl": "half{}"}
_BY_MARRIAGE: dict[str, str] = {"en": "{} by marriage", "nl": "aangetrouwde {}"}

DEFAULT_LANGUAGE = "en"


def kinship_label(
    relation: Kinship, gender: Gender | None = None, language: str = DEFAULT_LANGUAGE
) -> str:
    """Return the word for a relation: "aunt", "aangetrouwde oom", "half-brother".

    ``gender`` is that of the person being described. ``language`` may be a
    full tag such as ``nl-NL``; unknown languages fall back to English.
    """
    code = language.split("-")[0].lower()
    if code not in _WORDS:
        code = DEFAULT_LANGUAGE
    male, female, neutral = _WORDS[code][relation.kin]
    if gender is Gender.MALE:
        word = male
    elif gender is Gender.FEMALE:
        word = female
    else:
        word = neutral
    if relation.half:
        word = _HALF[code].format(word)
    if relation.by_marriage:
        word = _BY_MARRIAGE[code].format(word)
    return word
