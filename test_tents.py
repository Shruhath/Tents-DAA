from tents import TentsGame, TREE, TENT, EMPTY, GRASS
from solver_utils import solve_line_dp, find_forced_moves

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


if __name__ == "__main__":
    g = test_generation()
    test_validator(g)
    test_dp_simple_row()
