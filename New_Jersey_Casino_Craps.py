# nj_craps_full_v4.py
# Full New Jersey Compliant Craps — Buy, Lay, Odds, Place, Fire Bet, CSV Export
# No external dependencies except standard library + Tkinter

import tkinter as tk
from tkinter import ttk, messagebox
from random import randint
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, List, Set, Optional
import csv
import os

# ---------- Logging ----------
def log_event(msg: str):
    with open("craps_audit.log", "a", encoding="utf-8") as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{timestamp}] {msg}\n")

def export_log_to_csv():
    if not os.path.exists("craps_audit.log"):
        return False
    try:
        with open("craps_audit.log", "r", encoding="utf-8") as f_in, \
             open("craps_audit.csv", "w", newline="", encoding="utf-8") as f_out:
            writer = csv.writer(f_out)
            writer.writerow(["Timestamp", "Event"])
            for line in f_in:
                if line.strip().startswith("["):
                    try:
                        ts, event = line[1:].split("] ", 1)
                        writer.writerow([ts.strip(), event.strip()])
                    except:
                        writer.writerow(["", line.strip()])
                else:
                    writer.writerow(["", line.strip()])
        return True
    except Exception:
        return False

# ---------- Player Class ----------
@dataclass
class Player:
    name: str
    balance: int = 1000
    pass_bet: int = 0
    dont_pass_bet: int = 0
    come_bet: int = 0
    dont_come_bet: int = 0
    fire_bet: int = 0
    odds_pass: int = 0
    odds_come: Dict[int, int] = None
    place_bets: Dict[int, int] = None  # 4,5,6,8,9,10
    buy_bets: Dict[int, int] = None
    lay_bets: Dict[int, int] = None
    place_bets_on: Set[int] = None
    unique_points_made: Set[int] = None
    come_points: List[int] = None
    vig_paid: int = 0

    def __post_init__(self):
        if self.odds_come is None:
            self.odds_come = {}
        if self.place_bets is None:
            self.place_bets = {n: 0 for n in (4,5,6,8,9,10)}
        if self.buy_bets is None:
            self.buy_bets = {n: 0 for n in (4,5,6,8,9,10)}
        if self.lay_bets is None:
            self.lay_bets = {n: 0 for n in (4,5,6,8,9,10)}
        if self.place_bets_on is None:
            self.place_bets_on = set()
        if self.unique_points_made is None:
            self.unique_points_made = set()
        if self.come_points is None:
            self.come_points = []

