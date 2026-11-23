"""Work out how two people are related.

Only three things are stored: who is whose parent, who is married to whom and
who are partners. Everything else – sibling, uncle, cousin, mother-in-law – is
derived here, so it can never disagree with the stored facts.

Pure Python: no Home Assistant imports.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .model import AddressBook, RelationshipType


class Kin(StrEnum):
    """What someone is to you."""

    SELF = "self"
    SPOUSE = "spouse"
    PARTNER = "partner"
    EX_PARTNER = "ex_partner"
    PARENT = "parent"
    CHILD = "child"
    SIBLING = "sibling"
    GRANDPARENT = "grandparent"
    GRANDCHILD = "grandchild"
    GREAT_GRANDPARENT = "great_grandparent"
    GREAT_GRANDCHILD = "great_grandchild"
    AUNT_UNCLE = "aunt_uncle"
    NIECE_NEPHEW = "niece_nephew"
    COUSIN = "cousin"
    GREAT_AUNT_UNCLE = "great_aunt_uncle"
    GRAND_NIECE_NEPHEW = "grand_niece_nephew"
    RELATIVE = "relative"  # related by blood, further away than the above
    STEP_PARENT = "step_parent"
    STEP_CHILD = "step_child"
    PARENT_IN_LAW = "parent_in_law"
    CHILD_IN_LAW = "child_in_law"
    SIBLING_IN_LAW = "sibling_in_law"


@dataclass(frozen=True)
class Kinship:
    """How ``other`` is related to ``person``: "other is person's <kin>"."""

    kin: Kin
    by_marriage: bool = False  # e.g. the husband of your aunt
    half: bool = False  # half-brother, half-sister
    up: int = 0  # generations up from person to the common ancestor
    down: int = 0  # generations down from there to other
    via_id: str | None = None  # the person the link runs through, if any


# (generations up, generations down) -> kin, for blood relatives.
_BLOOD: dict[tuple[int, int], Kin] = {
    (0, 0): Kin.SELF,
    (1, 0): Kin.PARENT,
    (2, 0): Kin.GRANDPARENT,
    (3, 0): Kin.GREAT_GRANDPARENT,
    (0, 1): Kin.CHILD,
    (0, 2): Kin.GRANDCHILD,
    (0, 3): Kin.GREAT_GRANDCHILD,
    (1, 1): Kin.SIBLING,
    (2, 1): Kin.AUNT_UNCLE,
    (1, 2): Kin.NIECE_NEPHEW,
    (2, 2): Kin.COUSIN,
    (3, 1): Kin.GREAT_AUNT_UNCLE,
    (1, 3): Kin.GRAND_NIECE_NEPHEW,
}

# The partner of your <key> is your <value>.
_PARTNER_OF_RELATIVE: dict[Kin, Kin] = {
    Kin.PARENT: Kin.STEP_PARENT,
    Kin.CHILD: Kin.CHILD_IN_LAW,
    Kin.SIBLING: Kin.SIBLING_IN_LAW,
}

# The <key> of your partner is your <value>.
_RELATIVE_OF_PARTNER: dict[Kin, Kin] = {
    Kin.PARENT: Kin.PARENT_IN_LAW,
    Kin.CHILD: Kin.STEP_CHILD,
    Kin.SIBLING: Kin.SIBLING_IN_LAW,
}


def _ancestors(book: AddressBook, person_id: str) -> dict[str, int]:
    """Return every ancestor with the number of generations up (self = 0)."""
    depths = {person_id: 0}
    queue = [person_id]
    while queue:
        current = queue.pop(0)
        for parent_id in book.parent_ids(current):
            if parent_id not in depths:
                depths[parent_id] = depths[current] + 1
                queue.append(parent_id)
    return depths


def _blood(book: AddressBook, person_id: str, other_id: str) -> Kinship | None:
    """Return the blood relation through the nearest common ancestor."""
    mine = _ancestors(book, person_id)
    theirs = _ancestors(book, other_id)
    common = mine.keys() & theirs.keys()
    if not common:
        return None
    nearest = min(common, key=lambda i: (mine[i] + theirs[i], mine[i], i))
    up, down = mine[nearest], theirs[nearest]
    kin = _BLOOD.get((up, down), Kin.RELATIVE)

    half = False
    if kin is Kin.SIBLING:
        my_parents = set(book.parent_ids(person_id))
        their_parents = set(book.parent_ids(other_id))
        # Only call it "half" when both have two known parents and share one.
        half = (
            len(my_parents) >= 2
            and len(their_parents) >= 2
            and len(my_parents & their_parents) == 1
        )
    return Kinship(kin=kin, half=half, up=up, down=down)


def kinship(book: AddressBook, person_id: str, other_id: str) -> Kinship | None:
    """Return what ``other`` is to ``person``, or None when they are not family.

    Looked for in this order: the two as a couple, blood relatives, the partner
    of a blood relative, and a blood relative of your own partner.
    """
    for known in (person_id, other_id):
        if known not in book.people:
            raise KeyError(known)
    if person_id == other_id:
        return Kinship(kin=Kin.SELF)

    together = [
        r
        for r in book.couple_relationships(person_id, current_only=False)
        if r.involves(other_id)
    ]
    for relationship in together:
        if not relationship.ended:
            married = relationship.type is RelationshipType.SPOUSE
            return Kinship(kin=Kin.SPOUSE if married else Kin.PARTNER)

    if (blood := _blood(book, person_id, other_id)) is not None:
        return blood

    if together:
        return Kinship(kin=Kin.EX_PARTNER)

    candidates: list[Kinship] = []

    # other is the partner of one of my blood relatives
    for relative_id in book.partner_ids(other_id):
        via = _blood(book, person_id, relative_id)
        if via is None or relative_id == person_id:
            continue
        mapped = _PARTNER_OF_RELATIVE.get(via.kin)
        candidates.append(
            Kinship(
                kin=mapped or via.kin,
                by_marriage=mapped is None,
                up=via.up,
                down=via.down,
                via_id=relative_id,
            )
        )

    # other is a blood relative of my partner
    for partner_id in book.partner_ids(person_id):
        via = _blood(book, partner_id, other_id)
        if via is None or partner_id == other_id:
            continue
        mapped = _RELATIVE_OF_PARTNER.get(via.kin)
        candidates.append(
            Kinship(
                kin=mapped or via.kin,
                by_marriage=mapped is None,
                up=via.up,
                down=via.down,
                via_id=partner_id,
            )
        )

    if not candidates:
        return None
    return min(candidates, key=lambda k: (k.up + k.down, k.up, k.via_id or ""))
