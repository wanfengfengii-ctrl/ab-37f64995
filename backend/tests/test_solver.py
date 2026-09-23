"""Tests for the reconciliation solver.

A deliberately simple O(n^3)-style brute-force oracle re-derives every legal
scheme from scratch (no Fenwick trees, no cross tables) and the randomized fuzz
checks the optimized solver against it, including canonical ordering and the
unique/ambiguous distinction.
"""
from __future__ import annotations

import itertools
import random
from typing import Dict, List, Optional, Tuple

import pytest

from app.solver import solve


# ---------------------------------------------------------------------------
# Brute-force oracle
# ---------------------------------------------------------------------------


def _edges(times_a, codes_a, times_b, codes_b, d):
    out = []
    for i, (ta, ca) in enumerate(zip(times_a, codes_a)):
        for j, (tb, cb) in enumerate(zip(times_b, codes_b)):
            if ca == cb and ta - tb == d:
                out.append((i, j))
    return sorted(out)


def _after(edges, la, lb):
    return [e for e in edges if e[0] > la and e[1] > lb]


def _chain_max(edges) -> int:
    """Longest chain in an edge set ordered by strict (i, j)."""
    if not edges:
        return 0
    edges = sorted(edges)
    dp = [1] * len(edges)
    for a in range(len(edges)):
        for b in range(a):
            if edges[b][0] < edges[a][0] and edges[b][1] < edges[a][1]:
                dp[a] = max(dp[a], dp[b] + 1)
    return max(dp)


def _jump_max(pre, post) -> int:
    """Best total with one jump: pre-chain then post-chain."""
    # dp1[f]: longest post chain starting at f
    dp1 = {}
    for f in sorted(post, reverse=True):
        dp1[f] = 1 + max(
            [dp1[g] for g in post if g[0] > f[0] and g[1] > f[1]], default=0
        )
    dp0 = {}
    for e in sorted(pre, reverse=True):
        stay = max(
            [dp0[b] for b in pre if b[0] > e[0] and b[1] > e[1]], default=0
        )
        jump = max(
            [dp1[f] for f in post if f[0] > e[0] and f[1] > e[1]], default=0
        )
        dp0[e] = 1 + max(stay, jump)
    return max(dp0.values(), default=0)


def _enum_chains(edges, length, la=-1, lb=-1):
    """Yield chains of exactly `length` after (la, lb), tuple-ascending."""
    if length == 0:
        yield ()
        return
    for e in [x for x in edges if x[0] > la and x[1] > lb]:
        if _chain_max(_after(edges, e[0], e[1])) >= length - 1:
            for tail in _enum_chains(edges, length - 1, e[0], e[1]):
                yield (e,) + tail


def oracle(times_a, codes_a, times_b, codes_b, lo, hi, jump, min_hits):
    """Return (feasible, match_count, winner_key, witness_key)."""
    space_scores = []
    edge_cache: Dict[int, List[Tuple[int, int]]] = {}

    def edges(d):
        if d not in edge_cache:
            edge_cache[d] = _edges(times_a, codes_a, times_b, codes_b, d)
        return edge_cache[d]

    for d0 in range(lo, hi + 1):
        pre = edges(d0)
        score = _chain_max(pre)
        space_scores.append((score, d0, "none", None))
        if jump > 0:
            for sign, direction in ((-1, "minus"), (1, "plus")):
                post = edges(d0 + sign * jump)
                if post:
                    score = _jump_max(pre, post)
                    if score >= 2:
                        space_scores.append((score, d0, direction, sign))

    best = max((s[0] for s in space_scores), default=0)
    if best < min_hits:
        return False, best, None, None

    # Enumerate optimal keys in canonical order; at most two per space suffice.
    keys: List[Tuple] = []
    rank = {"none": 0, "minus": 1, "plus": 2}
    for d0 in range(lo, hi + 1):
        pre = edges(d0)
        # no-jump
        if _chain_max(pre) == best:
            for k, path in enumerate(_enum_chains(pre, best)):
                if k >= 2:
                    break
                keys.append((d0, 0, 0, tuple(path)))
        if jump > 0:
            for sign, direction in ((-1, "minus"), (1, "plus")):
                post = edges(d0 + sign * jump)
                if _jump_max(pre, post) != best:
                    continue
                for p_before in range(1, best):
                    produced = 0
                    for cp in _enum_chains(pre, p_before):
                        la, lb = cp[-1]
                        for tail in _enum_chains(
                            [f for f in post if f[0] > la and f[1] > lb],
                            best - p_before,
                        ):
                            keys.append(
                                (d0, rank[direction], p_before, cp + tail)
                            )
                            produced += 1
                            if produced >= 2:
                                break
                        if produced >= 2:
                            break
                    if produced >= 2:
                        break

    keys.sort()
    winner = keys[0]
    witness = keys[1] if len(keys) > 1 else None
    return True, best, winner, witness


