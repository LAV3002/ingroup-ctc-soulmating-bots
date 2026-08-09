from __future__ import annotations

from dataclasses import dataclass

from regabot.models import Participant


@dataclass(frozen=True)
class Match:
    a_badge: int
    b_badge: int
    a_priority: int
    b_priority: int
    super_match: bool


def compute_matches(
    registrations: dict[int, Participant],
    sympathies: dict[int, list[tuple[int, int]]],
) -> list[Match]:
    matches: list[Match] = []
    for a_badge, a_entries in sympathies.items():
        if a_badge not in registrations:
            continue
        for target_badge, a_priority in a_entries:
            if target_badge == a_badge or target_badge not in registrations:
                continue
            if a_badge > target_badge:
                # каждую пару учитываем один раз (a_badge < target_badge)
                continue
            b_priority = next(
                (p for (t, p) in sympathies.get(target_badge, []) if t == a_badge),
                None,
            )
            if b_priority is None:
                continue
            matches.append(
                Match(
                    a_badge=a_badge,
                    b_badge=target_badge,
                    a_priority=a_priority,
                    b_priority=b_priority,
                    super_match=a_priority == 1 and b_priority == 1,
                )
            )
    return matches


def partners_for_badge(matches: list[Match], badge: int) -> list[tuple[int, bool]]:
    result: list[tuple[int, bool]] = []
    for m in matches:
        if m.a_badge == badge:
            result.append((m.b_badge, m.super_match))
        elif m.b_badge == badge:
            result.append((m.a_badge, m.super_match))
    return result


def badges_with_matches(matches: list[Match]) -> set[int]:
    involved: set[int] = set()
    for m in matches:
        involved.add(m.a_badge)
        involved.add(m.b_badge)
    return involved


def assign_pairs(matches: list[Match]) -> list[Match]:
    """Жадное разбиение взаимных метчей на непересекающиеся пары.

    Порядок выбора: СуперМэтч первым, затем минимальная сумма приоритетов,
    затем меньший номер бейджа как тай-брейк. Каждый участник попадает
    максимум в одну пару.
    """
    ordered = sorted(
        matches,
        key=lambda m: (not m.super_match, m.a_priority + m.b_priority, m.a_badge, m.b_badge),
    )
    used: set[int] = set()
    pairs: list[Match] = []
    for m in ordered:
        if m.a_badge in used or m.b_badge in used:
            continue
        used.add(m.a_badge)
        used.add(m.b_badge)
        pairs.append(m)
    return pairs
