import random
import tkinter as tk
from tkinter import messagebox
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional


# ----------------- Core character classes ----------------- #
class Character:
    def __init__(self, name: str, max_health: int, attack: int):
        self.name = name
        self.max_health = max_health
        self.health = max_health
        self.attack = attack

    def take_damage(self, damage: int) -> int:
        """Apply damage and clamp values. Returns actual damage taken."""
        damage = max(0, int(damage))
        self.health -= damage
        if self.health < 0:
            self.health = 0
        return damage

    def heal(self, amount: int) -> int:
        """Heal up to max health. Returns HP actually restored."""
        amount = max(0, int(amount))
        before = self.health
        self.health = min(self.max_health, self.health + amount)
        return self.health - before

    def is_alive(self) -> bool:
        return self.health > 0


class Player(Character):
    def __init__(self, name: str):
        super().__init__(name=name, max_health=100, attack=20)
        self.level = 1
        self.exp = 0
        self.inventory: Dict[str, int] = {"Medkit": 3}
        self.skill_points = 0

    def exp_to_next_level(self) -> int:
        # Simple progression so you can actually level in a short playthrough
        return 20 + (self.level - 1) * 10

    def add_exp(self, amount: int) -> List[str]:
        """Add XP, handle level-ups, and return log lines."""
        logs = []
        self.exp += amount
        logs.append(f"{self.name} gained {amount} XP.")
        # Handle multiple level-ups if XP is high
        while self.exp >= self.exp_to_next_level():
            self.exp -= self.exp_to_next_level()
            self.level += 1
            self.skill_points += 1
            self.max_health += 10
            self.health = self.max_health
            self.attack += 2
            logs.append(
                f"{self.name} leveled up to {self.level}! "
                f"Max Health +10, Attack +2. Skill points available: {self.skill_points}."
            )
        return logs

    def use_medkit(self) -> str:
        """Try to use a medkit; returns a message summarizing what happened."""
        if self.inventory.get("Medkit", 0) <= 0:
            return "You rummage through your pack... no medkits left!"
        self.inventory["Medkit"] -= 1
        healed = self.heal(30)
        return f"You use a Medkit and recover {healed} health."


class Enemy(Character):
    def __init__(self, name: str, max_health: int, attack: int, exp_reward: int):
        super().__init__(name, max_health, attack)
        self.exp_reward = exp_reward


# ----------------- Story structures ----------------- #
@dataclass
class Option:
    text: str
    kind: str  # "story", "battle", "end"
    target: Optional[str] = None
    enemy_factory: Optional[Callable[[], Enemy]] = None
    end_text: Optional[str] = None


@dataclass
class StoryNode:
    node_id: str
    description: str
    sprite_text: str
    options: List[Option] = field(default_factory=list)


