"""
smart_bot.py - Phase 2 SmartBot (D&C + DP)

An advanced solver that combines the cheap greedy heuristics from Phase 1
with the DP row/column solver and Divide & Conquer decomposition from
solver_utils.
"""

from tents import TentsGame, TREE, TENT, GRASS, EMPTY
from solver_utils import solve_line_dp, find_forced_moves, solve_with_dnc


class SmartBot:
    def __init__(self, game: TentsGame):
        self.game = game
        self.size = game.size
        self.name = "SmartBot (D&C + DP)"

    def get_best_move(self):
        """Determine the next best move using greedy heuristics.

        Returns (r, c, move_type, cells_scanned) or None.
        Cheap O(1)-style checks are tried first before the expensive DP
        engine (added in later steps).
        """
        cells_scanned = 0

        # --- Heuristic 1: Adjacency Exclusion ---
        # Tent neighbours must be Grass.
        for r in range(self.size):
            for c in range(self.size):
                cells_scanned += 1
                if self.game.player_grid[r][c] == TENT:
                    for nr in range(max(0, r - 1), min(self.size, r + 2)):
                        for nc in range(max(0, c - 1), min(self.size, c + 2)):
                            if nr == r and nc == c:
                                continue
                            cells_scanned += 1
                            if self.game.player_grid[nr][nc] == EMPTY:
                                return (nr, nc, GRASS, cells_scanned)

        # --- Heuristic 2: Row/Col Saturation (constraint met → rest Grass) ---
        for r in range(self.size):
            cells_scanned += 1
            current_tents = self.game.player_grid[r].count(TENT)
            if current_tents == self.game.row_constraints[r]:
                for c in range(self.size):
                    cells_scanned += 1
                    if self.game.player_grid[r][c] == EMPTY:
                        return (r, c, GRASS, cells_scanned)

        for c in range(self.size):
            cells_scanned += 1
            current_tents = sum(
                1 for r in range(self.size)
                if self.game.player_grid[r][c] == TENT
            )
            if current_tents == self.game.col_constraints[c]:
                for r in range(self.size):
                    cells_scanned += 1
                    if self.game.player_grid[r][c] == EMPTY:
                        return (r, c, GRASS, cells_scanned)

        # --- Heuristic 3: Forced Tent (remaining empties == remaining need) ---
        for r in range(self.size):
            cells_scanned += 1
            tents = 0
            empties = []
            for c in range(self.size):
                cells_scanned += 1
                val = self.game.player_grid[r][c]
                if val == TENT:
                    tents += 1
                elif val == EMPTY:
                    empties.append(c)
            target = self.game.row_constraints[r]
            if tents + len(empties) == target and empties:
                return (r, empties[0], TENT, cells_scanned)

        for c in range(self.size):
            cells_scanned += 1
            tents = 0
            empties = []
            for r in range(self.size):
                cells_scanned += 1
                val = self.game.player_grid[r][c]
                if val == TENT:
                    tents += 1
                elif val == EMPTY:
                    empties.append(r)
            target = self.game.col_constraints[c]
            if tents + len(empties) == target and empties:
                return (empties[0], c, TENT, cells_scanned)

        # --- Heuristic 4: Isolated Tree (tree with 1 free neighbour → Tent) ---
        for r in range(self.size):
            for c in range(self.size):
                cells_scanned += 1
                if self.game.player_grid[r][c] == TREE:
                    neighbors = self.game._get_orthogonal_neighbors(r, c)
                    has_tent = False
                    empty_neighbors = []
                    for nr, nc in neighbors:
                        cells_scanned += 1
                        val = self.game.player_grid[nr][nc]
                        if val == TENT:
                            has_tent = True
                            break
                        elif val == EMPTY:
                            empty_neighbors.append((nr, nc))
                    if not has_tent and len(empty_neighbors) == 1:
                        er, ec = empty_neighbors[0]
                        return (er, ec, TENT, cells_scanned)

        # --- Heuristic 5: No-Man's Land (empty with no adjacent tree → Grass) ---
        for r in range(self.size):
            for c in range(self.size):
                cells_scanned += 1
                if self.game.player_grid[r][c] == EMPTY:
                    neighbors = self.game._get_orthogonal_neighbors(r, c)
                    has_tree = False
                    for nr, nc in neighbors:
                        cells_scanned += 1
                        if self.game.player_grid[nr][nc] == TREE:
                            has_tree = True
                            break
                    if not has_tree:
                        return (r, c, GRASS, cells_scanned)

        # --- Heuristic 6: Locked Candidates ---
        # Rows
        for r in range(self.size):
            locked_trees = []
            for tr, tc in self.game.trees:
                neighbors = self.game._get_orthogonal_neighbors(tr, tc)
                has_tent = False
                valid_spots = []
                for nr, nc in neighbors:
                    if self.game.player_grid[nr][nc] == TENT:
                        has_tent = True
                        break
                    if self.game.player_grid[nr][nc] == EMPTY:
                        valid_spots.append((nr, nc))
                if has_tent:
                    continue
                if valid_spots and all(sr == r for sr, sc in valid_spots):
                    locked_trees.append((tr, tc))

            current_tents = self.game.player_grid[r].count(TENT)
            target = self.game.row_constraints[r]
            if current_tents + len(locked_trees) == target:
                reserved = set()
                for tr, tc in locked_trees:
                    for nr, nc in self.game._get_orthogonal_neighbors(tr, tc):
                        if self.game.player_grid[nr][nc] == EMPTY:
                            reserved.add((nr, nc))
                for c in range(self.size):
                    cells_scanned += 1
                    if self.game.player_grid[r][c] == EMPTY:
                        if (r, c) not in reserved:
                            return (r, c, GRASS, cells_scanned)

        # Columns
        for c in range(self.size):
            locked_trees = []
            for tr, tc in self.game.trees:
                neighbors = self.game._get_orthogonal_neighbors(tr, tc)
                has_tent = False
                valid_spots = []
                for nr, nc in neighbors:
                    if self.game.player_grid[nr][nc] == TENT:
                        has_tent = True
                        break
                    if self.game.player_grid[nr][nc] == EMPTY:
                        valid_spots.append((nr, nc))
                if has_tent:
                    continue
                if valid_spots and all(sc == c for sr, sc in valid_spots):
                    locked_trees.append((tr, tc))

            current_tents = sum(
                1 for r in range(self.size)
                if self.game.player_grid[r][c] == TENT
            )
            target = self.game.col_constraints[c]
            if current_tents + len(locked_trees) == target:
                reserved = set()
                for tr, tc in locked_trees:
                    for nr, nc in self.game._get_orthogonal_neighbors(tr, tc):
                        if self.game.player_grid[nr][nc] == EMPTY:
                            reserved.add((nr, nc))
                for r in range(self.size):
                    cells_scanned += 1
                    if self.game.player_grid[r][c] == EMPTY:
                        if (r, c) not in reserved:
                            return (r, c, GRASS, cells_scanned)

        # --- DP Row/Col Solver (Step 16) ---
        dp_move = self._solve_rows_and_cols()
        if dp_move:
            r, c, val = dp_move
            cells_scanned += self.size * self.size  # approximate DP work
            return (r, c, val, cells_scanned)

        return None

    def _solve_rows_and_cols(self):
        """Run DP on every row and column, return the first forced move found.

        Returns (r, c, TENT/GRASS) or None.
        """
        size = self.size

        # --- Rows ---
        for r in range(size):
            row = self.game.player_grid[r]
            fixed = {c for c in range(size) if row[c] in (TENT, GRASS)}
            target = self.game.row_constraints[r]

            configs = solve_line_dp(size, target, row, fixed)
            if not configs:
                continue
            forced = find_forced_moves(configs)
            for c, val in forced.items():
                if self.game.player_grid[r][c] == EMPTY:
                    return (r, c, val)

        # --- Columns ---
        for c in range(size):
            col = [self.game.player_grid[r][c] for r in range(size)]
            fixed = {r for r in range(size) if col[r] in (TENT, GRASS)}
            target = self.game.col_constraints[c]

            configs = solve_line_dp(size, target, col, fixed)
            if not configs:
                continue
            forced = find_forced_moves(configs)
            for r, val in forced.items():
                if self.game.player_grid[r][c] == EMPTY:
                    return (r, c, val)

        return None
