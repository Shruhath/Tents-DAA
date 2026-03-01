from tents import TentsGame, TREE, TENT, EMPTY, GRASS
from greedy_bot import GreedyBot
from smart_bot import SmartBot
from back_bot import BackBot
from solver_utils import (
    solve_line_dp, find_forced_moves,
    build_constraint_graph, find_connected_components,
    solve_with_dnc,
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


def test_split_board_dnc():
    """Step 13 – Full split-board scenario using solve_with_dnc.

    5x5 board with a GRASS wall down column 2, creating two independent
    regions.  Row constraints [0, 1, 0, 1, 0] force rows 0/2/4 to all-GRASS.
    Column constraints [1, 0, 0, 0, 1] force cols 1/3 EMPTY cells to GRASS.

    Layout (initial):
        . . G . .       row constraint 0
        . . G . .       row constraint 1
        . . G . .       row constraint 0
        . . G . .       row constraint 1
        . . G . .       row constraint 0
       c0 c1 c2 c3 c4
       col constraints: 1  0  0  0  1

    After solve_with_dnc, at minimum:
      - All cells in rows 0, 2, 4 should be GRASS.
      - All cells in col 1 and col 3 (rows 1, 3) should be GRASS.
    """
    print("\nTesting Split Board D&C (5x5, GRASS wall at col 2)...")

    game = TentsGame(size=5)

    # Build player grid: col 2 = GRASS, rest EMPTY
    for r in range(5):
        for c in range(5):
            game.player_grid[r][c] = GRASS if c == 2 else EMPTY

    game.row_constraints = [0, 1, 0, 1, 0]
    game.col_constraints = [1, 0, 0, 0, 1]

    # Count EMPTY cells before
    empty_before = sum(
        1 for r in range(5) for c in range(5)
        if game.player_grid[r][c] == EMPTY
    )

    progress = solve_with_dnc(game)

    # Count EMPTY cells after
    empty_after = sum(
        1 for r in range(5) for c in range(5)
        if game.player_grid[r][c] == EMPTY
    )

    assert progress, "solve_with_dnc should have made progress"
    assert empty_after < empty_before, (
        f"Expected fewer EMPTY cells after solving. Before={empty_before}, After={empty_after}"
    )

    # Rows with constraint 0 should be entirely GRASS (no EMPTY left)
    for r in (0, 2, 4):
        for c in range(5):
            assert game.player_grid[r][c] != EMPTY, (
                f"Cell ({r},{c}) should not be EMPTY (row constraint is 0)"
            )

    # Cols 1 and 3 have constraint 0 → remaining EMPTY cells should be GRASS
    for c in (1, 3):
        for r in range(5):
            assert game.player_grid[r][c] != EMPTY, (
                f"Cell ({r},{c}) should not be EMPTY (col constraint is 0)"
            )

    print(f"  EMPTY cells: {empty_before} -> {empty_after}")
    print("test_split_board_dnc PASSED!")


def test_smart_vs_greedy():
    """Step 19 – Benchmark: SmartBot should solve >= what GreedyBot solves.

    Generates 5 puzzles with a fixed seed.  For each, both bots get an
    identical clone and solve iteratively.  SmartBot must fill at least as
    many cells as GreedyBot on every puzzle.
    """
    import random
    print("\nTesting Smart vs Greedy (5 seeded puzzles)...")

    seed = 42
    num_puzzles = 5
    smart_wins = 0
    ties = 0

    for i in range(num_puzzles):
        random.seed(seed + i)
        game = TentsGame(size=8)
        game.generate_level(10)

        # Clone for each bot
        greedy_game = game.clone_for_race()
        smart_game = game.clone_for_race()

        # --- Greedy ---
        greedy_bot = GreedyBot(greedy_game)
        greedy_moves = 0
        while True:
            move = greedy_bot.get_best_move()
            if not move:
                break
            r, c, mt, _ = move
            greedy_game.player_grid[r][c] = mt
            greedy_moves += 1

        greedy_empty = sum(
            1 for r in range(8) for c in range(8)
            if greedy_game.player_grid[r][c] == EMPTY
        )

        # --- Smart ---
        smart_bot = SmartBot(smart_game)
        smart_moves = smart_bot.solve_iteratively()

        smart_empty = sum(
            1 for r in range(8) for c in range(8)
            if smart_game.player_grid[r][c] == EMPTY
        )

        print(f"  Puzzle {i+1}: Greedy={greedy_moves} moves ({greedy_empty} empty), "
              f"Smart={smart_moves} moves ({smart_empty} empty)")

        assert smart_empty <= greedy_empty, (
            f"Puzzle {i+1}: SmartBot left MORE empty cells ({smart_empty}) "
            f"than GreedyBot ({greedy_empty})!"
        )

        if smart_empty < greedy_empty:
            smart_wins += 1
        else:
            ties += 1

    print(f"  Summary: Smart wins={smart_wins}, Ties={ties}")
    print("test_smart_vs_greedy PASSED!")


def test_backbot_empty_board():
    """Step 2 (Phase 3) – BackBot should solve a trivial 3x3 puzzle.

    Layout:
        . T .    row constraint 1
        . . .    row constraint 0
        . . .    row constraint 0
       c0 c1 c2
       col constraints: 1  0  0

    Only valid solution: Tent at (0, 0).
    The test currently fails (TDD red) because BackBot is a stub.
    """
    print("\nTesting BackBot Empty Board (3x3, 1 tree)...")

    game = TentsGame(size=3)
    game.player_grid = [
        [EMPTY, TREE, EMPTY],
        [EMPTY, EMPTY, EMPTY],
        [EMPTY, EMPTY, EMPTY],
    ]
    game.trees = [(0, 1)]
    game.row_constraints = [1, 0, 0]
    game.col_constraints = [1, 0, 0]

    bot = BackBot(game)
    move = bot.get_best_move()

    # BackBot must return a valid move
    assert move is not None, "BackBot should return a move for a trivial puzzle"
    r, c, mt, scanned = move
    assert mt == TENT, f"Move type should be TENT, got {mt}"
    assert game.is_move_legal(r, c, TENT), (
        f"Move ({r},{c}) should be legal"
    )
    # The only correct tent placement is (0,0)
    assert (r, c) == (0, 0), (
        f"Expected tent at (0,0), got ({r},{c})"
    )

    print("test_backbot_empty_board PASSED!")


def test_backbot_constraints():
    """Step 5 (Phase 3) – BackBot must reject impossible puzzles.

    Scenario A – Row capacity violation:
        . T .    row constraint 0
        . . .    row constraint 0
        . . .    row constraint 0
       col constraints: 0  0  0

    Tree at (0,1) needs a tent, but every row and column
    constraint is 0.  No tent can be legally placed.

    Scenario B – Adjacency impossibility:
        T T .    row constraint 0
        . . .    row constraint 2
        . . .    row constraint 0
       col constraints: 1  1  0

    Trees at (0,0) and (0,1).  Row 0 = 0 forces both tents
    into row 1: (1,0) and (1,1).  Those cells are horizontally
    adjacent, violating the no-touching rule.  No solution exists.
    """
    print("\nTesting BackBot Constraints (impossible puzzles)...")

    # --- Scenario A: Row/Col capacity makes placement impossible ---
    game_a = TentsGame(size=3)
    game_a.player_grid = [
        [EMPTY, TREE, EMPTY],
        [EMPTY, EMPTY, EMPTY],
        [EMPTY, EMPTY, EMPTY],
    ]
    game_a.trees = [(0, 1)]
    game_a.row_constraints = [0, 0, 0]
    game_a.col_constraints = [0, 0, 0]

    bot_a = BackBot(game_a)
    assert bot_a.get_best_move() is None, (
        "Scenario A: BackBot should return None when all constraints are 0"
    )
    print("  Scenario A (capacity violation) PASSED")

    # --- Scenario B: Adjacency makes placement impossible ---
    game_b = TentsGame(size=3)
    game_b.player_grid = [
        [TREE, TREE, EMPTY],
        [EMPTY, EMPTY, EMPTY],
        [EMPTY, EMPTY, EMPTY],
    ]
    game_b.trees = [(0, 0), (0, 1)]
    game_b.row_constraints = [0, 2, 0]
    game_b.col_constraints = [1, 1, 0]

    bot_b = BackBot(game_b)
    assert bot_b.get_best_move() is None, (
        "Scenario B: BackBot should return None when adjacency "
        "prevents a valid assignment"
    )
    print("  Scenario B (adjacency impossibility) PASSED")

    print("test_backbot_constraints PASSED!")


def test_backbot_performance():
    """Step 9 (Phase 3) – BackBot must solve a 10x10 puzzle under 2 seconds.

    Generates a seeded 10x10 puzzle (15 tents) and runs BackBot on it.
    Asserts the solver finishes within 2.0 seconds and actually finds
    a valid move.  Without MRV, this test may time out.
    """
    import random
    import time

    print("\nTesting BackBot Performance (10x10, 15 tents)...")

    random.seed(123)
    game = TentsGame(size=10)
    game.generate_level(15)

    bot = BackBot(game)

    start = time.time()
    move = bot.get_best_move()
    elapsed = time.time() - start

    print(f"  Solved in {elapsed:.3f}s")

    assert move is not None, "BackBot should find a move for a valid 10x10 puzzle"
    r, c, mt, _ = move
    assert mt == TENT, f"First move should be TENT, got {mt}"

    assert elapsed < 2.0, (
        f"BackBot took {elapsed:.3f}s on 10x10 — exceeds 2.0s limit"
    )

    print("test_backbot_performance PASSED!")


if __name__ == "__main__":
    g = test_generation()
    test_validator(g)
    test_dp_simple_row()
    test_dp_zero_constraint()
    test_dp_impossible_row()
    test_connected_components()
    test_split_board_dnc()
    test_smart_vs_greedy()
    test_backbot_empty_board()
    test_backbot_constraints()
    test_backbot_performance()