# ----------------- UI Layer ----------------- #
class GameUI:
    """
    Manages the Tkinter window, including:
      - top sprite area (like the 'video' player in your sketch)
      - middle text log box
      - bottom 3 buttons for options / battle actions
    """

    def __init__(self, root: tk.Tk, game: "Game"):
        self.root = root
        self.game = game

        self.root.title("Crashlanding")
        self.root.geometry("900x650")
        self.root.minsize(800, 550)

        # Use a grid so all regions are always visible
        self.root.rowconfigure(0, weight=2)  # top
        self.root.rowconfigure(1, weight=3)  # middle text
        self.root.rowconfigure(2, weight=1)  # bottom buttons
        self.root.rowconfigure(3, weight=0)  # status bar
        self.root.columnconfigure(0, weight=1)

        # Top: sprite / "video" area
        self.top_frame = tk.Frame(self.root, bg="#222222")
        self.top_frame.grid(row=0, column=0, sticky="nsew")
        self.sprite_label = tk.Label(
            self.top_frame,
            text="",
            fg="white",
            bg="#222222",
            font=("Helvetica", 24, "bold"),
            wraplength=760,
            justify="center",
        )
        self.sprite_label.pack(expand=True)

        # Middle: narration / log
        self.mid_frame = tk.Frame(self.root, bg="#111111")
        self.mid_frame.grid(row=1, column=0, sticky="nsew")
        self.mid_frame.rowconfigure(0, weight=1)
        self.mid_frame.columnconfigure(0, weight=1)

        self.text_widget = tk.Text(
            self.mid_frame,
            wrap="word",
            state="disabled",
            bg="#111111",
            fg="white",
            font=("Helvetica", 12),
        )
        self.text_widget.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # Bottom: 3 option buttons (wider & taller, text wraps to 2 lines)
        self.bottom_frame = tk.Frame(self.root, bg="#333333")
        self.bottom_frame.grid(row=2, column=0, sticky="nsew")
        self.bottom_frame.columnconfigure(0, weight=1, minsize=260)
        self.bottom_frame.columnconfigure(1, weight=1, minsize=260)
        self.bottom_frame.columnconfigure(2, weight=1, minsize=260)

        self.option_buttons: List[tk.Button] = []
        for i in range(3):
            btn = tk.Button(
                self.bottom_frame,
                text=f"Option {i+1}",
                command=lambda idx=i: self._on_button_click(idx),
                font=("Helvetica", 12, "bold"),
                padx=10,
                pady=15,
                wraplength=220,   # makes long text wrap onto two lines
                justify="center",
            )
            btn.grid(row=0, column=i, padx=20, pady=20, sticky="nsew")
            self.option_buttons.append(btn)

        # callbacks for buttons
        self.button_callbacks: List[Optional[Callable[[], None]]] = [None, None, None]

        # status bar
        self.status_label = tk.Label(
            self.root,
            text="",
            anchor="w",
            bg="#000000",
            fg="white",
            font=("Helvetica", 10),
        )
        self.status_label.grid(row=3, column=0, sticky="ew")

    def _on_button_click(self, idx: int):
        cb = self.button_callbacks[idx]
        if cb:
            cb()

    def update_status_bar(self):
        player = self.game.player
        hp_str = f"HP: {player.health}/{player.max_health}"
        xp_str = f"LV {player.level}  XP: {player.exp}/{player.exp_to_next_level()}"
        medkits = player.inventory.get("Medkit", 0)
        self.status_label.config(
            text=f"{player.name} | {hp_str} | {xp_str} | Medkits: {medkits}"
        )

    def set_scene(
        self,
        sprite_text: str,
        main_text: str,
        options: List[tuple],
    ):
        """
        Set the main scene.

        options: list of (button_text, callback) tuples.
        """
        self.sprite_label.config(text=sprite_text)
        self._set_text(main_text)

        # clear callbacks
        self.button_callbacks = [None, None, None]

        # configure buttons
        for i in range(3):
            if i < len(options):
                text, cb = options[i]
                self.option_buttons[i].config(text=text, state=tk.NORMAL)
                self.button_callbacks[i] = cb
            else:
                self.option_buttons[i].config(text="---", state=tk.DISABLED)
                self.button_callbacks[i] = None

        self.update_status_bar()

    def append_log_and_show_options(
        self, sprite_text: str, extra_log: List[str], options: List[tuple]
    ):
        """Append log lines to the existing text, then show options."""
        history = self._get_text()
        new_text = history + "\n" + "\n".join(extra_log) if history else "\n".join(extra_log)
        self.set_scene(sprite_text, new_text, options)

    def _set_text(self, text: str):
        self.text_widget.config(state="normal")
        self.text_widget.delete("1.0", tk.END)
        self.text_widget.insert("1.0", text)
        self.text_widget.config(state="disabled")

    def _get_text(self) -> str:
        return self.text_widget.get("1.0", tk.END).strip()

    def game_over(self, text: str):
        """Show a game-over screen and disable further input."""
        self.set_scene("Game Over", text, [])
        messagebox.showinfo("Game Over", text)
        for btn in self.option_buttons:
            btn.config(state=tk.DISABLED)


