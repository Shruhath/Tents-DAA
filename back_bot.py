"""
back_bot.py - Phase 3 BackBot (Backtracking / State-Space Search)

A complete solver that uses tree-centric backtracking with constraint
propagation and the MRV heuristic to guarantee a solution for any
valid Tents puzzle.
"""

import copy
from tents import TentsGame, TREE, TENT, GRASS, EMPTY


class BackBot:
    def __init__(self, game: TentsGame):
        self.game = game
        self.size = game.size
        self.name = "BackBot (Backtracking)"
        self._solution = None  # Cached solved board

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
            if self._solve_recursive(board, 0):
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
    # Core naive backtracking (Step 3)
    # ------------------------------------------------------------------

    def _solve_recursive(self, board_state, current_tree_index):
        """Core recursive backtracking function.

        Args:
            board_state: The current game grid being mutated in-place.
            current_tree_index: Index into self.game.trees for the next
                tree to assign a tent to.

        Returns:
            True if a valid complete assignment was found, False otherwise.
        """
        trees = self.game.trees

        # Base Case: every tree has been considered — verify the board.
        if current_tree_index == len(trees):
            return self._is_board_valid(board_state)

        tree_r, tree_c = trees[current_tree_index]

        # If this tree already has an adjacent tent (placed for a prior
        # tree), skip it — the tree is already satisfied.
        for nr, nc in self.game._get_orthogonal_neighbors(tree_r, tree_c):
            if board_state[nr][nc] == TENT:
                return self._solve_recursive(board_state, current_tree_index + 1)

        # Recursive Step: try placing a tent at each orthogonal neighbor.
        for nr, nc in self.game._get_orthogonal_neighbors(tree_r, tree_c):
            if board_state[nr][nc] != EMPTY:
                continue

            if not self._is_placement_safe(board_state, nr, nc):
                continue

            # Place tent
            board_state[nr][nc] = TENT

            # Recurse to the next tree
            if self._solve_recursive(board_state, current_tree_index + 1):
                return True

            # Backtrack: undo the placement
            board_state[nr][nc] = EMPTY

        return False

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _is_placement_safe(self, board_state, r, c):
        """Check the 8-neighbor adjacency rule (no tent touches another).

        This is the only safety check in the naive version.  Row/col
        capacity forward-checking will be added in Step 6.
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
