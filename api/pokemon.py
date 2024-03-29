import math
import random

from api.move import Move
from api.nature import Nature, natures
from api.type import Type
from api.evolution_chain import EvolutionChain
from api.util import utils, dl_utils

pokemon_data = {}
"""This can be filled with pokemon from the outside, for example using IOUtils.load_all_pokemon()"""


class Pokemon:
    """Contains all data and methods needed for a Pokemon."""

    def __init__(self, name: str, base_stats=[0, 0, 0, 0, 0, 0], types=[Type('normal')], index=-1):
        """
        Will attempt to load the Pokemon specified by 'name' out of 'pokemon_data'.
        If no matching Pokemon could be found, a new Pokemon is created.
        """
        raw = pokemon_data.get(name.replace(' ', '-').lower())
        if raw is None:  # Attempt download
            raw = dl_utils.get_pokemon(name)
        self.evolves_to = {}
        self.types = []
        self.abilities = []
        if raw is not None:
            self.id = raw['id']
            self.name = raw['name'].replace('-', ' ').title()
            self.base_stats = raw['base_stats']
            for t in raw['types']:
                self.types.append(Type(t))
            self.abilities = raw['abilities']
            self.base_experience = raw['base_xp']
            self.growth_rate = raw['growth_rate']
            self.moves = raw['moves']
            self.evolution_chain = EvolutionChain(raw['evolution_chain_id'])
            self.evolution_chain.set_stage(raw['name'])
            if self.evolution_chain.stage == 0:
                self.evolves_to = self.evolution_chain.stage_1_evolutions
            elif self.evolution_chain.stage == 1:
                self.evolves_to = self.evolution_chain.stage_2_evolutions
            self.base_happiness = raw['base_happiness']
            self.capture_rate = raw['capture_rate']
            self.gender_rate = raw['gender_rate']
            self.hatch_counter = raw['hatch_counter']
        else:
            # If no pokemon in the database matched the request, these values can
            # be set manually or automatically using the constructor parameters.
            # This gives the user the ability to create completely new pokemon.
            utils.log('No custom Pokemon found. Creating a new Pokemon.')
            self.id = index
            self.name = name.replace('-', ' ').title()
            self.base_stats = base_stats
            self.types = types
            self.abilities = []
            self.base_experience = 0
            self.growth_rate = 'slow'
            self.moves = []
            self.evolution_chain = EvolutionChain(-1)
            self.base_happiness = 70
            self.capture_rate = 45
            self.gender_rate = 4
            self.hatch_counter = 20
        # These are values that can be different for each pokemon of a species
        self.level = 1
        self.ivs = [0, 0, 0, 0, 0, 0]
        self.evs = [0, 0, 0, 0, 0, 0]
        self.nature = Nature('hardy')
        self.stats = [0, 0, 0, 0, 0, 0]
        self.current_moves = []
        for m in self.moves:
            if m['level_learned_at'] == self.level:
                if len(self.current_moves) < 4:
                    self.current_moves.append(Move(m['name']))
                else:
                    self.current_moves[random.randint(0, 3)] = Move(m['name'])
        self.current_xp = self.calculate_xp(self.level)
        self.current_stats = [0, 0, 0, 0, 0, 0]  # Values that are needed in battle
        self.calculate_stats()
        self.heal()  # Set current stats

    def set_level(self, level: int):
        """Set the pokemon's level and automatically recalculate stats."""
        self.level = level
        self.calculate_stats()
        # The following lines ensure that a Pokemon's current stats are recalculated upon the level up,
        # but the missing hp (if any) are not restored. This way, a hit pokemon won't magically heal
        # when it levels up.
        hp_diff = self.stats[0] - self.current_stats[0]  # If the is at full hp, this will be 0
        self.heal()
        self.current_stats[0] -= hp_diff

    def add_xp(self, amount: int):
        """Add 'amount' xp to current_xp, calculate if there are any level ups, and check for any level up moves."""
        self.current_xp += amount
        old_stats = []
        for i in self.stats:
            old_stats.append(i)
        stat_diff = [0, 0, 0, 0, 0, 0]
        old_level = self.level
        new_level = self.level
        while (self.current_xp > self.calculate_xp(new_level)) and (new_level < 100):
            new_level += 1
        for i in range(0, new_level - old_level):
            self.set_level(self.level + 1)
            print(f'{self.name} reached Level {str(self.level)}! (', end='')
            for j in range(0, 6):
                stat_diff[j] = self.stats[j] - old_stats[j]
                print(f'+{str(stat_diff[j])}', end='')
                if j < 5: print(', ', end='')
            print(')')
            if self.evolution_chain.stage != 2:
                self.try_level_evolution()
            for j in range(0, 6):
                old_stats[j] = self.stats[j]
            for m in self.moves:
                if m['level_learned_at'] == self.level:
                    move = Move(m['name'])
                    if len(self.current_moves) == 4:
                        replace = 5
                        print(f'{self.name} wants to learn {move.name}, but it already knows 4 Moves:')
                        print(f'{self.current_moves[0].name}, {self.current_moves[1].name}, '
                              f'{self.current_moves[2].name}, {self.current_moves[3].name}')
                        while 1:
                            try:
                                _in = input('Please specify which move shall be forgotten(1-4), '
                                            'leave empty if no move should be forgotten: ')
                                if _in != '':
                                    replace = int(_in)
                                else:
                                    replace = None
                                if (replace is None) or (1 <= replace <= 4):
                                    break
                            except ValueError:
                                pass
                            print('Invalid Input!')
                        if replace is not None:
                            print(f'{self.name} forgot {self.current_moves[replace - 1].name} and learned {move.name}!')
                            self.current_moves[replace - 1] = move
                        else:
                            print(f'{self.name} did not learn {move.name}.')
                    else:
                        self.current_moves.append(move)
                        print(f'{self.name} learned {move.name}!')

    def set_ev(self, index: int, value: int):
        """Set the pokemon's evs and automatically recalculate stats."""
        self.evs[index] = value
        self.calculate_stats()

    def calculate_xp(self, level: int):
        """Calculate the amount of xp needed for the level 'level'"""
        if self.growth_rate == 'slow-then-very-fast':
            if level <= 1:
                return 0
            elif (level > 1) and (level <= 50):
                return math.floor((level ** 3) * ((100 - level) / 50))
            elif (level > 50) and (level <= 68):
                return math.floor((level ** 3) * ((150 - level) / 100))
            elif (level > 68) and (level <= 98):
                return math.floor((level ** 3) * (math.floor((1911 - 10 * level) / 3) / 500))
            else:
                return math.floor((level ** 3) * ((160 - level) / 100))
        elif self.growth_rate == 'fast':
            if level <= 1:
                return 0
            else:
                return math.floor((4 * (level ** 3)) / 5)
        elif self.growth_rate == 'medium-fast':
            return level ** 3
        elif self.growth_rate == 'medium-slow':
            if level <= 1:
                return 0
            else:
                return math.floor(((6 / 5) * (level ** 3)) - (15 * (level ** 2)) + (100 * level) - 140)
        elif self.growth_rate == 'slow':
            if level <= 1:
                return 0
            else:
                return math.floor((5 * (level ** 3)) / 4)
        elif self.growth_rate == 'fast-then-very-slow':
            if level <= 1:
                return 0
            elif (level > 1) and (level <= 15):
                return math.floor((level ** 3) * ((24 + math.floor((level + 1) / 3)) / 50))
            elif (level > 15) and (level <= 36):
                return math.floor((level ** 3) * ((14 + level) / 50))
            else:
                return math.floor((level ** 3) * ((32 + math.floor(level / 2)) / 50))

    def battle_xp(self, other):
        """Calculate the xp that the pokemon gets for defeating the pokemon 'other'"""
        return math.floor(((other.base_experience * other.level) / 5) *
                          (((2 * other.level + 10) ** 2.5) / ((other.level + self.level + 10) ** 2.5)) + 1)

    def try_level_evolution(self):
        """Check if min_level in evolves_to is sufficient and attempt an evolution"""
        if self.evolution_chain.stage == 2:
            return
        evolution_name = ''
        try:
            evolution_name = list(self.evolves_to.keys())[0]
        except IndexError:
            pass
        evolution_level = 0
        try:
            evolution_level = self.evolves_to[evolution_name]['min_level']
        except KeyError:
            pass
        if (self.level >= evolution_level) and (evolution_level != 0):
            confirmation = ''
            while (confirmation.lower() != 'a') or (confirmation.lower() != 'b'):
                try:
                    confirmation = input(self.name + ' is evolving! Type b to abort, leave empty to continue: ')
                    if (confirmation.lower() == '') or (confirmation.lower() == 'b'):
                        break
                except ValueError:
                    pass
                print('Invalid Input!')
            if confirmation == '':
                # perform evolution
                old_name = self.name
                evolution = Pokemon(evolution_name)
                evolution.name.replace('-', ' ').title()
                evolution.current_xp = self.current_xp
                evolution.current_moves = self.current_moves
                evolution.ivs = self.ivs
                evolution.evs = self.evs
                evolution.nature = self.nature
                evolution.set_level(self.level)
                self.__dict__ = evolution.__dict__
                print(f'Congratulations! Your {old_name} evolved into {self.name}!')
                return
            print(f'{self.name} did not evolve.')

    def print(self):
        """Print formatted information about the Pokemon species on the screen."""
        print('_' * 56)
        types = self.types[0].name.capitalize()
        if len(self.types) > 1: types += (', ' + self.types[1].name.capitalize())
        print('{:<20} {:>35}'.format(self.name, types))
        print('\nBase Stats:')
        for stat in self.base_stats:
            i = math.ceil(stat / 5)
            print('█' * i + '░' * (51 - i) + ' ' + str(stat))
        print(f'Total: {str(sum(self.base_stats))}')
        print('_' * 56)

    # ========== FUNCTIONS FOR CALCULATING & GENERATING ================================================================

    def calculate_stats(self):
        """calculate the stats of the pokemon using the base_stats, ivs, evs, level and nature."""
        self.stats[0] = math.floor(
            ((2 * self.base_stats[0] + self.ivs[0] + math.floor(self.evs[0] / 4)) * self.level) / 100) + self.level + 10
        for x in range(1, 6):
            self.stats[x] = math.floor(
                (((2 * self.base_stats[x] + self.ivs[x] + math.floor(self.evs[x] / 4)) * self.level) / 100) + 5)
            if x == self.nature.increased_stat:
                self.stats[x] = math.floor(self.stats[x] * 1.1)
            elif x == self.nature.decreased_stat:
                self.stats[x] = math.floor(self.stats[x] * 0.9)

    def generate_ivs(self):
        """Randomly generate all IVs for the pokemon."""
        for x in range(0, 6):
            self.ivs[x] = random.randint(0, 31)
        self.calculate_stats()

    def generate_nature(self):
        """Randomly generate a nature."""
        self.nature = Nature(natures[random.randint(0, len(natures) - 1)])
        self.calculate_stats()

    def generate(self):
        """All-In-One method for generating all required values for a new pokemon."""
        self.generate_ivs()
        self.generate_nature()
        self.calculate_stats()
        self.heal()

    # ========== FUNCTIONS FOR USE IN & AFTER BATTLE ===================================================================

    def heal(self):
        """Reset current stats to the value of the stats."""
        self.current_stats = self.stats

    def attack(self, other, move:  Move):
        """Perform an attack against a Pokemon 'other' using the Move 'move'."""
        print(f'{self.name} used {move.name}!')
        if random.randint(1, 100) > move.accuracy:
            print(f'The opposing {other.name} avoided the attack!')
            return
        damage = math.floor(self.level * 2 / 5) + 2
        damage *= move.power
        if move.damage_class == 'special':
            damage *= self.current_stats[3] / (50 * other.current_stats[4])
        else:
            damage *= self.current_stats[1] / (50 * other.current_stats[2])
        damage = math.floor(damage)
        damage += 2
        critical = (1.5 if random.randint(1, 100) < 7 else 1)  # Critical chance is set to 6% for now
        if critical > 1: print('A critical hit!')
        damage *= critical
        damage = math.floor(damage)
        damage *= (random.randint(85, 100) / 100)
        damage = math.floor(damage)
        if len(self.types) == 1:
            if self.types[0].name == move.type.name:
                damage *= 1.5
        elif (self.types[0].name == move.type.name) or (self.types[1].name == move.type.name):
            damage *= 1.5
        damage = math.floor(damage)
        effectivity = move.get_effectivity(other)
        damage *= effectivity
        if effectivity >= 2:
            print('It\'s super effective!')
        elif effectivity < 1:
            print('It\'s not very effective...')
        elif effectivity == 0:
            print(f'It doesn\'t affect the opposing {other.name}...')
        damage = math.floor(damage)
        if damage > other.current_stats[0]: damage = other.current_stats[0]
        print(f'The opposing {other.name} lost {str(math.floor((damage / other.stats[0]) * 100))}% ({str(damage)} HP) '
              f'of it\'s health!')
        other.current_stats[0] -= damage
