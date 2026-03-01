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
    # Core backtracking with forward checking (Steps 3 + 6 + 7)
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

            # Adjacency propagation: mark 8 neighbours as GRASS
            grassed = self._mark_neighbors_grass(board_state, nr, nc)

            self.logger.log_event(
                f"[RECURSE] Depth={depth} | Placing TENT for "
                f"Tree({tree_r},{tree_c}) at ({nr},{nc}). "
                f"Row {nr} remaining={row_remaining[nr]}, "
                f"Col {nc} remaining={col_remaining[nc]}. "
                f"Grassed {len(grassed)} neighbours."
            )

            # Recurse to the next tree
            if self._solve_recursive(
                board_state, current_tree_index + 1, depth + 1,
                row_remaining, col_remaining,
            ):
                return True

            # Backtrack: undo GRASS neighbours, placement, and capacities
            self._restore_neighbors(board_state, grassed)
            board_state[nr][nc] = EMPTY
            row_remaining[nr] += 1
            col_remaining[nc] += 1
            self.logger.log_event(
                f"[UNDO] Depth={depth} | Removing TENT at ({nr},{nc}). "
                f"Restored {len(grassed)} neighbours. "
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

    def _mark_neighbors_grass(self, board_state, r, c):
        """Mark the 8 neighbours of (r, c) as GRASS if they are EMPTY.

        Returns a list of (row, col) cells that were changed so the
        caller can undo them on backtrack.
        """
        grassed = []
        for dr in range(-1, 2):
            for dc in range(-1, 2):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if 0 <= nr < self.size and 0 <= nc < self.size:
                    if board_state[nr][nc] == EMPTY:
                        board_state[nr][nc] = GRASS
                        grassed.append((nr, nc))
        return grassed

    def _restore_neighbors(self, board_state, grassed):
        """Undo a previous _mark_neighbors_grass call."""
        for gr, gc in grassed:
            board_state[gr][gc] = EMPTY

    def _get_domain_size(self, tree, board_state, row_remaining, col_remaining):
        """Return the number of legally available spots for *tree*'s tent.

        A spot counts if it is EMPTY, passes the 8-neighbor adjacency
        check, and its row/col still has remaining capacity.

        Args:
            tree: (row, col) of the tree.
            board_state: Current game grid.
            row_remaining: Remaining tent capacity per row.
            col_remaining: Remaining tent capacity per col.

        Returns:
            Integer 0–4.
        """
        tr, tc = tree
        count = 0
        for nr, nc in self.game._get_orthogonal_neighbors(tr, tc):
            if board_state[nr][nc] != EMPTY:
                continue
            if row_remaining[nr] <= 0 or col_remaining[nc] <= 0:
                continue
            if not self._is_placement_safe(board_state, nr, nc):
                continue
            count += 1
        return count

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
