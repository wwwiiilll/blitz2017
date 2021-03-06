import sys
from collections import defaultdict

MAXINT = 2 ** 32 - 1

TAVERN = 0
AIR = -1
WALL = -2
SPIKE = -3
CUSTOMER = -4

PLAYER1 = 1
PLAYER2 = 2
PLAYER3 = 3
PLAYER4 = 4

AIM = {'North': (-1, 0),
       'East': (0, 1),
       'South': (1, 0),
       'West': (0, -1)}


class HeroTile:
    def __init__(self, id):
        self.id = int(id)


class CustomerTile:
    def __init__(self, id):
        self.id = int(id)


class FriesTile:
    def __init__(self, hero_id=None):
        self.hero_id = int(-1 if hero_id == "-" else hero_id)


class BurgerTile:
    def __init__(self, hero_id=None):
        self.hero_id = int(-1 if hero_id == "-" else hero_id)


class Game:
    def __init__(self, state):
        self.state = state
        self.board = Board(state['game']['board'])
        self.heroes = [Hero(state['game']['heroes'][i]) for i in range(len(state['game']['heroes']))]
        self.customers = [Customer(state['game']['customers'][i]) for i in range(len(state['game']['customers']))]
        self.fries_locs = {}
        self.burger_locs = {}
        self.heroes_locs = {}
        self.taverns_locs = set()
        self.spikes_locs = set()
        self.customers_locs = {}
        self.me = Hero(state['hero'])
        for row in range(len(self.board.tiles)):
            for col in range(len(self.board.tiles[row])):
                obj = self.board.tiles[row][col]
                if isinstance(obj, FriesTile):
                    self.fries_locs[(row, col)] = int(obj.hero_id)
                if isinstance(obj, BurgerTile):
                    self.burger_locs[(row, col)] = int(obj.hero_id)
                elif isinstance(obj, HeroTile):
                    self.heroes_locs[(row, col)] = int(obj.id)
                elif obj == TAVERN:
                    self.taverns_locs.add((row, col))
                elif obj == SPIKE:
                    self.spikes_locs.add((row, col))
                elif isinstance(obj, CustomerTile):
                    self.customers_locs[(row, col)] = int(obj.id ==  (-1 if obj.id == '-' else obj.id))


class Board:
    def __parseTile(self, tile_string):
        if tile_string == '  ':
            return AIR
        if tile_string == '##':
            return WALL
        if tile_string == '[]':
            return TAVERN
        if tile_string == '^^':
            return SPIKE
        if tile_string[0] == 'F':
            return FriesTile(tile_string[1])
        if tile_string[0] == 'B':
            return BurgerTile(tile_string[1])
        if tile_string[0] == '@':
            return HeroTile(tile_string[1])
        if tile_string[0] == 'C':
            return CustomerTile(tile_string[1])

    def __parseTiles(self, tiles):
        vector = [tiles[i:i+2] for i in range(0, len(tiles), 2)]
        matrix = [vector[i:i+self.size] for i in range(0, len(vector), self.size)]

        return [[self.__parseTile(x) for x in xs] for xs in matrix]

    def __init__(self, board):
        self.size = board['size']
        self.tiles = self.__parseTiles(board['tiles'])

    def passable(self, loc):
        """True if can walk through."""
        x, y = loc
        pos = self.tiles[x][y]
        return (pos != WALL) and (pos != TAVERN) and not isinstance(pos, CustomerTile) and not isinstance(pos, FriesTile) and not isinstance(pos, BurgerTile)

    def hazard(self, loc):
        """True if is hazard."""
        x, y = loc
        pos = self.tiles[x][y]
        return pos == SPIKE or isinstance(pos, HeroTile)

    def to(self, loc, direction):
        """Calculate a new location given the direction."""
        row, col = loc
        d_row, d_col = AIM[direction]
        n_row = row + d_row
        if n_row < 0:
            n_row = 0
        if n_row >= self.size:
            n_row = self.size - 1
        n_col = col + d_col
        if n_col < 0:
            n_col = 0
        if n_col >= self.size:
            n_col = self.size - 1

        return (n_row, n_col)

    def path_find_to(self, start, target, hazard_cost=None):
        """Get next direction to target"""
        (s, path) = self.path_find(start, target, hazard_cost)
        print('Path length is {} and score is {}'.format(len(path), s))
        if path is None:
            return None
        if len(path) > 1:
            n = (path[-2][0] - start[0], path[-2][1] - start[1])
            return next(a for (a, d) in AIM.items() if d == n)
        else:
            return 'Stay'

    def path_find(self, start, target, hazard_cost=None):
        """Get path (in reverse order) from start to target"""
        def heuristic(start, target):
            return abs(start[0] - target[0]) + abs(start[1] - target[1])

        def cost(loc):
            if hazard_cost is not None and self.hazard(loc):
                heroes = [h for h in (self.to(loc, a) for a in AIM.keys()) if isinstance(h, HeroTile)]
                if callable(hazard_cost):
                    return hazard_cost(self.tiles[loc[0]][loc[1]]) + sum(hazard_cost(h) for h in heroes)
                else:
                    return int(hazard_cost) + int(hazard_cost) * len(heroes)
            else:
                return 1

        def reconstruct(came_from, current):
            total_path = [current]
            while current in came_from:
                current = came_from[current]
                total_path.append(current)
            return total_path

        if start is None:
            return (MAXINT, None)

        if target is None:
            return (0, [start])

        closed_set = set()
        open_set = {start}
        came_from = dict()

        g_score = defaultdict(lambda: MAXINT)
        g_score[start] = 0

        f_score = defaultdict(lambda: MAXINT)
        f_score[start] = heuristic(start, target)

        while open_set:
            current = sorted(list(open_set), key=lambda x: f_score[x])[0]
            if current == target:
                return (g_score[current], reconstruct(came_from, current))

            open_set.remove(current)
            closed_set.add(current)
            for neighbor in (self.to(current, a) for a in AIM.keys()):
                if neighbor != target and (neighbor in closed_set or not self.passable(neighbor)):
                    continue

                tentative_g_score = g_score[current] + cost(neighbor)
                if neighbor not in open_set:
                    open_set.add(neighbor)
                elif tentative_g_score >= g_score[neighbor]:
                    continue

                came_from[neighbor] = current
                g_score[neighbor] = tentative_g_score
                f_score[neighbor] = g_score[neighbor] + heuristic(neighbor, target)

        return (MAXINT, None)


class Hero:
    def __init__(self, hero):
        self.name = hero['name']
        self.pos = hero['pos']
        self.id = int(hero['id'])
        self.life = int(hero['life'])
        self.calories = int(hero['calories'])
        self.french_fries = int(hero['frenchFriesCount'])
        self.burger = int(hero['burgerCount'])


class Customer:
    def __init__(self, customer):
        self.id = customer['id']
        self.burger = customer['burger']
        self.french_fries = customer['frenchFries']
        self.fulfilled_orders = customer['fulfilledOrders']
