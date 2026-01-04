import os
from random import randint
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, List, Set, Optional
import csv

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, Rectangle, Line
from kivy.uix.widget import Widget
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.core.window import Window

Window.size = (420, 800)

# ---------- LOGGING ----------
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

# ---------- PLAYER ----------
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
    place_bets: Dict[int, int] = None
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

# ---------- CRAPS ENGINE (full from your file) ----------
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

    def resolve_come_out(self, total: int):
        shooter = self.current_shooter
        for p in self.players:
            if p.pass_bet:
                if total in (7,11):
                    p.balance += p.pass_bet * 2
                    log_event(f"{p.name} wins Pass bet: +${p.pass_bet}")
                elif total in (2,3,12):
                    log_event(f"{p.name} loses Pass bet")
                else:
                    if total in (4,5,6,8,9,10) and p == shooter:
                        p.unique_points_made.add(total)
            if p.dont_pass_bet:
                if total in (2,3):
                    p.balance += p.dont_pass_bet * 2
                elif total == 12:
                    p.balance += p.dont_pass_bet
                    log_event(f"{p.name} Don't Pass pushes on 12")
                elif total in (7,11):
                    log_event(f"{p.name} loses Don't Pass")
            if p == shooter and p.fire_bet and total in (2,3,7,11,12):
                log_event(f"{p.name} Fire bet lost (no point made)")
                p.fire_bet = 0
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
                self._resolve_place_buy_lay(p, total)
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
        for num in list(p.place_bets.keys()):
            amt = p.place_bets[num]
            if amt == 0: continue
            active = (not come_out) or (num in p.place_bets_on)
            if not active: continue
            if roll == num:
                win = self._place_payout(num, amt)
                p.balance += amt + win
                p.place_bets[num] = 0
                log_event(f"{p.name} wins Place Bet on {num}: +${win}")
            elif roll == 7:
                p.place_bets[num] = 0
                log_event(f"{p.name} loses Place Bet on {num}")
        for num in list(p.buy_bets.keys()):
            amt = p.buy_bets[num]
            if amt == 0: continue
            if roll == num:
                win = self._buy_payout(num, amt)
                p.balance += win
                p.buy_bets[num] = 0
                log_event(f"{p.name} wins Buy Bet on {num}: +${win}")
            elif roll == 7:
                p.buy_bets[num] = 0
                log_event(f"{p.name} loses Buy Bet on {num}")
        for num in list(p.lay_bets.keys()):
            win_amt = p.lay_bets[num]
            if win_amt == 0: continue
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
                    log_event(f"{p.name} Don't Come pushes on 12}")
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

