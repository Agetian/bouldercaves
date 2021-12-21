"""
Boulder Caves+ - a Boulder Dash (tm) clone.
Krissz Engine-compatible remake based on Boulder Caves 5.7.2.

This module contains the game logic.

Original version written by Irmen de Jong (irmen@razorvine.net)
Extended version by Michael Kamensky

License: GNU GPL 3.0, see LICENSE
"""

import datetime
import math
import random
import json
from .caves import C64Cave
from enum import Enum
from typing import List, Optional, Sequence, Generator
from .objects import Direction
from .helpers import TextHelper
from . import caves, audio, user_data_dir, tiles, objects


class GameStatus(Enum):
    WAITING = 1
    REVEALING_PLAY = 2
    REVEALING_DEMO = 3
    PLAYING = 4
    PAUSED = 5
    LOST = 6
    WON = 7
    DEMO = 8
    HIGHSCORE = 9
    OUT_OF_TIME = 10


class HighScores:
    # high score table is 8 entries, name len=7 max, score max=999999
    # table starts with score then the name, for easy sorting
    max_namelen = 7

    def __init__(self, cavesetname) -> None:
        self.name = cavesetname.lower().replace(' ', '_').replace('.', '_')
        self.load()

    def __iter__(self):
        yield from self.scores

    def save(self) -> None:
        with open(user_data_dir + "highscores-{:s}.json".format(self.name), "wt") as out:
            json.dump(self.scores, out)

    def load(self) -> None:
        try:
            with open(user_data_dir + "highscores-{:s}.json".format(self.name), "rt") as scorefile:
                self.scores = json.load(scorefile)
        except FileNotFoundError:
            print("Using new high-score table.")
            self.scores = [[0, "-----"]] * 8
            self.save()

    def score_pos(self, playerscore: int) -> Optional[int]:
        for pos, (score, _) in enumerate(self.scores, start=1):
            if score < playerscore:
                return pos
        return None

    def add(self, name: str, score: int) -> None:
        pos = self.score_pos(score)
        if not pos:
            raise ValueError("score is not a new high score")
        self.scores.insert(pos - 1, [score, name])
        self.scores = self.scores[:8]


class Cell:
    __slots__ = ("obj", "x", "y", "frame", "falling", "direction", "anim_start_gfx_frame", "update_stage")

    def __init__(self, obj: objects.GameObject, x: int, y: int) -> None:
        self.obj = obj  # what object is in the cell
        self.x = x
        self.y = y
        self.frame = 0
        self.falling = False
        self.direction = Direction.NOWHERE
        self.anim_start_gfx_frame = 0
        self.update_stage = 0 # for explosions and other things that change to other objs at the end

    def __repr__(self):
        return "<Cell {:s} @{:d},{:d}>".format(self.obj.name, self.x, self.y)

    def isempty(self) -> bool:
        return self.obj.id in (objects.EMPTY.id, objects.BONUSBG.id)

    def isdirt(self) -> bool:
        return self.obj.id == objects.DIRT.id
        #return self.obj in {objects.DIRTBALL, objects.DIRT, objects.DIRT2, objects.DIRTLOOSE,
        #                    objects.DIRTSLOPEDDOWNLEFT, objects.DIRTSLOPEDDOWNRIGHT,
        #                    objects.DIRTSLOPEDUPLEFT, objects.DIRTSLOPEDUPRIGHT}

    def isrockford(self) -> bool:
        return self.obj.id == objects.ROCKFORD.id

    def isrounded(self) -> bool:
        return self.obj.rounded

    def isexplodable(self) -> bool:
        return self.obj.explodable

    def isconsumable(self) -> bool:
        return self.obj.consumable

    def ismagic(self) -> bool:
        return self.obj.id == objects.MAGICWALL.id

    def isslime(self) -> bool:
        return self.obj.id == objects.SLIME.id

    def isbutterfly(self) -> bool:
        # these explode to diamonds
        return self.obj.id in (objects.BUTTERFLY.id, objects.ALTBUTTERFLY.id)

    def isfirefly(self) -> bool:
        return self.obj.id in (objects.FIREFLY.id, objects.ALTFIREFLY.id)

    def isamoeba(self) -> bool:
        return self.obj.id in (objects.AMOEBA.id, objects.AMOEBARECTANGLE.id)

    def isdiamond(self) -> bool:
        return self.obj.id in (objects.DIAMOND.id, objects.FLYINGDIAMOND.id)

    def isboulder(self) -> bool:
        return self.obj.id in (objects.BOULDER.id, objects.MEGABOULDER.id, objects.LIGHTBOULDER.id)
        #return self.obj in {objects.BOULDER, objects.MEGABOULDER, objects.CHASINGBOULDER, objects.FLYINGBOULDER, objects.LIGHTBOULDER}
    
    def isheavy(self) -> bool:
        return self.obj.id == objects.MEGABOULDER.id
    
    def islight(self) -> bool:
        return self.obj.id == objects.LIGHTBOULDER.id

    def iswall(self) -> bool:
        return self.obj.id in (objects.BRICK.id, objects.STEEL.id, objects.HEXPANDINGWALL.id, objects.VEXPANDINGWALL.id,
                               objects.EXPANDINGWALL.id, objects.MAGICWALL.id, objects.FILLERWALL.id)
        #return self.obj in {objects.HEXPANDINGWALL, objects.VEXPANDINGWALL, objects.BRICK,
        #                    objects.MAGICWALL, objects.STEEL, objects.STEELWALLBIRTH,
        #                    objects.BRICKSLOPEDDOWNRIGHT, objects.BRICKSLOPEDDOWNLEFT,
        #                    objects.BRICKSLOPEDUPRIGHT, objects.BRICKSLOPEDUPLEFT,
        #                    objects.STEELSLOPEDDOWNLEFT, objects.STEELSLOPEDDOWNRIGHT,
        #                    objects.STEELSLOPEDUPLEFT, objects.STEELSLOPEDUPRIGHT,
        #                    objects.EXPANDINGWALL, objects.FILLERWALL}

    def isexpandingwall(self) -> bool:
        return self.obj.id in (objects.HEXPANDINGWALL.id, objects.VEXPANDINGWALL.id, objects.EXPANDINGWALL.id)

    def isinbox(self) -> bool:
        return self.obj.id in (objects.INBOXBLINKING.id, objects.INBOXBLINKING_1.id, objects.INBOXBLINKING_2.id)
       
    def isoutbox(self) -> bool:
        return self.obj.id in (objects.OUTBOXBLINKING.id, objects.OUTBOXBLINKING_1.id, objects.OUTBOXBLINKING_2.id,
                               objects.OUTBOXHIDDENOPEN.id)
    
    def isoutboxblinking(self) -> bool:
        return self.obj.id in (objects.OUTBOXBLINKING_1.id, objects.OUTBOXBLINKING_2.id)

    def isexplosion(self) -> bool:
        return self.obj.id in (objects.EXPLOSION.id, objects.DIAMONDBIRTH.id)

    def canfall(self) -> bool:
        return self.obj.id in (objects.BOULDER.id, objects.DIAMOND.id, objects.MEGABOULDER.id, objects.LIGHTBOULDER.id)
        #return self.obj in {objects.BOULDER, objects.SWEET, objects.DIAMONDKEY, objects.BOMB,
        #                    objects.IGNITEDBOMB, objects.KEY1, objects.KEY2, objects.KEY3,
        #                    objects.DIAMOND, objects.MEGABOULDER, objects.SKELETON, objects.NITROFLASK,
        #                    objects.DIRTBALL, objects.COCONUT, objects.ROCKETLAUNCHER, objects.LIGHTBOULDER}


