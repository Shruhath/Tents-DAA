"""
solver_utils.py - Phase 2 Advanced Solvers (DP + D&C)

Core utility functions for the SmartBot solver:
  - solve_line_dp:     Row/Column DP solver (finds all valid tent/grass configs)
  - find_forced_moves: Intersection logic (deduces guaranteed placements)
"""

from functools import lru_cache

from tents import EMPTY, TREE, TENT, GRASS


# ---------------------------------------------------------------------------
# Stage 1 – Core DP Logic
# ---------------------------------------------------------------------------

def solve_line_dp(
    length: int,
    target_count: int,
    current_line: list,
    fixed_positions: set,
) -> list:
    """Enumerate every valid tent/grass configuration for a single row or column.

    Uses recursive back-tracking (later memoised) to explore all ways of
    placing exactly *target_count* tents in *length* cells while obeying:
      1. No two tents may be adjacent.
      2. Cells listed in *fixed_positions* keep their current value.

    Args:
        length:          Number of cells in the row / column.
        target_count:    Exact number of tents required.
        current_line:    Current cell states (EMPTY, TENT, GRASS, TREE).
        fixed_positions: Set of indices whose value is already locked.

    Returns:
        A list of valid configurations.  Each configuration is a list of
        length *length* containing TENT or GRASS for every non-TREE cell.
        Returns an empty list if no valid configuration exists.
    """
    # Pre-compute suffix tree counts for O(1) pruning
    suffix_trees = [0] * (length + 1)
    for i in range(length - 1, -1, -1):
        suffix_trees[i] = suffix_trees[i + 1] + (1 if current_line[i] == TREE else 0)

    @lru_cache(maxsize=None)
    def _recurse(index: int, placed: int, last_was_tent: bool) -> tuple:
        # Returns a tuple of valid suffix-tuples from this state onward.
        # Base case: reached end of line
        if index == length:
            if placed == target_count:
                return ((),)   # one valid (empty) suffix
            return ()          # no valid suffixes

        cell = current_line[index]

        # TREE cells are kept as-is; they break tent adjacency
        if cell == TREE:
            suffixes = _recurse(index + 1, placed, False)
            return tuple((TREE,) + s for s in suffixes)

        # Early prune: already placed too many tents
        if placed > target_count:
            return ()

        # Early prune: not enough remaining cells to reach target
        remaining = length - index
        max_possible = placed + (remaining - suffix_trees[index])
        if max_possible < target_count:
            return ()

        # --- Fixed-position constraints (Step 4) ---
        if index in fixed_positions:
            forced = current_line[index]
            if forced == TENT:
                if last_was_tent:
                    return ()
                suffixes = _recurse(index + 1, placed + 1, True)
                return tuple((TENT,) + s for s in suffixes)
            elif forced == GRASS:
                suffixes = _recurse(index + 1, placed, False)
                return tuple((GRASS,) + s for s in suffixes)

        # --- Normal (non-fixed) cell choices ---
        result = []

        # Option A: place TENT (only if last cell wasn't a tent)
        if not last_was_tent:
            suffixes = _recurse(index + 1, placed + 1, True)
            result.extend((TENT,) + s for s in suffixes)

        # Option B: place GRASS
        suffixes = _recurse(index + 1, placed, False)
        result.extend((GRASS,) + s for s in suffixes)

        return tuple(result)

    raw = _recurse(0, 0, False)
    return [list(cfg) for cfg in raw]


def find_forced_moves(valid_configs: list) -> dict:
    """Identify cells that must be TENT or GRASS across *all* valid configs.

    Stacks every configuration returned by :func:`solve_line_dp` and checks
    each cell index:
      - If the cell is TENT in **every** config  → forced TENT.
      - If the cell is GRASS in **every** config → forced GRASS.
      - Otherwise                                → no forced move.

    Args:
        valid_configs: List of valid row/column configurations (each a list
                       of TENT / GRASS values).

    Returns:
        Dict mapping cell index (int) → TENT or GRASS for every forced
        position.  Indices with no consensus are omitted.
    """
    if not valid_configs:
        return {}

    length = len(valid_configs[0])
    forced = {}

    for i in range(length):
        values = {cfg[i] for cfg in valid_configs}
        # If every config agrees on this cell, it's forced
        if len(values) == 1:
            val = values.pop()
            if val in (TENT, GRASS):
                forced[i] = val

    return forced
