"""Core reconciliation solver.

Convention
----------
A matched pair satisfies ``tA == tB + offset`` (the offset is added to clock B).
For a fixed offset *d*, only same-code events with ``tA - tB == d`` can pair, and
strictly increasing timestamps on both sides guarantee that increasing indices on
one side are also increasing on the other.

A legal scheme picks an integer initial offset ``d0`` in the allowed range and
may, strictly between two matched pairs, permanently switch the offset to
``d0 + jump`` or ``d0 - jump`` at most once.  Matched pairs therefore form a
prefix under ``d0`` followed by a suffix under ``d1 = d0 +/- jump``.

The solver first maximises the number of matches, then exposes solutions in the
canonical tie-break order: initial offset, no-jump before minus before plus,
matches before the jump, and lexicographic pair-index sequence.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterator, List, Optional, Tuple


class FenwickMax:
    """Fenwick tree holding prefix maxima over 0..n-1."""

    __slots__ = ("n", "bit")

    def __init__(self, n: int) -> None:
        self.n = n
        self.bit = [0] * (n + 1)

    def update(self, pos: int, value: int) -> None:
        k = pos + 1
        while k <= self.n:
            if value > self.bit[k]:
                self.bit[k] = value
            k += k & -k

    def query(self, pos: int) -> int:
        """Maximum over positions ``0 .. pos-1`` (``pos`` excluded)."""
        best = 0
        k = pos
        while k > 0:
            if self.bit[k] > best:
                best = self.bit[k]
            k -= k & -k
        return best


@dataclass
class DiffRecord:
    """All match edges sharing one time difference, sorted by (i, j)."""

    d: int
    gi: List[int] = field(default_factory=list)  # global edge indices
    ii: List[int] = field(default_factory=list)  # index in stream A
    jj: List[int] = field(default_factory=list)  # index in stream B
    pre: List[int] = field(default_factory=list)  # longest within-diff chain ending
    suf: List[int] = field(default_factory=list)  # longest within-diff chain starting
    succ: List[List[int]] = field(default_factory=list)  # local dominating edges


@dataclass
class Space:
    """One solution space: fixed initial offset and fixed jump direction."""

    d0: int
    direction: str  # "none" | "plus" | "minus"
    rank: int       # canonical direction rank: none=0, minus=1, plus=2
    rec0: DiffRecord
    rec1: Optional[DiffRecord] = None
    score: int = 0
    # Jump spaces, aligned with rec0: best suffix length after each edge.
    # Successor lists in rec1 are built lazily, only for the winning space.
    cross: List[int] = field(default_factory=list)
    cross_succ: List[Optional[List[int]]] = field(default_factory=list)
    # w[q][e]: longest feasible suffix-after-jump reachable when a prefix chain
    # of exactly q within-rec0 edges ends at local edge e.
    w: List[List[int]] = field(default_factory=list)


def _cross_values(
    e0_i: List[int],
    e0_j: List[int],
    e1_i: List[int],
    e1_j: List[int],
    val1: List[int],
    m: int,
) -> List[int]:
    """For every edge of set 0, max ``val1[f]`` over set-1 edges f strictly after it.

    Both edge lists are sorted by (i, j) ascending.
    """
    fw = FenwickMax(m)
    out = [0] * len(e0_i)
    p = len(e1_i) - 1
    g = len(e0_i) - 1
    while g >= 0:
        i = e0_i[g]
        h = g
        while h > 0 and e0_i[h - 1] == i:
            h -= 1
        # Strictly greater i; equal-i edges must never bridge (same event).
        while p >= 0 and e1_i[p] > i:
            fw.update(m - 1 - e1_j[p], val1[p])
            p -= 1
        for q in range(h, g + 1):
            out[q] = fw.query(m - 1 - e0_j[q])  # jb > ja
        g = h - 1
    return out


def solve(
    times_a: List[int],
    codes_a: List[str],
    times_b: List[str],
    codes_b: List[str],
    min_offset: int,
    max_offset: int,
    jump: int,
    min_hits: int,
) -> Dict[str, object]:
    n, m = len(times_a), len(times_b)
    lo, hi = min_offset, max_offset

    # -- build every same-code edge whose difference can ever be used ---------
    by_code_b: Dict[str, List[Tuple[int, int]]] = {}
    for j, (tb, cb) in enumerate(zip(times_b, codes_b)):
        by_code_b.setdefault(cb, []).append((tb, j))

    e_i: List[int] = []
    e_j: List[int] = []
    e_d: List[int] = []
    for i, (ta, ca) in enumerate(zip(times_a, codes_a)):
        for tb, j in by_code_b.get(ca, ()):
            d = ta - tb
            in_range = lo <= d <= hi
            can_post = jump > 0 and (
                lo - jump <= d <= hi - jump or lo + jump <= d <= hi + jump
            )
            if in_range or can_post:
                e_i.append(i)
                e_j.append(j)
                e_d.append(d)

    if not e_i:
        return {
            "feasible": False,
            "match_count": 0,
            "reason": f"no same-code pair supports an offset in [{lo}, {hi}]",
        }

    # Edges grouped/ordered by (i, j); timestamps on each side are strictly
    # increasing, so index order equals time order.
    order = sorted(range(len(e_i)), key=lambda g: (e_i[g], e_j[g]))

    recs: Dict[int, DiffRecord] = {}
    for g in order:
        rec = recs.get(e_d[g])
        if rec is None:
            rec = DiffRecord(d=e_d[g])
            recs[e_d[g]] = rec
        rec.gi.append(g)
        rec.ii.append(e_i[g])
        rec.jj.append(e_j[g])

    # Within-difference chains in both directions.
    for rec in recs.values():
        k = len(rec.ii)
        pre = [0] * k
        fw = FenwickMax(m)
        g = 0
        while g < k:
            i = rec.ii[g]
            h = g
            while h + 1 < k and rec.ii[h + 1] == i:
                h += 1
            for q in range(g, h + 1):  # query before update: no equal-i chaining
                pre[q] = 1 + fw.query(rec.jj[q])
            for q in range(g, h + 1):
                fw.update(rec.jj[q], pre[q])
            g = h + 1
        rec.pre = pre

        suf = [0] * k
        fw2 = FenwickMax(m)
        g = k - 1
        while g >= 0:
            i = rec.ii[g]
            h = g
            while h > 0 and rec.ii[h - 1] == i:
                h -= 1
            for q in range(h, g + 1):
                suf[q] = 1 + fw2.query(m - 1 - rec.jj[q])
            for q in range(h, g + 1):
                fw2.update(m - 1 - rec.jj[q], suf[q])
            g = h - 1
        rec.suf = suf

        rec.succ = [[] for _ in range(k)]
        for a in range(k):
            ia, ja = rec.ii[a], rec.jj[a]
            for b in range(a + 1, k):
                if rec.ii[b] > ia and rec.jj[b] > ja:
                    rec.succ[a].append(b)

    # -- build all solution spaces --------------------------------------------
    spaces: List[Space] = []
    for d0 in sorted(d for d in recs if lo <= d <= hi):
        rec0 = recs[d0]
        spaces.append(
            Space(d0=d0, direction="none", rank=0, rec0=rec0, score=max(rec0.pre))
        )
        if jump <= 0:
            continue
        for sign, direction, rank in ((-1, "minus", 1), (1, "plus", 2)):
            d1 = d0 + sign * jump
            rec1 = recs.get(d1)
            if rec1 is None:
                continue
            best = _cross_values(rec0.ii, rec0.jj, rec1.ii, rec1.jj, rec1.suf, m)
            score = 0
            for a in range(len(rec0.ii)):
                if best[a] >= 1:  # a real jump needs at least one post edge
                    total = rec0.pre[a] + best[a]
                    if total > score:
                        score = total
            if score >= 2:  # and at least one pre edge
                spaces.append(
                    Space(
                        d0=d0,
                        direction=direction,
                        rank=rank,
                        rec0=rec0,
                        rec1=rec1,
                        score=score,
                        cross=best,
                    )
                )

    best_count = max((sp.score for sp in spaces), default=0)
    if best_count < min_hits:
        return {
            "feasible": False,
            "match_count": best_count,
            "reason": f"maximum match count {best_count} is below minHits {min_hits}",
        }

    top = [sp for sp in spaces if sp.score == best_count]
    K = best_count

    # -- solution enumeration -------------------------------------------------
    def enum_nojump(sp: Space) -> Iterator[Tuple[int, List[int]]]:
        """(matches-before-jump=0, global edge path), canonical order."""
        rec = sp.rec0
        path: List[int] = []

        def dfs() -> Iterator[None]:
            t = len(path) + 1
            rem = K - t + 1
            cands = range(len(rec.ii)) if not path else rec.succ[path[-1]]
            for c in cands:
                if rec.suf[c] >= rem:
                    path.append(c)
                    if t == K:
                        yield
                    else:
                        yield from dfs()
                    path.pop()

        for _ in dfs():
            yield 0, [rec.gi[c] for c in path]

    def ensure_w(sp: Space) -> int:
        """Largest prefix length q for which w[q] is available."""
        if sp.w:
            return len(sp.w) - 1
        rec0 = sp.rec0
        max_p = min(len(rec0.ii), K - 1)
        w: List[List[int]] = [[0] * len(rec0.ii), list(sp.cross)]
        for _ in range(2, max_p + 1):
            w.append(_cross_values(rec0.ii, rec0.jj, rec0.ii, rec0.jj, w[-1], m))
        sp.w = w
        return max_p

    def enum_jump(sp: Space, p_before: int) -> Iterator[Tuple[int, List[int]]]:
        """Paths with exactly ``p_before`` matches before the jump."""
        rec0, rec1 = sp.rec0, sp.rec1
        assert rec1 is not None
        suffix_len = K - p_before
        prefix: List[int] = []

        if not sp.cross_succ:
            sp.cross_succ = [None] * len(rec0.ii)

        def succ_after(c: int) -> List[int]:
            row = sp.cross_succ[c]
            if row is None:
                ia, ja = rec0.ii[c], rec0.jj[c]
                row = [
                    b
                    for b in range(len(rec1.ii))
                    if rec1.ii[b] > ia and rec1.jj[b] > ja
                ]
                sp.cross_succ[c] = row
            return row

        def dfs_suffix(first: List[int], t: int) -> Iterator[List[int]]:
            rem = K - t + 1
            for c in first:
                if rec1.suf[c] >= rem:
                    if t == K:
                        yield [c]
                    else:
                        for tail in dfs_suffix(rec1.succ[c], t + 1):
                            yield [c] + tail

        def dfs_pre() -> Iterator[List[int]]:
            # left = prefix edges still required starting at the candidate,
            # i.e. candidate is the (p_before - left + 1)-th picked edge.
            left = p_before - len(prefix)
            cands = range(len(rec0.ii)) if not prefix else rec0.succ[prefix[-1]]
            for c in cands:
                if sp.w[left][c] >= suffix_len:
                    prefix.append(c)
                    if len(prefix) == p_before:
                        for tail in dfs_suffix(succ_after(c), p_before + 1):
                            yield list(prefix) + tail
                    else:
                        yield from dfs_pre()
                    prefix.pop()

        max_p = ensure_w(sp)
        if p_before <= max_p:
            for local_path in dfs_pre():
                g0 = [rec0.gi[c] for c in local_path[:p_before]]
                g1 = [rec1.gi[c] for c in local_path[p_before:]]
                yield p_before, g0 + g1

    def space_solutions(sp: Space) -> Iterator[Tuple[int, List[int]]]:
        if sp.direction == "none":
            yield from enum_nojump(sp)
        else:
            for p_before in range(1, K):
                yield from enum_jump(sp, p_before)

    def canonical_key(sp: Space, p_before: int, global_path: List[int]):
        pairs = tuple((e_i[g], e_j[g]) for g in global_path)
        return sp.d0, sp.rank, p_before, pairs

    # Best solution inside each top space, then compare across spaces.
    ranked: List[Tuple[Tuple, Space, int, List[int]]] = []
    for sp in top:
        p_before, global_path = next(space_solutions(sp))
        ranked.append((canonical_key(sp, p_before, global_path), sp, p_before, global_path))
    ranked.sort(key=lambda x: x[0])

    win_key, win_sp, win_before, win_path = ranked[0]
    runner: Optional[Tuple[Space, int, List[int]]] = None
    if len(ranked) > 1:
        runner = (ranked[1][1], ranked[1][2], ranked[1][3])

    # A different solution inside the winning space may outrank other spaces.
    for p2, path2 in space_solutions(win_sp):
        key2 = canonical_key(win_sp, p2, path2)
        if key2 == win_key:
            continue
        if runner is None or key2 < canonical_key(runner[0], runner[1], runner[2]):
            runner = (win_sp, p2, path2)
        break

    def build(sp: Space, p_before: int, global_path: List[int]) -> Dict[str, object]:
        d1 = None
        if sp.direction == "plus":
            d1 = sp.d0 + jump
        elif sp.direction == "minus":
            d1 = sp.d0 - jump
        pairs_out = []
        for k, g in enumerate(global_path):
            ia, ib = e_i[g], e_j[g]
            post = p_before > 0 and k >= p_before
            at_last_pre = p_before > 0 and k == p_before - 1
            offset = d1 if post else sp.d0
            pairs_out.append(
                {
                    "indexA": ia,
                    "indexB": ib,
                    "timeA": times_a[ia],
                    "timeB": times_b[ib],
                    "code": codes_a[ia],
                    "offset": offset,
                    "offsetBefore": sp.d0 if at_last_pre else offset,
                    "offsetAfter": d1 if at_last_pre else offset,
                    "jumpAppliedBefore": post,
                }
            )
        jump_a = jump_b = None
        if p_before > 0:
            jump_a = e_i[global_path[p_before]]
            jump_b = e_j[global_path[p_before]]
        return {
            "initialOffset": sp.d0,
            "jumpDirection": sp.direction,
            "jumpIndexA": jump_a,
            "jumpIndexB": jump_b,
            "matchesBeforeJump": p_before,
            "pairs": pairs_out,
            "pairIndices": [[p["indexA"], p["indexB"]] for p in pairs_out],
        }

    result: Dict[str, object] = {
        "feasible": True,
        "match_count": K,
        "uniqueness": "unique" if runner is None else "ambiguous",
        "solution": build(win_sp, win_before, win_path),
        "witness": None,
    }
    if runner is not None:
        r_sp, r_before, r_path = runner
        result["witness"] = build(r_sp, r_before, r_path)
    return result
