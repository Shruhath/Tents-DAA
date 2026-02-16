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