# C64 predictable random generator for PCLK- and Krissz Engine-compatible slime permeability
# noinspection PyAttributeOutsideInit
class GameState:
    def __init__(self, game) -> None:
        self.game = game
        self.graphics_frame_counter = 0    # will be set via the update() method
        self.fps = 7      # by default, game logic updates 7 fps which is about ~143 ms per frame (original game = ~150 ms)
        self.update_timestep = 1 / self.fps
        self.caveset = caves.CaveSet()
        self.start_level_number = 1
        self.reveal_duration = 3.0
        # predictable slime permeability (Krissz Engine-compatible, based on PLCK)
        self.slime_permeability_patterns = [0b00000000, 0b00010000, 0b00011000, 
                                            0b00111000, 0b00111100, 0b01111100,
                                            0b01111110, 0b11111110, 0b11111111]
        self.rockford_birth_stages = (objects.ROCKFORDBIRTH_1, objects.ROCKFORDBIRTH_2, objects.ROCKFORDBIRTH_3, objects.ROCKFORDBIRTH_4)
        self.highscores = HighScores(self.caveset.name)
        self.playtesting = False
        # set the anim end callbacks:
        # animation callbacks are ONLY used when the level is won/lost in order to finish pending animations
        # they should not be tied to game logic during the regular cave scans when playing the game, or it
        # will break the cave scanning order!
        objects.EXPLOSION.anim_end_callback = self.end_explosion_animation
        objects.DIAMONDBIRTH.anim_end_callback = self.end_diamondbirth_animation
        # will be used when resizing smaller caves to fit nearly into a larger visible playfield
        self.cave_orig_width = self.cave_orig_height = 0
        # and start the game on the title screen.
        self.restart()

    def set_object_animation_speeds(self, fps):
        # explosions happen to the rhythm of the game
        objects.EXPLOSION.sfps = fps
        objects.DIAMONDBIRTH.sfps = fps
        # objects.BOULDERBIRTH.sfps = fps # Not used at the moment
        # objects.AMOEBAEXPLODE.sfps = fps # Not used at the moment
        
        # update fps-based animation speed for everything else
        # this approximates Krissz Engine update FPS, but may not be frame-perfect
        # FIXME: maybe just update at half the FPS (e.g. 30 in 60fps, 15 in 30fps mode)? It won't match KE then though.
        update_speed = int(math.ceil(min(self.game.update_fps, 60) * 60 / 100)) 
        #print("Animation update speed is : " + str(update_speed) + " fps.")
        objects.DIAMOND.sfps = update_speed
        objects.BUTTERFLY.sfps = update_speed
        objects.ALTBUTTERFLY.sfps = update_speed
        objects.FIREFLY.sfps = update_speed
        objects.ALTFIREFLY.sfps = update_speed
        objects.AMOEBA.sfps = update_speed
        objects.SLIME.sfps = update_speed
        objects.MAGICWALL.sfps = update_speed
        objects.BONUSBG.sfps = update_speed
        objects.COVERED.sfps = update_speed
        # rockford movement
        objects.ROCKFORD.left.sfps = update_speed
        objects.ROCKFORD.right.sfps = update_speed
        objects.ROCKFORD.pushleft.sfps = update_speed
        objects.ROCKFORD.pushright.sfps = update_speed
        objects.ROCKFORD.blink.sfps = update_speed
        objects.ROCKFORD.tap.sfps = update_speed
        objects.ROCKFORD.tapblink.sfps = update_speed
        objects.ROCKFORD.stirring.sfps = update_speed

    def destroy(self) -> None:
        self.highscores.save()

    def end_explosion_animation(self, cell: Cell) -> None:
        if self.level_won:
            self.clear_cell(cell)

    def end_diamondbirth_animation(self, cell: Cell) -> None:
        if self.level_won:
            self.draw_single_cell(cell, objects.DIAMOND)

    def restart(self) -> None:
        audio.silence_audio()
        audio.play_sample("music", repeat=True, after=1)
        self.frame = 0
        self.initial_update_frame = 0
        self.demo_or_highscore = True
        self.game.set_screen_colors(0, 0)
        self.bonusbg_frame = 0    # till what frame should the bg be the bonus sparkly things instead of spaces
        self.level = -1
        self.level_name = self.level_description = "???"
        self.level_won = False
        self.game_status = GameStatus.PLAYING if self.playtesting else GameStatus.WAITING
        self.intermission = False
        self.score = self.extralife_score = 0
        self.cheat_used = self.start_level_number > 1
        self.death_by_voodoo = False
        self.slime_permeability = 0
        self.diamondvalue_initial = self.diamondvalue_extra = 0
        self.diamonds = self.diamonds_needed = 0
        self.lives = 3
        self.idle = {
            "blink": False,
            "tap": False
        }
        self.keys = {
            "diamond": 0,
            "one": True,
            "two": True,
            "three": True
        }
        self.magicwall = {
            "active": False,
            "time": 0.0
        }
        self.amoeba = {
            "size": 0,
            "max": 0,
            "slow": 0.0,
            "enclosed": False,
            "dormant": True,
            "dead": None
        }
        self.timeremaining = datetime.timedelta(0)
        self.timelimit = None   # type: Optional[datetime.datetime]
        self.reverse_timer = 0.0  # for ReverseTime (substandard)
        self.rockford_cell = self.inbox_cell = self.last_focus_cell = None   # type: Optional[Cell]
        self.rockford_found_frame = -1
        self.start_signal_frame = -1
        self.movement = MovementInfo()
        self.flash = 0
        self.inbox_outbox_blink_state = False
        # draw the 'title screen'
        title=r"""
WWWWWWWWWWWWWWWWWWWWWWWWWWWWWW
W............................W
W.%%          *   %         .W
W.% %  *  % % r   %  ** % % .W
W.%%  r r % % r  %% r r %%  .W
W.% % r r % % r % % rr  %   .W
W.%%   r   %  r  %%  rr %   .W
W.   %%                     .W
W.  %    *  %  %  **  %%  d .W
W.  %   r r  % % r r %   ddd.W
W.  %   r r  % % rr   %%  d .W
W.   %%  r r  %   rr %%     .W
W.                          .W
W.       wwwwwwwwwww        .W
W.       wc   Q   cw        .W
W.       w  Q   Q  w        .W
W........wwwwwwwwwww.........W
WWWWWWWWWWWWWWWWWWWWWWWWWWWWWW
"""
        title_objs = {
                        ' ': objects.EMPTY,
                        '.': objects.DIRT,
                        '%': objects.MEGABOULDER,
                        'r': objects.BOULDER,
                        '*': objects.LIGHTBOULDER,
                        'w': objects.BRICK,
                        'W': objects.STEEL,
                        'd': objects.DIAMOND,
                        'c': objects.BUTTERFLY,
                        'Q': objects.FIREFLY
        }
        if self.game.window30x18:
            self._create_cave(30, 18)
            for y, tl in enumerate(title.splitlines()):
                for x, c in enumerate(tl):
                    obj = title_objs[c]
                    self.draw_single(obj, x, y - 1)
        else:
            self._create_cave(40, 22)
            self.draw_rectangle(objects.DIRT2, 0, 0, self.width, self.height, objects.EMPTY)
            
            for y, tl in enumerate(title.splitlines()):
                for x, c in enumerate(tl):
                    obj = title_objs[c]
                    self.draw_single(obj, 5 + x, y)

            self.draw_line(objects.LAVA, 4, self.height - 3, self.width - 8, Direction.RIGHT)
            self.draw_line(objects.DIRT, 3, self.height - 2, self.width - 6, Direction.RIGHT)
            self.draw_single(objects.DIRTSLOPEDUPLEFT, 3, self.height - 3)
            self.draw_single(objects.DIRTSLOPEDUPLEFT, 2, self.height - 2)
            self.draw_single(objects.DIRTSLOPEDUPRIGHT, self.width - 4, self.height - 3)
            self.draw_single(objects.DIRTSLOPEDUPRIGHT, self.width - 3, self.height - 2)

    def _create_cave(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self._dirxy = {
            Direction.NOWHERE: 0,
            Direction.UP: -self.width,
            Direction.DOWN: self.width,
            Direction.LEFT: -1,
            Direction.RIGHT: 1,
            Direction.LEFTUP: -self.width - 1,
            Direction.RIGHTUP: -self.width + 1,
            Direction.LEFTDOWN: self.width - 1,
            Direction.RIGHTDOWN: self.width + 1
        }
        self.cave = []   # type: List[Cell]
        for y in range(self.height):
            for x in range(self.width):
                self.cave.append(Cell(objects.EMPTY, x, y))

    def draw_new_cave(self, levelnumber):
        # clear the previous cave data and replace with data from new cave
        self.game.clear_tilesheet()
        self.draw_rectangle(objects.FILLERWALL, 0, 0, self.width, self.height, objects.FILLERWALL)
        cave = self.caveset.cave(levelnumber)
        self.cave_delta_x = self.cave_delta_y = 0
        if cave.width > self.game.visible_columns or cave.height > self.game.visible_rows:
            delta_x, delta_y = cave.add_mirrored_borders(self.game.mirrored_border_size, \
                self.open_horizontal_borders, self.open_vertical_borders)
            self.cave_delta_x += delta_x
            self.cave_delta_y += delta_y
        if cave.width < self.game.visible_columns or cave.height < self.game.visible_rows:
            filler = objects.FILLERWALL
            delta_x, delta_y = cave.resize(self.game.visible_columns, self.game.visible_rows, filler)
            self.cave_delta_x += delta_x
            self.cave_delta_y += delta_y
        for i, (gobj, direction) in enumerate(cave.map):
            y, x = divmod(i, cave.width)
            self.draw_single(gobj, x, y, initial_direction=direction)
            if self.game_status in (GameStatus.REVEALING_DEMO, GameStatus.REVEALING_PLAY):
                self.game.tilesheet.dirty_tiles[x + self.game.tilesheet.width * y] = 0

    def use_bdcff(self, filename: str) -> None:
        self.caveset = caves.CaveSet(filename)
        self.highscores = HighScores(self.caveset.name)

    def use_startlevel(self, levelnumber: int) -> None:
        if levelnumber < 1 or levelnumber > self.caveset.num_caves:
            levelnumber = 1
        self.cheat_used = levelnumber > 1
        self.start_level_number = levelnumber

    def use_playtesting(self) -> None:
        # enable playtest mode, used from the editor.
        # skips all intro popups and title screen and immediately drops into the level.
        self.cheat_used = True
        self.playtesting = True
        self.level = self.start_level_number - 1
        self.reveal_duration = 0.0
        self.load_next_level(False)

    def load_level(self, levelnumber: int, level_intro_popup: bool=True) -> None:
        if levelnumber == 1 or self.start_level_number == levelnumber:
            audio.silence_audio() # silence all sounds for the first level, to ensure music is stopped
        else:
            audio.silence_audio("amoeba") # otherwise, at least finish playing the sounds that are on repeat
            audio.silence_audio("magic_wall")
        self.game.popup_close()    # make sure any open popup won't restore the old tiles
        self.cheat_used = self.cheat_used or (self.start_level_number > 1)
        cave = self.caveset.cave(levelnumber)
        self.cave_orig_width = cave.width
        self.cave_orig_height = cave.height
        self.cave_orig_len = len(self.cave)
        self.cave_delta_x = 0
        self.cave_delta_y = 0
        if self.game.mirrored_border_size > self.game.visible_columns // 2 + 3:
            self.game.mirrored_border_size = self.game.visible_columns // 2 + 3
        if cave.width > self.game.visible_columns or cave.height > self.game.visible_rows:
            delta_x, delta_y = cave.add_mirrored_borders(self.game.mirrored_border_size, \
                cave.open_horizontal_borders, cave.open_vertical_borders)
            self.cave_delta_x += delta_x
            self.cave_delta_y += delta_y
        if cave.width < self.game.visible_columns or cave.height < self.game.visible_rows:
            filler = objects.FILLERWALL
            delta_x, delta_y = cave.resize(self.game.visible_columns, self.game.visible_rows, filler)
            self.cave_delta_x += delta_x
            self.cave_delta_y += delta_y
        self._create_cave(cave.width, cave.height)
        self.game.create_canvas_playfield_and_tilesheet(cave.width, cave.height)
        self.level_name = cave.name
        self.level_description = cave.description
        self.intermission = cave.intermission
        # The update frame for the Rockford Birth property
        self.initial_update_frame = 0
        # Set the cave frame time to match Krissz Engine "Game Speed"
        self.fps = float(cave.target_fps)
        self.update_timestep = 1 / self.fps 
        self.set_object_animation_speeds(self.fps)
        # print("Update timestep: " + str(self.update_timestep * 1000))
        self.wraparound = cave.wraparound
        self.lineshift = cave.lineshift
        self.magic_wall_stops_amoeba = cave.magic_wall_stops_amoeba # Substandard, emulates Krissz "Magic wall stops amoeba"
        self.magic_wall_stops_amoeba_phase = 0 # 0 - not triggered, 1 - triggered, converting to diamonds, 2 - overwritten by max amoeba count, converting to boulders
        self.rockford_birth_time = cave.rockford_birth_time # Substandard, emulates Krissz "Rockford birth time"
        self.amoeba_limit = cave.amoeba_limit - 1 # Substandard, emulates Krissz "Amoeba limit"
        self.amoeba_grows_before_spawn = cave.amoeba_grows_before_spawn # Substandard, emulates Krissz amoeba growing before Rockford spawns
        self.value_of_a_second = cave.value_of_a_second # Substandard, defines the value of a second (bonus/penalty) when counting score
        self.no_time_limit = cave.no_time_limit # Substandard, disables time limit on the cave
        self.reverse_time = cave.reverse_time # Substandard, disables time limit and makes the timer count upwards
        self.open_horizontal_borders = cave.open_horizontal_borders # Substandard, emulates Open Borders: Horizontal
        self.open_vertical_borders = cave.open_vertical_borders # Substandard, emulates Open Borders: Vertical
        self.single_life = cave.single_life # Substandard, only gives a single life to complete the cave before high score
        self.krissz_slime_permeability = cave.krissz_slime_permeability # Substandard, predictable C64 permeability with PLCK patterns, as used on Krissz's engine
        self.c64_random_slime_seeds = [0x00, 0x1E] # The 0x001E seed is used (decimal 30) for the slime permeability, the same as PLCK
        if self.single_life:
            self.lives = 1
        level_intro_popup = level_intro_popup and levelnumber != self.level
        self.level = levelnumber
        self.level_won = False
        self.frame = 0
        self.rockford_blink_frame = 0
        self.bonusbg_frame = 0
        self.game_status = GameStatus.PLAYING if self.playtesting else GameStatus.REVEALING_PLAY
        self.reveal_frame = 0 if self.playtesting else self.fps * self.reveal_duration
        self.flash = 0
        self.diamonds = 0
        self.diamonds_needed = cave.diamonds_required
        self.diamondvalue_initial = cave.diamondvalue_normal
        self.diamondvalue_extra = cave.diamondvalue_extra
        self.timeremaining = datetime.timedelta(seconds=cave.time)
        self.slime_permeability = cave.slime_permeability
        self.death_by_voodoo = False
        self.timelimit = None   # will be set as soon as Rockford spawned
        self.reverse_timer = 0.0  # Reverse Time reset on reload
        self.idle["blink"] = self.idle["tap"] = False
        self.magicwall["active"] = False
        self.magicwall["time"] = cave.magicwall_millingtime / self.update_timestep
        self.rockford_cell = None     # the cell where Rockford currently is
        self.inbox_cell = self.last_focus_cell = None
        self.rockford_found_frame = 0
        self.start_signal_frame = -1
        self.movement = MovementInfo()
        self.amoeba = {
            "size": 0,
            "max": cave.amoebafactor * self.width * self.height,
            "slow": cave.amoeba_slowgrowthtime / self.update_timestep,
            "enclosed": False,
            "dormant": True,
            "dead": None
        }
        if self.amoeba_limit >= 0:
            self.amoeba["max"] = self.amoeba_limit
        have_level_intro_popup = level_intro_popup and self.level_description
        if have_level_intro_popup:
            # don't reveal the cave already
            self.game.clear_tilesheet()
        else:
            self.draw_new_cave(self.level)
        self.game.create_colored_tiles(cave.colors)
        self.game.set_screen_colors(cave.colors.rgb_screen, cave.colors.rgb_border)
        self.check_initial_amoeba_dormant()

        def prepare_reveal() -> None:
            self.game.prepare_reveal()
            audio.play_sample("cover", repeat=True)

        if self.game.krissz_engine_compat:
            inbox_location = None
            for cell in self.cave:
                if cell.obj.id == objects.INBOXBLINKING.id:
                    inbox_location = cell
                    break
            # on Krissz Engine, always seems to scroll from the vicinity of the inbox. In our implementation,
            # scroll from the vicinity of the inbox when the inbox is too far from the origin point (0, 0)
            if inbox_location and (inbox_location.x > self.game.visible_columns * 2 or inbox_location.y > self.game.visible_rows * 2):
                x, y = tiles.tile2pixels(inbox_location.x, inbox_location.y)
                curx, cury = self.game.view_x + self.game.visible_columns / 2, self.game.view_y + self.game.visible_rows / 2
                self.game.scrollxypixels((curx + x) / 2, (cury + y) / 2)
            else:
                self.game.scrollxypixels(0, 0)
        else:
            self.game.scrollxypixels(0, 0)
        if have_level_intro_popup:
            self.game.clear_tilesheet()
            self.game.popup("{:s}\n\n{:s}".format(self.level_name, self.level_description), on_close=prepare_reveal)
        elif not self.playtesting:
            prepare_reveal()

    def check_initial_amoeba_dormant(self) -> None:
        if self.amoeba["dormant"]:
            for cell in self.cave:
                if cell.isamoeba():
                    cell_up = self.get(cell, Direction.UP)
                    cell_down = self.get(cell, Direction.DOWN)
                    cell_left = self.get(cell, Direction.LEFT)
                    cell_right = self.get(cell, Direction.RIGHT)
                    if cell_up.isempty() or cell_down.isempty() or cell_right.isempty() or cell_left.isempty() \
                            or cell_up.isdirt() or cell_down.isdirt() or cell_right.isdirt() or cell_left.isdirt():
                        # amoeba can grow, so is not dormant
                        self.amoeba["dormant"] = False
                        audio.play_sample("amoeba", repeat=True)  # start playing amoeba sound
                        return

    def tile_music_ended(self) -> None:
        # do one of two things: play the demo, or show the highscore list for a short time
        self.demo_or_highscore = (not self.demo_or_highscore) and self.caveset.cave_demo is not None
        if self.demo_or_highscore:
            self.start_demo()
        else:
            self.show_highscores()

    def start_demo(self) -> None:
        if self.game_status == GameStatus.WAITING:
            if self.caveset.cave_demo:
                self.level = 0
                self.load_next_level(intro_popup=False)
                self.game_status = GameStatus.REVEALING_DEMO     # the sound is already being played.
                self.reveal_frame = self.frame + self.fps * self.reveal_duration
                self.movement = DemoMovementInfo(self.caveset.cave_demo)  # is reset to regular handling when demo ends/new level
            else:
                self.game.popup("This cave set doesn't have a demo.", duration=3)
            
    def show_highscores(self) -> None:
        def reset_game_status():
            self.game_status = GameStatus.WAITING
        if self.game_status == GameStatus.WAITING:
            self.game_status = GameStatus.HIGHSCORE
            if self.game.smallwindow:
                smallname = self.caveset.name.replace('.', '').replace("Vol", "").replace("vol", "")[:16]
                txt = [smallname, "\x0e\x0e\x0eHigh Scores\x0e\x0e"]
                for pos, (score, name) in enumerate(self.highscores, start=1):
                    name = "".join([char if ord(char) > 31 and ord(char) < 128 else '?' for char in name])
                    txt.append("{:d} {:\x0f<7s} {:_>6d}".format(pos, name, score))
            else:
                caveset_name = TextHelper.center_string("\x05" + self.caveset.name + "\x05", 22)
                txt = [caveset_name, "\n\x0e\x0e\x0e High Scores \x0e\x0e\x0e\n-------------------\n"]
                for pos, (score, name) in enumerate(self.highscores, start=1):
                    name = "".join([char if ord(char) > 31 and ord(char) < 128 else '?' for char in name])
                    txt.append("\x0f{:d}\x0f {:\x0f<7s}\x0f {:_>6d}".format(pos, name, score))
            self.game.popup("\n".join(txt), 12, on_close=reset_game_status, prealigned=True)

    def pause(self) -> None:
        if self.game_status == GameStatus.PLAYING:
            self.time_paused = datetime.datetime.now()
            self.game_status = GameStatus.PAUSED
        elif self.game_status == GameStatus.PAUSED:
            if self.timelimit:
                pause_duration = datetime.datetime.now() - self.time_paused
                self.timelimit = self.timelimit + pause_duration
            self.game_status = GameStatus.PLAYING

    def suicide(self) -> None:
        if self.rockford_cell:
            self.explode(self.rockford_cell)
        else:
            self.life_lost()

    def cheat_skip_level(self) -> None:
        if self.game_status in (GameStatus.PLAYING, GameStatus.PAUSED):
            self.cheat_used = True
            self.load_level(self.level % self.caveset.num_caves + 1)

    def draw_rectangle(self, obj: objects.GameObject, x1: int, y1: int, width: int, height: int,
                       fillobject: objects.GameObject=None) -> None:
        self.draw_line(obj, x1, y1, width, Direction.RIGHT)
        self.draw_line(obj, x1, y1 + height - 1, width, Direction.RIGHT)
        self.draw_line(obj, x1, y1 + 1, height - 2, Direction.DOWN)
        self.draw_line(obj, x1 + width - 1, y1 + 1, height - 2, Direction.DOWN)
        if fillobject is not None:
            for y in range(y1 + 1, y1 + height - 1):
                self.draw_line(fillobject, x1 + 1, y, width - 2, Direction.RIGHT)

    def draw_line(self, obj: objects.GameObject, x: int, y: int, length: int, direction: Direction) -> None:
        dx, dy = {
            Direction.LEFT: (-1, 0),
            Direction.RIGHT: (1, 0),
            Direction.UP: (0, -1),
            Direction.DOWN: (0, 1),
            Direction.LEFTUP: (-1, -1),
            Direction.RIGHTUP: (1, -1),
            Direction.LEFTDOWN: (-1, 1),
            Direction.RIGHTDOWN: (1, 1)
        }[direction]
        for _ in range(length):
            self.draw_single(obj, x, y)
            x += dx
            y += dy

    def draw_single(self, obj: objects.GameObject, x: int, y: int, initial_direction: Direction=Direction.NOWHERE) -> None:
        self.draw_single_cell(self.cave[x + y * self.width], obj, initial_direction)

    def draw_single_cell(self, cell: Cell, obj: objects.GameObject, initial_direction: Direction=Direction.NOWHERE) -> None:
        cell.obj = obj
        cell.direction = initial_direction
        cell.frame = self.frame   # make sure the new cell is not immediately scanned
        if cell.obj in (objects.ROCKFORD, objects.DIAMONDBIRTH, objects.EXPLOSION):
            cell.anim_start_gfx_frame = self.graphics_frame_counter   # this makes sure that (new) anims start from the first frame
        else:
            cell.anim_start_gfx_frame = 0 # other objects should always sync up across the entire map
        cell.falling = False
        if obj.id == objects.MAGICWALL.id:
            if not self.magicwall["active"]:
                obj = objects.BRICK
        elif obj.id == objects.ROCKFORDBIRTH_1.id:
            # RockfordBirth1 is set to look the same as the inbox, since first the crack sound is heard, and then next frame,
            # the actual rockford birth animation is played
            obj = objects.INBOXBLINKING_1 if self.inbox_outbox_blink_state else objects.INBOXBLINKING_2
        self.game.set_canvas_tile(cell.x, cell.y, obj)
        # animation is handled by the graphics refresh

    def clear_cell(self, cell: Cell) -> None:
        self.draw_single_cell(cell, objects.BONUSBG if self.bonusbg_frame > self.frame else objects.EMPTY)

    def get(self, cell: Cell, direction: Direction=Direction.NOWHERE) -> Cell:
        # retrieve the cell relative to the given cell
        # deals with wrapping around the up/bottom edge
        cell_index = cell.x + cell.y * self.width + self._dirxy[direction]
        # cave_delta_x and cave_delta_y represent the shift from (0, 0) 
        # that accounts for the cave resize and extended open border mirror tiles
        if self.open_horizontal_borders:
            if cell.x == self.cave_delta_x and (direction == Direction.LEFT or direction == Direction.LEFTDOWN or direction == Direction.LEFTUP):
                cell_index = self.cave_orig_width + self.cave_delta_x + cell.y * self.width + self._dirxy[direction]
                if self.lineshift:
                    if cell.y != self.cave_delta_y:
                        cell_index -= self.width
            elif cell.x == self.cave_orig_width - 1 + self.cave_delta_x and (direction == Direction.RIGHT or direction == Direction.RIGHTDOWN or direction == Direction.RIGHTUP):
                cell_index = cell.y * self.width - 1 + self.cave_delta_x + self._dirxy[direction]
                if self.lineshift:
                    if cell.y != self.cave_orig_height + self.cave_delta_y - 1:
                        cell_index += self.width
        if self.open_vertical_borders or self.wraparound: # GDash: wraparound is treated as an open vertical border
            if cell.y == self.cave_delta_y and (direction == Direction.UP or direction == Direction.LEFTUP or direction == Direction.RIGHTUP):
                cell_index = (self.cave_orig_height + self.cave_delta_y) * self.width + cell.x + self._dirxy[direction]
            elif cell.y == self.cave_orig_height - 1 + self.cave_delta_y and (direction == Direction.DOWN or direction == Direction.LEFTDOWN or direction == Direction.RIGHTDOWN):
                cell_index = cell.x + (self.cave_delta_y * self.width)
                if direction == Direction.LEFTDOWN:
                    cell_index -= 1
                elif direction == Direction.RIGHTDOWN:
                    cell_index += 1
        if self.lineshift:
            if cell.x == self.cave_orig_width - 1 + self.cave_delta_x and cell.y == self.cave_orig_height - 1 + self.cave_delta_y and direction == Direction.RIGHT:
                # wrap around lower edge
                cell_index = (self.cave_delta_y * self.width) + self.cave_delta_x
            if cell.x == self.cave_delta_x and cell.y == self.cave_delta_y and direction == Direction.LEFT:
                # wrap around upper edge
                cell_index = ((self.cave_delta_y + self.cave_orig_height - 1) * self.width) + self.cave_orig_width + self.cave_delta_x - 1
        if not self.wraparound:
            if not self.lineshift and not self.open_horizontal_borders and ((cell.x == self.cave_delta_x and direction == Direction.LEFT) \
                or (cell.x == self.cave_orig_width - 1 + self.cave_delta_x and direction == Direction.RIGHT)):
                return Cell(objects.STEEL, cell.x, cell.y)  # do not allow to escape the horizontal border of the map
            if not self.open_vertical_borders and ((cell.y == self.cave_delta_y and direction == Direction.UP) \
                or (cell.y == self.cave_orig_height - 1 + self.cave_delta_y and direction == Direction.DOWN)):
                return Cell(objects.STEEL, cell.x, cell.y)  # do not allow to escape the vertical border of the map
        return self.cave[cell_index]

    def move(self, cell: Cell, direction: Direction=Direction.NOWHERE) -> Optional[Cell]:
        # move the object in the cell to the given relative direction
        if direction == Direction.NOWHERE:
            return None  # no movement...
        newcell = self.get(cell, direction)
        self.draw_single_cell(newcell, cell.obj)
        newcell.falling = cell.falling
        newcell.direction = cell.direction
        self.clear_cell(cell)
        cell.falling = False
        cell.direction = Direction.NOWHERE
        return newcell

    def push(self, cell: Cell, direction: Direction=Direction.NOWHERE) -> Cell:
        # try to push the thing in the given direction
        pushedcell = self.get(cell, direction)
        targetcell = self.get(pushedcell, direction)
        if targetcell.isempty():
            # GDash source uses 250000 out of 1000000 probability, light boulder is always pushable
            if pushedcell.islight() or random.randrange(0, 1000000) < 250000:
                self.move(pushedcell, direction)
                self.fall_sound(targetcell, pushing=True)
                if not self.movement.grab:
                    newcell = self.move(cell, direction)
                    if newcell:
                        cell = newcell
        self.movement.pushing = True
        return cell

    def cells_with_animations(self) -> List[Cell]:
        return [cell for cell in self.cave if cell.obj.sframes]

    def mirror_border_tiles(self) -> List[Cell]:
        return [cell for cell in self.cave if cell.obj.id == objects.BORDER_MIRROR.id]

    def update(self, graphics_frame_counter: int) -> None:
        self.graphics_frame_counter = graphics_frame_counter           # we store this to properly sync up animation frames
        self.diamond_sound_played = self.boulder_sound_played = False  # prevent grindy sounds on maps like Blifil
        self.inbox_outbox_blink_state = not self.inbox_outbox_blink_state # for inbox and outbox blinking animation
        self.frame_start()
        if self.game_status in (GameStatus.REVEALING_DEMO, GameStatus. REVEALING_PLAY):
            if self.reveal_frame > self.frame:
                return
            # reveal period has ended
            audio.silence_audio("cover")
            self.game.tilesheet.all_dirty()  # force full redraw
            if self.game_status == GameStatus.REVEALING_DEMO:
                self.game_status = GameStatus.DEMO
            elif self.game_status == GameStatus.REVEALING_PLAY:
                self.game_status = GameStatus.PLAYING
        if self.game_status not in (GameStatus.PLAYING, GameStatus.DEMO):
            return
        if not self.level_won:
            # sweep the cave
            for cell in self.cave:
                if cell.obj.id == objects.BORDER_MIRROR.id or cell.obj.id == objects.FILLERWALL.id:
                    continue # not processed in the cave scanning order
                if cell.frame < self.frame:
                    if cell.falling:
                        self.update_falling(cell)
                    elif cell.canfall():
                        self.update_canfall(cell)
                    elif cell.isexplosion():
                        self.update_explosion(cell)
                    elif cell.isfirefly():
                        self.update_firefly(cell)
                    elif cell.isbutterfly():
                        self.update_butterfly(cell)
                    elif cell.isamoeba():
                        self.update_amoeba(cell)
                    elif cell.isslime():
                        self.update_slime(cell)
                    elif cell.isexpandingwall():
                        self.update_expandingwall(cell)
                    elif cell.isrockford():
                        self.update_rockford(cell)
                    elif cell.isinbox():
                        self.update_inbox(cell)
                    elif cell.obj.id == objects.OUTBOXCLOSED.id:
                        self.update_outboxclosed(cell)
                    elif cell.obj.id == objects.OUTBOXHIDDEN.id:
                        self.update_outboxhidden(cell)
                    elif cell.isoutboxblinking():
                        self.update_outboxblinking(cell)
                    elif cell.obj.id == objects.BONUSBG.id:
                        if self.bonusbg_frame < self.frame:
                            self.draw_single_cell(cell, objects.EMPTY)
                    elif cell.obj.id in (objects.ROCKFORDBIRTH_1.id, objects.ROCKFORDBIRTH_2.id, objects.ROCKFORDBIRTH_3.id,
                                         objects.ROCKFORDBIRTH_4.id):
                        self.update_rockfordbirth(cell)
        self.frame_end()

    def frame_start(self) -> None:
        # called at beginning of every game logic update
        self.frame += 1
        self.movement.pushing = False
        if not self.movement.moving and self.rockford_cell:
            # TODO: fix the blinking animation somehow
            self.idle["blink"] = random.randint(1, 4) == 1
            if random.randint(1, 16) == 1:
                self.idle["tap"] = not self.idle["tap"]
        else:
            self.idle["blink"] = self.idle["tap"] = False
        self.amoeba["size"] = 0
        self.amoeba["enclosed"] = True
        if self.amoeba["dead"] == objects.DIAMOND and self.magic_wall_stops_amoeba_phase == 1:
            if self.amoeba["size"] > self.amoeba["max"]: # overwrite conversion to diamonds (CSO 206)
                self.amoeba["dead"] = objects.BOULDER
                audio.play_sample("boulder")
                self.magic_wall_stops_amoeba_phase = 2
        if not self.level_won and not self.game_status == GameStatus.OUT_OF_TIME:
            self.rockford_cell = None

    def frame_end(self) -> None:
        # called at end of every game logic update
        if self.amoeba["dead"] is None:
            if self.amoeba["enclosed"] and not self.amoeba["dormant"]:
                self.amoeba["dead"] = objects.DIAMOND       # type: ignore
                audio.silence_audio("amoeba")
                audio.play_sample("diamond1")
            elif self.amoeba["size"] > self.amoeba["max"]:  # type: ignore
                self.amoeba["dead"] = objects.BOULDER       # type: ignore
                audio.silence_audio("amoeba")
                audio.play_sample("boulder")
            elif self.amoeba["slow"] > 0 and self.start_signal_frame != -1: # type: ignore
                self.amoeba["slow"] -= 1                    # type: ignore
        if self.magicwall["active"]:
            self.magicwall["time"] -= 1
            still_magic = self.magicwall["time"] > 0
            if self.magicwall["active"] and not still_magic:
                # magic wall has stopped! stop playing the milling sound
                audio.silence_audio("magic_wall")
            self.magicwall["active"] = still_magic
        secs_before = self.timeremaining.seconds if not self.reverse_time else int(self.reverse_timer)
        if self.timelimit and not self.level_won and self.rockford_cell:
            if self.no_time_limit or self.reverse_time:
                self.timeremaining = datetime.timedelta(seconds=10)
                if self.reverse_time:
                    self.reverse_timer += self.update_timestep
            else:
                self.timeremaining = self.timelimit - datetime.datetime.now()
            secs_after = self.timeremaining.seconds
            if secs_after <= 0:
                self.timeremaining = datetime.timedelta(0)
        secs_after = self.timeremaining.seconds if not self.reverse_time else int(self.reverse_timer)
        if 1 <= secs_after <= 9:
            if self.level_won or secs_after < secs_before:
                audio.play_timeout_sample(10 - secs_after)
        if self.level_won:
            original_update_timestep = self.update_timestep
            #self.update_timestep = 1 / self.game.update_fps
            self.update_timestep = 1 / 20.0 # FIXME: update at 20 fps during the final score count - check Krissz
            if self.timeremaining.seconds > 0 and not self.no_time_limit and not self.reverse_time:
                self.score += self.value_of_a_second
                self.extralife_score += self.value_of_a_second
                self.check_extralife_score()
                self.timeremaining -= datetime.timedelta(seconds=1)
            elif self.reverse_time and self.reverse_timer > 0:
                self.reverse_timer = int(self.reverse_timer)
                sub_score = min(int(self.reverse_timer), 1)
                self.score -= sub_score * self.value_of_a_second
                if self.score < 0:
                    self.score = 0
                self.reverse_timer -= sub_score
                if self.reverse_timer < 0:
                    self.reverse_timer = 0
                if self.reverse_timer == 0:
                    audio.silence_audio("finished")
            elif self.no_time_limit and self.timeremaining.seconds > 0:
                self.timeremaining -= datetime.timedelta(seconds=1)
            else:
                self.update_timestep = original_update_timestep
                if self.game_status == GameStatus.DEMO:
                    self.restart()  # go back to title screen when demo finishes
                else:
                    self.load_next_level()
        elif self.timelimit and self.update_timestep * (self.frame - self.rockford_found_frame) > 10 \
            and not (self.rockford_cell or self.inbox_cell):
            # after 10 seconds with dead rockford we reload the current level
            self.life_lost()

    def focus_cell(self) -> Optional[Cell]:
        focus_cell = self.rockford_cell or self.inbox_cell or self.last_focus_cell
        if focus_cell:
            self.last_focus_cell = focus_cell
            return focus_cell
        # search for the inbox when the game isn't running yet
        if self.level > 0:
            for cell in self.cave:
                if cell.obj.id == objects.INBOXBLINKING.id:
                    self.last_focus_cell = cell
                    break
        return self.last_focus_cell

    def life_lost(self) -> None:
        if self.intermission:
            self.load_next_level()  # don't lose a life, instead skip out of the intermission.
            return
        self.lives = max(0, self.lives - 1)
        if self.lives > 0:
            self.load_level(self.level)  # retry current level
        else:
            self.stop_game(GameStatus.LOST)

    def stop_game(self, status: GameStatus) -> None:
        self.game_status = status
        # enable the code below to remove Rockford from screen when the game is over
        #if self.rockford_cell:
        #    self.clear_cell(self.rockford_cell)
        self.rockford_found_frame = 0
        if self.game.mirrored_border_size > 0 and self.game.stippled_mirrored_border:
            self.game.canvas.delete('mirrorborder') # remove the stippled border overlay if it was present
        if status == GameStatus.LOST:
            audio.play_sample("game_over")
            popuptxt = "Game Over.\n\nScore: {:d}".format(self.score)
        elif status == GameStatus.WON:
            self.lives = 0
            audio.silence_audio("finished")
            popuptxt = "Congratulations, you finished the game!\n\nScore: {:d}".format(self.score)
        else:
            popuptxt = "??invalid status??"
        score_pos = None
        if self.cheat_used or self.start_level_number > 1:
            popuptxt += "\n\nYou cheated, so the score is not recorded."
            score_pos = 0
        elif self.single_life and status != GameStatus.WON:
            # in Single Life mode, only enter the high score if the game is actually won
            score_pos = 0
        else:
            score_pos = self.highscores.score_pos(self.score)
            if score_pos:
                popuptxt += "\n\nYou got a new #{:d} high score!".format(score_pos)

        def ask_highscore_name(position: Optional[int], score):
            if position:
                name = self.game.ask_highscore_name(position, score)
                if name != "":
                    self.highscores.add(name, score)
        self.game.popup(popuptxt, on_close=lambda: ask_highscore_name(score_pos, self.score))

    def load_next_level(self, intro_popup: bool=True) -> None:
        level = self.level + 1
        if level > self.caveset.num_caves:
            self.stop_game(GameStatus.WON)
        else:
            audio.silence_audio("finished")
            self.load_level(level, level_intro_popup=intro_popup)

    def update_canfall(self, cell: Cell) -> None:
        # if the cell below this one is empty, or slime, the object starts to fall
        # (in case of slime, it only falls through of course if the space below the slime is empty)
        cellbelow = self.get(cell, Direction.DOWN)
        if cellbelow.isempty():
            if not cell.falling:
                if not self.game.krissz_engine_compat:
                    self.fall_sound(cell)
                cell.falling = True
                self.update_falling(cell)
        elif cellbelow.isrounded() and not cellbelow.falling:
            if self.get(cell, Direction.LEFT).isempty() and self.get(cell, Direction.LEFTDOWN).isempty():
                if not self.game.krissz_engine_compat:
                    self.fall_sound(cell)
                new_cell = self.move(cell, Direction.LEFT)
                if new_cell:
                    new_cell.falling = True
            elif self.get(cell, Direction.RIGHT).isempty() and self.get(cell, Direction.RIGHTDOWN).isempty():
                if not self.game.krissz_engine_compat:
                    self.fall_sound(cell)
                new_cell = self.move(cell, Direction.RIGHT)
                if new_cell:
                    new_cell.falling = True

    def update_falling(self, cell: Cell) -> None:
        # let the object fall down, explode stuff if explodable!
        cellbelow = self.get(cell, Direction.DOWN)
        if cellbelow.isempty():
            # cell below is empty, move down and continue falling
            self.move(cell, Direction.DOWN)
        elif cellbelow.obj.id == objects.VOODOO.id and cell.obj.id == objects.DIAMOND.id and not self.game.krissz_engine_compat:
            self.clear_cell(cell)   # this is not allowed in Krissz Engine
            self.collect_diamond()  # voodoo doll catches falling diamond - FIXME: is this allowed in C64/GDash?
        elif cellbelow.isexplodable() and (cellbelow.obj.id != objects.VOODOO.id or not self.game.krissz_engine_compat):
            self.explode(cell, Direction.DOWN) # apparently, falling objects do not explode Voodoo Rockford in Krissz Engine
        elif cellbelow.ismagic():
            self.do_magic(cell)
        elif cellbelow.isslime():
            cell.falling = False  # just block falling and wait for permeability
        elif cellbelow.isrounded() and not cellbelow.falling and self.get(cell, Direction.LEFT).isempty() and self.get(cell, Direction.LEFTDOWN).isempty():
            self.fall_sound(cell)
            self.move(cell, Direction.LEFT)
        elif cellbelow.isrounded() and not cellbelow.falling and self.get(cell, Direction.RIGHT).isempty() and self.get(cell, Direction.RIGHTDOWN).isempty():
            self.fall_sound(cell)
            self.move(cell, Direction.RIGHT)
        else:
            cell.falling = False  # falling was blocked by something
            self.fall_sound(cell)

    def update_explosion(self, cell: Cell) -> None:
        if cell.obj.id == objects.EXPLOSION.id:
            num_stages = 5
            change_to_object = objects.EMPTY
        elif cell.obj.id == objects.DIAMONDBIRTH.id:
            num_stages = 4
            change_to_object = objects.DIAMOND
        cell.update_stage += 1
        if cell.update_stage >= num_stages:
            self.draw_single_cell(cell, change_to_object)
            cell.update_stage = 0

    def update_slime(self, cell: Cell) -> None:
        # let the object through a slime if it's permeable
        rand_value = 0
        permeable = False
        if self.krissz_slime_permeability != -1:
            if self.krissz_slime_permeability < 0 or self.krissz_slime_permeability > 8:
                print("Warning: illegal Krissz Engine slime permeability value specified, assuming default 6.")
                self.krissz_slime_permeability = 6
            C64Cave.bdrandom(self.c64_random_slime_seeds)
            rand_value = self.c64_random_slime_seeds[0]
            permeable = (rand_value & self.slime_permeability_patterns[self.krissz_slime_permeability]) == 0
        else:
            rand_value = random.random()
            permeable = rand_value < self.slime_permeability
        if permeable:
            cell_above_slime = self.get(cell, Direction.UP)
            cell_under_slime = self.get(cell, Direction.DOWN)
            if cell_under_slime.isempty() and cell_above_slime.canfall():
                if not self.game.krissz_engine_compat: # no slime sound is played in Krissz Engine
                    audio.play_sample("slime")
                obj = cell_above_slime.obj
                self.clear_cell(cell_above_slime)
                self.draw_single_cell(cell_under_slime, obj)
                cell_under_slime.falling = True

    def update_firefly(self, cell: Cell) -> None:
        # if it hits Rockford or Amoeba it explodes
        # tries to rotate 90 degrees left and move to empty cell in new or original direction
        # if not possible rotate 90 right and wait for next update
        newdir = cell.direction.rotate90left()
        cell_up = self.get(cell, Direction.UP)
        cell_down = self.get(cell, Direction.DOWN)
        cell_left = self.get(cell, Direction.LEFT)
        cell_right = self.get(cell, Direction.RIGHT)
        if cell_up.isrockford() or cell_down.isrockford() or cell_left.isrockford() or cell_right.isrockford():
            self.explode(cell)
        elif cell_up.isamoeba() or cell_down.isamoeba() or cell_left.isamoeba() or cell_right.isamoeba():
            self.explode(cell)
        elif cell_up.obj.id == objects.VOODOO.id or cell_down.obj.id == objects.VOODOO.id \
            or cell_left.obj.id == objects.VOODOO.id or cell_right.obj.id == objects.VOODOO.id:
            self.explode(cell)
            self.death_by_voodoo = True
        elif self.get(cell, newdir).isempty():
            new_cell = self.move(cell, newdir)
            if new_cell:
                new_cell.direction = newdir
        elif self.get(cell, cell.direction).isempty():
            self.move(cell, cell.direction)
        else:
            cell.direction = cell.direction.rotate90right()

    def update_butterfly(self, cell: Cell) -> None:
        # same as firefly except butterflies rotate in the opposite direction
        newdir = cell.direction.rotate90right()
        cell_up = self.get(cell, Direction.UP)
        cell_down = self.get(cell, Direction.DOWN)
        cell_left = self.get(cell, Direction.LEFT)
        cell_right = self.get(cell, Direction.RIGHT)
        if cell_up.isrockford() or cell_down.isrockford() or cell_left.isrockford() or cell_right.isrockford():
            self.explode(cell)
        elif cell_up.isamoeba() or cell_down.isamoeba() or cell_left.isamoeba() or cell_right.isamoeba():
            self.explode(cell)
        elif cell_up.obj.id == objects.VOODOO.id or cell_down.obj.id == objects.VOODOO.id \
                or cell_left.obj.id == objects.VOODOO.id or cell_right.obj.id == objects.VOODOO.id:
            self.explode(cell)
            self.death_by_voodoo = True
        elif self.get(cell, newdir).isempty():
            new_cell = self.move(cell, newdir)
            if new_cell:
                new_cell.direction = newdir
        elif self.get(cell, cell.direction).isempty():
            self.move(cell, cell.direction)
        else:
            cell.direction = cell.direction.rotate90left()
       
    def update_rockfordbirth(self, cell: Cell) -> None:
        cell.update_stage += 1
        if cell.update_stage == 2: # On Krissz Engine, this is when the timer first activates and jumps to one second less
            self.draw_single_cell(cell, self.rockford_birth_stages[cell.update_stage])
            self.start_signal_frame = self.frame # Currently used for timing of start signal, e.g. for Amoeba Slow Time. A bit hacky, consider revising.
            self.timelimit = datetime.datetime.now() + self.timeremaining
            if self.reverse_time:
                self.reverse_timer += 1.0
            if self.diamonds_needed <= 0:
                # need to subtract this from the current number of diamonds in the cave
                numdiamonds = sum([1 for c in self.cave if c.isdiamond()])
                self.diamonds_needed = max(0, numdiamonds + self.diamonds_needed)
        elif cell.update_stage == 4: # the fourth stage is when the birth object is switched to proper Rockford
            if self.game_status in (GameStatus.PLAYING, GameStatus.DEMO):
                cell.update_stage = 0
                cell.frame = self.frame # Rockford is scanned for this frame, won't move
                self.draw_single_cell(cell, objects.ROCKFORD)
                # detect the Rockford cell and also inform the animation system if the player is trying to move
                self.rockford_cell = cell
                self.rockford_found_frame = self.frame
                self.movement.moving_this_update = self.movement.moving # allow the Rockford to animate this frame, but not move yet
                self.inbox_cell = None
        else: # in all other stages, just draw the relevant animation frame
            self.draw_single_cell(cell, self.rockford_birth_stages[cell.update_stage])

    def update_inbox(self, cell: Cell) -> None:
        # after 4 blinks (=2 seconds) or whatever is specified in rockford_birth_time,
        # Rockford spawns in the inbox.
        self.inbox_cell = cell
        update_condition = False
        if self.rockford_birth_time == -1:
            update_condition = self.update_timestep * self.frame > (2.0 + self.reveal_duration)
        else:
            if self.initial_update_frame == 0:
                self.initial_update_frame = self.frame
            update_condition = self.frame >= self.initial_update_frame + self.rockford_birth_time
        if update_condition:
            self.inbox_outbox_blink_state = not self.inbox_outbox_blink_state # flip the state right before transitioning
            self.draw_single_cell(cell, objects.ROCKFORDBIRTH_1)
            audio.play_sample("crack")
        else:
            self.draw_single_cell(cell, objects.INBOXBLINKING_2 if self.inbox_outbox_blink_state else objects.INBOXBLINKING_1)
        # Krissz Engine: if Voodoo Rockford is killed before the level starts, the inbox blows up
        if self.game.krissz_engine_compat and self.death_by_voodoo:
            self.timelimit = datetime.datetime.now()
            self.explode(cell)
            return

    def update_outboxclosed(self, cell: Cell) -> None:
        if self.rockford_found_frame <= 0:
            return   # do nothing if rockford hasn't appeared yet
        if self.diamonds >= self.diamonds_needed:
            if cell.obj.id != objects.OUTBOXBLINKING.id:
                audio.play_sample("crack")
                self.draw_single_cell(cell, objects.OUTBOXBLINKING_2 if self.inbox_outbox_blink_state else objects.OUTBOXBLINKING_1)
    
    def update_outboxblinking(self, cell: Cell) -> None:
        self.draw_single_cell(cell, objects.OUTBOXBLINKING_2 if self.inbox_outbox_blink_state else objects.OUTBOXBLINKING_1)

    def update_outboxhidden(self, cell: Cell) -> None:
        if self.rockford_found_frame <= 0:
            return   # do nothing if rockford hasn't appeared yet
        if self.diamonds >= self.diamonds_needed:
            if cell.obj.id != objects.OUTBOXHIDDENOPEN.id:
                audio.play_sample("crack")
            self.draw_single_cell(cell, objects.OUTBOXHIDDENOPEN)

    def update_amoeba(self, cell: Cell) -> None:
        if self.amoeba["dead"] is not None:
            self.draw_single_cell(cell, self.amoeba["dead"])    # type: ignore
        else:
            self.amoeba["size"] += 1        # type: ignore
            cell_up = self.get(cell, Direction.UP)
            cell_down = self.get(cell, Direction.DOWN)
            cell_left = self.get(cell, Direction.LEFT)
            cell_right = self.get(cell, Direction.RIGHT)
            if cell_up.isempty() or cell_down.isempty() or cell_right.isempty() or cell_left.isempty() \
                    or cell_up.isdirt() or cell_down.isdirt() or cell_right.isdirt() or cell_left.isdirt():
                self.amoeba["enclosed"] = False
                if self.amoeba["dormant"]:
                    # amoeba can grow, so is not dormant anymore
                    self.amoeba["dormant"] = False
                    audio.play_sample("amoeba", repeat=True)  # start playing amoeba sound
            if self.timelimit or self.amoeba_grows_before_spawn:
                grow = random.randint(1, 128) <= 4 if self.amoeba["slow"] > 0 else random.randint(1, 4) == 1
                target_cell = random.choice([cell_up, cell_down, cell_left, cell_right])
                if grow and (target_cell.isdirt() or target_cell.isempty()):
                    self.draw_single_cell(target_cell, cell.obj)

    def update_rockford(self, cell: Cell) -> None:
        self.rockford_cell = cell
        self.rockford_found_frame = self.frame
        limited_time = not (self.reverse_time or self.no_time_limit)
        approaching_timeout = limited_time and (0 <= self.timeremaining.seconds <= 9)
        if self.level_won:
            return
        self.movement.moving_this_update = self.movement.moving # Sync this with repaint if Rockford will move this frame
        new_cell = cell     # type: Optional[Cell]
        if self.death_by_voodoo:
            self.explode(cell)
        elif self.timeremaining.seconds <= 0 and limited_time and not self.level_won:
            self.game_status = GameStatus.OUT_OF_TIME
            self.movement.moving_this_update = False
        elif self.movement.moving:
            targetcell = self.get(cell, self.movement.direction)
            if not targetcell.falling:
                if self.movement.grab:
                    if targetcell.isdirt():
                        if not approaching_timeout:
                            audio.play_sample("walk_dirt")
                        self.clear_cell(targetcell)
                    elif targetcell.isdiamond():
                        self.collect_diamond()
                        self.clear_cell(targetcell)
                    elif targetcell.isoutbox():
                        self.level_won = True   # exit found!
                        self.clear_cell(targetcell)
                        audio.silence_audio()
                        if not self.no_time_limit or self.reverse_time:
                            audio.play_sample("finished", repeat=True)
                        self.movement.stop_all()
                    elif self.movement.direction in (Direction.LEFT, Direction.RIGHT) and targetcell.isboulder() \
                        and not targetcell.isheavy():
                        self.push(cell, self.movement.direction)
                    elif targetcell.isempty():
                        if not approaching_timeout:
                            audio.play_sample("walk_empty")
                elif targetcell.isempty():
                    if not approaching_timeout:
                        audio.play_sample("walk_empty")
                    new_cell = self.move(cell, self.movement.direction)
                elif targetcell.isdirt():
                    if not approaching_timeout:
                        audio.play_sample("walk_dirt")
                    new_cell = self.move(cell, self.movement.direction)
                elif targetcell.isboulder() and self.movement.direction in (Direction.LEFT, Direction.RIGHT) \
                    and not targetcell.isheavy():
                    new_cell = self.push(cell, self.movement.direction)
                elif targetcell.isdiamond():
                    self.collect_diamond()
                    new_cell = self.move(cell, self.movement.direction)
                elif targetcell.isoutbox():
                    new_cell = self.move(cell, self.movement.direction)
                    self.level_won = True   # exit found!
                    audio.silence_audio()
                    if not self.no_time_limit or self.reverse_time:
                        audio.play_sample("finished", repeat=True)
                    self.movement.stop_all()
            self.movement.move_done()
        if new_cell and new_cell is not self.rockford_cell:
            # rockford has moved, tweak his walk animation so it keeps going and is not reset to the first anim frame
            new_cell.anim_start_gfx_frame = 0
        self.rockford_cell = new_cell
        # Open borders: jump into view immediately to imitate smooth transition
        if self.open_horizontal_borders and ((cell.x == self.cave_delta_x and self.movement.direction == Direction.LEFT) or (cell.x == self.cave_orig_width - 1 + self.cave_delta_x and self.movement.direction == Direction.RIGHT)):
            self.game.scroll_focuscell_into_view(immediate=True)
        if self.open_vertical_borders and ((cell.y == self.cave_delta_y and self.movement.direction == Direction.UP) or (cell.y == self.cave_orig_height - 1 + self.cave_delta_y and self.movement.direction == Direction.DOWN)):
            self.game.scroll_focuscell_into_view(immediate=True)
        # - Open borders -

    def update_expandingwall(self, cell: Cell) -> None:
        # cell is an expanding wall (horizontally or vertically or both directions)
        expanded = False
        if cell.obj in {objects.HEXPANDINGWALL, objects.EXPANDINGWALL}:
            left = self.get(cell, Direction.LEFT)
            right = self.get(cell, Direction.RIGHT)
            if left.isempty():
                self.draw_single_cell(left, cell.obj)
                expanded = True
            if right.isempty():
                self.draw_single_cell(right, cell.obj)
                expanded = True
        if cell.obj in {objects.VEXPANDINGWALL, objects.EXPANDINGWALL}:
            up = self.get(cell, Direction.UP)
            down = self.get(cell, Direction.DOWN)
            if up.isempty():
                self.draw_single_cell(up, cell.obj)
                expanded = True
            if down.isempty():
                self.draw_single_cell(down, cell.obj)
                expanded = True
        if expanded and not self.boulder_sound_played:
            audio.play_sample("boulder")
            self.boulder_sound_played = True

    def do_magic(self, cell: Cell) -> None:
        # something (diamond, boulder) is falling on a magic wall
        if self.magicwall["time"] > 0:
            if not self.magicwall["active"]:
                # magic wall activates! play sound. Will be silenced once the milling timer runs out.
                audio.play_sample("magic_wall", repeat=True)
                # substandard: if magic wall stops amoeba, switch all amoeba into diamonds upon activation.
                if self.magic_wall_stops_amoeba and self.magic_wall_stops_amoeba_phase == 0:
                    audio.silence_audio("amoeba")
                    self.amoeba["dead"] = objects.DIAMOND
                    self.magic_wall_stops_amoeba_phase = 1 # trigger Magic Wall Stops Amoeba starting this moment.
            self.magicwall["active"] = True
            obj = cell.obj
            self.clear_cell(cell)
            cell_under_wall = self.get(self.get(cell, Direction.DOWN), Direction.DOWN)
            if cell_under_wall.isempty():
                if obj.id == objects.DIAMOND.id:
                    self.draw_single_cell(cell_under_wall, objects.BOULDER)
                elif obj.id in {objects.BOULDER.id, objects.MEGABOULDER.id, objects.LIGHTBOULDER.id}:
                    self.draw_single_cell(cell_under_wall, objects.DIAMOND)
                cell_under_wall.falling = True
        else:
            # magic wall is disabled, stuff falling on it just disappears (a sound is already played)
            self.clear_cell(cell)
        # play the diamond sound regardless of what happens (per Krissz Engine, GDash, BDCFF specs)
        if not self.diamond_sound_played:
            if self.game.krissz_engine_compat:
                audio.play_krissz_diamond_sample()
            else:
                audio.play_sample("diamond" + str(random.randint(1, 6)))
            self.diamond_sound_played = True

    def update_scorebar(self) -> None:
        # draw the score bar.
        # note: the following is a complex score bar including keys, but those are not used in the C64 boulderdash:
        # text = ("\x08{lives:2d}  \x0c {keys:02d}\x7f\x7f\x7f  {diamonds:<10s}  {time:s}  $ {score:06d}".format(
        #     lives=self.lives,
        #     time=str(self.timeremaining)[3:7],
        #     score=self.score,
        #     diamonds="\x0e {:02d}/{:02d}".format(self.diamonds, self.diamonds_needed),
        #     keys=self.keys["diamond"]
        # )).ljust(width)
        # self.game.tilesheet_score.set_tiles(0, 0, tiles.text2tiles(text))
        # if self.keys["one"]:
        #     self.game.tilesheet_score[9, 0] = objects.KEY1.spritex + objects.KEY1.spritey * self.game.tile_image_numcolumns
        # if self.keys["two"]:
        #     self.game.tilesheet_score[10, 0] = objects.KEY2.spritex + objects.KEY2.spritey * self.game.tile_image_numcolumns
        # if self.keys["three"]:
        #     self.game.tilesheet_score[11, 0] = objects.KEY3.spritex + objects.KEY3.spritey * self.game.tile_image_numcolumns
        width = self.game.tilesheet_score.width
        if self.level < 1:
            # level has not been loaded yet (we're still at the title screen)
            if self.game.smallwindow and self.game.c64colors:
                self.game.set_scorebar_tiles(0, 0, tiles.text2tiles("Welcome to Boulder Caves+ 'authentic'".center(width)))
            else:
                self.game.set_scorebar_tiles(0, 0, tiles.text2tiles("Welcome to Boulder Caves+".center(width)))
            self.game.set_scorebar_tiles(0, 1, tiles.text2tiles("F1\x04New game F4\x04Scores F10\x04Quit".center(width)))
            if not self.game.smallwindow and not self.game.window30x18:
                left = [objects.MEGABOULDER.tile(), objects.FLYINGDIAMOND.tile(), objects.DIAMOND.tile(), objects.ROCKFORD.pushleft.tile()]
                right = [objects.ROCKFORD.pushright.tile(), objects.DIAMOND.tile(), objects.FLYINGDIAMOND.tile(), objects.MEGABOULDER.tile()]
                self.game.set_scorebar_tiles(0, 0, left)
                self.game.set_scorebar_tiles(0, 1, left)
                self.game.set_scorebar_tiles(width - len(right), 0, right)
                self.game.set_scorebar_tiles(width - len(right), 1, right)
            return
        if self.reverse_time:
            timervalue = "{time:.0f}".format(time=self.reverse_timer)
        elif self.no_time_limit:
            timervalue = "   "
        else:
            timervalue = "{time:>3d}".format(time=self.timeremaining.seconds)
        self.fmt_time = timervalue
        if self.game.window30x18:
            if self.diamonds < self.diamonds_needed:
                diamonds_line = f"{tiles.colorize_digits(str(self.diamonds_needed))}\x0e{self.diamondvalue_initial}"
            else:
                diamonds_line = f"\x0e\x0e\x0e{self.diamondvalue_extra}"
            text = ("{lifeindicator} {diamondline:>7s}  {diamonds:<3s} {time:>4s}   {score:06d}".format(
                lifeindicator="\x08{lives:2d}".format(lives=self.lives) if not self.single_life else "",
                time=self.fmt_time,
                score=self.score,
                diamondline = diamonds_line,
                diamonds=tiles.colorize_digits("{:03d}".format(self.diamonds)),
            )).ljust(width)
        else:
            if self.diamonds < self.diamonds_needed:
                diamonds_line = f"{tiles.colorize_digits(str(self.diamonds_needed))}\x0e{self.diamondvalue_initial}"
            else:
                diamonds_line = f"\x0e\x0e\x0e{self.diamondvalue_extra}"
            text = ("{lifeindicator}   {diamondline:>6s}  {diamonds:<6s}   {time:5s}   $ {score:06d}".format(
                lifeindicator="\x08{lives:2d}".format(lives=self.lives) if not self.single_life else "",
                time=self.fmt_time,
                score=self.score,
                diamondline = diamonds_line,
                diamonds=tiles.colorize_digits("{:03d}".format(self.diamonds)),
            )).ljust(width)
        self.game.tilesheet_score.set_tiles(0, 0, tiles.text2tiles(text))
        if self.game_status == GameStatus.WON:
            if self.game.window30x18:
                line_tiles = tiles.text2tiles("C O N G R A T U L A T I O N S".center(width))
            else:
                line_tiles = tiles.text2tiles("\x0e  C O N G R A T U L A T I O N S  \x0e".center(width))
        elif self.game_status == GameStatus.LOST:
            line_tiles = tiles.text2tiles("\x0b  G A M E   O V E R  \x0b".center(width))
        elif self.game_status == GameStatus.PAUSED:
            line_tiles = tiles.text2tiles("\x08  P A U S E D  \x08".center(width))
        elif self.game_status == GameStatus.OUT_OF_TIME:
            line_tiles = tiles.text2tiles("\x0b  O U T   O F   T I M E  \x0b".center(width))
        else:
            if self.level_name.lower().startswith(("cave ", "intermission ")):
                fmt = "{:s}"
            else:
                fmt = "Bonus: {:s}" if self.intermission else "Cave: {:s}"
            if self.game_status == GameStatus.DEMO:
                fmt += " [Demo]"
            if self.playtesting:
                fmt += " [Testing]"
            line_tiles = tiles.text2tiles(fmt.format(self.level_name).center(width))
        self.game.set_scorebar_tiles(0, 1, line_tiles[:40] if not self.game.window30x18 else line_tiles[:30]) # line 2

    def fall_sound(self, cell: Cell, pushing: bool=False) -> None:
        if cell.isboulder() or cell.iswall():
            if pushing:
                audio.play_sample("box_push")
            else:
                if not self.boulder_sound_played:
                    if self.game.krissz_engine_compat:
                        audio.play_krissz_boulder_sample()
                    else:
                        audio.play_sample("boulder")
                    self.boulder_sound_played = True
        elif cell.isdiamond():
            if not self.diamond_sound_played:
                if self.game.krissz_engine_compat:
                    audio.play_krissz_diamond_sample()
                else:
                    audio.play_sample("diamond" + str(random.randint(1, 6)))
                self.diamond_sound_played = True

    def collect_diamond(self) -> None:
        audio.silence_audio("collect_diamond")
        audio.play_sample("collect_diamond")
        self.diamonds += 1
        points = self.diamondvalue_extra if self.diamonds > self.diamonds_needed else self.diamondvalue_initial
        self.score += points
        self.extralife_score += points
        if self.diamonds >= self.diamonds_needed and not self.flash:
            self.flash = self.frame + 1
        self.check_extralife_score()

    def check_extralife_score(self) -> None:
        # extra life every 500 points (or as specified in bonus_life_points)
        if self.extralife_score >= self.caveset.bonus_life_points:
            self.extralife_score -= self.caveset.bonus_life_points
            self.add_extra_life()

    def add_extra_life(self) -> None:
        if self.lives < 9 and not self.single_life:   # 9 is the maximum number of lives
            self.lives += 1
            audio.play_sample("extra_life")
            for cell in self.cave:
                if cell.obj.id == objects.EMPTY.id:
                    self.draw_single_cell(cell, objects.BONUSBG)
                    self.bonusbg_frame = self.frame + self.fps * 6   # sparkle for 6 seconds

    def add_extra_time(self, seconds: float) -> None:
        assert self.timelimit
        self.timelimit += datetime.timedelta(seconds=seconds)

    def explode(self, cell: Cell, direction: Direction=Direction.NOWHERE) -> None:
        explosion_sample = "explosion"
        explosioncell = self.get(cell, direction)
        if explosioncell.isbutterfly():
            explode_obj = objects.DIAMONDBIRTH
        else:
            explode_obj = objects.EXPLOSION
        if explosioncell.obj.id == objects.VOODOO.id and not self.game.krissz_engine_compat:
            explosion_sample = "voodoo_explosion"
            self.draw_single_cell(explosioncell, objects.GRAVESTONE)
        else:
            self.draw_single_cell(explosioncell, explode_obj)
        for direction in Direction:
            if direction == Direction.NOWHERE:
                continue
            try:
                cell = self.get(explosioncell, direction)
                if cell.isconsumable():
                    if cell.obj.id == objects.VOODOO.id and not self.game.krissz_engine_compat:
                        explosion_sample = "voodoo_explosion"
                        self.draw_single_cell(cell, objects.GRAVESTONE)
                    else:
                        self.draw_single_cell(cell, explode_obj)
            except:
                pass # prevent crashes when e.g. exploding in the bottom row
        audio.play_sample(explosion_sample)


class MovementInfo:
    def __init__(self) -> None:
        self._direction = Direction.NOWHERE
        self.lastXdir = Direction.RIGHT
        self.up = self.down = self.left = self.right = False
        self.grab = False           # is rockford grabbing something?
        self.moving_this_update = False
        self.pushing = False        # is rockford pushing something?

    @property
    def moving(self) -> bool:
        return bool(self._direction != Direction.NOWHERE)

    @property
    def direction(self) -> Direction:
        return self._direction

    @direction.setter
    def direction(self, value: Direction) -> None:
        self._direction = value

    def start_up(self) -> None:
        self._direction = Direction.UP
        self.up = True

    def start_down(self) -> None:
        self._direction = Direction.DOWN
        self.down = True

    def start_left(self) -> None:
        self._direction = Direction.LEFT
        self.left = True
        self.lastXdir = Direction.LEFT

    def start_right(self) -> None:
        self._direction = Direction.RIGHT
        self.right = True
        self.lastXdir = Direction.RIGHT

    def start_grab(self) -> None:
        self.grab = True

    def stop_all(self) -> None:
        self.grab = self.up = self.down = self.left = self.right = False
        self._direction = Direction.NOWHERE

    def stop_grab(self) -> None:
        self.grab = False

    def stop_up(self) -> None:
        self.up = False
        self._direction = self.where() if self._direction == Direction.UP else self._direction

    def stop_down(self) -> None:
        self.down = False
        self._direction = self.where() if self._direction == Direction.DOWN else self._direction

    def stop_left(self) -> None:
        self.left = False
        self._direction = self.where() if self._direction == Direction.LEFT else self._direction

    def stop_right(self) -> None:
        self.right = False
        self._direction = self.where() if self._direction == Direction.RIGHT else self._direction

    def where(self) -> Direction:
        if self.up:
            return Direction.UP
        elif self.down:
            return Direction.DOWN
        elif self.left:
            return Direction.LEFT
        elif self.right:
            return Direction.RIGHT
        else:
            return Direction.NOWHERE

    def move_done(self) -> None:
        pass


class DemoMovementInfo(MovementInfo):
    # movement controller that doesn't respond to user input,
    # and instead plays a prerecorded sequence of moves.
    def __init__(self, demo_moves: Sequence[int]) -> None:
        super().__init__()
        self.demo_direction = Direction.NOWHERE
        self.demo_moves = self.decompressed(demo_moves)
        self.demo_finished = False

    @property
    def moving(self) -> bool:
        return True

    @property
    def direction(self) -> Direction:
        return self.demo_direction

    @direction.setter
    def direction(self, value: Direction) -> None:
        pass

    def move_done(self) -> None:
        try:
            self.demo_direction = next(self.demo_moves)
            if self.demo_direction == Direction.LEFT:
                self.lastXdir = Direction.LEFT
            elif self.demo_direction == Direction.RIGHT:
                self.lastXdir = Direction.RIGHT
        except StopIteration:
            self.demo_finished = True
            self.demo_direction = Direction.NOWHERE

    def decompressed(self, demo: Sequence[int]) -> Generator[Direction, None, None]:
        for step in demo:
            d = step & 0x0f
            if d == 0:
                break
            direction = {
                0x0f: Direction.NOWHERE,
                0x07: Direction.RIGHT,
                0x0b: Direction.LEFT,
                0x0d: Direction.DOWN,
                0x0e: Direction.UP
            }[d]
            for _ in range(step >> 4):
                yield direction
