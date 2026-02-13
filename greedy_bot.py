from tents import TentsGame, TREE, TENT, GRASS, EMPTY

class GreedyBot:
    def __init__(self, game: TentsGame):
        self.game = game
        self.size = game.size

    def get_best_move(self):
        """
        Determines the next best move using greedy strategies.
        Returns: (r, c, move_type, cells_scanned) or None
        Priority:
        1. Adjacency Exclusion (Tents -> Grass)
        2. Row/Col Full Check (Max Tents reached -> Grass)
        3. Forced Tent Check (Must place Tents to meet target -> Tent)
        4. Isolated Tree Check (Tree has only one free neighbor -> Tent)
        """
        cells_scanned = 0
        
        # 1. Adjacency Exclusion
        # If a Tent exists, all neighbors must be Grass (if currently Empty/unknown)
        # Note: In our game, Grass is explicit. Empty means unknown.
        for r in range(self.size):
            for c in range(self.size):
                cells_scanned += 1
                if self.game.player_grid[r][c] == TENT:
                    # Check 8 neighbors
                    r_min = max(0, r - 1)
                    r_max = min(self.size, r + 2)
                    c_min = max(0, c - 1)
                    c_max = min(self.size, c + 2)
                    
                    for nr in range(r_min, r_max):
                        for nc in range(c_min, c_max):
                            if nr == r and nc == c: continue
                            cells_scanned += 1 # counting neighbor check
                            if self.game.player_grid[nr][nc] == EMPTY:
                                return (nr, nc, GRASS, cells_scanned)

        # 2. Row/Col Full Check (Mark remaining as Grass)
        # Rows
        for r in range(self.size):
            cells_scanned += 1 # Check row metadata
            current_tents = self.game.player_grid[r].count(TENT)
            if current_tents == self.game.row_constraints[r]:
                # Any empty cell in this row must be Grass
                for c in range(self.size):
                    cells_scanned += 1
                    if self.game.player_grid[r][c] == EMPTY:
                        return (r, c, GRASS, cells_scanned)
        
        # Cols
        for c in range(self.size):
            cells_scanned += 1
            current_tents = sum(1 for r in range(self.size) if self.game.player_grid[r][c] == TENT)
            if current_tents == self.game.col_constraints[c]:
                for r in range(self.size):
                    cells_scanned += 1
                    if self.game.player_grid[r][c] == EMPTY:
                        return (r, c, GRASS, cells_scanned)

        # 3. Forced Tent Check (Must fill remaining to meet target)
        # Rows
        for r in range(self.size):
            cells_scanned += 1
            tents = 0
            empties = []
            for c in range(self.size):
                cells_scanned += 1
                val = self.game.player_grid[r][c]
                if val == TENT: tents += 1
                elif val == EMPTY: empties.append(c)
            
            target = self.game.row_constraints[r]
            # Rule: If Tents + Empty == Target, all Empties MUST be Tents
            if tents + len(empties) == target and len(empties) > 0:
                return (r, empties[0], TENT, cells_scanned)

        # Cols
        for c in range(self.size):
            cells_scanned += 1
            tents = 0
            empties = []
            for r in range(self.size):
                cells_scanned += 1
                val = self.game.player_grid[r][c]
                if val == TENT: tents += 1
                elif val == EMPTY: empties.append(r)
            
            target = self.game.col_constraints[c]
            if tents + len(empties) == target and len(empties) > 0:
                return (empties[0], c, TENT, cells_scanned)

        # 4. Isolated Tree Check (Tree has exactly one empty spot around it)
        # We need to know which trees already have tents.
        # This is tricky because we don't strictly track Tree->Tent links in player_grid
        # But we can look for trees that are not adjacent to ANY tent yet.
        for r in range(self.size):
            for c in range(self.size):
                cells_scanned += 1
                if self.game.player_grid[r][c] == TREE:
                    # Check if it already has a tent neighbor
                    neighbors = self.game._get_orthogonal_neighbors(r, c) # Using internal helper from game
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
                    
                    if not has_tent:
                        # If only 1 empty neighbor, it MUST be the tent
                        if len(empty_neighbors) == 1:
                            return (empty_neighbors[0][0], empty_neighbors[0][1], TENT, cells_scanned)

        # 5. "No-Man's Land" Heuristic (Empty cell has no adjacent Tree -> Grass)
        # Tents MUST be adjacent to a tree. If a spot is not near a tree, it's useless.
        for r in range(self.size):
            for c in range(self.size):
                cells_scanned += 1
                if self.game.player_grid[r][c] == EMPTY:
                    # Check neighbors for TREE
                    neighbors = self.game._get_orthogonal_neighbors(r, c)
                    has_tree_neighbor = False
                    for nr, nc in neighbors:
                         cells_scanned += 1
                         if self.game.player_grid[nr][nc] == TREE:
                                has_tree_neighbor = True
                                break
                    
                    if not has_tree_neighbor:
                        return (r, c, GRASS, cells_scanned)

        # 6. Locked Candidates Rule (Advanced)
        # If N trees are "locked" into a specific Row/Col (meaning all their valid spots are in that line),
        # AND that Row/Col needs exactly N more tents (or existing_tents + N == target),
        # THEN all *other* empty cells in that Row/Col (not utilized by these trees) must be GRASS.
        
        # Check ROWS
        for r in range(self.size):
            locked_trees = [] 
            # Find trees locked to this row
            for tree_idx, (tr, tc) in enumerate(self.game.trees):
                # Is this tree satisfied?
                neighbors = self.game._get_orthogonal_neighbors(tr, tc)
                has_tent = False
                valid_spots = []
                for nr, nc in neighbors:
                    if self.game.player_grid[nr][nc] == TENT:
                        has_tent = True
                        break
                    if self.game.player_grid[nr][nc] == EMPTY:
                        valid_spots.append((nr, nc))
                
                if has_tent: continue 
                
                if valid_spots:
                    # Check if all valid spots are in THIS row
                    if all(spot[0] == r for spot in valid_spots):
                        locked_trees.append((tr, tc)) # This tree relies on this row
            
            # Now, check logic
            current_tents = self.game.player_grid[r].count(TENT)
            target = self.game.row_constraints[r]
            
            if current_tents + len(locked_trees) == target:
                # Elimination: Mark non-locked empties as GRASS
                # We need to know which cells are "reserved" by the locked trees
                reserved_cells = set()
                for tr, tc in locked_trees:
                    neighbors = self.game._get_orthogonal_neighbors(tr, tc)
                    for nr, nc in neighbors:
                         if self.game.player_grid[nr][nc] == EMPTY:
                                reserved_cells.add((nr, nc))
                
                # Scan row for empties NOT in reserved
                for c in range(self.size):
                    cells_scanned += 1
                    if self.game.player_grid[r][c] == EMPTY:
                        if (r, c) not in reserved_cells:
                            return (r, c, GRASS, cells_scanned)

        # Check COLS
        for c in range(self.size):
            locked_trees = []
            for tree_idx, (tr, tc) in enumerate(self.game.trees):
                neighbors = self.game._get_orthogonal_neighbors(tr, tc)
                has_tent = False
                valid_spots = []
                for nr, nc in neighbors:
                    if self.game.player_grid[nr][nc] == TENT:
                        has_tent = True
                        break
                    if self.game.player_grid[nr][nc] == EMPTY:
                        valid_spots.append((nr, nc))
                
                if has_tent: continue
                
                if valid_spots:
                    if all(spot[1] == c for spot in valid_spots):
                        locked_trees.append((tr, tc))
            
            # Logic
            current_tents = sum(1 for r in range(self.size) if self.game.player_grid[r][c] == TENT)
            target = self.game.col_constraints[c]
            
            if current_tents + len(locked_trees) == target:
                 reserved_cells = set()
                 for tr, tc in locked_trees:
                    neighbors = self.game._get_orthogonal_neighbors(tr, tc)
                    for nr, nc in neighbors:
                         if self.game.player_grid[nr][nc] == EMPTY:
                                reserved_cells.add((nr, nc))
                                
                 for r in range(self.size):
                    cells_scanned += 1
                    if self.game.player_grid[r][c] == EMPTY:
                        if (r, c) not in reserved_cells:
                            return (r, c, GRASS, cells_scanned)

        return None

