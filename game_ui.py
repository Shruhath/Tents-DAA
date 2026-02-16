"""
game_ui.py ΓÇô Pygame frontend for the Tents puzzle game.
Replaces the Tkinter gui.py with a modern, sprite-based interface.

Run:
    pip install pygame
    python game_ui.py
"""

import pygame
import sys
import time
import threading
from tents import TentsGame, TREE, TENT, GRASS, EMPTY
from greedy_bot import GreedyBot
from smart_bot import SmartBot

#  CONSTANTS
SCREEN_W, SCREEN_H = 1280, 720
FPS = 60

BLACK      = (0, 0, 0)
WHITE      = (255, 255, 255)
LGRAY      = (180, 180, 180)
DGRAY      = (50, 50, 50)
GREEN      = (0, 255, 0)
DGREEN     = (34, 139, 34)
RED        = (220, 60, 60)
BLUE       = (70, 130, 220)
BROWN      = (139, 69, 19)
ORANGE     = (255, 165, 0)

# Asset colours
GRASS_C    = (90, 170, 70)
GRASS_D    = (60, 130, 50)
TREE_TRUNK = (110, 75, 35)
TREE_LEAF  = (35, 145, 35)
TREE_LT    = (55, 175, 55)
TENT_C     = (190, 75, 55)
TENT_DOOR  = (130, 60, 30)
CELL_BG    = (240, 240, 235)

# UI colours
BTN_N      = (50, 50, 50)
BTN_H      = (75, 75, 75)
BTN_SEL    = (30, 120, 30)

# Layout
HEADER_H   = 60
FOOTER_H   = 50
LABEL_H    = 28
CON_M      = 30        # constraint-number margin

# Game settings
TENT_COUNTS = {5: 4, 8: 10, 10: 15, 12: 22}
BOT_MS      = 500      # milliseconds between bot moves


