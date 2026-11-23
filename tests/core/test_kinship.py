"""Tests for deriving family relations."""

from __future__ import annotations

import pytest

from custom_components.address_book.core.kinship import Kin, kinship
from custom_components.address_book.core.labels import kinship_label
from custom_components.address_book.core.model import AddressBook


@pytest.mark.parametrize(
    ("person", "other", "kin", "by_marriage", "dutch"),
    [
        # couples
        ("tom", "iris", Kin.SPOUSE, False, "echtgenote"),
        ("iris", "tom", Kin.SPOUSE, False, "echtgenoot"),
        ("piet", "els", Kin.EX_PARTNER, False, "ex-partner"),
        # straight up and down
        ("tom", "piet", Kin.PARENT, False, "vader"),
        ("tom", "maria", Kin.PARENT, False, "moeder"),
        ("tom", "henk", Kin.GRANDPARENT, False, "opa"),
        ("tom", "wim", Kin.GRANDPARENT, False, "opa"),
        ("noor", "truus", Kin.GREAT_GRANDPARENT, False, "overgrootmoeder"),
        ("tom", "noor", Kin.CHILD, False, "dochter"),
        ("piet", "noor", Kin.GRANDCHILD, False, "kleindochter"),
        ("henk", "noor", Kin.GREAT_GRANDCHILD, False, "achterkleindochter"),
        # sideways
        ("tom", "eva", Kin.SIBLING, False, "zus"),
        ("tom", "anna", Kin.AUNT_UNCLE, False, "tante"),
        ("tom", "bas", Kin.AUNT_UNCLE, False, "oom"),
        ("anna", "tom", Kin.NIECE_NEPHEW, False, "neef"),
        ("eva", "noor", Kin.NIECE_NEPHEW, False, "nicht"),
        ("tom", "sam", Kin.COUSIN, False, "neef"),
        ("tom", "lot", Kin.COUSIN, False, "nicht"),
        ("noor", "anna", Kin.GREAT_AUNT_UNCLE, False, "oudtante"),
        ("anna", "noor", Kin.GRAND_NIECE_NEPHEW, False, "achternicht"),
        ("noor", "sam", Kin.RELATIVE, False, "familielid"),
        # the partner of a relative
        ("tom", "kees", Kin.AUNT_UNCLE, True, "aangetrouwde oom"),
        ("piet", "iris", Kin.CHILD_IN_LAW, False, "schoondochter"),
        ("eva", "iris", Kin.SIBLING_IN_LAW, False, "schoonzus"),
        ("rik", "maria", Kin.STEP_PARENT, False, "stiefmoeder"),
        ("finn", "tom", Kin.STEP_PARENT, False, "stiefvader"),
        # a relative of your partner
        ("iris", "piet", Kin.PARENT_IN_LAW, False, "schoonvader"),
        ("iris", "eva", Kin.SIBLING_IN_LAW, False, "schoonzus"),
        ("tom", "finn", Kin.STEP_CHILD, False, "stiefzoon"),
        ("iris", "anna", Kin.AUNT_UNCLE, True, "aangetrouwde tante"),
        ("iris", "sam", Kin.COUSIN, True, "aangetrouwde neef"),
        ("kees", "tom", Kin.NIECE_NEPHEW, True, "aangetrouwde neef"),
    ],
)
def test_kinship(
    family: AddressBook,
    person: str,
    other: str,
    kin: Kin,
    by_marriage: bool,
    dutch: str,
) -> None:
    """Every family term follows from parents and partners alone."""
    relation = kinship(family, person, other)
    assert relation is not None
    assert (relation.kin, relation.by_marriage) == (kin, by_marriage)
    gender = family.people[other].gender
    assert kinship_label(relation, gender, "nl") == dutch


def test_half_sibling(family: AddressBook) -> None:
    """Tom and Rik share a father but not a mother."""
    relation = kinship(family, "tom", "rik")
    assert relation is not None
    assert relation.kin is Kin.SIBLING
    assert relation.half
    assert kinship_label(relation, family.people["rik"].gender, "nl") == "halfbroer"
    assert kinship_label(relation, family.people["rik"].gender, "en") == "half-brother"

    full = kinship(family, "tom", "eva")
    assert full is not None and not full.half


def test_self_and_strangers(family: AddressBook) -> None:
    """You are yourself; a stranger is nobody's family."""
    me = kinship(family, "tom", "tom")
    assert me is not None and me.kin is Kin.SELF
    assert kinship(family, "tom", "vreemde") is None


def test_ended_relationship_gives_no_in_laws(family: AddressBook) -> None:
    """Piet's ex-partner is not Tom's step-mother."""
    assert kinship(family, "tom", "els") is None
    assert kinship(family, "els", "tom") is None


def test_unknown_person_raises(family: AddressBook) -> None:
    """Asking about someone who is not in the book is an error."""
    with pytest.raises(KeyError):
        kinship(family, "tom", "nobody")


def test_label_falls_back(family: AddressBook) -> None:
    """Unknown gender gives a neutral word, unknown language gives English."""
    relation = kinship(family, "tom", "anna")
    assert relation is not None
    assert kinship_label(relation, None, "nl-NL") == "oom of tante"
    assert kinship_label(relation, family.people["anna"].gender, "fr") == "aunt"


def test_family_queries(family: AddressBook) -> None:
    """The questions the address book is for: "who are Anna's children?"."""
    assert [p.given_name for p in family.children_of("piet")] == ["Rik", "Tom", "Eva"]
    assert [p.given_name for p in family.parents_of("tom")] == ["Piet", "Maria"]
    assert [p.given_name for p in family.siblings_of("tom")] == ["Rik", "Eva"]
    # Lot's birth year is unknown, so she sorts after Sam.
    assert [p.given_name for p in family.children_of("anna")] == ["Sam", "Lot"]
    assert family.partner_ids("piet") == ["maria"]
    assert set(family.partner_ids("piet", current_only=False)) == {"maria", "els"}


def test_death_does_not_end_in_laws(family: AddressBook) -> None:
    """Your late aunt's husband is still your uncle."""
    family.people["anna"].deceased = True
    relation = kinship(family, "tom", "kees")
    assert relation is not None
    assert (relation.kin, relation.by_marriage) == (Kin.AUNT_UNCLE, True)
