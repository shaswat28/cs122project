import random

class Character:
    def __init__(self, name, health, attack):
        self.name = name
        self.health = health
        self.attack = attack

    def take_damage(self, damage):
        self.health -= damage
        if self.health < 0:
            self.health = 0

    def is_alive(self):
        return self.health > 0

    def display_status(self):
        print(f"{self.name}: Health - {self.health}")

def battle(player, enemy):
    print(f"\n--- {player.name} vs {enemy.name} ---")
    while player.is_alive() and enemy.is_alive():
        # player turn
        print(f"\n{player.name}'s Turn:")
        player.display_status()
        enemy.display_status()
        
        action = input("Enter 'attack' to attack: ").lower()
        if action == "attack":
            damage_dealt = random.randint(player.attack - 5, player.attack + 5) # some randomness in attack
            enemy.take_damage(damage_dealt)
            print(f"{player.name} attacks {enemy.name} for {damage_dealt} damage!")
        else:
            print("Invalid action. You lose your turn.")
        
        if not enemy.is_alive():
            print(f"\n{enemy.name} has been defeated! {player.name} wins!")
            break

        # enemy turn
        print(f"\n{enemy.name}'s Turn:")
        damage_taken = random.randint(enemy.attack - 3, enemy.attack + 3)
        player.take_damage(damage_taken)
        print(f"{enemy.name} attacks {player.name} for {damage_taken} damage!")

        if not player.is_alive():
            print(f"\n{player.name} has been defeated! {enemy.name} wins!")
            break

#setup
player_char = Character("Astronaut", 100, 20)
frog1 = Character("Tusked Frog", 50, 10)

# Start the battle
battle(player_char, frog1)


