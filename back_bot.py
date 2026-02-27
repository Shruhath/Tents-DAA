"""
back_bot.py - Phase 3 BackBot (Backtracking / State-Space Search)

A complete solver that uses tree-centric backtracking with constraint
propagation and the MRV heuristic to guarantee a solution for any
valid Tents puzzle.
"""

from tents import TentsGame, TREE, TENT, GRASS, EMPTY


class BackBot:
    def __init__(self, game: TentsGame):
        self.game = game
        self.size = game.size
        self.name = "BackBot (Backtracking)"

    def get_best_move(self):
        """Determine the next best move using backtracking search.

        Returns (r, c, move_type, cells_scanned) or None.
        """
        # TODO (Step 3+): Run greedy pre-processing, then backtracking.
        return None

    def _solve_recursive(self, board_state, current_tree_index):
        """Core recursive backtracking function.

        Args:
            board_state: The current game grid being mutated in-place.
            current_tree_index: Index into self.game.trees for the next
                tree to assign a tent to.

        Returns:
            True if a valid complete assignment was found, False otherwise.
        """
        # TODO (Step 3): Implement naive 4-way branching.
        return False
