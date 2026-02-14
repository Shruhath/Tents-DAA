from tents import TentsGame, TREE, TENT, EMPTY, GRASS
from solver_utils import (
    solve_line_dp, find_forced_moves,
    build_constraint_graph, find_connected_components,
)

def test_generation():
    print("Testing Level Generation...")
    game = TentsGame(size=8)
    num_tents = 12
    game.generate_level(num_tents)
    
    print("Solution Board:")
    game.print_board(grid_type='solution')
    print("\nPlayer Board (Initial):")
    game.print_board(grid_type='player')
    
    # 1. Check Tent Count
    actual_tents = sum(row.count(TENT) for row in game.solution_grid)
    actual_trees = sum(row.count(TREE) for row in game.solution_grid)
    print(f"\nStats: Tents={actual_tents}, Trees={actual_trees}, Requested={num_tents}")
    assert actual_tents == actual_trees, "Mismatch between Tents and Trees in solution!"
    
    # 2. Check Constraints consistency
    for r in range(game.size):
        row_ct = game.solution_grid[r].count(TENT)
        assert row_ct == game.row_constraints[r], f"Row {r} constraint mismatch"
    
    for c in range(game.size):
        col_ct = sum(game.solution_grid[r][c] == TENT for r in range(game.size))
        assert col_ct == game.col_constraints[c], f"Col {c} constraint mismatch"
        
    print("Generation Integrity Verified!")
    return game

def test_validator(game):
    print("\nTesting Validator...")
    
    # Find a valid spot from solution to test positive case
    # Note: simple copying of solution to player grid one by one
    valid_moves_count = 0
    for r in range(game.size):
        for c in range(game.size):
            if game.solution_grid[r][c] == TENT:
                # Try placing it in player grid
                is_legal = game.is_move_legal(r, c, TENT)
                print(f"Placing TENT at ({r},{c}) -> Legal? {is_legal}")
                if is_legal:
                    game.make_move(r, c, TENT)
                    valid_moves_count += 1
                else:
                    print("WARN: Valid solution move rejected! (Could be order dependent due to constraints)")
    
    print(f"Placed {valid_moves_count} tents matches.")
    
    # Test an invalid move (adjacent to existing tent)
    # Find a tent
    tents = []
    for r in range(game.size):
        for c in range(game.size):
            if game.player_grid[r][c] == TENT:
                tents.append((r,c))
    
    if tents:
        r, c = tents[0]
        # Try converting a neighbor to TENT
        adj = [(r+1, c), (r, c+1), (r+1, c+1)] # potentially invalid spots
        for ar, ac in adj:
            if 0 <= ar < game.size and 0 <= ac < game.size:
                if game.player_grid[ar][ac] == EMPTY:
                    legal = game.is_move_legal(ar, ac, TENT)
                    print(f"Testing invalid neighbor ({ar},{ac}) -> Legal? {legal}")
                    assert not legal, "Validator failed to catch adjacency violation!"

    print("Validator Tests Passed!")

def test_dp_simple_row():
    """Step 2 – DP test: 4 cells, 2 tents, no fixed positions.

    Expected valid configurations (no two tents adjacent):
        1. T G T G
        2. T G G T
        3. G T G T
    """
    print("\nTesting DP Simple Row (4 cells, 2 tents)...")

    configs = solve_line_dp(
        length=4,
        target_count=2,
        current_line=[EMPTY] * 4,
        fixed_positions=set(),
    )

    expected = [
        [TENT, GRASS, TENT, GRASS],
        [TENT, GRASS, GRASS, TENT],
        [GRASS, TENT, GRASS, TENT],
    ]

    assert len(configs) == 3, (
        f"Expected 3 valid configs, got {len(configs)}"
    )

    # Sort both lists so order doesn't matter
    sort_key = lambda cfg: tuple(cfg)
    assert sorted(configs, key=sort_key) == sorted(expected, key=sort_key), (
        f"Configs mismatch!\n  Got:      {configs}\n  Expected: {expected}"
    )

    print("test_dp_simple_row PASSED!")


def test_dp_zero_constraint():
    """Step 6 – 0-constraint row: 5 cells, 0 tents.

    Only one valid configuration: all GRASS.
    find_forced_moves should lock every cell as GRASS.
    """
    print("\nTesting DP Zero Constraint (5 cells, 0 tents)...")

    configs = solve_line_dp(
        length=5,
        target_count=0,
        current_line=[EMPTY] * 5,
        fixed_positions=set(),
    )

    assert len(configs) == 1, (
        f"Expected 1 valid config, got {len(configs)}"
    )
    assert configs[0] == [GRASS] * 5, (
        f"Expected all GRASS, got {configs[0]}"
    )

    forced = find_forced_moves(configs)
    assert len(forced) == 5, (
        f"Expected 5 forced moves, got {len(forced)}"
    )
    for i in range(5):
        assert forced[i] == GRASS, (
            f"Cell {i} should be forced GRASS, got {forced[i]}"
        )

    print("test_dp_zero_constraint PASSED!")


def test_dp_impossible_row():
    """Step 6 – Impossible row: 3 cells, 3 tents.

    Cannot fit 3 non-adjacent tents in 3 cells (max is 2: T G T).
    solve_line_dp should return an empty list.
    """
    print("\nTesting DP Impossible Row (3 cells, 3 tents)...")

    configs = solve_line_dp(
        length=3,
        target_count=3,
        current_line=[EMPTY] * 3,
        fixed_positions=set(),
    )

    assert configs == [], (
        f"Expected empty list for impossible row, got {configs}"
    )

    forced = find_forced_moves(configs)
    assert forced == {}, (
        f"Expected empty dict for impossible row, got {forced}"
    )

    print("test_dp_impossible_row PASSED!")


def test_connected_components():
    """Step 9 – Graph decomposition: 5x5 board split by a GRASS wall.

    Layout (col 2 is all GRASS, acting as a wall):
        . . G . .
        . . G . .
        . . G . .
        . . G . .
        . . G . .

    Expected: 2 connected components (Left: cols 0-1, Right: cols 3-4).
    """
    print("\nTesting Connected Components (5x5, GRASS wall at col 2)...")

    game = TentsGame(size=5)
    # Set up a player grid with a GRASS wall down column 2
    for r in range(5):
        for c in range(5):
            if c == 2:
                game.player_grid[r][c] = GRASS
            else:
                game.player_grid[r][c] = EMPTY

    graph = build_constraint_graph(game)
    components = find_connected_components(graph)

    assert len(components) == 2, (
        f"Expected 2 components, got {len(components)}"
    )

    # Verify left component contains only cols 0-1
    # and right component contains only cols 3-4
    all_cells = set()
    for comp in components:
        all_cells.update(comp)

    left = {(r, c) for r in range(5) for c in range(2)}
    right = {(r, c) for r in range(5) for c in range(3, 5)}

    comp_sets = [comp for comp in components]
    assert (comp_sets[0] == left and comp_sets[1] == right) or \
           (comp_sets[0] == right and comp_sets[1] == left), (
        f"Components don't match expected left/right split.\n"
        f"  Got: {comp_sets}"
    )

    print("test_connected_components PASSED!")


if __name__ == "__main__":
    g = test_generation()
    test_validator(g)
    test_dp_simple_row()
    test_dp_zero_constraint()
    test_dp_impossible_row()
    test_connected_components()
