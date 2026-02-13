import random
import copy

# Constants representing the grid state
EMPTY = 0
TREE = 1
TENT = 2
GRASS = 3 # Optional, for user marking

class TentsGame:
    def __init__(self, size=8):
        self.size = size
        # internal representation of the solution
        self.solution_grid = [[EMPTY for _ in range(size)] for _ in range(size)]
        # representation of the player's view (trees and user moves)
        self.player_grid = [[EMPTY for _ in range(size)] for _ in range(size)]
        self.row_constraints = [0] * size
        self.col_constraints = [0] * size
        self.trees = [] # List of (r, c) tuples

    def generate_level(self, num_tents):
        """
        Generates a solvable level with the specified number of tents.
        Returns the initial visible board (only trees).
        """
        # Reset grids
        self.solution_grid = [[EMPTY for _ in range(self.size)] for _ in range(self.size)]
        self.trees = []
        
        tents_placed = 0
        attempts = 0
        max_attempts = 1000 # Safety break
        
        while tents_placed < num_tents and attempts < max_attempts:
            attempts += 1
            r = random.randint(0, self.size - 1)
            c = random.randint(0, self.size - 1)
            
            # Check if we can place a tent here
            if not self._can_place_tent_conceptually(r, c):
                continue
                
            # Tent placement is valid regarding other tents. 
            # Now we need to place a tree adjacent to it.
            neighbors = self._get_orthogonal_neighbors(r, c)
            random.shuffle(neighbors)
            
            tree_placed = False
            for nr, nc in neighbors:
                if self.solution_grid[nr][nc] == EMPTY:
                    # Place pair
                    self.solution_grid[r][c] = TENT
                    self.solution_grid[nr][nc] = TREE
                    self.trees.append((nr, nc))
                    tree_placed = True
                    tents_placed += 1
                    break
            
            if not tree_placed:
                # Could not place a tree for this tent, so this tent spot is invalid for now
                continue

        # Calculate constraints
        self._calculate_constraints()
        
        # Prepare player grid (Trees only)
        self.player_grid = [[EMPTY for _ in range(self.size)] for _ in range(self.size)]
        for r, c in self.trees:
            self.player_grid[r][c] = TREE
            
        return self.player_grid

    def _can_place_tent_conceptually(self, r, c):
        """
        Checks if a tent can be placed at (r, c) during GENERATION.
        Rules:
        1. Spot must be empty.
        2. No other tents in 8-neighbor radius.
        """
        if self.solution_grid[r][c] != EMPTY:
            return False
            
        # Check 8 neighbors for existing TENTs
        r_min = max(0, r - 1)
        r_max = min(self.size, r + 2)
        c_min = max(0, c - 1)
        c_max = min(self.size, c + 2)
        
        for i in range(r_min, r_max):
            for j in range(c_min, c_max):
                if self.solution_grid[i][j] == TENT:
                    return False
        return True

    def _get_orthogonal_neighbors(self, r, c):
        """Returns list of valid (r, c) tuples for N, S, E, W neighbors."""
        neighbors = []
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.size and 0 <= nc < self.size:
                neighbors.append((nr, nc))
        return neighbors

    def _calculate_constraints(self):
        self.row_constraints = [0] * self.size
        self.col_constraints = [0] * self.size
        
        for r in range(self.size):
            for c in range(self.size):
                if self.solution_grid[r][c] == TENT:
                    self.row_constraints[r] += 1
                    self.col_constraints[c] += 1

    def is_move_legal(self, r, c, move_type):
        """
        Validates a move.
        row, col: coordinates
        move_type: TENT or GRASS (or EMPTY to clear)
        
        Returns: True if move is 'locally' legal (respects no-touching and counts).
        Note: This does not verify global solvability, just immediate rule violations.
        """
        if not (0 <= r < self.size and 0 <= c < self.size):
            return False
            
        # Trees cannot be moved or overwritten usually, but assuming we check emptiness first
        if self.player_grid[r][c] == TREE:
            return False # Can't overwrite a tree
            
        if move_type == TENT:
            # 1. Check No-Touching Rule against other TENTS in player_grid
            # Note: We check against player_grid which reflects current state
            r_min = max(0, r - 1)
            r_max = min(self.size, r + 2)
            c_min = max(0, c - 1)
            c_max = min(self.size, c + 2)
            
            for i in range(r_min, r_max):
                for j in range(c_min, c_max):
                    if i == r and j == c: continue # Skip self
                    if self.player_grid[i][j] == TENT:
                        return False # Adjacency violation
            
            # 2. Check Row/Col Limits
            # We need to count current tents in this row/col + 1
            current_row_tents = sum(1 for x in self.player_grid[r] if x == TENT)
            if current_row_tents + 1 > self.row_constraints[r]:
                return False
                
            current_col_tents = sum(1 for i in range(self.size) if self.player_grid[i][c] == TENT)
            if current_col_tents + 1 > self.col_constraints[c]:
                return False
        
        return True

    def make_move(self, r, c, move_type):
        """Attempts to apply a move if legal. Returns True if successful."""
        if self.is_move_legal(r, c, move_type):
            self.player_grid[r][c] = move_type
            return True
        return False


    def print_board(self, grid_type='player'):
        """Helper to print board to console."""
        grid = self.player_grid if grid_type == 'player' else self.solution_grid
        
        # Print column constraints
        print("   " + " ".join(str(x) for x in self.col_constraints))
        print("  " + "-" * (self.size * 2))
        
        for r in range(self.size):
            row_str = f"{self.row_constraints[r]}| "
            for c in range(self.size):
                val = grid[r][c]
                char = '.'
                if val == TREE: char = 'T'
                elif val == TENT: char = 'A'
                elif val == GRASS: char = '_'
                row_str += char + " "
            print(row_str)

    def check_victory(self):
        """
        Checks if the current player_grid is a valid winning state.
        For Phase 1, we simply check against the generated solution_grid
        to ensure all tents are found.
        Returns: True if correct, False otherwise.
        """
        # 1. Compare Tents
        for r in range(self.size):
            for c in range(self.size):
                solution_is_tent = (self.solution_grid[r][c] == TENT)
                player_is_tent = (self.player_grid[r][c] == TENT)
                
                if solution_is_tent != player_is_tent:
                    return False
        return True

    def clone_for_race(self):
        """
        Creates a new TentsGame instance with the exact same solution and constraints,
        but a fresh player_grid (reset to initial state).
        Used for the Bot in Versus Mode.
        """
        new_game = TentsGame(self.size)
        
        # Copy solution and constraints
        new_game.solution_grid = copy.deepcopy(self.solution_grid)
        new_game.row_constraints = self.row_constraints[:]
        new_game.col_constraints = self.col_constraints[:]
        new_game.trees = self.trees[:]
        
        # Setup player grid (Trees only)
        new_game.player_grid = [[EMPTY for _ in range(self.size)] for _ in range(self.size)]
        for r, c in self.trees:
            new_game.player_grid[r][c] = TREE
            
        return new_game