#  ASSET MANAGER ΓÇô procedural sprite generation with size-based caching
class AssetManager:
    def __init__(self):
        self._cache: dict[tuple, pygame.Surface] = {}

    def get(self, name: str, size: int) -> pygame.Surface:
        key = (name, size)
        if key not in self._cache:
            self._cache[key] = self._make(name, size)
        return self._cache[key]

    def _make(self, name: str, sz: int) -> pygame.Surface:
        s = pygame.Surface((sz, sz), pygame.SRCALPHA)
        pad = max(2, sz // 10)

        if name == "grass":
            s.fill(GRASS_C)
            for i in range(1, 4):
                y = sz * i // 4
                pygame.draw.line(s, GRASS_D, (pad, y), (sz - pad, y - 1), 1)
            for x in range(sz // 4, sz - sz // 4, max(1, sz // 5)):
                pygame.draw.line(s, GRASS_D,
                                 (x, sz * 3 // 5), (x - 2, sz * 2 // 5), 2)

        elif name == "tree":
            s.fill(CELL_BG)
            tw = max(3, sz // 5)
            th = sz // 3
            tx = (sz - tw) // 2
            ty = sz - th - pad
            pygame.draw.rect(s, TREE_TRUNK, (tx, ty, tw, th))
            tri = [(sz // 2, pad),
                   (pad, sz - th - pad),
                   (sz - pad, sz - th - pad)]
            pygame.draw.polygon(s, TREE_LEAF, tri)
            inner = [(sz // 2, pad + 4),
                     (sz // 3, sz - th - pad - 2),
                     (sz * 2 // 3, sz - th - pad - 2)]
            pygame.draw.polygon(s, TREE_LT, inner)

        elif name == "tent":
            s.fill(CELL_BG)
            tri = [(sz // 2, pad + 1),
                   (pad, sz - pad - 1),
                   (sz - pad, sz - pad - 1)]
            pygame.draw.polygon(s, TENT_C, tri)
            dw = max(2, sz // 6)
            dh = max(3, sz // 4)
            door = [(sz // 2, sz - pad - 1 - dh),
                    (sz // 2 - dw, sz - pad - 1),
                    (sz // 2 + dw, sz - pad - 1)]
            pygame.draw.polygon(s, TENT_DOOR, door)

        elif name == "empty":
            s.fill(CELL_BG)

        return s


#  BUTTON
class Button:
    def __init__(self, rect, text, *, color=BTN_N, hover=BTN_H,
                 text_color=WHITE, font=None, selected=False):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.color = color
        self.hover_color = hover
        self.text_color = text_color
        self.font = font
        self.selected = selected

    def draw(self, screen, font=None):
        f = self.font or font
        hovered = self.rect.collidepoint(pygame.mouse.get_pos())
        if self.selected:
            bg = BTN_SEL
        elif hovered:
            bg = self.hover_color
        else:
            bg = self.color
        pygame.draw.rect(screen, bg, self.rect, border_radius=6)
        pygame.draw.rect(screen, LGRAY, self.rect, 2, border_radius=6)
        if f:
            surf = f.render(self.text, True, self.text_color)
            screen.blit(surf, surf.get_rect(center=self.rect.center))

    def clicked(self, pos):
        return self.rect.collidepoint(pos)


#  SCENE MANAGER
class SceneManager:
    def __init__(self):
        self.scene = None

    def switch(self, scene):
        self.scene = scene

    def handle(self, event):
        if self.scene:
            self.scene.handle_event(event)

    def update(self):
        if self.scene:
            self.scene.update()

    def draw(self, screen):
        if self.scene:
            self.scene.draw(screen)


#  MENU SCENE
class MenuScene:
    def __init__(self, sm: SceneManager, assets: AssetManager):
        self.sm = sm
        self.assets = assets
        self.grid_size = 8

        self.title_font = pygame.font.SysFont("arial", 64, bold=True)
        self.sub_font   = pygame.font.SysFont("arial", 22)
        self.btn_font   = pygame.font.SysFont("arial", 20, bold=True)

        # Grid-size selector buttons
        sizes = [5, 8, 10, 12]
        bw, bh = 80, 42
        total = len(sizes) * bw + (len(sizes) - 1) * 15
        sx = (SCREEN_W - total) // 2
        sy = 310
        self.size_btns = []
        for i, s in enumerate(sizes):
            b = Button((sx + i * (bw + 15), sy, bw, bh),
                       f"{s}x{s}", font=self.btn_font,
                       selected=(s == self.grid_size))
            b._size = s
            self.size_btns.append(b)

        # Mode buttons
        mw, mh = 220, 50
        gap = 20
        total_w = 3 * mw + 2 * gap
        mx = (SCREEN_W - total_w) // 2
        my = 420
        self.practice_btn = Button((mx, my, mw, mh),
                                   "Practice (Solo)", font=self.btn_font)
        self.versus_btn   = Button((mx + mw + gap, my, mw, mh),
                                   "Versus Greedy", font=self.btn_font)
        self.smart_btn    = Button((mx + 2 * (mw + gap), my, mw, mh),
                                   "Versus Smart", font=self.btn_font)

    def handle_event(self, ev):
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            for b in self.size_btns:
                if b.clicked(ev.pos):
                    self.grid_size = b._size
                    for bb in self.size_btns:
                        bb.selected = (bb._size == self.grid_size)
            if self.practice_btn.clicked(ev.pos):
                self.sm.switch(GameScene(self.sm, self.assets,
                                        self.grid_size, "practice"))
            elif self.versus_btn.clicked(ev.pos):
                self.sm.switch(GameScene(self.sm, self.assets,
                                        self.grid_size, "versus"))
            elif self.smart_btn.clicked(ev.pos):
                self.sm.switch(GameScene(self.sm, self.assets,
                                        self.grid_size, "versus_smart"))

    def update(self):
        pass

    def draw(self, screen):
        screen.fill(BLACK)

        # Title with brown outline
        title = "TENTS  GAME"
        cx, cy = SCREEN_W // 2, 160
        for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2),
                       (-2, -2), (2, -2), (-2, 2), (2, 2)]:
            s = self.title_font.render(title, True, BROWN)
            screen.blit(s, s.get_rect(center=(cx + dx, cy + dy)))
        s = self.title_font.render(title, True, GREEN)
        screen.blit(s, s.get_rect(center=(cx, cy)))

        # Subtitles
        sub = self.sub_font.render("Select Grid Size", True, LGRAY)
        screen.blit(sub, sub.get_rect(center=(SCREEN_W // 2, 275)))

        for b in self.size_btns:
            b.draw(screen)

        sub2 = self.sub_font.render("Choose Game Mode", True, LGRAY)
        screen.blit(sub2, sub2.get_rect(center=(SCREEN_W // 2, 395)))

        self.practice_btn.draw(screen)
        self.versus_btn.draw(screen)
        self.smart_btn.draw(screen)

        hint = self.sub_font.render("ESC to quit", True, DGRAY)
        screen.blit(hint, hint.get_rect(center=(SCREEN_W // 2, SCREEN_H - 40)))


#  GAME SCENE
class GameScene:
    def __init__(self, sm: SceneManager, assets: AssetManager,
                 grid_size: int, mode: str):
        self.sm = sm
        self.assets = assets
        self.grid_size = grid_size
        self.mode = mode                     # "practice" | "versus"

        #  game state 
        self.player_game = TentsGame(size=grid_size)
        self.player_game.generate_level(TENT_COUNTS.get(grid_size, 10))

        self.bot_game = None
        self.bot = None
        self.bot_stuck = False
        self.bot_thinking = False
        self.bot_thread = None
        self.bot_move_result = None
        self.bot_last_scanned = 0
        self.last_bot_tick = 0

        if mode == "versus":
            self.bot_game = self.player_game.clone_for_race()
            self.bot = GreedyBot(self.bot_game)

        self.wrong_clicks = 0
        self.start_time = time.time()
        self.game_over = False
        self.winner = None
        self.gave_up = False
        self.elapsed = 0

        #  layout 
        self._calc_layout()

        #  fonts 
        self.heading_font = pygame.font.SysFont("arial", 24, bold=True)
        self.label_font   = pygame.font.SysFont("arial", 18)
        self.btn_font     = pygame.font.SysFont("arial", 18, bold=True)
        csz = max(14, min(22, self.cell_size * 2 // 3))
        self.con_font     = pygame.font.SysFont("arial", csz, bold=True)
        self.overlay_font = pygame.font.SysFont("arial", 48, bold=True)
        self.overlay_sub  = pygame.font.SysFont("arial", 22)

        #  footer buttons 
        bw, bh, gap = 130, 36, 15
        bx = (SCREEN_W - bw * 2 - gap) // 2
        by = SCREEN_H - FOOTER_H + 4
        self.submit_btn = Button((bx, by, bw, bh), "Submit",
                                 font=self.btn_font)
        self.giveup_btn = Button((bx + bw + gap, by, bw, bh), "Give Up",
                                 font=self.btn_font,
                                 color=(100, 40, 40), hover=(140, 60, 60))

        # Overlay buttons (created on game end)
        self.again_btn = None
        self.menu_btn  = None

        #  animations 
        self.flashes = []        # {board, r, c, color, time}
        self.pops    = []        # {board, r, c, time}

        #  hover 
        self.hover_cell = None   # (r, c) on player board

    #  layout 
    def _calc_layout(self):
        n = self.grid_size
        if self.mode == "versus":
            half = SCREEN_W // 2
            aw = half - 70
            ah = SCREEN_H - HEADER_H - LABEL_H - FOOTER_H - 20
            mx = min(aw - CON_M, ah - CON_M)
            self.cell_size = min(mx // n, 60)
            gp = self.cell_size * n
            bw = CON_M + gp
            bh = CON_M + gp
            top = HEADER_H + LABEL_H
            self.p_bx = (half - bw) // 2
            self.p_by = top + (ah - bh) // 2
            self.b_bx = half + (half - bw) // 2
            self.b_by = self.p_by
        else:
            aw = SCREEN_W - 200
            ah = SCREEN_H - HEADER_H - LABEL_H - FOOTER_H - 20
            mx = min(aw - CON_M, ah - CON_M)
            self.cell_size = min(mx // n, 60)
            gp = self.cell_size * n
            bw = CON_M + gp
            bh = CON_M + gp
            top = HEADER_H + LABEL_H
            self.p_bx = (SCREEN_W - bw) // 2
            self.p_by = top + (ah - bh) // 2

    #  grid cell under mouse 
    def _cell_at(self, pos, bx, by):
        mx, my = pos
        gx, gy = bx + CON_M, by + CON_M
        gp = self.cell_size * self.grid_size
        if gx <= mx < gx + gp and gy <= my < gy + gp:
            return ((my - gy) // self.cell_size,
                    (mx - gx) // self.cell_size)
        return None

    #  EVENTS
    def handle_event(self, ev):
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
            self.sm.switch(MenuScene(self.sm, self.assets))
            return

        if ev.type != pygame.MOUSEBUTTONDOWN:
            return

        #  overlay buttons 
        if self.game_over:
            if ev.button == 1:
                if self.again_btn and self.again_btn.clicked(ev.pos):
                    self.sm.switch(GameScene(self.sm, self.assets,
                                            self.grid_size, self.mode))
                elif self.menu_btn and self.menu_btn.clicked(ev.pos):
                    self.sm.switch(MenuScene(self.sm, self.assets))
            return

        #  footer buttons 
        if ev.button == 1:
            if self.submit_btn.clicked(ev.pos):
                self._manual_submit()
                return
            if self.giveup_btn.clicked(ev.pos):
                self._give_up()
                return

        #  board clicks (player only) 
        cell = self._cell_at(ev.pos, self.p_bx, self.p_by)
        if cell:
            r, c = cell
            if ev.button == 1:
                self._left_click(r, c)
            elif ev.button == 3:
                self._right_click(r, c)

    #  player moves 
    def _left_click(self, r, c):
        g = self.player_game
        cur = g.player_grid[r][c]
        if cur == TREE:
            return
        if cur == TENT:
            g.player_grid[r][c] = EMPTY
            return
        # attempt tent placement
        if g.is_move_legal(r, c, TENT):
            g.player_grid[r][c] = TENT
            self.pops.append({"board": "player", "r": r, "c": c,
                              "time": time.time()})
            if g.check_victory():
                self._end_game("YOU")
        else:
            self.wrong_clicks += 1
            self.flashes.append({"board": "player", "r": r, "c": c,
                                 "color": RED, "time": time.time()})

    def _right_click(self, r, c):
        g = self.player_game
        cur = g.player_grid[r][c]
        if cur == TREE:
            return
        g.player_grid[r][c] = EMPTY if cur == GRASS else GRASS

    def _manual_submit(self):
        if self.player_game.check_victory():
            self._end_game("YOU")

    def _give_up(self):
        self.gave_up = True
        g = self.player_game
        for r in range(g.size):
            for c in range(g.size):
                g.player_grid[r][c] = g.solution_grid[r][c]
        self._end_game("NOBODY")

    def _end_game(self, winner):
        self.game_over = True
        self.winner = winner
        self.elapsed = int(time.time() - self.start_time)
        bw, bh = 170, 42
        cx = SCREEN_W // 2
        cy = SCREEN_H // 2 + 55
        self.again_btn = Button((cx - bw - 10, cy, bw, bh),
                                "Play Again", font=self.btn_font)
        self.menu_btn  = Button((cx + 10, cy, bw, bh),
                                "Menu", font=self.btn_font)

    #  UPDATE (called every frame)
    def update(self):
        if self.game_over:
            return

        # Hover
        self.hover_cell = self._cell_at(pygame.mouse.get_pos(),
                                        self.p_bx, self.p_by)

        # Bot moves (threaded)
        if self.mode == "versus" and not self.bot_stuck:
            now = pygame.time.get_ticks()
            if not self.bot_thinking and now - self.last_bot_tick >= BOT_MS:
                self.bot_thinking = True
                self.bot_thread = threading.Thread(
                    target=self._compute_bot, daemon=True)
                self.bot_thread.start()
            if (self.bot_thinking and self.bot_thread
                    and not self.bot_thread.is_alive()):
                self._apply_bot()
                self.bot_thinking = False
                self.last_bot_tick = pygame.time.get_ticks()

        # Expire animations
        now = time.time()
        self.flashes = [f for f in self.flashes if now - f["time"] < 0.35]
        self.pops    = [p for p in self.pops    if now - p["time"] < 0.22]

    def _compute_bot(self):
        self.bot_move_result = self.bot.get_best_move()

    def _apply_bot(self):
        move = self.bot_move_result
        self.bot_move_result = None
        if move:
            r, c, mt, scanned = move
            self.bot_game.player_grid[r][c] = mt
            self.bot_last_scanned = scanned
            self.flashes.append({"board": "bot", "r": r, "c": c,
                                 "color": BLUE, "time": time.time()})
            if self.bot_game.check_victory():
                self._end_game("GREEDY BOT")
        else:
            if self.bot_game.check_victory():
                self._end_game("GREEDY BOT")
            else:
                self.bot_stuck = True

    #  DRAW
    def draw(self, screen):
        screen.fill(BLACK)
        self._draw_header(screen)
        self._draw_board(screen, self.player_game,
                         self.p_bx, self.p_by, is_player=True)
        if self.mode == "versus":
            self._draw_board(screen, self.bot_game,
                             self.b_bx, self.b_by, is_player=False)
            # Divider line
            pygame.draw.line(screen, DGRAY,
                             (SCREEN_W // 2, HEADER_H),
                             (SCREEN_W // 2, SCREEN_H - FOOTER_H), 1)
        self._draw_flashes(screen)
        self._draw_footer(screen)
        if self.game_over:
            self._draw_overlay(screen)

    #  header 
    def _draw_header(self, screen):
        elapsed = int(time.time() - self.start_time) if not self.game_over \
                  else self.elapsed
        t = f"{elapsed // 60}:{elapsed % 60:02d}" if elapsed >= 60 \
            else f"{elapsed}s"
        ts = self.heading_font.render(f"Time: {t}", True, WHITE)
        screen.blit(ts, ts.get_rect(center=(SCREEN_W // 2, 20)))

        # Wrong clicks
        ws = self.label_font.render(
            f"Wrong Clicks: {self.wrong_clicks}", True, LGRAY)
        screen.blit(ws, (20, 12))

        # Bot info (versus only)
        if self.mode == "versus":
            bs = self.label_font.render(
                f"Bot Scanned: {self.bot_last_scanned}", True, LGRAY)
            screen.blit(bs, (SCREEN_W - bs.get_width() - 20, 12))
            if self.bot_stuck:
                st = self.label_font.render("Bot Stuck!", True, ORANGE)
                screen.blit(st, (SCREEN_W - st.get_width() - 20, 34))
            elif self.bot_thinking:
                dots = "." * ((pygame.time.get_ticks() // 300) % 4)
                th = self.label_font.render(f"Thinking{dots}", True, BLUE)
                screen.blit(th, (SCREEN_W - th.get_width() - 20, 34))

        # Board labels (just above each board)
        grid_center_x = self.p_bx + CON_M + self.cell_size * self.grid_size // 2
        yl = self.heading_font.render("YOU", True, GREEN)
        screen.blit(yl, yl.get_rect(center=(grid_center_x, self.p_by - 14)))

        if self.mode == "versus":
            bot_cx = self.b_bx + CON_M + self.cell_size * self.grid_size // 2
            lbl = "GREEDY BOT (STUCK)" if self.bot_stuck else "GREEDY BOT"
            col = ORANGE if self.bot_stuck else BLUE
            bl = self.heading_font.render(lbl, True, col)
            screen.blit(bl, bl.get_rect(center=(bot_cx, self.b_by - 14)))

    #  board 
    def _draw_board(self, screen, game, bx, by, *, is_player):
        n   = game.size
        cs  = self.cell_size
        gx  = bx + CON_M
        gy  = by + CON_M
        gp  = cs * n

        # Grid background
        pygame.draw.rect(screen, CELL_BG, (gx, gy, gp, gp))

        # Draw cells
        for r in range(n):
            for c in range(n):
                cx = gx + c * cs
                cy = gy + r * cs
                st = game.player_grid[r][c]
                if st == TREE:
                    screen.blit(self.assets.get("tree", cs), (cx, cy))
                elif st == TENT:
                    pop = self._active_pop(is_player, r, c)
                    if pop:
                        el = time.time() - pop["time"]
                        scale = 0.5 + 0.5 * min(el / 0.2, 1.0)
                        sz = max(1, int(cs * scale))
                        full = self.assets.get("tent", cs)
                        scaled = pygame.transform.smoothscale(full, (sz, sz))
                        off = (cs - sz) // 2
                        screen.blit(self.assets.get("empty", cs), (cx, cy))
                        screen.blit(scaled, (cx + off, cy + off))
                    else:
                        screen.blit(self.assets.get("tent", cs), (cx, cy))
                elif st == GRASS:
                    screen.blit(self.assets.get("grass", cs), (cx, cy))
                else:
                    screen.blit(self.assets.get("empty", cs), (cx, cy))

        # Hover highlight (drawn over cells, semi-transparent)
        if is_player and self.hover_cell:
            hr, hc = self.hover_cell
            rh = pygame.Surface((gp, cs), pygame.SRCALPHA)
            rh.fill((255, 255, 100, 30))
            screen.blit(rh, (gx, gy + hr * cs))
            ch = pygame.Surface((cs, gp), pygame.SRCALPHA)
            ch.fill((255, 255, 100, 30))
            screen.blit(ch, (gx + hc * cs, gy))

        # Grid lines
        for i in range(n + 1):
            pygame.draw.line(screen, LGRAY,
                             (gx, gy + i * cs), (gx + gp, gy + i * cs))
            pygame.draw.line(screen, LGRAY,
                             (gx + i * cs, gy), (gx + i * cs, gy + gp))

        # Outer border
        pygame.draw.rect(screen, WHITE, (gx, gy, gp, gp), 2)

        # Hovered-cell border
        if is_player and self.hover_cell:
            hr, hc = self.hover_cell
            pygame.draw.rect(screen, ORANGE,
                             (gx + hc * cs, gy + hr * cs, cs, cs), 3)

        #  constraints 
        # Column constraints (above grid)
        for c in range(n):
            target = game.col_constraints[c]
            cur = sum(1 for r2 in range(n)
                      if game.player_grid[r2][c] == TENT)
            col = _con_color(cur, target)
            if is_player and self.hover_cell and self.hover_cell[1] == c:
                col = _brighten(col, 60)
            txt = self.con_font.render(str(target), True, col)
            screen.blit(txt, txt.get_rect(
                center=(gx + c * cs + cs // 2, by + CON_M // 2)))

        # Row constraints (left of grid)
        for r in range(n):
            target = game.row_constraints[r]
            cur = sum(1 for c2 in range(n)
                      if game.player_grid[r][c2] == TENT)
            col = _con_color(cur, target)
            if is_player and self.hover_cell and self.hover_cell[0] == r:
                col = _brighten(col, 60)
            txt = self.con_font.render(str(target), True, col)
            screen.blit(txt, txt.get_rect(
                center=(bx + CON_M // 2, gy + r * cs + cs // 2)))

    #  animation helpers 
    def _active_pop(self, is_player, r, c):
        board = "player" if is_player else "bot"
        for p in self.pops:
            if p["board"] == board and p["r"] == r and p["c"] == c:
                return p
        return None

    def _draw_flashes(self, screen):
        now = time.time()
        for f in self.flashes:
            el = now - f["time"]
            alpha = int(160 * max(0, 1 - el / 0.35))
            if alpha <= 0:
                continue
            if f["board"] == "player":
                bx, by = self.p_bx, self.p_by
            else:
                if self.mode != "versus":
                    continue
                bx, by = self.b_bx, self.b_by
            fx = bx + CON_M + f["c"] * self.cell_size
            fy = by + CON_M + f["r"] * self.cell_size
            ov = pygame.Surface((self.cell_size, self.cell_size),
                                pygame.SRCALPHA)
            c = f["color"]
            ov.fill((c[0], c[1], c[2], alpha))
            screen.blit(ov, (fx, fy))

    #  footer 
    def _draw_footer(self, screen):
        if not self.game_over:
            self.submit_btn.draw(screen)
            self.giveup_btn.draw(screen)
        hint = self.label_font.render(
            "ESC: Menu  |  Left-click: Tent  |  Right-click: Grass",
            True, DGRAY)
        screen.blit(hint, hint.get_rect(
            center=(SCREEN_W // 2, SCREEN_H - 10)))

    #  victory / game-over overlay 
    def _draw_overlay(self, screen):
        ov = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 180))
        screen.blit(ov, (0, 0))

        if self.gave_up:
            msg, col = "You Gave Up!", ORANGE
        elif self.winner == "YOU":
            msg, col = "YOU WIN!", GREEN
        elif self.winner == "GREEDY BOT":
            msg, col = "GREEDY BOT WINS!", BLUE
        else:
            msg, col = "Game Over", WHITE

        ts = self.overlay_font.render(msg, True, col)
        screen.blit(ts, ts.get_rect(
            center=(SCREEN_W // 2, SCREEN_H // 2 - 40)))

        sub = self.overlay_sub.render(
            f"Time: {self.elapsed}s   |   Wrong Clicks: {self.wrong_clicks}",
            True, LGRAY)
        screen.blit(sub, sub.get_rect(
            center=(SCREEN_W // 2, SCREEN_H // 2 + 10)))

        self.again_btn.draw(screen)
        self.menu_btn.draw(screen)


#  HELPERS
def _con_color(current, target):
    """Constraint colour: green=satisfied, red=exceeded, white=pending."""
    if current == target:
        return GREEN
    if current > target:
        return RED
    return WHITE


def _brighten(color, amount):
    return tuple(min(v + amount, 255) for v in color)


#  MAIN
def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("Tents Game")
    clock = pygame.time.Clock()

    assets = AssetManager()
    sm = SceneManager()
    sm.switch(MenuScene(sm, assets))

    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                if isinstance(sm.scene, MenuScene):
                    pygame.quit()
                    sys.exit()
            sm.handle(ev)
        sm.update()
        sm.draw(screen)
        pygame.display.flip()
        clock.tick(FPS)


if __name__ == "__main__":
    main()
