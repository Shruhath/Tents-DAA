"""
back_bot.py - Phase 3 BackBot (Backtracking / State-Space Search)

A complete solver that uses tree-centric backtracking with constraint
propagation and the MRV heuristic to guarantee a solution for any
valid Tents puzzle.
"""

import copy
from tents import TentsGame, TREE, TENT, GRASS, EMPTY
from smart_bot import SmartBot
from game_logger import GameLogger


class BackBot:
    def __init__(self, game: TentsGame):
        self.game = game
        self.size = game.size
        self.name = "BackBot (Backtracking)"
        self._solution = None  # Cached solved board
        self.focus_tree = None  # (r, c) of tree the bot is currently working on
        self.logger = GameLogger(self.size)

    def get_best_move(self):
        """Determine the next best move using hybrid greedy + backtracking.

        Phase A: Apply SmartBot's O(M) greedy heuristics to reduce the
        board — filling forced TENT and GRASS cells.
        Phase B: Compile a list of unresolved trees (those without an
        adjacent tent after greedy) and pass the shrunk board to
        the backtracking solver.

        Results are cached; subsequent calls diff the cached solution
        against the live player_grid.

        Returns (r, c, move_type, cells_scanned) or None.
        """
        cells_scanned = 0

        # Solve once and cache
        if self._solution is None:
            board = copy.deepcopy(self.game.player_grid)

            # --- Phase A: Greedy Pre-processing ---
            greedy_game = TentsGame(size=self.size)
            greedy_game.player_grid = board
            greedy_game.solution_grid = self.game.solution_grid
            greedy_game.trees = list(self.game.trees)
            greedy_game.row_constraints = list(self.game.row_constraints)
            greedy_game.col_constraints = list(self.game.col_constraints)

            greedy_bot = SmartBot(greedy_game)
            greedy_moves = greedy_bot.solve_iteratively()
            self.logger.log_event(
                f"[GREEDY] Pre-processing applied {greedy_moves} forced moves."
            )

            # --- Phase B: Identify unresolved trees ---
            remaining_trees = []
            for tr, tc in self.game.trees:
                satisfied = False
                for nr, nc in self.game._get_orthogonal_neighbors(tr, tc):
                    if board[nr][nc] == TENT:
                        satisfied = True
                        break
                if not satisfied:
                    remaining_trees.append((tr, tc))

            self.logger.log_event(
                f"[BACKTRACK] {len(remaining_trees)} trees unresolved "
                f"(of {len(self.game.trees)} total). Starting backtracking."
            )

            # Build remaining capacities from the greedy-processed board
            row_remaining = list(self.game.row_constraints)
            col_remaining = list(self.game.col_constraints)
            for r in range(self.size):
                for c in range(self.size):
                    if board[r][c] == TENT:
                        row_remaining[r] -= 1
                        col_remaining[c] -= 1

            if not remaining_trees:
                # Greedy solved everything — verify constraints
                if (all(v == 0 for v in row_remaining)
                        and all(v == 0 for v in col_remaining)):
                    self._solution = board
                else:
                    return None
            elif self._solve_recursive(board, remaining_trees, 0,
                                       row_remaining, col_remaining):
                self._solution = board
            else:
                return None

        # Priority 1: return the first pending TENT placement
        for r in range(self.size):
            for c in range(self.size):
                cells_scanned += 1
                if (self.game.player_grid[r][c] == EMPTY
                        and self._solution[r][c] == TENT):
                    self.focus_tree = self._find_paired_tree(r, c)
                    return (r, c, TENT, cells_scanned)

        # Priority 2: fill remaining EMPTY cells as GRASS
        for r in range(self.size):
            for c in range(self.size):
                cells_scanned += 1
                if self.game.player_grid[r][c] == EMPTY:
                    self.focus_tree = None
                    return (r, c, GRASS, cells_scanned)

        self.focus_tree = None
        return None

    # ------------------------------------------------------------------
    # Core backtracking with MRV + forward checking (Steps 3–7, 11)
    # ------------------------------------------------------------------

    def _solve_recursive(self, board_state, remaining_trees, depth,
                         row_remaining, col_remaining):
        """Core recursive backtracking with MRV heuristic.

        Args:
            board_state: The current game grid being mutated in-place.
            remaining_trees: List of (r, c) trees not yet assigned.
            depth: Current recursion depth (for logging).
            row_remaining: Mutable list — how many tents each row still needs.
            col_remaining: Mutable list — how many tents each col still needs.

        Returns:
            True if a valid complete assignment was found, False otherwise.
        """
        # Base Case: no remaining trees — verify capacities.
        if not remaining_trees:
            valid = (all(v == 0 for v in row_remaining)
                     and all(v == 0 for v in col_remaining))
            if valid:
                self.logger.log_event("[SOLVED] All trees assigned successfully!")
            return valid

        # MRV: compute domain sizes and pick the most constrained tree.
        best_tree = None
        best_domain = 5  # larger than max possible (4)
        for tree in remaining_trees:
            ds = self._get_domain_size(tree, board_state,
                                       row_remaining, col_remaining)
            # Domain 0 → immediate dead end
            if ds == 0:
                self.logger.log_event(
                    f"[DEAD END] Depth={depth} | Tree({tree[0]},{tree[1]}) "
                    f"has domain=0. Backtracking."
                )
                return False
            if ds < best_domain:
                best_domain = ds
                best_tree = tree

        tree_r, tree_c = best_tree
        next_remaining = [t for t in remaining_trees if t != best_tree]

        self.logger.log_event(
            f"[MRV] Depth={depth} | Selected Tree({tree_r},{tree_c}) "
            f"(domain={best_domain})."
        )

        # Branch on the MRV tree's valid neighbours.
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

            # Recurse with remaining trees
            if self._solve_recursive(
                board_state, next_remaining, depth + 1,
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

    def _find_paired_tree(self, tent_r, tent_c):
        """Return the (r, c) of the tree orthogonally adjacent to a tent."""
        for tr, tc in self.game.trees:
            for nr, nc in self.game._get_orthogonal_neighbors(tr, tc):
                if nr == tent_r and nc == tent_c:
                    return (tr, tc)
        return None

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
