"""Export utilities for grouping and organizing requirements."""

from typing import Dict, List, Tuple


def group_requirements_by_sections(
    sections: List, all_requirements: List
) -> Tuple[Dict[int, List], List]:
    """Group requirements by section and collect orphans.

    Args:
        sections: List of section objects with .id attribute.
        all_requirements: List of requirement objects with .id, .section_id.

    Returns:
        Tuple of (section_id -> requirements dict, orphans list).
        Orphans are requirements not linked to any section in the given list.
    """
    section_reqs: Dict[int, List] = {}
    assigned_ids: set = set()

    for section in sections:
        reqs = [r for r in all_requirements if r.section_id == section.id]
        section_reqs[section.id] = reqs
        assigned_ids.update(r.id for r in reqs)

    orphans = [r for r in all_requirements if r.id not in assigned_ids]
    return section_reqs, orphans
