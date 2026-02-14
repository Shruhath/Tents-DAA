"""
solver_utils.py - Phase 2 Advanced Solvers (DP + D&C)

Core utility functions for the SmartBot solver:
  - solve_line_dp:     Row/Column DP solver (finds all valid tent/grass configs)
  - find_forced_moves: Intersection logic (deduces guaranteed placements)
"""

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
    results = []

    def _recurse(index: int, placed: int, last_was_tent: bool, path: list):
        # Base case: reached end of line
        if index == length:
            if placed == target_count:
                results.append(path[:])
            return

        cell = current_line[index]

        # TREE cells are kept as-is; they break tent adjacency
        if cell == TREE:
            path.append(TREE)
            _recurse(index + 1, placed, False, path)
            path.pop()
            return

        # Early prune: already placed too many tents
        if placed > target_count:
            return

        # Early prune: not enough remaining cells to reach target
        remaining = length - index
        # Count remaining TREE cells that can't hold tents
        remaining_trees = sum(
            1 for i in range(index, length) if current_line[i] == TREE
        )
        max_possible = placed + (remaining - remaining_trees)
        if max_possible < target_count:
            return

        # --- Fixed-position constraints (Step 4) ---
        # If this cell is locked, we must respect its current value.
        if index in fixed_positions:
            forced = current_line[index]
            if forced == TENT:
                # Must place TENT here (unless adjacency forbids it)
                if last_was_tent:
                    return  # Adjacency violation → no valid path
                path.append(TENT)
                _recurse(index + 1, placed + 1, True, path)
                path.pop()
                return
            elif forced == GRASS:
                # Must place GRASS here
                path.append(GRASS)
                _recurse(index + 1, placed, False, path)
                path.pop()
                return

        # --- Normal (non-fixed) cell choices ---

        # Option A: place TENT (only if last cell wasn't a tent)
        if not last_was_tent:
            path.append(TENT)
            _recurse(index + 1, placed + 1, True, path)
            path.pop()

        # Option B: place GRASS
        path.append(GRASS)
        _recurse(index + 1, placed, False, path)
        path.pop()

    _recurse(0, 0, False, [])
    return results


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
    # TODO: Implement in Step 5 (intersection logic).
    raise NotImplementedError("find_forced_moves not yet implemented")
