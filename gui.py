import tkinter as tk
from tkinter import messagebox
import time
from tents import TentsGame, TREE, TENT, GRASS, EMPTY
from greedy_bot import GreedyBot

class GameWindow:
    def __init__(self, master):
        self.master = master
        self.master.title("Tents Puzzle Game - Versus Mode")
        
        # Initialize Player Game
        self.player_game = TentsGame(size=8)
        self.player_game.generate_level(num_tents=12)
        
        # Initialize Bot Game (Clone of Player Game)
        self.bot_game = self.player_game.clone_for_race()
        self.bot = GreedyBot(self.bot_game)
        
        self.player_buttons = [[None for _ in range(8)] for _ in range(8)]
        self.bot_buttons = [[None for _ in range(8)] for _ in range(8)]
        
        self.player_wrong_clicks = 0
        self.start_time = time.time()
        self.game_over = False
        
        # --- UI LAYOUT ---
        # Main Container
        main_frame = tk.Frame(master)
        main_frame.pack(padx=10, pady=10)
        
        # Header
        self.header_frame = tk.Frame(main_frame)
        self.header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        
        self.status_label = tk.Label(self.header_frame, text="Your Wrong Clicks: 0", font=("Arial", 10))
        self.status_label.pack(side=tk.LEFT, padx=10)
        
        self.bot_status_label = tk.Label(self.header_frame, text="Bot Scanned: 0", font=("Arial", 10, "italic"), fg="blue")
        self.bot_status_label.pack(side=tk.LEFT, padx=10)
        
        self.timer_label = tk.Label(self.header_frame, text="Time: 0s", font=("Arial", 10))
        self.timer_label.pack(side=tk.RIGHT, padx=10)

        # Player Frame (Left)
        player_frame = tk.Frame(main_frame, bd=2, relief=tk.GROOVE)
        player_frame.grid(row=1, column=0, padx=10)
        tk.Label(player_frame, text="YOU", font=("Arial", 14, "bold"), fg="green").grid(row=0, column=0, columnspan=10)
        
        # Bot Frame (Right)
        self.bot_frame = tk.Frame(main_frame, bd=2, relief=tk.GROOVE)
        self.bot_frame.grid(row=1, column=1, padx=10)
        self.bot_title = tk.Label(self.bot_frame, text="GREEDY BOT", font=("Arial", 14, "bold"), fg="blue")
        self.bot_title.grid(row=0, column=0, columnspan=10)
        
        # Create Grids
        self.create_grid(player_frame, self.player_buttons, is_player=True)
        self.create_grid(self.bot_frame, self.bot_buttons, is_player=False)
        
        # Footer
        self.control_frame = tk.Frame(main_frame)
        self.control_frame.grid(row=2, column=0, columnspan=2, pady=10)
        
        self.submit_btn = tk.Button(self.control_frame, text="Submit/Check", command=self.manual_submit, bg="#dddddd", font=("Arial", 10, "bold"))
        self.submit_btn.pack()

        # Start Loops
        self.update_timer()
        self.schedule_bot_move()

    def create_grid(self, parent, button_matrix, is_player):
        game = self.player_game if is_player else self.bot_game
        size = game.size
        
        # Cols constraints
        for c in range(size):
            lbl = tk.Label(parent, text=str(game.col_constraints[c]), font=("Arial", 12, "bold"))
            lbl.grid(row=1, column=c+1, padx=2, pady=2)
            
        # Rows constraints
        for r in range(size):
            lbl = tk.Label(parent, text=str(game.row_constraints[r]), font=("Arial", 12, "bold"))
            lbl.grid(row=r+2, column=0, padx=2, pady=2)
            
        for r in range(size):
            for c in range(size):
                btn = tk.Button(parent, width=4, height=2, font=("Arial", 10))
                
                if is_player:
                    btn.bind('<Button-1>', lambda e, row=r, col=c: self.on_player_left_click(row, col))
                    btn.bind('<Button-3>', lambda e, row=r, col=c: self.on_player_right_click(row, col))
                else:
                    btn.config(state="disabled") # Users can't click bot's board
                
                btn.grid(row=r+2, column=c+1, padx=1, pady=1)
                button_matrix[r][c] = btn
                self.update_button_visual(button_matrix, game, r, c)

    def update_button_visual(self, buttons, game, r, c):
        state = game.player_grid[r][c]
        btn = buttons[r][c]
        
        if state == TREE:
            btn.config(bg="green", text="TREE") 
        elif state == TENT:
            btn.config(bg="red", text="TENT")
        elif state == GRASS:
            btn.config(bg="brown", text="")
        else: # EMPTY
            btn.config(bg="SystemButtonFace", text="")

    def flash_error(self, r, c):
        btn = self.player_buttons[r][c]
        original_bg = btn.cget("bg")
        btn.config(bg="#ff9999") 
        self.master.after(200, lambda: btn.config(bg=original_bg))
        
    def flash_bot_move(self, r, c):
        btn = self.bot_buttons[r][c]
        # original_bg = btn.cget("bg") # Not strictly needed as we update visual after
        btn.config(bg="#99ccff")
        self.master.after(400, lambda: self.update_button_visual(self.bot_buttons, self.bot_game, r, c))

    def on_player_left_click(self, r, c):
        if self.game_over: return
        
        current = self.player_game.player_grid[r][c]
        
        if current == TENT:
            self.player_game.player_grid[r][c] = EMPTY
            self.update_button_visual(self.player_buttons, self.player_game, r, c)
            return

        if current == EMPTY or current == GRASS:
            if self.player_game.is_move_legal(r, c, TENT):
                self.player_game.make_move(r, c, TENT)
                self.update_button_visual(self.player_buttons, self.player_game, r, c)
                if self.player_game.check_victory():
                    self.end_game(winner="YOU")
            else:
                self.player_wrong_clicks += 1
                self.status_label.config(text=f"Your Wrong Clicks: {self.player_wrong_clicks}")
                self.flash_error(r, c)

    def on_player_right_click(self, r, c):
        if self.game_over: return
        
        current = self.player_game.player_grid[r][c]
        if current == GRASS:
            self.player_game.player_grid[r][c] = EMPTY
        elif current == EMPTY or current == TENT:
            self.player_game.player_grid[r][c] = GRASS
            
        self.update_button_visual(self.player_buttons, self.player_game, r, c)
        
    def schedule_bot_move(self):
        if not self.game_over:
            self.master.after(1000, self.execute_bot_move)
            
    def execute_bot_move(self):
        if self.game_over: return
        
        move = self.bot.get_best_move()
        
        if move:
            r, c, move_type, scanned = move
            self.bot_game.player_grid[r][c] = move_type
            self.bot_status_label.config(text=f"Bot Scanned: {scanned}")
            self.flash_bot_move(r, c)
            
            if self.bot_game.check_victory():
                self.end_game(winner="GREEDY BOT")
                return # Stop loop
                
            self.schedule_bot_move()
        else:
            # BOT IS STUCK
            # Check if it finished?
            if self.bot_game.check_victory():
                self.end_game(winner="GREEDY BOT")
            else:
                self.bot_status_label.config(text="Bot Stuck - Your Turn!", fg="red", font=("Arial", 10, "bold"))
                # Visual Feedback: Change Bot Frame Background to Orange
                self.bot_frame.config(bg="#FFA500") # Orange
                self.bot_title.config(bg="#FFA500")
                # Do NOT schedule next move. The bot has given up.

    def update_timer(self):
        if not self.game_over:
            elapsed = int(time.time() - self.start_time)
            self.timer_label.config(text=f"Time: {elapsed}s")
            self.master.after(1000, self.update_timer)

    def manual_submit(self):
        if self.game_over: return
        if self.player_game.check_victory():
            self.end_game("YOU")
        else:
            messagebox.showwarning("Not Done", "Incorrect or Incomplete. Keep trying!")

    def end_game(self, winner):
        self.game_over = True
        elapsed = int(time.time() - self.start_time)
        msg = f"Winner: {winner}!\nTime: {elapsed}s\nYour Errors: {self.player_wrong_clicks}"
        messagebox.showinfo("Game Over", msg)

if __name__ == "__main__":
    root = tk.Tk()
    app = GameWindow(root)
    root.mainloop()

if __name__ == "__main__":
    root = tk.Tk()
    app = GameWindow(root)
    root.mainloop()
