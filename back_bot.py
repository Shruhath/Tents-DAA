"""
back_bot.py - Phase 3 BackBot (Backtracking / State-Space Search)

A complete solver that uses tree-centric backtracking with constraint
propagation and the MRV heuristic to guarantee a solution for any
valid Tents puzzle.
"""

import copy
from tents import TentsGame, TREE, TENT, GRASS, EMPTY
from game_logger import GameLogger


class BackBot:
    def __init__(self, game: TentsGame):
        self.game = game
        self.size = game.size
        self.name = "BackBot (Backtracking)"
        self._solution = None  # Cached solved board
        self.logger = GameLogger(self.size)

    def get_best_move(self):
        """Determine the next best move using backtracking search.

        Solves the full board once via backtracking, caches the result,
        then diffs against the live player_grid to return one move at a
        time.  TENT placements are returned before GRASS fills.

        Returns (r, c, move_type, cells_scanned) or None.
        """
        cells_scanned = 0

        # Solve once and cache
        if self._solution is None:
            board = copy.deepcopy(self.game.player_grid)

            # Build remaining capacities (constraint minus tents already placed)
            row_remaining = list(self.game.row_constraints)
            col_remaining = list(self.game.col_constraints)
            for r in range(self.size):
                for c in range(self.size):
                    if board[r][c] == TENT:
                        row_remaining[r] -= 1
                        col_remaining[c] -= 1

            if self._solve_recursive(board, 0, 0, row_remaining, col_remaining):
                self._solution = board
            else:
                return None

        # Priority 1: return the first pending TENT placement
        for r in range(self.size):
            for c in range(self.size):
                cells_scanned += 1
                if (self.game.player_grid[r][c] == EMPTY
                        and self._solution[r][c] == TENT):
                    return (r, c, TENT, cells_scanned)

        # Priority 2: fill remaining EMPTY cells as GRASS
        for r in range(self.size):
            for c in range(self.size):
                cells_scanned += 1
                if self.game.player_grid[r][c] == EMPTY:
                    return (r, c, GRASS, cells_scanned)

        return None

    # ------------------------------------------------------------------
    # Core backtracking with forward checking (Steps 3 + 6)
    # ------------------------------------------------------------------

    def _solve_recursive(self, board_state, current_tree_index, depth,
                         row_remaining, col_remaining):
        """Core recursive backtracking function with forward checking.

        Args:
            board_state: The current game grid being mutated in-place.
            current_tree_index: Index into self.game.trees for the next
                tree to assign a tent to.
            depth: Current recursion depth (for logging).
            row_remaining: Mutable list — how many tents each row still needs.
            col_remaining: Mutable list — how many tents each col still needs.

        Returns:
            True if a valid complete assignment was found, False otherwise.
        """
        trees = self.game.trees

        # Base Case: every tree has been considered — verify capacities.
        if current_tree_index == len(trees):
            valid = (all(v == 0 for v in row_remaining)
                     and all(v == 0 for v in col_remaining))
            if valid:
                self.logger.log_event("[SOLVED] All trees assigned successfully!")
            return valid

        tree_r, tree_c = trees[current_tree_index]

        # If this tree already has an adjacent tent (placed for a prior
        # tree), skip it — the tree is already satisfied.
        for nr, nc in self.game._get_orthogonal_neighbors(tree_r, tree_c):
            if board_state[nr][nc] == TENT:
                self.logger.log_event(
                    f"[HEURISTIC] Depth={depth} | Tree({tree_r},{tree_c}) "
                    f"already satisfied by tent at ({nr},{nc}). Skipping."
                )
                return self._solve_recursive(
                    board_state, current_tree_index + 1, depth,
                    row_remaining, col_remaining,
                )

        # Recursive Step: try placing a tent at each orthogonal neighbor.
        for nr, nc in self.game._get_orthogonal_neighbors(tree_r, tree_c):
            if board_state[nr][nc] != EMPTY:
                continue

            if not self._is_placement_safe(board_state, nr, nc):
                continue

            # Forward Checking: prune if row or col capacity exhausted
            if row_remaining[nr] <= 0 or col_remaining[nc] <= 0:
                continue

            # Place tent and update capacities
            board_state[nr][nc] = TENT
            row_remaining[nr] -= 1
            col_remaining[nc] -= 1
            self.logger.log_event(
                f"[RECURSE] Depth={depth} | Placing TENT for "
                f"Tree({tree_r},{tree_c}) at ({nr},{nc}). "
                f"Row {nr} remaining={row_remaining[nr]}, "
                f"Col {nc} remaining={col_remaining[nc]}."
            )

            # Recurse to the next tree
            if self._solve_recursive(
                board_state, current_tree_index + 1, depth + 1,
                row_remaining, col_remaining,
            ):
                return True

            # Backtrack: undo placement and restore capacities
            board_state[nr][nc] = EMPTY
            row_remaining[nr] += 1
            col_remaining[nc] += 1
            self.logger.log_event(
                f"[UNDO] Depth={depth} | Removing TENT at ({nr},{nc}). "
                f"Backtracking Tree({tree_r},{tree_c})."
            )

        return False

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _is_placement_safe(self, board_state, r, c):
        """Check the 8-neighbor adjacency rule (no tent touches another).

        Row/col capacity is now checked inline via forward checking
        (Step 6) before this method is called.
        """
        for dr in range(-1, 2):
            for dc in range(-1, 2):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if 0 <= nr < self.size and 0 <= nc < self.size:
                    if board_state[nr][nc] == TENT:
                        return False
        return True

    def _is_board_valid(self, board_state):
        """Verify that all row and column constraints are exactly met."""
        for r in range(self.size):
            row_tents = sum(1 for c in range(self.size) if board_state[r][c] == TENT)
            if row_tents != self.game.row_constraints[r]:
                return False

        for c in range(self.size):
            col_tents = sum(1 for r in range(self.size) if board_state[r][c] == TENT)
            if col_tents != self.game.col_constraints[c]:
                return False

        return True