# ---------- DICE WIDGET ----------
class DiceWidget(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.value1 = 1
        self.value2 = 1
        self.size_hint = (None, None)
        self.size = (200, 120)
        self.pos_hint = {'center_x': 0.5}
        self.bind(pos=self.update_canvas, size=self.update_canvas)
        self.update_canvas()

    def update_canvas(self, *args):
        self.canvas.clear()
        with self.canvas:
            Color(1, 1, 1)
            Rectangle(pos=(self.x, self.y), size=(90, 90))
            Color(0, 0, 0)
            Line(rectangle=(self.x, self.y, 90, 90), width=2)
            self.draw_pips(self.x, self.y, self.value1, 90)

            Color(1, 1, 1)
            Rectangle(pos=(self.x + 110, self.y), size=(90, 90))
            Color(0, 0, 0)
            Line(rectangle=(self.x + 110, self.y, 90, 90), width=2)
            self.draw_pips(self.x + 110, self.y, self.value2, 90)

    def draw_pips(self, x, y, value, size):
        center = (x + size / 2, y + size / 2)
        offset = size / 3
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
            pips = [(x+offset, y+offset), (x+size-offset, y+offset), center,
                    (x+offset, y+size-offset), (x+size-offset, y+size-offset)]
        elif value == 6:
            pips = [(x+offset, y+offset), (x+size-offset, y+offset),
                    (x+offset, y+size/2), (x+size-offset, y+size/2),
                    (x+offset, y+size-offset), (x+size-offset, y+size-offset)]
        for px, py in pips:
            Color(0, 0, 0)
            Rectangle(pos=(px - 4, py - 4), size=(8, 8))

    def set_dice(self, v1, v2):
        self.value1 = v1
        self.value2 = v2
        self.update_canvas()

    def animate_roll(self):
        anim = Animation(x=self.x - 10, duration=0.05) + Animation(x=self.x + 20, duration=0.1) + Animation(x=self.x, duration=0.05)
        anim.start(self)

# ---------- SETUP SCREEN ----------
class SetupScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=20, spacing=20)
        layout.add_widget(Label(text="👥 Player Setup", font_size=24, color=(1, 0.9, 0, 1)))

        self.name_input = TextInput(hint_text="Player names, one per line", multiline=True, size_hint_y=None, height=120)
        self.name_input.text = "Sara"
        layout.add_widget(self.name_input)

        layout.add_widget(Label(text="Starting Balance ($):", font_size=16))
        self.balance_input = TextInput(text="1000", input_filter='int', multiline=False, size_hint_y=None, height=40)
        layout.add_widget(self.balance_input)

        btn = Button(text="Start Game", size_hint_y=None, height=50, background_color=(0, 0.7, 0, 1))
        btn.bind(on_press=self.start_game)
        layout.add_widget(btn)

        self.add_widget(layout)

    def start_game(self, instance):
        names = [n.strip() for n in self.name_input.text.strip().split('\n') if n.strip()]
        if not names:
            self.show_popup("Error", "Enter at least one player name.")
            return
        try:
            balance = int(self.balance_input.text)
            if balance <= 0:
                raise ValueError
        except:
            self.show_popup("Error", "Invalid balance.")
            return

        app = App.get_running_app()
        app.players = names
        app.starting_balance = balance
        self.manager.current = 'game'

    def show_popup(self, title, msg):
        popup = Popup(title=title, content=Label(text=msg), size_hint=(0.8, 0.4))
        popup.open()