# ---------- Game Engine ----------
class CrapsEngine:
    def __init__(self, player_names: List[str]):
        self.players = [Player(name) for name in player_names]
        self.current_shooter_index = 0
        self.point = None
        self.phase = "come_out"

    @property
    def current_shooter(self) -> Player:
        return self.players[self.current_shooter_index]

    def roll_dice(self) -> tuple[int, int, int]:
        d1, d2 = randint(1, 6), randint(1, 6)
        total = d1 + d2
        log_event(f"Dice rolled: {d1} + {d2} = {total}")
        return d1, d2, total

    def _get_player(self, name: str) -> Optional[Player]:
        return next((p for p in self.players if p.name == name), None)

    # --- Bet Placement ---
    def _safe_bet(self, player: Player, amount: int) -> bool:
        return amount > 0 and amount <= player.balance

    def place_pass(self, name: str, amt: int) -> bool:
        if self.phase != "come_out": return False
        p = self._get_player(name)
        if not p or not self._safe_bet(p, amt): return False
        p.balance -= amt
        p.pass_bet = amt
        log_event(f"{name} placed Pass bet: ${amt}")
        return True

    def place_dont_pass(self, name: str, amt: int) -> bool:
        if self.phase != "come_out": return False
        p = self._get_player(name)
        if not p or not self._safe_bet(p, amt): return False
        p.balance -= amt
        p.dont_pass_bet = amt
        log_event(f"{name} placed Don't Pass bet: ${amt}")
        return True

    def place_come(self, name: str, amt: int) -> bool:
        if self.phase != "point": return False
        p = self._get_player(name)
        if not p or not self._safe_bet(p, amt): return False
        p.balance -= amt
        p.come_bet = amt
        log_event(f"{name} placed Come bet: ${amt}")
        return True

    def place_dont_come(self, name: str, amt: int) -> bool:
        if self.phase != "point": return False
        p = self._get_player(name)
        if not p or not self._safe_bet(p, amt): return False
        p.balance -= amt
        p.dont_come_bet = amt
        log_event(f"{name} placed Don't Come bet: ${amt}")
        return True

    def place_fire(self, name: str, amt: int) -> bool:
        if self.phase != "come_out": return False
        if not (1 <= amt <= 5): return False
        p = self._get_player(name)
        if not p or p != self.current_shooter or not self._safe_bet(p, amt): return False
        p.balance -= amt
        p.fire_bet = amt
        p.unique_points_made.clear()
        log_event(f"{name} placed Fire bet: ${amt}")
        return True

    def place_odds_pass(self, name: str, amt: int) -> bool:
        if self.phase != "point" or not self.point: return False
        p = self._get_player(name)
        if not p or p.pass_bet == 0 or not self._safe_bet(p, amt): return False
        p.balance -= amt
        p.odds_pass = amt
        log_event(f"{name} placed Odds on Pass: ${amt}")
        return True

    def place_place_bet(self, name: str, number: int, amt: int, turn_on: bool = False) -> bool:
        if number not in (4,5,6,8,9,10): return False
        p = self._get_player(name)
        if not p or not self._safe_bet(p, amt): return False
        p.balance -= amt
        p.place_bets[number] += amt
        if turn_on:
            p.place_bets_on.add(number)
        log_event(f"{name} placed Place Bet on {number}: ${amt}")
        return True

    def place_buy_bet(self, name: str, number: int, amt: int) -> bool:
        if number not in (4,5,6,8,9,10): return False
        p = self._get_player(name)
        if not p or not self._safe_bet(p, amt): return False
        vig = max(1, int(amt * 0.05))
        total = amt + vig
        if total > p.balance: return False
        p.balance -= total
        p.buy_bets[number] += amt
        p.vig_paid += vig
        log_event(f"{name} placed Buy Bet on {number}: ${amt} + ${vig} vig")
        return True

    def place_lay_bet(self, name: str, number: int, win_amt: int) -> bool:
        if number not in (4,5,6,8,9,10): return False
        p = self._get_player(name)
        if not p or win_amt <= 0: return False
        # Determine risk amount
        if number in (4,10):
            risk = int(win_amt / 2)
        elif number in (5,9):
            risk = int(win_amt * 2 / 3)
        else:  # 6,8
            risk = int(win_amt * 5 / 6)
        vig = max(1, int(win_amt * 0.05))
        total_risk = risk + vig
        if total_risk > p.balance: return False
        p.balance -= total_risk
        p.lay_bets[number] = p.lay_bets.get(number, 0) + win_amt
        p.vig_paid += vig
        log_event(f"{name} placed Lay Bet on {number}: to win ${win_amt} (risk ${risk}) + ${vig} vig")
        return True

    # --- Payout Helpers ---
    def _odds_payout(self, point: int, amount: int, is_pass: bool) -> int:
        if is_pass:
            map_ = {4: 2, 5: 1.5, 6: 6/5, 8: 6/5, 9: 1.5, 10: 2}
            return int(amount * map_[point])
        else:
            map_ = {4: 0.5, 5: 2/3, 6: 5/6, 8: 5/6, 9: 2/3, 10: 0.5}
            return int(amount * map_[point])

    def _place_payout(self, number: int, amt: int) -> int:
        if number in (4,10):
            return int(amt * 9 / 5)
        elif number in (5,9):
            return int(amt * 7 / 5)
        else:  # 6,8
            return int(amt * 7 / 6)

    def _buy_payout(self, number: int, amt: int) -> int:
        if number in (4,10):
            return amt * 2
        elif number in (5,9):
            return int(amt * 3 / 2)
        else:  # 6,8
            return int(amt * 6 / 5)

    # --- Resolution ---
    def resolve_come_out(self, total: int):
        shooter = self.current_shooter
        for p in self.players:
            # Pass
            if p.pass_bet:
                if total in (7,11):
                    p.balance += p.pass_bet * 2
                    log_event(f"{p.name} wins Pass bet: +${p.pass_bet}")
                elif total in (2,3,12):
                    log_event(f"{p.name} loses Pass bet")
                else:
                    if total in (4,5,6,8,9,10) and p == shooter:
                        p.unique_points_made.add(total)
            # Don't Pass
            if p.dont_pass_bet:
                if total in (2,3):
                    p.balance += p.dont_pass_bet * 2
                elif total == 12:
                    p.balance += p.dont_pass_bet
                    log_event(f"{p.name} Don't Pass pushes on 12")
                elif total in (7,11):
                    log_event(f"{p.name} loses Don't Pass")
            # Fire Bet
            if p == shooter and p.fire_bet and total in (2,3,7,11,12):
                log_event(f"{p.name} Fire bet lost (no point made)")
                p.fire_bet = 0
            # Place/Buy/Lay (only if "On")
            self._resolve_place_buy_lay(p, total, come_out=True)

        if total in (4,5,6,8,9,10):
            self.point = total
            self.phase = "point"
            log_event(f"Point established: {total}")
        else:
            self._reset_bets()

    def resolve_point_phase(self, total: int):
        shooter = self.current_shooter
        if total == self.point:
            for p in self.players:
                if p.pass_bet:
                    p.balance += p.pass_bet * 2
                    win_odds = self._odds_payout(self.point, p.odds_pass, True)
                    p.balance += win_odds
                    if p == shooter:
                        p.unique_points_made.add(self.point)
                    log_event(f"{p.name} wins Pass + Odds: ${p.pass_bet + win_odds}")
                self._resolve_place_buy_lay(p, total)
            self._reset_bets()
        elif total == 7:
            for p in self.players:
                if p.dont_pass_bet:
                    p.balance += p.dont_pass_bet * 2
                    win_odds = self._odds_payout(self.point, p.odds_pass, False)
                    p.balance += win_odds
                    log_event(f"{p.name} wins Don't Pass + Odds: ${p.dont_pass_bet + win_odds}")
                if p.come_bet:
                    p.come_bet = 0
                    log_event(f"{p.name} loses Come bet on 7")
                if p.dont_come_bet:
                    p.balance += p.dont_come_bet * 2
                    p.dont_come_bet = 0
                    log_event(f"{p.name} wins Don't Come on 7")
                # Place/Buy/Lay lose on 7 (except Lay wins)
                self._resolve_place_buy_lay(p, total)
                # Fire Bet
                if p == shooter and p.fire_bet:
                    self._resolve_fire_bet(p)
            self.current_shooter_index = (self.current_shooter_index + 1) % len(self.players)
            self._reset_bets()
            log_event(f"7-out. Next shooter: {self.current_shooter.name}")
        else:
            self._resolve_come_bets(total)
            for p in self.players:
                self._resolve_place_buy_lay(p, total)

    def _resolve_place_buy_lay(self, p: Player, roll: int, come_out: bool = False):
        # Place Bets
        for num in list(p.place_bets.keys()):
            amt = p.place_bets[num]
            if amt == 0:
                continue
            active = (not come_out) or (num in p.place_bets_on)
            if not active:
                continue
            if roll == num:
                win = self._place_payout(num, amt)
                p.balance += amt + win
                p.place_bets[num] = 0
                log_event(f"{p.name} wins Place Bet on {num}: +${win}")
            elif roll == 7:
                p.place_bets[num] = 0
                log_event(f"{p.name} loses Place Bet on {num}")

        # Buy Bets (always active)
        for num in list(p.buy_bets.keys()):
            amt = p.buy_bets[num]
            if amt == 0:
                continue
            if roll == num:
                win = self._buy_payout(num, amt)
                p.balance += win
                p.buy_bets[num] = 0
                log_event(f"{p.name} wins Buy Bet on {num}: +${win}")
            elif roll == 7:
                p.buy_bets[num] = 0
                log_event(f"{p.name} loses Buy Bet on {num}")

        # Lay Bets (win on 7, lose on number)
        for num in list(p.lay_bets.keys()):
            win_amt = p.lay_bets[num]
            if win_amt == 0:
                continue
            if roll == 7:
                p.balance += win_amt
                p.lay_bets[num] = 0
                log_event(f"{p.name} wins Lay Bet on {num}: +${win_amt}")
            elif roll == num:
                p.lay_bets[num] = 0
                log_event(f"{p.name} loses Lay Bet on {num}")

    def _resolve_come_bets(self, total: int):
        for p in self.players:
            if p.come_bet:
                if total in (7,11):
                    p.balance += p.come_bet * 2
                    p.come_bet = 0
                    log_event(f"{p.name} wins Come bet on {total}")
                elif total in (2,3,12):
                    p.come_bet = 0
                    log_event(f"{p.name} loses Come bet on {total}")
                else:
                    p.come_points.append(total)
                    p.come_bet = 0
                    log_event(f"{p.name} Come point: {total}")
            if p.dont_come_bet:
                if total in (2,3):
                    p.balance += p.dont_come_bet * 2
                    p.dont_come_bet = 0
                    log_event(f"{p.name} wins Don't Come on {total}")
                elif total in (7,11):
                    p.dont_come_bet = 0
                    log_event(f"{p.name} loses Don't Come on {total}")
                elif total == 12:
                    p.balance += p.dont_come_bet
                    p.dont_come_bet = 0
                    log_event(f"{p.name} Don't Come pushes on 12")
                else:
                    p.come_points.append(-total)
                    p.dont_come_bet = 0
                    log_event(f"{p.name} Don't Come point: {total}")

    def _resolve_fire_bet(self, player: Player):
        points = len(player.unique_points_made)
        if points >= 4:
            payout = player.fire_bet * {4:24, 5:249, 6:999}[points]
            player.balance += payout
            log_event(f"{player.name} wins Fire Bet! {points} points → +${payout}")
        else:
            log_event(f"{player.name} Fire Bet lost ({points} points)")
        player.fire_bet = 0

    def _reset_bets(self):
        for p in self.players:
            p.pass_bet = 0
            p.dont_pass_bet = 0
            p.come_bet = 0
            p.dont_come_bet = 0
            p.odds_pass = 0
            p.odds_come.clear()
            p.come_points.clear()
            p.place_bets = {n: 0 for n in (4,5,6,8,9,10)}
            p.buy_bets = {n: 0 for n in (4,5,6,8,9,10)}
            p.lay_bets = {n: 0 for n in (4,5,6,8,9,10)}
            p.place_bets_on.clear()
        self.point = None
        self.phase = "come_out"

