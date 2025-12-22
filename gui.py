import tkinter as tk
from tkinter import messagebox
import time
from tents import TentsGame, TREE, TENT, GRASS, EMPTY
from greedy_bot import GreedyBot

class GameWindow:
    def __init__(self, master):
        self.master = master
        self.master.title("Tents Puzzle Game")
        
        self.game = TentsGame(size=8)
        self.game.generate_level(num_tents=12)
        
        # Initialize Bot
        self.bot = GreedyBot(self.game)
        
        self.buttons = [[None for _ in range(self.game.size)] for _ in range(self.game.size)]
        self.wrong_clicks = 0
        self.start_time = time.time()
        self.game_over = False
        self.is_bot_turn = False # Prevent user input during bot turn
        
        # Header Frame for Status
        self.header_frame = tk.Frame(master)
        self.header_frame.grid(row=0, column=0, columnspan=self.game.size + 2, pady=5, sticky="ew")
        
        self.status_label = tk.Label(self.header_frame, text="Wrong Clicks: 0", font=("Arial", 10))
        self.status_label.pack(side=tk.LEFT, padx=10)
        
        # Bot Stats Label
        self.bot_label = tk.Label(self.header_frame, text="Bot Scanned: 0", font=("Arial", 10, "italic"), fg="blue")
        self.bot_label.pack(side=tk.LEFT, padx=10)
        
        self.timer_label = tk.Label(self.header_frame, text="Time: 0s", font=("Arial", 10))
        self.timer_label.pack(side=tk.RIGHT, padx=10)
        
        self.create_grid()
        
        # Assessment/Control Frame
        self.control_frame = tk.Frame(master)
        self.control_frame.grid(row=self.game.size + 3, column=0, columnspan=self.game.size + 2, pady=10)
        
        self.submit_btn = tk.Button(self.control_frame, text="Submit", command=self.manual_submit, bg="#dddddd", font=("Arial", 10, "bold"))
        self.submit_btn.pack()

        # Start Timer Loop
        self.update_timer()
        
    def update_timer(self):
        if not self.game_over:
            elapsed = int(time.time() - self.start_time)
            self.timer_label.config(text=f"Time: {elapsed}s")
            self.master.after(1000, self.update_timer)

    def create_grid(self):
        # Grid Size + 1 for constraints
        for c in range(self.game.size):
            lbl = tk.Label(self.master, text=str(self.game.col_constraints[c]), font=("Arial", 12, "bold"))
            lbl.grid(row=1, column=c+1, padx=5, pady=5)
            
        for r in range(self.game.size):
            lbl = tk.Label(self.master, text=str(self.game.row_constraints[r]), font=("Arial", 12, "bold"))
            lbl.grid(row=r+2, column=0, padx=5, pady=5)
            
        for r in range(self.game.size):
            for c in range(self.game.size):
                btn = tk.Button(self.master, width=4, height=2, font=("Arial", 10))
                btn.bind('<Button-1>', lambda e, row=r, col=c: self.on_left_click(row, col))
                btn.bind('<Button-3>', lambda e, row=r, col=c: self.on_right_click(row, col))
                
                btn.grid(row=r+2, column=c+1, padx=1, pady=1)
                self.buttons[r][c] = btn
                self.update_button_visual(r, c)

    def update_button_visual(self, r, c):
        state = self.game.player_grid[r][c]
        btn = self.buttons[r][c]
        
        if state == TREE:
            btn.config(bg="green", text="TREE", state="disabled") 
        elif state == TENT:
            btn.config(bg="red", text="TENT")
        elif state == GRASS:
            btn.config(bg="brown", text="")
        else: # EMPTY
            btn.config(bg="SystemButtonFace", text="")

    def flash_error(self, r, c):
        """Flashes the button red to indicate error."""
        btn = self.buttons[r][c]
        original_bg = btn.cget("bg")
        btn.config(bg="#ff9999") 
        self.master.after(200, lambda: btn.config(bg=original_bg))

    def flash_bot_move(self, r, c):
        """Flashes blue to indicate bot move."""
        btn = self.buttons[r][c]
        original_bg = btn.cget("bg")
        btn.config(bg="#99ccff") # Light Blue
        self.master.after(400, lambda: self.update_button_visual(r, c))

    def on_left_click(self, r, c):
        if self.game_over or self.is_bot_turn: return
        
        current = self.game.player_grid[r][c]
        if current == TENT:
            self.game.player_grid[r][c] = EMPTY
            self.update_button_visual(r, c)
            self.trigger_bot_turn() # Player made a move
            return

        if current == EMPTY or current == GRASS:
            if self.game.is_move_legal(r, c, TENT):
                self.game.make_move(r, c, TENT)
                self.update_button_visual(r, c)
                if self.check_victory_condition(): return
                self.trigger_bot_turn()
            else:
                self.wrong_clicks += 1
                self.status_label.config(text=f"Wrong Clicks: {self.wrong_clicks}")
                self.flash_error(r, c)

    def on_right_click(self, r, c):
        if self.game_over or self.is_bot_turn: return
        
        current = self.game.player_grid[r][c]
        changed = False
        if current == GRASS:
            self.game.player_grid[r][c] = EMPTY
            changed = True
        elif current == EMPTY or current == TENT:
            self.game.player_grid[r][c] = GRASS
            changed = True
            
        self.update_button_visual(r, c)
        if changed: self.trigger_bot_turn()
    
    def trigger_bot_turn(self):
        """Schedules the bot move."""
        self.is_bot_turn = True
        # 0.5 sec delay
        self.master.after(500, self.execute_bot_move)
        
    def execute_bot_move(self):
        if self.game_over: return
        
        move = self.bot.get_best_move()
        
        if move:
            r, c, move_type, scanned = move
            # Apply move
            self.game.player_grid[r][c] = move_type
            
            # Visuals
            self.bot_label.config(text=f"Bot Scanned: {scanned}")
            self.flash_bot_move(r, c)
            
            # Check victory after bot
            if move_type == TENT and self.check_victory_condition():
                return
        else:
            self.bot_label.config(text="Bot Scanned: All Checked (No Move)")
            
        self.is_bot_turn = False

    def check_victory_condition(self):
        if self.game.check_victory():
            self.game_over = True
            self.show_results(True, auto=True)
            return True
        return False

    def manual_submit(self):
        if self.game_over: return
        
        is_win = self.game.check_victory()
        if is_win:
            self.game_over = True
            self.show_results(True, auto=False)
        else:
            self.show_results(False, auto=False)

    def show_results(self, is_win, auto=False):
        elapsed = int(time.time() - self.start_time)
        
        msg = f"Time Taken: {elapsed} seconds\n"
        msg += f"Invalid Moves: {self.wrong_clicks}\n\n"
        
        if is_win:
            msg += "Correct! Implementation Successful!"
            if auto:
                msg = "Auto-Submitted! Only Valid Moves Remaining!\n" + msg
            messagebox.showinfo("Victory!", msg)
        else:
            msg += "Incorrect/Incomplete.\nKeep trying!"
            messagebox.showwarning("Not Done", msg)

if __name__ == "__main__":
    root = tk.Tk()
    app = GameWindow(root)
    root.mainloop()
