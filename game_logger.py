"""
game_logger.py - Phase 3 Game Logger

Handles all file I/O for BackBot game traces.  Writes timestamped
.log files into the logs/ directory.  back_bot.py imports GameLogger
and calls log_event / log_board — no logging code lives in the bot.
"""

import logging
import os
from datetime import datetime

from tents import EMPTY, TREE, TENT, GRASS

# Map cell values to single-character symbols for ASCII board rendering
_SYMBOL = {EMPTY: '.', TREE: 'T', TENT: 'O', GRASS: 'G'}


class GameLogger:
    def __init__(self, board_size: int):
        self.board_size = board_size
        self._setup_logger()

    def _setup_logger(self):
        """Create a timestamped log file inside logs/."""
        os.makedirs("logs", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"logs/backbot_game_{timestamp}.log"

        self.logger = logging.getLogger(f"BackBot_{timestamp}")
        self.logger.setLevel(logging.DEBUG)

        # Prevent duplicate handlers if re-instantiated in same process
        if not self.logger.handlers:
            fh = logging.FileHandler(log_filename)
            fh.setFormatter(
                logging.Formatter(
                    "%(asctime)s | %(message)s", datefmt="%H:%M:%S"
                )
            )
            self.logger.addHandler(fh)

        self.logger.info(
            f"[GAME START] Board={self.board_size}x{self.board_size}"
        )

    def log_event(self, msg: str):
        """Log a single-line event message."""
        self.logger.info(msg)

    def log_board(self, board, row_constraints, reason: str):
        """Render the full ASCII board grid into the log file.

        Args:
            board: 2-D list (size x size) of cell values.
            row_constraints: list of per-row tent targets.
            reason: human-readable label for why the snapshot was taken.
        """
        size = self.board_size
        self.logger.info(f"--- Board After: {reason} ---")

        # Column header
        col_header = "     " + "  ".join(f"C{c}" for c in range(size))
        self.logger.info(col_header)

        # Each row with its constraint
        for r in range(size):
            row_str = "  ".join(
                _SYMBOL.get(board[r][c], '?') for c in range(size)
            )
            target = row_constraints[r]
            self.logger.info(f"  R{r}: {row_str}   (need={target})")

        self.logger.info("")