# ---------------------------------------------------------------------------
# Helpers to build solver inputs
# ---------------------------------------------------------------------------


def run(ta, ca, tb, cb, lo=0, hi=100, jump=0, min_hits=1):
    return solve(ta, ca, tb, cb, lo, hi, jump, min_hits)


def result_key(sol):
    return (
        sol["initialOffset"],
        {"none": 0, "minus": 1, "plus": 2}[sol["jumpDirection"]],
        sol["matchesBeforeJump"],
        tuple((p["indexA"], p["indexB"]) for p in sol["pairs"]),
    )


# ---------------------------------------------------------------------------
# Fixed scenarios
# ---------------------------------------------------------------------------


def test_simple_exact_alignment():
    r = run([1, 2, 3], ["A", "B", "C"], [1, 2, 3], ["A", "B", "C"], -5, 5)
    assert r["feasible"]
    assert r["match_count"] == 3
    s = r["solution"]
    assert s["initialOffset"] == 0
    assert s["jumpDirection"] == "none"
    assert [p["offset"] for p in s["pairs"]] == [0, 0, 0]
    assert s["pairIndices"] == [[0, 0], [1, 1], [2, 2]]


def test_skipped_events_allowed():
    # A: A . B . C at offset -10 against B's A, B, Q, C
    r = run(
        [1, 5, 10, 20],
        ["A", "X", "B", "C"],
        [11, 20, 26, 30],
        ["A", "B", "Q", "C"],
        -10, 10,
    )
    assert r["match_count"] == 3
    assert r["solution"]["initialOffset"] == -10
    assert result_key(r["solution"])[3] == ((0, 0), (2, 1), (3, 3))


def test_min_hits_rejects():
    r = run([1, 2], ["A", "B"], [10, 20], ["A", "B"], -1, 1, min_hits=2)
    assert not r["feasible"]
    assert r["match_count"] == 0
    assert r["reason"]


def test_jump_plus_extends_matches():
    # offset -2 for first pair, then permanent +5 jump -> offset 3
    A_t, A_c = [1, 9, 13], ["A", "B", "C"]
    B_t, B_c = [3, 4, 10], ["A", "B", "C"]
    # diffs: A-B = -2, 5, 3 ; d0=-2, jump=5 -> d1=3
    r = run(A_t, A_c, B_t, B_c, -5, 5, jump=5, min_hits=1)
    assert r["feasible"]
    assert r["match_count"] == 2
    s = r["solution"]
    assert s["initialOffset"] == -2
    assert s["jumpDirection"] == "plus"
    assert s["matchesBeforeJump"] == 1
    p0, p1 = s["pairs"]
    assert p0["offsetBefore"] == -2 and p0["offsetAfter"] == 3
    assert p0["timeA"] == p0["timeB"] + (-2)
    assert p1["offsetBefore"] == 3 and p1["jumpAppliedBefore"] is True
    assert p1["timeA"] == p1["timeB"] + 3
    assert s["jumpIndexA"] == 2 and s["jumpIndexB"] == 2


def test_canonical_prefers_no_jump_at_same_count():
    # Two matches at d0=0, and an equally good jumpy solution elsewhere.
    A_t = [0, 10, 11]
    A_c = ["A", "B", "C"]
    B_t = [0, 5, 10]
    B_c = ["A", "C", "B"]
    # diff 0 edges: (0,0)A,(1,2)B chain len2 ; jump possibilities exist too
    r = run(A_t, A_c, B_t, B_c, -10, 10, jump=5)
    assert r["match_count"] == 2
    assert r["solution"]["jumpDirection"] == "none"
    assert r["solution"]["initialOffset"] == 0


def test_ambiguous_ladder_returns_witness():
    # Ladder with offset -1 vs offset 0; canonical winner is the smaller d0.
    A_t = [1, 2]
    A_c = ["X", "X"]
    B_t = [1, 2, 3]
    B_c = ["X", "X", "X"]
    r = run(A_t, A_c, B_t, B_c, -1, 1, jump=0)
    assert r["match_count"] == 2
    assert r["uniqueness"] == "ambiguous"
    assert r["witness"] is not None
    s = result_key(r["solution"])
    w = result_key(r["witness"])
    assert s < w
    # distinct pair-index sequences
    assert s[3] != w[3]
    assert s[0] == -1
    assert s[3] == ((0, 1), (1, 2))
    assert w[3] == ((0, 0), (1, 1))


def test_unique_solution_has_no_witness():
    r = run([1, 2], ["A", "B"], [1, 2], ["A", "B"], -1, 1)
    assert r["uniqueness"] == "unique"
    assert r["witness"] is None


