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


# ---------------------------------------------------------------------------
# Stage 2 – Divide & Conquer Logic
# ---------------------------------------------------------------------------

def build_constraint_graph(game) -> dict:
    """Build an adjacency graph of unknown (EMPTY) cells on the player board.

    Two EMPTY cells are connected if placing a tent in one could affect the
    validity of placing a tent in the other.  Specifically, cells are
    neighbours when they are within 8-way (King's move) distance of each
    other, since tents may not touch even diagonally.

    Args:
        game: A :class:`TentsGame` instance whose ``player_grid`` reflects
              the current solving state.

    Returns:
        Dict mapping each EMPTY cell ``(r, c)`` to a list of its EMPTY
        8-way neighbours: ``{(r, c): [(nr, nc), ...]}``.
    """
    # TODO: Implement in Step 10 (neighbor logic).
    size = game.size
    graph = {}

    # Collect all EMPTY cells as nodes
    for r in range(size):
        for c in range(size):
            if game.player_grid[r][c] == EMPTY:
                graph[(r, c)] = []

    # Connect 8-way neighbours (King's move)
    for (r, c) in graph:
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if (nr, nc) in graph:
                    graph[(r, c)].append((nr, nc))

    return graph


def find_connected_components(graph: dict) -> list:
    """Find connected components in the constraint graph via BFS.

    Args:
        graph: Adjacency dict from :func:`build_constraint_graph`.
               ``{(r, c): [(nr, nc), ...]}``.

    Returns:
        List of sets, where each set contains the ``(r, c)`` tuples
        belonging to one connected component.
    """
    visited = set()
    components = []

    for node in graph:
        if node in visited:
            continue
        # BFS from this unvisited node
        component = set()
        queue = [node]
        visited.add(node)
        while queue:
            current = queue.pop(0)
            component.add(current)
            for neighbour in graph[current]:
                if neighbour not in visited:
                    visited.add(neighbour)
                    queue.append(neighbour)
        components.append(component)

    return components


def _apply_dp_to_lines(game) -> bool:
    """Run DP on every row and column, applying any forced moves found.

    Returns True if at least one cell was changed on the player grid.
    """
    size = game.size
    progress = False

    # --- Rows ---
    for r in range(size):
        row = game.player_grid[r]
        fixed = {c for c in range(size) if row[c] in (TENT, GRASS)}
        target = game.row_constraints[r]

        configs = solve_line_dp(size, target, row, fixed)
        if not configs:
            continue
        forced = find_forced_moves(configs)
        for c, val in forced.items():
            if game.player_grid[r][c] == EMPTY:
                game.player_grid[r][c] = val
                progress = True

    # --- Columns ---
    for c in range(size):
        col = [game.player_grid[r][c] for r in range(size)]
        fixed = {r for r in range(size) if col[r] in (TENT, GRASS)}
        target = game.col_constraints[c]

        configs = solve_line_dp(size, target, col, fixed)
        if not configs:
            continue
        forced = find_forced_moves(configs)
        for r, val in forced.items():
            if game.player_grid[r][c] == EMPTY:
                game.player_grid[r][c] = val
                progress = True

    return progress


def solve_with_dnc(game) -> bool:
    """Divide & Conquer entry point.

    1. Build the constraint graph of EMPTY cells.
    2. Find connected components.
    3. If multiple components exist, solve each independently by
       restricting DP to the rows/columns each component touches.
    4. If only one component (or no split possible), run DP on all
       rows and columns.

    Args:
        game: A :class:`TentsGame` instance (modifies ``player_grid``
              in place).

    Returns:
        True if any progress was made (at least one cell filled).
    """
    graph = build_constraint_graph(game)
    if not graph:
        return False  # No EMPTY cells left

    components = find_connected_components(graph)

    if len(components) <= 1:
        # Single component – just run DP on all rows/cols
        return _apply_dp_to_lines(game)

    # Multiple components – solve rows/cols touched by each component
    progress = False
    for comp in components:
        comp_rows = {r for r, c in comp}
        comp_cols = {c for r, c in comp}
        size = game.size

        # DP on rows touched by this component
        for r in comp_rows:
            row = game.player_grid[r]
            fixed = {c for c in range(size) if row[c] in (TENT, GRASS)}
            target = game.row_constraints[r]

            configs = solve_line_dp(size, target, row, fixed)
            if not configs:
                continue
            forced = find_forced_moves(configs)
            for c, val in forced.items():
                if game.player_grid[r][c] == EMPTY:
                    game.player_grid[r][c] = val
                    progress = True

        # DP on columns touched by this component
        for c in comp_cols:
            col = [game.player_grid[r][c] for r in range(size)]
            fixed = {r for r in range(size) if col[r] in (TENT, GRASS)}
            target = game.col_constraints[c]

            configs = solve_line_dp(size, target, col, fixed)
            if not configs:
                continue
            forced = find_forced_moves(configs)
            for r, val in forced.items():
                if game.player_grid[r][c] == EMPTY:
                    game.player_grid[r][c] = val
                    progress = True

    return progress