# ---------- GAME SCREEN ----------
class GameScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        self.add_widget(self.layout)

    def on_enter(self):
        self.build_ui()

    def build_ui(self):
        self.layout.clear_widgets()
        app = App.get_running_app()
        self.engine = CrapsEngine(app.players)
        for p in self.engine.players:
            p.balance = app.starting_balance

        # Header
        self.layout.add_widget(Label(text="🎲 NJ Craps", font_size=24, color=(1, 0.9, 0, 1)))

        self.shooter_label = Label(text="", font_size=16, color=(0, 1, 1, 1))
        self.point_label = Label(text="", font_size=16, color=(1, 1, 0, 1))
        self.player_label = Label(text="", font_size=18, color=(1, 1, 1, 1))

        self.layout.add_widget(self.shooter_label)
        self.layout.add_widget(self.point_label)
        self.layout.add_widget(self.player_label)

        # Dice
        self.dice_widget = DiceWidget(size_hint_y=None, height=120)
        self.layout.add_widget(self.dice_widget)

        # Wager
        wager_box = BoxLayout(size_hint_y=None, height=45)
        wager_box.add_widget(Label(text="Wager ($):", size_hint_x=0.3))
        self.wager_input = TextInput(text="10", input_filter='int', multiline=False, size_hint_x=0.7)
        wager_box.add_widget(self.wager_input)
        self.layout.add_widget(wager_box)

        # Bet Buttons (Scrollable Grid)
        scroll = ScrollView(size_hint_y=0.5)
        btn_grid = GridLayout(cols=4, spacing=5, size_hint_y=None)
        btn_grid.bind(minimum_height=btn_grid.setter('height'))

        core_bets = [
            ("Pass", "pass"),
            ("DontP", "dont_pass"),
            ("Come", "come"),
            ("DontC", "dont_come"),
            ("Odds", "odds_pass"),
            ("🔥 Fire", "fire"),
        ]
        for label, cmd in core_bets:
            btn = Button(text=label, size_hint_y=None, height=45)
            btn.bind(on_press=lambda x, c=cmd: self.place_bet(c))
            btn_grid.add_widget(btn)

        for num in [4,5,6,8,9,10]:
            for bet_type in ["P", "Buy", "Lay"]:
                label = f"{bet_type}{num}"
                cmd = f"{bet_type.lower()}_{num}"
                btn = Button(text=label, size_hint_y=None, height=40, font_size=12)
                btn.bind(on_press=lambda x, c=cmd: self.place_bet(c))
                btn_grid.add_widget(btn)

        scroll.add_widget(btn_grid)
        self.layout.add_widget(scroll)

        # Action buttons
        action_layout = BoxLayout(size_hint_y=None, height=55, spacing=10)
        self.roll_btn = Button(text="🎲 Roll Dice", background_color=(0.8, 0, 0, 1))
        self.roll_btn.bind(on_press=self.roll_dice)
        export_btn = Button(text="📄 CSV", size_hint_x=0.3)
        export_btn.bind(on_press=self.export_csv)
        action_layout.add_widget(self.roll_btn)
        action_layout.add_widget(export_btn)
        self.layout.add_widget(action_layout)

        self.update_display()

    def place_bet(self, bet_type):
        try:
            amt = int(self.wager_input.text)
            if amt <= 0:
                self.show_popup("Error", "Wager must be positive.")
                return
            p = self.engine.current_shooter.name
            success = False
            if bet_type == "pass":
                success = self.engine.place_pass(p, amt)
            elif bet_type == "dont_pass":
                success = self.engine.place_dont_pass(p, amt)
            elif bet_type == "come":
                success = self.engine.place_come(p, amt)
            elif bet_type == "dont_come":
                success = self.engine.place_dont_come(p, amt)
            elif bet_type == "fire":
                success = self.engine.place_fire(p, amt)
            elif bet_type == "odds_pass":
                success = self.engine.place_odds_pass(p, amt)
            elif bet_type.startswith("place_"):
                num = int(bet_type.split("_")[1])
                success = self.engine.place_place_bet(p, num, amt)
            elif bet_type.startswith("buy_"):
                num = int(bet_type.split("_")[1])
                success = self.engine.place_buy_bet(p, num, amt)
            elif bet_type.startswith("lay_"):
                num = int(bet_type.split("_")[1])
                success = self.engine.place_lay_bet(p, num, amt)
            if success:
                self.update_display()
            else:
                self.show_popup("Bet Failed", "Invalid bet (phase, balance, or rules).")
        except Exception as e:
            self.show_popup("Input Error", f"Invalid wager: {e}")

    def roll_dice(self, instance):
        self.dice_widget.animate_roll()
        def final_roll(dt):
            d1, d2, total = self.engine.roll_dice()
            self.dice_widget.set_dice(d1, d2)
            if self.engine.phase == "come_out":
                self.engine.resolve_come_out(total)
            else:
                self.engine.resolve_point_phase(total)
            self.update_display()
            self.show_popup("Roll", f"{d1} + {d2} = {total}")
        Clock.schedule_once(final_roll, 0.6)

    def update_display(self):
        shooter = self.engine.current_shooter.name
        point = self.engine.point
        balance = self.engine.current_shooter.balance
        self.shooter_label.text = f"Shooter: {shooter}"
        self.point_label.text = f"POINT: {point}" if point else "No Point"
        self.player_label.text = f"{shooter}: ${balance}"

    def export_csv(self, instance):
        if export_log_to_csv():
            self.show_popup("Success", "Log exported to craps_audit.csv")
        else:
            self.show_popup("Warning", "No log found.")

    def show_popup(self, title, msg):
        popup = Popup(title=title, content=Label(text=msg, padding=(10, 10)), size_hint=(0.8, 0.4))
        popup.open()

# ---------- APP ----------
class CrapsMobileApp(App):
    def build(self):
        self.players = []
        self.starting_balance = 1000
        sm = ScreenManager()
        sm.add_widget(SetupScreen(name='setup'))
        sm.add_widget(GameScreen(name='game'))
        return sm

if __name__ == "__main__":
    CrapsMobileApp().run()