# ---------- Dice Drawing ----------
def draw_die(canvas, x, y, value, size=70):
    canvas.create_rectangle(x, y, x+size, y+size, fill="white", outline="black", width=2)
    center = (x + size//2, y + size//2)
    offset = size // 3
    pips = []
    if value == 1:
        pips = [center]
    elif value == 2:
        pips = [(x+offset, y+offset), (x+size-offset, y+size-offset)]
    elif value == 3:
        pips = [(x+offset, y+offset), center, (x+size-offset, y+size-offset)]
    elif value == 4:
        pips = [(x+offset, y+offset), (x+size-offset, y+offset),
                (x+offset, y+size-offset), (x+size-offset, y+size-offset)]
    elif value == 5:
        pips = [(x+offset, y+offset), (x+size-offset, y+offset),
                center,
                (x+offset, y+size-offset), (x+size-offset, y+size-offset)]
    elif value == 6:
        pips = [(x+offset, y+offset), (x+size-offset, y+offset),
                (x+offset, y+size//2), (x+size-offset, y+size//2),
                (x+offset, y+size-offset), (x+size-offset, y+size-offset)]
    for px, py in pips:
        canvas.create_oval(px-4, py-4, px+4, py+4, fill="black")

# ---------- GUI ----------
class CrapsGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🎰 NJ Compliant Craps — Full Rules")
        self.root.geometry("1200x800")
        self.setup_wizard()

    def setup_wizard(self):
        wizard = tk.Toplevel(self.root)
        wizard.title("👥 Player Setup")
        wizard.geometry("400x250")
        wizard.transient(self.root)
        wizard.grab_set()

        ttk.Label(wizard, text="Player Names (one per line):").pack(pady=10)
        self.name_text = tk.Text(wizard, height=4, width=30)
        self.name_text.pack()
        self.name_text.insert("1.0", "Alice\nBob")

        self.balance_var = tk.IntVar(value=1000)
        ttk.Label(wizard, text="Starting Balance ($):").pack()
        ttk.Spinbox(wizard, from_=100, to=10000, textvariable=self.balance_var, width=10).pack()

        def start():
            names = [n.strip() for n in self.name_text.get("1.0", "end").split("\n") if n.strip()]
            if not names:
                messagebox.showerror("Error", "At least one player required.")
                return
            self.players = names
            self.balance = self.balance_var.get()
            for name in names:
                log_event(f"Player added: {name}")
            wizard.destroy()
            self.start_game()

        ttk.Button(wizard, text="Start Game", command=start).pack(pady=15)
        wizard.wait_window()

    def start_game(self):
        self.engine = CrapsEngine(self.players)
        for p in self.engine.players:
            p.balance = self.balance
        self.create_widgets()

    def create_widgets(self):
        self.canvas = tk.Canvas(self.root, bg="#0a5e2a", width=1200, height=800)
        self.canvas.pack()

        self.canvas.create_rectangle(50, 50, 1150, 750, outline="white", width=4)
        self.canvas.create_text(600, 80, text="NEW JERSEY CRAPS TABLE", fill="gold", font=("Arial", 16, "bold"))

        self.player_data = {}
        for i, name in enumerate(self.players):
            x = 100 + i * 200
            self.canvas.create_text(x, 120, text=name, fill="white", font=("Arial", 10))
            bal_id = self.canvas.create_text(x, 140, text=f"${self.balance}", fill="yellow")
            frame = ttk.Frame(self.root)
            frame.place(x=x-80, y=160)
            btns = [
                ("Pass", lambda n=name: self.bet("pass", n)),
                ("DontP", lambda n=name: self.bet("dont_pass", n)),
                ("Come", lambda n=name: self.bet("come", n)),
                ("DontC", lambda n=name: self.bet("dont_come", n)),
                ("🔥", lambda n=name: self.bet("fire", n)),
                ("Odds", lambda n=name: self.bet("odds_pass", n)),
                ("P6", lambda n=name: self.bet("place_6", n)),
                ("Buy6", lambda n=name: self.bet("buy_6", n)),
                ("Lay6", lambda n=name: self.bet("lay_6", n)),
            ]
            for txt, cmd in btns:
                ttk.Button(frame, text=txt, command=cmd).pack(side="left", padx=1)
            self.player_data[name] = {"balance_id": bal_id, "frame": frame}

        self.die1_x, self.die1_y = 450, 300
        self.die2_x, self.die2_y = 580, 300
        self.die_size = 80

        self.point_id = self.canvas.create_text(600, 250, text="No Point", fill="yellow", font=("Arial", 14))
        self.shooter_id = self.canvas.create_text(600, 280, text=f"Shooter: {self.engine.current_shooter.name}", fill="cyan")

        self.roll_btn = ttk.Button(self.root, text="🎲 ROLL DICE", command=self.roll_dice)
        self.roll_btn.place(x=550, y=650)

        self.wager_var = tk.IntVar(value=10)
        ttk.Entry(self.root, textvariable=self.wager_var, width=8).place(x=550, y=620)

        ttk.Button(self.root, text="📄 Export to CSV", command=self.export_csv).place(x=1000, y=700)

        self.update_display()

    def bet(self, bet_type: str, player_name: str):
        try:
            amt = self.wager_var.get()
            e = self.engine
            success = False
            if bet_type == "pass":
                success = e.place_pass(player_name, amt)
            elif bet_type == "dont_pass":
                success = e.place_dont_pass(player_name, amt)
            elif bet_type == "come":
                success = e.place_come(player_name, amt)
            elif bet_type == "dont_come":
                success = e.place_dont_come(player_name, amt)
            elif bet_type == "fire":
                success = e.place_fire(player_name, amt)
            elif bet_type == "odds_pass":
                success = e.place_odds_pass(player_name, amt)
            elif bet_type == "place_6":
                success = e.place_place_bet(player_name, 6, amt)
            elif bet_type == "buy_6":
                success = e.place_buy_bet(player_name, 6, amt)
            elif bet_type == "lay_6":
                success = e.place_lay_bet(player_name, 6, amt)
            if success:
                self.update_display()
            else:
                messagebox.showerror("Bet Error", "Invalid bet (phase, balance, or rules).")
        except Exception as ex:
            messagebox.showerror("Input Error", f"Invalid wager: {ex}")

    def roll_dice(self):
        for _ in range(6):
            d1, d2 = randint(1,6), randint(1,6)
            self.redraw_dice(d1, d2)
            self.canvas.update()
            self.canvas.after(100)

        d1, d2, total = self.engine.roll_dice()
        self.redraw_dice(d1, d2)

        if self.engine.phase == "come_out":
            self.engine.resolve_come_out(total)
        else:
            self.engine.resolve_point_phase(total)

        self.update_display()
        messagebox.showinfo("Roll", f"Rolled: {d1} + {d2} = {total}")

    def redraw_dice(self, d1, d2):
        self.canvas.delete("die")
        draw_die(self.canvas, self.die1_x, self.die1_y, d1, self.die_size)
        draw_die(self.canvas, self.die2_x, self.die2_y, d2, self.die_size)

    def update_display(self):
        for p in self.engine.players:
            self.canvas.itemconfig(self.player_data[p.name]["balance_id"], text=f"${p.balance}")
        pt = f"POINT: {self.engine.point}" if self.engine.point else "No Point"
        self.canvas.itemconfig(self.point_id, text=pt)
        self.canvas.itemconfig(self.shooter_id, text=f"Shooter: {self.engine.current_shooter.name}")

    def export_csv(self):
        if export_log_to_csv():
            messagebox.showinfo("Export", "Log exported to craps_audit.csv")
        else:
            messagebox.showwarning("Export", "No log found.")

# ---------- Run ----------
if __name__ == "__main__":
    root = tk.Tk()
    app = CrapsGUI(root)
    root.mainloop()