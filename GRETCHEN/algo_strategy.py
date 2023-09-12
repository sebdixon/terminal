import gamelib
import random
import math
import warnings
import statistics
import numpy as np
from sys import maxsize
import json


"""
Most of the algo code you write will be in this file unless you create new
modules yourself. Start by modifying the 'on_turn' function.

Advanced strategy tips: 

  - You can analyze action frames by modifying on_action_frame function

  - The GameState.map object can be manually manipulated to create hypothetical 
  board states. Though, we recommended making a copy of the map to preserve 
  the actual current map state.
"""

class AlgoStrategy(gamelib.AlgoCore):
    def __init__(self):
        super().__init__()
        seed = random.randrange(maxsize)
        random.seed(seed)
        gamelib.debug_write('Random seed: {}'.format(seed))
        

    def getinfo(self):
        return super().getinfo()

    def on_game_start(self, config):
        """ 
        Read in config and perform any initial setup here 
        """
        gamelib.debug_write('Configuring your custom algo strategy...')
        self.config = config
        global WALL, SUPPORT, TURRET, SCOUT, DEMOLISHER, INTERCEPTOR, MP, SP
        WALL = config["unitInformation"][0]["shorthand"]
        SUPPORT = config["unitInformation"][1]["shorthand"]
        TURRET = config["unitInformation"][2]["shorthand"]
        SCOUT = config["unitInformation"][3]["shorthand"]
        DEMOLISHER = config["unitInformation"][4]["shorthand"]
        INTERCEPTOR = config["unitInformation"][5]["shorthand"]
        MP = 1
        SP = 0
        # This is a good place to do initial setup
        self.turret_locations_new = []
        self.scored_on_locations = []
        self.past_enemy_attacks = []
        self.location_weightings = [1] * 28

    def on_turn(self, turn_state):
        """
        This function is called every turn with the game state wrapper as
        an argument. The wrapper stores the state of the arena and has methods
        for querying its state, allocating your current resources as planned
        unit deployments, and transmitting your intended deployments to the
        game engine.
        """
        self.defence_built_this_turn = []
        info = self.getinfo()
        if info is not None:
            frame_0_gamestate = gamelib.GameState(self.config, info)
            for attack in frame_0_gamestate.enemy_unit_locations:
                gamelib.debug_write("The enemy attacked from " + str(attack) + " last turn.")
                self.past_enemy_attacks.append(attack)
                enemy_attack_x = attack[0]
                self.location_weightings[enemy_attack_x] += 1
        game_state = gamelib.GameState(self.config, turn_state)
        gamelib.debug_write('Performing turn {} of your custom algo strategy'.format(game_state.turn_number))
        game_state.suppress_warnings(True)  #Comment or remove this line to enable warnings.

        self.starter_strategy(game_state, turn_state)
        gamelib.debug_write(f"New locations:{self.turret_locations_new}")

        game_state.submit_turn()


    """
    NOTE: All the methods after this point are part of the sample starter-algo
    strategy and can safely be replaced for your custom algo.
    """
    def build_walls(self, game_state):
        walls_locs = [[0, 13], [1, 13], [2, 13], [25, 13], [26, 13], [27, 13]]
        game_state.attempt_spawn(WALL, walls_locs)
        for loc in walls_locs:
            if len(game_state.game_map[loc]):
                if game_state.game_map[loc][0].health < game_state.game_map[loc][0].max_health * 0.9:
                    game_state.attempt_remove(loc)
    def starter_strategy(self, game_state, turn_state):
        """
        For defense we will use a spread out layout and some interceptors early on.
        We will place turrets near locations the opponent managed to score on.
        For offense we will use long range demolishers if they place stationary units near the enemy's front.
        If there are no stationary units to attack in the front, we will send Scouts to try and score quickly.
        """
        ####DEFENSE
        #is_deleter = self.block_removal_in_front_line(game_state)
        #if is_deleter: 
            #self.location_weightings = [1] * 28

        self.build_walls(game_state)
        if game_state.turn_number > 0:
            self.build_defence_probabilistic(game_state, turn_state)
            if game_state.turn_number % 3 == 0:
                self.build_supports(game_state)
                self.upgrade_supports(game_state)
                self.additional_supports(game_state)
                self.upgrade_additional_supports(game_state)
        self.build_supports(game_state)
        self.upgrade_supports(game_state)
        self.reactive_defence(game_state)
        self.additional_supports(game_state)
        self.upgrade_additional_supports(game_state)
        ####ATTACK
        if game_state.get_resource(1, 0) > 10 or 0 < game_state.turn_number < 3:
            self.attack(game_state, turn_state)


    def euclidean_distance(self, pointOne, pointTwo):
        eucDist = ((pointOne[0] - pointTwo[0])**2 + (pointOne[1] - pointTwo[1])**2)**0.5
        return eucDist
    
    def get_points_in_distance(self, point, search_points, d):
        other_points = []
        for point1 in search_points:
            if self.euclidean_distance(point, point1) <= d:
                    other_points.append(point1)
        return other_points

    def calculate_damages(self, game_state, start_location, search_points, turn_state):
        game_state_copy = gamelib.GameState(self.config, turn_state)
        pending_removal = self.get_pending_removal(game_state)
        if len(pending_removal) > 0:
            for loc in pending_removal:
                game_state_copy.game_map.remove_unit(loc)
        path = game_state_copy.find_path_to_edge(start_location)
        damages = np.zeros((28, 28))
        if path is not None and len(path):
            for path_location in path:
                attack_points = self.get_points_in_distance(path_location, search_points, 3.5)
                for point in attack_points:
                    damages[point[0], point[1]] +=1
        return damages

    def get_pending_removal(self, game_state):
        locs = []
        for loc in game_state.game_map:
            for unit in game_state.game_map[loc]:
                if unit.pending_removal:
                    locs.append(loc)
        return locs


    def build_supports(self, game_state):
        support_locations = [[13, 4], [14, 4], [13, 5], [14, 5]]
        game_state.attempt_spawn(SUPPORT, support_locations)
        game_state.attempt_spawn(TURRET, [13, 6])

    def upgrade_supports(self, game_state):
        support_locations = [[13, 4], [14, 4], [13, 5], [14, 5]]
        game_state.attempt_upgrade(support_locations)

    def additional_supports(self, game_state):
        support_locations = [[12, 6], [15, 6], [10, 8], [17, 8]]
        game_state.attempt_spawn(SUPPORT, support_locations)
        support_locations = [[12, 5], [12, 4], [15, 5], [15, 4]]
        game_state.attempt_spawn(SUPPORT, support_locations)
    
    def upgrade_additional_supports(self, game_state):
        support_locations = [[12, 6], [15, 6], [10, 8], [17, 8]]
        game_state.attempt_upgrade(support_locations)

    def probabilistic_turret_model(self, game_state, turn_state):
        scout_coords_total = [[13, 27], [14, 27], [12, 26], [15, 26], [11, 25], [16, 25], [10, 24], [17, 24], [9, 23], [18, 23], [8, 22], [19, 22], [7, 21], [20, 21], [6, 20], [21, 20], [5, 19], [22, 19], [4, 18], [23, 18], [3, 17], [24, 17], [2, 16], [25, 16], [1, 15], [26, 15], [0, 14], [27, 14]]
        scout_coords_unoccupied = []
        for coord in scout_coords_total:
            if game_state.contains_stationary_unit(coord):
                continue
            scout_coords_unoccupied.append(coord)
        turret_coords_total = [[0, 13], [1, 13], [2, 13], [3, 13], [4, 13], [5, 13], [6, 13], [7, 13], [8, 13], [9, 13], [10, 13], [11, 13], [12, 13], [13, 13], [14, 13], [15, 13], [16, 13], [17, 13], [18, 13], [19, 13], [20, 13], [21, 13], [22, 13], [23, 13], [24, 13], [25, 13], [26, 13], [27, 13], [1, 12], [2, 12], [3, 12], [4, 12], [5, 12], [6, 12], [7, 12], [8, 12], [9, 12], [10, 12], [11, 12], [12, 12], [13, 12], [14, 12], [15, 12], [16, 12], [17, 12], [18, 12], [19, 12], [20, 12], [21, 12], [22, 12], [23, 12], [24, 12], [25, 12], [26, 12], [2, 11], [3, 11], [4, 11], [5, 11], [6, 11], [7, 11], [8, 11], [9, 11], [10, 11], [11, 11], [12, 11], [13, 11], [14, 11], [15, 11], [16, 11], [17, 11], [18, 11], [19, 11], [20, 11], [21, 11], [22, 11], [23, 11], [24, 11], [25, 11], [4, 10], [5, 10], [6, 10], [7, 10], [8, 10], [9, 10], [10, 10], [11, 10], [12, 10], [13, 10], [14, 10], [15, 10], [16, 10], [17, 10], [18, 10], [19, 10], [20, 10], [21, 10], [22, 10], [23, 10]]
        turret_coords_unoccupied = []
        for coord in turret_coords_total:
            if game_state.contains_stationary_unit(coord):
                continue
            turret_coords_unoccupied.append(coord)
        turret_damages = np.zeros((28, 28))
        for scout_loc in scout_coords_unoccupied:
            turret_damages += self.calculate_damages(game_state, scout_loc, turret_coords_unoccupied, turn_state) * self.location_weightings[scout_loc[0]]
        #gamelib.debug_write(f"Damages:{turret_damages}")
        max_index = np.argmax(turret_damages)
        #gamelib.debug_write(f"Index {max_index}")
        return list([max_index // 28, max_index % 28])

    def build_defence_probabilistic(self, game_state, turn_state):
        
        built_defence = []
        best_location = self.probabilistic_turret_model(game_state, turn_state)
        best_location = [int(best_location[0]), int(best_location[1])]
        game_state_modified = gamelib.GameState(self.config, turn_state)
        n = game_state.attempt_spawn(TURRET, best_location)
        if n:
            self.defence_built_this_turn.append(best_location)
        game_state.attempt_upgrade(best_location)
        game_state_modified.game_map.add_unit(TURRET, best_location, 0)
        best_location = self.probabilistic_turret_model(game_state, turn_state)
        best_location = [int(best_location[0]), int(best_location[1])]
        n = game_state.attempt_spawn(TURRET, best_location)
        if n:
            self.defence_built_this_turn.append(best_location)
        game_state.attempt_upgrade(best_location)
        game_state_modified.game_map.add_unit(TURRET, best_location, 0)
        best_location = self.probabilistic_turret_model(game_state, turn_state)
        best_location = [int(best_location[0]), int(best_location[1])]
        n = game_state.attempt_spawn(TURRET, best_location)
        if n:
            self.defence_built_this_turn.append(best_location)
        game_state.attempt_upgrade(best_location)
        return built_defence

    def reactive_defence(self, game_state):
        for location in self.scored_on_locations:
            # Build turret one space above so that it doesn't block our own edge spawn locations
            build_locations = []
            if location[0] <= 12:
                build_locations = [[location[0], location[1] + 2], [location[0] + 2, location[1]]]
                self.defence_side = 'LEFT'
            elif location[0] >= 15:
                build_locations = [[location[0] - 2, location[1]], [location[0], location[1] + 2]]
                self.defence_side = 'RIGHT'
            if location[1] >= 11:
                build_locations = [[location[0], location[1] + 1], [location[0], location[1] - 1], [location[0] - 1, location[1] + 1], [location[0] + 1, location[1] + 1], [location[0] - 1, location[1] - 1], [location[0] + 1, location[1] - 1], [location[0] + 1, location[1]], [location[0] - 1, location[1]]]
            for loc in build_locations:
                n_units = game_state.attempt_spawn(TURRET, loc)
                if n_units:
                    self.turret_locations_new.append(loc)
                    self.defence_built_this_turn.append(loc)

                game_state.attempt_upgrade(build_locations)

    def block_removal_in_front_line(self, game_state):
        points_to_block = []
        front_line = [[i, 14] for i in range(28)]
        for point in front_line:
            for unit in game_state.game_map[point]:
                if unit.pending_removal:
                    points_to_block.append(point)
                    points_to_block.append([point[0]-1, point[1]])
                    points_to_block.append([point[0]+1, point[1]])
        if len(points_to_block) > 4:
            return []
        for point in points_to_block:
            n = game_state.attempt_spawn(TURRET, point)
            if n:
                self.defence_built_this_turn.append(point)
            game_state.attempt_upgrade(point)
        return True
                
    def attack(self, game_state, turn_state):
        best_location = self.simulate_attack(game_state, turn_state)
        game_state.attempt_spawn(SCOUT, best_location,1000)


    def simulate_attack(self, game_state, turn_state):
        n_shielding = 0
        finish_options = [[13, 27], [14, 27], [12, 26], [15, 26], [11, 25], [16, 25], [10, 24], [17, 24], [9, 23], [18, 23], [8, 22], [19, 22], [7, 21], [20, 21], [6, 20], [21, 20], [5, 19], [22, 19], [4, 18], [23, 18], [3, 17], [24, 17], [2, 16], [25, 16], [1, 15], [26, 15], [0, 14], [27, 14]]
        start_options = [[0, 13], [27, 13], [1, 12], [26, 12], [2, 11], [25, 11], [3, 10], [24, 10], [4, 9], [23, 9], [5, 8], [22, 8], [6, 7], [21, 7], [7, 6], [20, 6], [8, 5], [19, 5], [9, 4], [18, 4], [10, 3], [17, 3], [11, 2], [16, 2], [12, 1], [15, 1], [13, 0], [14, 0]]
        start_options_unoc = []
        for coord in start_options:
            if game_state.contains_stationary_unit(coord):
                continue
            start_options_unoc.append(coord)
        game_state_copy = gamelib.GameState(self.config, turn_state)
        start_options_score = [0] * len(start_options_unoc)
        if len(self.defence_built_this_turn):
            for loc in self.defence_built_this_turn:
                game_state_copy.game_map.add_unit(TURRET, loc, 0)
        turrets = np.zeros((28,28))
        supports = np.zeros((28, 28))
        all_locations = [[i, j] for i in range(28) for j in range(14, 28)]
        for loc in all_locations:
            if game_state.contains_stationary_unit(loc):
                for unit in game_state.game_map[loc]:
                    turrets[loc] = (unit.damage_i > 0) * unit.health
                    supports[loc] = (unit.shieldPerUnit > 0) * unit.health
                    n_shielding += unit.shieldPerUnit
        
    
        gamelib.debug_write("Scores before {}".format(start_options_score))
        for i, start in enumerate(start_options_unoc):
            path = game_state_copy.find_path_to_edge(start)
            if len(path) < 5 and path[-1] not in finish_options:
                start_options_score[i] = -100000
            if 4 < start[0] < 23:
                health = 15 * (game_state.get_resource(0, 0) // 1 + n_shielding +1.5)
            else:
                health = 15 * (game_state.get_resource(0, 0) // 1)
            for point in path:
                points_in_range = self.get_points_in_distance(point, all_locations, 3.5)
                attackers = game_state_copy.get_attackers(point, 0)
                gamelib.debug_write(f"points in range:{points_in_range}")
                for pos in points_in_range:
                    if game_state.contains_stationary_unit(pos):
                        for unit in game_state.game_map[pos]:
                            if len(attackers):
                                turrets[pos[0], pos[1]] -= (game_state.get_resource(0, 0) // 1 * (unit.damage_i > 0)) / len(attackers)
                            supports[pos[0], pos[1]] -= (game_state.get_resource(0, 0) // 1 * (unit.shieldPerUnit > 0))
                            health -= unit.damage_i
                    start_options_score[i] -= turrets[pos[0], pos[1]]
                    start_options_score[i] -= supports[pos[0], pos[1]] * 100
                if health > 0:
                    if point == path[-1]:
                        start_options_score[i] += 1000 + health
                else:
                    continue
        
        gamelib.debug_write("Scores {}".format(start_options_score))
        return start_options_unoc[np.argmax(start_options_score)]

            


    def on_action_frame(self, turn_string):
        """
        This is the action frame of the game. This function could be called 
        hundreds of times per turn and could slow the algo down so avoid putting slow code here.
        Processing the action frames is complicated so we only suggest it if you have time and experience.
        Full doc on format of a game frame at in json-docs.html in the root of the Starterkit.
        """
        # Let's record at what position we get scored on
        state = json.loads(turn_string)
        events = state["events"]
        breaches = events["breach"]
        for breach in breaches:
            location = breach[0]
            unit_owner_self = True if breach[4] == 1 else False
            # When parsing the frame data directly, 
            # 1 is integer for yourself, 2 is opponent (StarterKit code uses 0, 1 as player_index instead)
            if not unit_owner_self:
                gamelib.debug_write("Got scored on at: {}".format(location))
                self.scored_on_locations.append(location)
                gamelib.debug_write("All locations: {}".format(self.scored_on_locations))

    def build_reactive_defense(self, game_state):
        """
        This function builds reactive defenses based on where the enemy scored on us from.
        We can track where the opponent scored by looking at events in action frames 
        as shown in the on_action_frame function
        """
        for location in self.scored_on_locations:
            # Build turret one space above so that it doesn't block our own edge spawn locations
            build_locations = []
            if location[0] <= 7:
                build_locations = [[location[0], location[1]],[location[0]+1, location[1]]]
                self.defence_side = 'LEFT'
            elif location[0] >= 19:
                build_locations = [[location[0], location[1]]]
                if location[0] >= 25:
                    build_locations = [[location[0] - 1, location[1]], [location[0], location[1]]]
                
            game_state.attempt_spawn(TURRET, build_locations)
            game_state.attempt_upgrade(build_locations)

    def least_damage_spawn_location(self, game_state, location_options):
        """
        This function will help us guess which location is the safest to spawn moving units from.
        It gets the path the unit will take then checks locations on that path to 
        estimate the path's damage risk.
        """
        damages = []
        # Get the damage estimate each path will take
        for location in location_options:
            path = game_state.find_path_to_edge(location)
            damage = 0
            for path_location in path:
                # Get number of enemy turrets that can attack each location and multiply by turret damage
                damage += len(game_state.get_attackers(path_location, 0)) * gamelib.GameUnit(TURRET, game_state.config).damage_i
            damages.append(damage)
        
        # Now just return the location that takes the least damage
        return location_options[damages.index(min(damages))]
        
        # Now just return the location that takes the least damage
        return location_options[damages.index(min(damages))]


if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