# ----------------- Game controller ----------------- #
class Game:
    def __init__(self, root: tk.Tk):
        self.player = Player("Astronaut")
        self.ui = GameUI(root, self)

        self.story_nodes: Dict[str, StoryNode] = {}
        self._build_story()

        self.current_node_id: Optional[str] = None
        self.current_enemy: Optional[Enemy] = None
        self.victory_target: Optional[str] = None
        self.battle_log: List[str] = []

        # flags to prevent repeated farming of events
        self.flags: Dict[str, bool] = {
            "wreckage_looted": False,
            "rest1_healed": False,
            "camp_good_healed": False,
        }

    def start(self):
        self.go_to_node("intro")

    # ----- Story setup ----- #
    def _build_story(self):
        # Intro node
        self.story_nodes["intro"] = StoryNode(
            node_id="intro",
            description=(
                "Alarms blare as your pod tears through the atmosphere. "
                "You slam into the alien soil, alive but shaken.\n\n"
                "Smoke curls from the wreckage. The sky is a deep violet, "
                "and strange silhouettes move in the distance."
            ),
            sprite_text="Crash Site",
            options=[
                Option(
                    text="Check the crash site for supplies.",
                    kind="story",
                    target="wreckage",
                ),
                Option(
                    text="Head toward the glowing forest.",
                    kind="story",
                    target="forest_edge",
                ),
                Option(
                    text="Climb a nearby ridge to scan for rescue.",
                    kind="story",
                    target="ridge",
                ),
            ],
        )

        # Wreckage node
        self.story_nodes["wreckage"] = StoryNode(
            node_id="wreckage",
            description=(
                "You search the twisted metal of your pod.\n"
                "You find a half-burned medkit case and salvage one more usable Medkit."
            ),
            sprite_text="Twisted Wreckage",
            options=[
                Option(
                    text="Return to the clearing.",
                    kind="story",
                    target="intro",
                ),
                Option(
                    text="Head toward the glowing forest.",
                    kind="story",
                    target="forest_edge",
                ),
                Option(
                    text="Rest for a moment to gather your thoughts.",
                    kind="story",
                    target="rest1",
                ),
            ],
        )

        # Forest edge node (first battle options)
        self.story_nodes["forest_edge"] = StoryNode(
            node_id="forest_edge",
            description=(
                "Bioluminescent trees hum softly as you approach the forest edge.\n"
                "A low growl vibrates through the air—something is watching you."
            ),
            sprite_text="Glowing Forest Edge",
            options=[
                Option(
                    text="Call out, trying to sound friendly.",
                    kind="battle",
                    enemy_factory=lambda: Enemy(
                        "Tusked Frog", max_health=50, attack=12, exp_reward=25
                    ),
                    target="post_frog",
                ),
                Option(
                    text="Slowly back away toward the ridge.",
                    kind="story",
                    target="ridge",
                ),
                Option(
                    text="Charge into the forest, weapon raised.",
                    kind="battle",
                    enemy_factory=lambda: Enemy(
                        "Forest Stalker", max_health=60, attack=14, exp_reward=30
                    ),
                    target="post_frog",
                ),
            ],
        )

        # Ridge node
        self.story_nodes["ridge"] = StoryNode(
            node_id="ridge",
            description=(
                "From the ridge, you see storm clouds forming on the horizon.\n"
                "Your distress beacon might punch through the interference if powered."
            ),
            sprite_text="Windy Ridge",
            options=[
                Option(
                    text="Rig the beacon using pod batteries.",
                    kind="story",
                    target="beacon_online",
                ),
                Option(
                    text="Return to the crash site.",
                    kind="story",
                    target="intro",
                ),
                Option(
                    text="Descend on the far side, toward a shadowed valley.",
                    kind="story",
                    target="deep_valley",
                ),
            ],
        )

        # Rest node (small heal)
        self.story_nodes["rest1"] = StoryNode(
            node_id="rest1",
            description=(
                "You sit on a cracked piece of hull and steady your breathing.\n"
                "Your injuries knit together slightly."
            ),
            sprite_text="Quiet Moment",
            options=[
                Option(
                    text="Head toward the forest.",
                    kind="story",
                    target="forest_edge",
                ),
                Option(
                    text="Climb to the ridge.",
                    kind="story",
                    target="ridge",
                ),
                Option(
                    text="Search the wreckage one last time.",
                    kind="story",
                    target="wreckage",
                ),
            ],
        )

        # After first battle
        self.story_nodes["post_frog"] = StoryNode(
            node_id="post_frog",
            description=(
                "The creature collapses, its tusks sinking into the moss.\n"
                "You catch your breath and notice a cluster of edible-looking pods nearby."
            ),
            sprite_text="Clearing After Battle",
            options=[
                Option(
                    text="Harvest the pods for food.",
                    kind="story",
                    target="food_found",
                ),
                Option(
                    text="Press deeper into the forest.",
                    kind="story",
                    target="deep_forest",
                ),
                Option(
                    text="Head back to the ridge with new confidence.",
                    kind="story",
                    target="ridge",
                ),
            ],
        )

        self.story_nodes["food_found"] = StoryNode(
            node_id="food_found",
            description=(
                "You carefully collect the pods. They smell sweet and your scanner "
                "flags them as safe.\nYou won't starve tonight."
            ),
            sprite_text="Foraged Supplies",
            options=[
                Option(
                    text="Return to the ridge to focus on rescue.",
                    kind="story",
                    target="beacon_online",
                ),
                Option(
                    text="Make a small camp in the forest.",
                    kind="story",
                    target="camp_good",
                ),
                Option(
                    text="Head back to the crash site.",
                    kind="story",
                    target="intro",
                ),
            ],
        )

        # Deep forest with carnivorous plant battle
        self.story_nodes["deep_forest"] = StoryNode(
            node_id="deep_forest",
            description=(
                "The forest grows denser. Strange eyes glint between the trunks, "
                "but none approach.\nYou feel like you've stepped into an ancient cathedral "
                "of bioluminescent branches."
            ),
            sprite_text="Deep Forest",
            options=[
                Option(
                    text="Investigate a patch of red, pulsing flowers.",
                    kind="battle",
                    enemy_factory=lambda: Enemy(
                        "Carnivorous Bloom", max_health=70, attack=15, exp_reward=35
                    ),
                    target="post_plant",
                ),
                Option(
                    text="Return toward the crash site while you still remember the way.",
                    kind="story",
                    target="intro",
                ),
                Option(
                    text="Circle around toward the ridge, marking trees as you go.",
                    kind="story",
                    target="ridge",
                ),
            ],
        )

        self.story_nodes["post_plant"] = StoryNode(
            node_id="post_plant",
            description=(
                "The last of the plant's tendrils curl and blacken.\n"
                "Hidden among its roots you find mineral nodules—perfect power cells."
            ),
            sprite_text="Wilting Clearing",
            options=[
                Option(
                    text="Use the power cells to supercharge your beacon at the ridge.",
                    kind="story",
                    target="beacon_online",
                ),
                Option(
                    text="Carry the cells back to camp and store them.",
                    kind="story",
                    target="camp_good",
                ),
                Option(
                    text="Press even deeper into the forest, hunting for more secrets.",
                    kind="story",
                    target="forest_depths",
                ),
            ],
        )

        self.story_nodes["forest_depths"] = StoryNode(
            node_id="forest_depths",
            description=(
                "Here the air is thick with spores. Massive trees arch overhead, "
                "their roots forming natural tunnels.\n"
                "You realize this place could hide you from almost anything."
            ),
            sprite_text="Forest Depths",
            options=[
                Option(
                    text="Claim this area as your permanent home.",
                    kind="end",
                    end_text=(
                        "You map out caverns among the roots and learn which spores to avoid.\n"
                        "Seasons pass. You become a legend in the forest, a ghost the "
                        "wildlife fears.\n\nYou survive, not because of rescue—"
                        "but because you adapted."
                    ),
                ),
                Option(
                    text="Return to your earlier camp with new knowledge.",
                    kind="story",
                    target="camp_good",
                ),
                Option(
                    text="Head back toward the ridge to attempt rescue.",
                    kind="story",
                    target="beacon_online",
                ),
            ],
        )

        # Deep valley with alien animal battle
        self.story_nodes["deep_valley"] = StoryNode(
            node_id="deep_valley",
            description=(
                "You descend into a shadowed valley. The air is cold and thin.\n"
                "A metallic glint catches your eye—a derelict alien probe half-buried in ice.\n"
                "As you step closer, something moves between the rocks."
            ),
            sprite_text="Shadowed Valley",
            options=[
                Option(
                    text="Approach the probe cautiously.",
                    kind="battle",
                    enemy_factory=lambda: Enemy(
                        "Valley Hunter", max_health=75, attack=16, exp_reward=40
                    ),
                    target="probe_salvaged",
                ),
                Option(
                    text="Leave it and head to the forest instead.",
                    kind="story",
                    target="forest_edge",
                ),
                Option(
                    text="Camp here for the night despite the chill.",
                    kind="end",
                    end_text=(
                        "The valley's chill saps your strength.\n"
                        "By morning, your body cannot fight the cold. "
                        "Your story ends here—frozen beneath alien stars."
                    ),
                ),
            ],
        )

        self.story_nodes["probe_salvaged"] = StoryNode(
            node_id="probe_salvaged",
            description=(
                "With the valley beast driven off, you examine the probe.\n"
                "Its core contains a compact power array and a functioning transmitter dish."
            ),
            sprite_text="Alien Probe",
            options=[
                Option(
                    text="Carry the salvaged tech back up to the ridge beacon.",
                    kind="story",
                    target="beacon_online",
                ),
                Option(
                    text="Drag the probe toward the forest to study later.",
                    kind="story",
                    target="deep_forest",
                ),
                Option(
                    text="Use the probe's casing to reinforce a shelter here.",
                    kind="end",
                    end_text=(
                        "You build a reinforced bunker out of probe plating.\n"
                        "The valley is harsh, but nothing gets through your defenses.\n"
                        "You live alone, but unbroken."
                    ),
                ),
            ],
        )

        self.story_nodes["beacon_online"] = StoryNode(
            node_id="beacon_online",
            description=(
                "With shaking hands you wire the beacon to alien parts and pod batteries.\n"
                "A piercing signal cuts through the thick clouds.\n\n"
                "Hours later, a silhouette appears in the sky—rescue has arrived."
            ),
            sprite_text="Rescue Incoming",
            options=[
                Option(
                    text="Signal frantically and prepare for pickup.",
                    kind="end",
                    end_text=(
                        "The shuttle sets down in a cloud of dust.\n"
                        "You're whisked aboard, battered but alive.\n\n"
                        "You survived Crashlanding. For now."
                    ),
                ),
                Option(
                    text="Refuse rescue and stay to study the planet.",
                    kind="end",
                    end_text=(
                        "You mute the beacon and watch the shuttle arc away.\n"
                        "This world tried to kill you, but it also feels like a beginning.\n"
                        "You choose to stay and build a new life here."
                    ),
                ),
                Option(
                    text="Ask them to send supplies, not extraction.",
                    kind="end",
                    end_text=(
                        "You negotiate over the comms: supplies only.\n"
                        "A cache of tools and rations drops through the clouds.\n"
                        "With help from above and grit below, you carve out a future."
                    ),
                ),
            ],
        )

        self.story_nodes["camp_good"] = StoryNode(
            node_id="camp_good",
            description=(
                "You establish a small, hidden camp using scraps from the pod and "
                "forest materials.\n"
                "It's not much, but it's home—for now."
            ),
            sprite_text="Hidden Camp",
            options=[
                Option(
                    text="Focus on improving the camp for long-term survival.",
                    kind="end",
                    end_text=(
                        "Days turn into weeks as you refine your camp.\n"
                        "You master the local wildlife, forage safely, and sleep under "
                        "alien constellations.\n\n"
                        "Rescue may come someday, but you no longer depend on it."
                    ),
                ),
                Option(
                    text="Use the camp as a base while you fix the beacon.",
                    kind="story",
                    target="beacon_online",
                ),
                Option(
                    text="Abandon the camp and roam freely.",
                    kind="end",
                    end_text=(
                        "You decide never to stay in one place.\n"
                        "You become a wanderer, a ghost among the purple trees.\n"
                        "The planet is dangerous—but it's yours."
                    ),
                ),
            ],
        )

    # ----- Story navigation and passive effects ----- #
    def go_to_node(self, node_id: str):
        node = self.story_nodes[node_id]
        self.current_node_id = node_id

        extra_logs: List[str] = []
        # Simple built-in effects when visiting certain nodes (one-time)
        if node_id == "wreckage":
            if not self.flags["wreckage_looted"]:
                self.player.inventory["Medkit"] = self.player.inventory.get("Medkit", 0) + 1
                extra_logs.append("You gain +1 Medkit from the wreckage.")
                self.flags["wreckage_looted"] = True
            else:
                extra_logs.append("You've already salvaged everything useful here.")
        elif node_id == "rest1":
            if not self.flags["rest1_healed"]:
                healed = self.player.heal(15)
                extra_logs.append(f"You feel a bit better. (+{healed} HP)")
                self.flags["rest1_healed"] = True
            else:
                extra_logs.append("You've already rested here; your body aches to keep moving.")
        elif node_id == "camp_good":
            if not self.flags["camp_good_healed"]:
                healed = self.player.heal(20)
                extra_logs.append(f"Resting at camp restores your strength. (+{healed} HP)")
                self.flags["camp_good_healed"] = True
            else:
                extra_logs.append("The camp feels familiar now, but offers no new comfort.")

        main_text = node.description
        if extra_logs:
            main_text += "\n\n" + "\n".join(extra_logs)

        options = [(opt.text, self._make_option_handler(opt)) for opt in node.options]
        self.ui.set_scene(node.sprite_text, main_text, options)

    def _make_option_handler(self, option: Option) -> Callable[[], None]:
        def handler():
            if option.kind == "story":
                if option.target is not None:
                    self.go_to_node(option.target)
            elif option.kind == "battle":
                if option.enemy_factory:
                    self.start_battle(option.enemy_factory(), option.target)
            elif option.kind == "end":
                text = option.end_text or "The story ends."
                self.ui.game_over(text)

        return handler

    # ----- Battle system ----- #
    def start_battle(self, enemy: Enemy, victory_target: Optional[str]):
        self.current_enemy = enemy
        self.victory_target = victory_target
        self.battle_log = [
            f"A hostile {enemy.name} appears!",
            "Choose your action:",
        ]
        self._show_battle_scene()

    def _show_battle_scene(self):
        if not self.current_enemy:
            return
        enemy = self.current_enemy
        sprite_text = f"{self.player.name} vs {enemy.name}"
        battle_status = (
            f"{self.player.name} HP: {self.player.health}/{self.player.max_health}\n"
            f"{enemy.name} HP: {enemy.health}/{enemy.max_health}\n\n"
            + "\n".join(self.battle_log)
        )
        options = [
            ("Quick Attack", lambda: self.player_action("quick")),
            ("Heavy Attack", lambda: self.player_action("heavy")),
            ("Use Medkit", lambda: self.player_action("medkit")),
        ]
        self.ui.set_scene(sprite_text, battle_status, options)

    def player_action(self, action: str):
        if not self.current_enemy or not self.player.is_alive():
            return

        enemy = self.current_enemy
        logs: List[str] = []

        # Player turn
        if action == "quick":
            base = self.player.attack
            dmg = random.randint(base - 5, base + 5)
            dmg = enemy.take_damage(dmg)
            logs.append(f"You strike quickly for {dmg} damage!")
        elif action == "heavy":
            base = int(self.player.attack * 1.5)
            if random.random() < 0.6:  # 60% chance to hit
                dmg = random.randint(base - 5, base + 5)
                dmg = enemy.take_damage(dmg)
                logs.append(f"You commit to a heavy blow for {dmg} damage!")
            else:
                logs.append("You swing hard—but the enemy dodges!")
        elif action == "medkit":
            result = self.player.use_medkit()
            logs.append(result)
        else:
            logs.append("You hesitate and lose your chance to act.")

        # Check for victory
        if not enemy.is_alive():
            logs.append(f"The {enemy.name} is defeated!")
            logs.extend(self.player.add_exp(enemy.exp_reward))
            self.current_enemy = None

            # After victory, return to story
            target = self.victory_target or self.current_node_id or "intro"
            self.ui.append_log_and_show_options(
                sprite_text="Battle Won",
                extra_log=logs,
                options=[("Continue...", lambda: self.go_to_node(target))],
            )
            return

        # Enemy's turn if still alive
        self.battle_log = logs
        self.enemy_turn()

    def enemy_turn(self):
        if not self.current_enemy or not self.player.is_alive():
            return
        enemy = self.current_enemy
        logs = self.battle_log

        base = enemy.attack
        dmg = random.randint(base - 3, base + 3)
        dmg = self.player.take_damage(dmg)
        logs.append(f"The {enemy.name} attacks and deals {dmg} damage!")

        if not self.player.is_alive():
            logs.append("You collapse. The world fades to black.")
            self.ui.game_over("\n".join(logs))
            return

        logs.append("What will you do next?")
        self.battle_log = logs
        self._show_battle_scene()


# ----------------- Entry point ----------------- #
def main():
    root = tk.Tk()
    game = Game(root)
    game.start()
    root.mainloop()


if __name__ == "__main__":
    main()