def test_offset_bounds_filter_edges():
    # matches only at offset 7, outside [-1,1]
    r = run([7, 8], ["A", "B"], [0, 1], ["A", "B"], -1, 1)
    assert not r["feasible"]
    r2 = run([7, 8], ["A", "B"], [0, 1], ["A", "B"], -1, 7)
    assert r2["feasible"]
    assert r2["solution"]["initialOffset"] == 7


def test_solution_pair_integrity():
    rng = random.Random(4242)
    for _ in range(200):
        ta, ca, tb, cb = _random_streams(rng, n=6, m=6, alphabet=3, tmax=12)
        lo, hi, J = -6, 6, rng.choice([0, 2, 3, 5])
        r = run(ta, ca, tb, cb, lo, hi, J, 1)
        if not r["feasible"]:
            continue
        for sol in (r["solution"], r.get("witness")):
            if sol is None:
                continue
            d0 = sol["initialOffset"]
            d1 = d0
            if sol["jumpDirection"] == "plus":
                d1 = d0 + J
            elif sol["jumpDirection"] == "minus":
                d1 = d0 - J
            pairs = sol["pairs"]
            ia = [p["indexA"] for p in pairs]
            ib = [p["indexB"] for p in pairs]
            assert ia == sorted(ia) and len(set(ia)) == len(ia)
            assert ib == sorted(ib) and len(set(ib)) == len(ib)
            pb = sol["matchesBeforeJump"]
            for k, p in enumerate(pairs):
                assert p["code"] == ca[p["indexA"]] == cb[p["indexB"]]
                d = d1 if pb and k >= pb else d0
                assert p["timeA"] == p["timeB"] + d
                assert p["offset"] == d
            assert len(pairs) == r["match_count"]
            if pb:
                assert 1 <= pb <= len(pairs) - 1


# ---------------------------------------------------------------------------
# Randomized fuzz against the oracle
# ---------------------------------------------------------------------------


def _random_streams(rng, n, m, alphabet, tmax):
    def gen(k):
        times = sorted(rng.sample(range(tmax), k))
        codes = [
            rng.choice("ABCDEFGH"[:alphabet]) for _ in range(k)
        ]
        return times, codes

    ta, ca = gen(n)
    tb, cb = gen(m)
    return ta, ca, tb, cb


def test_fuzz_matches_oracle():
    rng = random.Random(1234)
    trials = 1500
    for it in range(trials):
        n = rng.randint(2, 6)
        m = rng.randint(2, 6)
        ta, ca, tb, cb = _random_streams(rng, n, m, rng.randint(1, 4), 14)
        lo = rng.randint(-8, 2)
        hi = lo + rng.randint(0, 10)
        jump = rng.choice([0, 1, 2, 3, 5])
        min_hits = rng.randint(1, 4)

        r = run(ta, ca, tb, cb, lo, hi, jump, min_hits)
        feas, best, wkey, wit_key = oracle(
            ta, ca, tb, cb, lo, hi, jump, min_hits
        )
        assert r["feasible"] == feas, (ta, ca, tb, cb, lo, hi, jump, min_hits)
        assert r["match_count"] == best
        if feas:
            assert result_key(r["solution"]) == wkey
            if wit_key is None:
                assert r["uniqueness"] == "unique"
                assert r["witness"] is None
            else:
                assert r["uniqueness"] == "ambiguous"
                assert result_key(r["witness"]) == wit_key


def test_fuzz_larger_smoke():
    rng = random.Random(99)
    for _ in range(40):
        ta, ca, tb, cb = _random_streams(rng, 30, 30, 6, 400)
        lo, hi, J = -30, 30, rng.choice([0, 7, 25])
        r = run(ta, ca, tb, cb, lo, hi, J, 1)
        assert r["match_count"] >= 0
        if r["feasible"]:
            s = r["solution"]
            assert len(s["pairs"]) == r["match_count"]


def test_fuzz_medium_full_enumeration():
    # Up to 8 events per side, still fully enumerated by the slow oracle.
    rng = random.Random(2025)
    for it in range(250):
        n = rng.randint(2, 8)
        m = rng.randint(2, 8)
        ta, ca, tb, cb = _random_streams(rng, n, m, rng.randint(2, 5), 20)
        lo = rng.randint(-6, 2)
        hi = lo + rng.randint(0, 8)
        jump = rng.choice([0, 2, 4])
        min_hits = rng.randint(1, 3)
        r = run(ta, ca, tb, cb, lo, hi, jump, min_hits)
        feas, best, wkey, wit_key = oracle(ta, ca, tb, cb, lo, hi, jump, min_hits)
        assert r["feasible"] == feas
        assert r["match_count"] == best
        if feas:
            assert result_key(r["solution"]) == wkey
            if wit_key is None:
                assert r["uniqueness"] == "unique" and r["witness"] is None
            else:
                assert r["uniqueness"] == "ambiguous"
                assert result_key(r["witness"]) == wit_key
