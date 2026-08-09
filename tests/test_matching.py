from regabot.matching import assign_pairs, badges_with_matches, compute_matches, partners_for_badge
from regabot.models import Participant


def _p(badge: int) -> Participant:
    return Participant(
        chat_id=badge,
        user_id=badge,
        name=f"u{badge}",
        phone="+0",
        username=None,
        table_tag="art",
        badge=badge,
    )


def test_no_sympathies_no_matches():
    assert compute_matches({1: _p(1), 2: _p(2)}, {}) == []


def test_one_way_is_not_a_match():
    regs = {1: _p(1), 2: _p(2)}
    symp = {1: [(2, 1)]}
    assert compute_matches(regs, symp) == []


def test_mutual_match_with_priorities():
    regs = {1: _p(1), 2: _p(2)}
    symp = {1: [(2, 1)], 2: [(1, 2)]}
    matches = compute_matches(regs, symp)
    assert len(matches) == 1
    m = matches[0]
    assert (m.a_badge, m.b_badge) == (1, 2)
    assert m.a_priority == 1
    assert m.b_priority == 2
    assert not m.super_match


def test_super_match_when_both_rank_one():
    regs = {1: _p(1), 2: _p(2)}
    symp = {1: [(2, 1)], 2: [(1, 1)]}
    matches = compute_matches(regs, symp)
    assert matches[0].super_match


def test_self_sympathy_ignored():
    regs = {1: _p(1)}
    symp = {1: [(1, 1)]}
    assert compute_matches(regs, symp) == []


def test_unknown_target_ignored():
    regs = {1: _p(1)}
    symp = {1: [(99, 1)]}
    assert compute_matches(regs, symp) == []


def test_each_pair_counted_once():
    regs = {1: _p(1), 2: _p(2)}
    symp = {1: [(2, 1)], 2: [(1, 1)]}
    assert len(compute_matches(regs, symp)) == 1


def test_partners_and_involved():
    regs = {1: _p(1), 2: _p(2), 3: _p(3)}
    symp = {1: [(2, 1), (3, 2)], 2: [(1, 1)], 3: [(1, 3)]}
    matches = compute_matches(regs, symp)
    assert sorted(badges_with_matches(matches)) == [1, 2, 3]
    partners = sorted(b for (b, _) in partners_for_badge(matches, 1))
    assert partners == [2, 3]


def test_assign_pairs_super_first_and_disjoint():
    regs = {i: _p(i) for i in (1, 2, 3, 4, 5)}
    symp = {
        1: [(3, 1), (2, 2)],
        2: [(1, 2), (3, 1)],
        3: [(1, 1), (2, 2)],
        4: [(5, 1)],
        5: [(4, 3)],
    }
    pairs = assign_pairs(compute_matches(regs, symp))
    pair_keys = sorted((m.a_badge, m.b_badge) for m in pairs)
    assert pair_keys == [(1, 3), (4, 5)]


def test_assign_pairs_lower_combined_priority_wins():
    regs = {1: _p(1), 2: _p(2), 3: _p(3)}
    symp = {
        1: [(2, 1), (3, 2)],
        2: [(1, 2)],
        3: [(1, 3)],
    }
    pairs = assign_pairs(compute_matches(regs, symp))
    assert [(m.a_badge, m.b_badge) for m in pairs] == [(1, 2)]


def test_assign_pairs_each_node_at_most_once():
    regs = {1: _p(1), 2: _p(2), 3: _p(3)}
    symp = {
        1: [(2, 1), (3, 1)],
        2: [(1, 1), (3, 1)],
        3: [(1, 1), (2, 1)],
    }
    pairs = assign_pairs(compute_matches(regs, symp))
    used = [b for m in pairs for b in (m.a_badge, m.b_badge)]
    assert len(used) == len(set(used))
    assert len(pairs) == 1


def test_assign_pairs_unmatched_when_partner_taken():
    regs = {1: _p(1), 2: _p(2), 3: _p(3)}
    symp = {
        1: [(2, 1)],
        2: [(1, 1), (3, 2)],
        3: [(2, 2)],
    }
    pairs = assign_pairs(compute_matches(regs, symp))
    badges = {b for m in pairs for b in (m.a_badge, m.b_badge)}
    assert badges == {1, 2}
    assert 3 not in badges
