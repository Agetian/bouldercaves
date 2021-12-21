"""
Boulder Caves+ - a Boulder Dash (tm) clone.
Krissz Engine-compatible remake based on Boulder Caves 5.7.2.

This module contains the GUI window logic, handles keyboard input
and screen drawing via tkinter bitmaps.

Original version written by Irmen de Jong (irmen@razorvine.net)
Extended version by Michael Kamensky

License: GNU GPL 3.0, see LICENSE
"""

import os
import random
import sys
import math
import tkinter
import tkinter.messagebox
from tkinter import simpledialog
import pkgutil
import time
from typing import Tuple, Sequence, List, Iterable, Callable, Optional
from .gamelogic import GameState, Direction, GameStatus, HighScores
from .caves import colorpalette, Palette
from .helpers import TextHelper, KeyHelper
from . import audio, synthsamples, tiles, objects, bdcff

__version__ = "1.1.0"


class BoulderWindow(tkinter.Tk):
    update_fps = 30
    update_timestep = 1 / update_fps
    visible_columns = 40
    visible_rows = 22
    scalexy = 2.0

    def __init__(self, title: str, fps: int=30, scale: float=2,
                 c64colors: bool=False, c64_alternate_tiles: bool=False, smallwindow: bool=False,
                 hidexwalls: bool=False, window30x18: bool=False, animatereveal: bool=False, 
                 krisszcompat: bool=False, krissztileset: bool=False, fullscreen: bool=False,
                 size_defined: bool=False, optimize: int=0, mirror_size: int=0, 
                 stipple_mirror: bool=False) -> None:
        self.smallwindow = smallwindow
        self.fullscreen = fullscreen
        self.window30x18 = window30x18
        if smallwindow:
            if int(scale) != scale:
                print("Warning: Scaling must be integer, not a fraction, when using the small scrolling window, adjusting the scaling value.")
                scale -= 0.5
            self.visible_columns = 20
            self.visible_rows = 12
        elif window30x18:
            self.visible_columns = 30 # Krissz Engine-style size for window
            self.visible_rows = 18
        super().__init__()
        if self.fullscreen and not size_defined:
            scale = self.determine_optimal_scale(smallwindow or mirror_size > 0)
        scale = scale / 2
        self.update_fps = fps
        self.update_timestep = 1 / fps
        self.perf_optimization_level = optimize # 0 = no optimization, 1 = light optimization, 2 = moderate optimization, 3 = heavy optimization
        self.scalexy = scale
        self.c64colors = c64colors
        self.c64_alternate_tiles = c64_alternate_tiles
        self.krissz_tileset = krissztileset
        self.hidexwalls = hidexwalls
        self.animatereveal = animatereveal
        self.krissz_engine_compat = krisszcompat
        if self.visible_columns <= 4 or self.visible_columns > 100 or self.visible_rows <= 4 or self.visible_rows > 100:
            raise ValueError("invalid visible size")
        if self.scalexy not in (1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5, 5.5, 6, 6.5, 7, 7.5, 8, 8.5, 9, 9.5, 10):
            raise ValueError("invalid scalexy factor", self.scalexy)
        if mirror_size > 0 and self.scalexy != int(self.scalexy):
            print("Warning: extended open border mode is buggy in fractional scale size, making the window smaller to use an integer scale value") # TODO: figure out where this is failing for e.g. scalexy == 2.5
            self.scalexy -= 0.5
        self.geometry("+200+40")
        self.resizable(0, 0)
        self.configure(borderwidth=16, background="black")
        self.wm_title(title)
        self.appicon = tkinter.PhotoImage(data=pkgutil.get_data(__name__, "gfx/gdash_icon_48.gif"))
        self.wm_iconphoto(self, self.appicon)
        if self.fullscreen:
            self.geometry("{0}x{1}+0+0".format(self.winfo_screenwidth(), self.winfo_screenheight()))
            self.wm_attributes("-fullscreen", True)
            self.config(cursor="none")
        if sys.platform == "win32":
            # tell windows to use a new toolbar icon
            import ctypes
            myappid = 'net.Razorvine.Bouldercaves.game'  # arbitrary string
            try:
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
            except AttributeError:
                pass    # that function is not available on windows versions older than win7
        if smallwindow:
            self.tilesheet_score = tiles.Tilesheet(self.visible_columns * 2, 2, self.visible_columns * 2, 2)
            score_canvas_height = 16 * self.scalexy
        else:
            self.tilesheet_score = tiles.Tilesheet(self.visible_columns, 2, self.visible_columns, 2)
            score_canvas_height = 32 * self.scalexy
        self.popup_tiles_save = None   # type: Optional[Tuple[int, int, int, int, Sequence[Iterable[int]]]]
        self.on_popup_closed = None   # type: Optional[Callable]
        self.scrolling_into_view = False
        self.scorecanvas = tkinter.Canvas(self, width=self.visible_columns * 16 * self.scalexy,
                                          height=score_canvas_height, borderwidth=0, highlightthickness=0, background="black")
        self.canvas = tkinter.Canvas(self, width=self.visible_columns * 16 * self.scalexy,
                                     height=self.visible_rows * 16 * self.scalexy,
                                     borderwidth=0, highlightthickness=0, background="black",
                                     xscrollincrement=self.scalexy, yscrollincrement=self.scalexy)
        self.c_tiles = []         # type: List[str]
        self.cscore_tiles = []    # type: List[str]
        self.view_x = 0
        self.view_y = 0
        self.canvas.view_x = self.view_x        # type: ignore
        self.canvas.view_y = self.view_y        # type: ignore
        self.mirrored_border_size = mirror_size # mirrored borders beyond the open boundary
        self.stippled_mirrored_border = stipple_mirror   # overlay a stipple pattern to indicate the mirrored border
        self.tile_images = []  # type: List[tkinter.PhotoImage]
        self.playfield_columns = 0
        self.playfield_rows = 0
        self.create_tile_images()
        self.create_canvas_playfield_and_tilesheet(40, 22)
        self.bind("<KeyPress>", self.keypress)
        self.bind("<KeyRelease>", self.keyrelease)
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.scorecanvas.pack(pady=(0, 10))
        self.canvas.pack()
        self.gfxupdate_starttime = 0.0
        self.game_update_dt = 0.0
        self.graphics_update_dt = 0.0
        self.graphics_frame = 0
        self.popup_frame = 0
        self.last_demo_or_highscore_frame = 0
        if self.hidexwalls:
            for obj in {objects.VEXPANDINGWALL, objects.HEXPANDINGWALL, objects.EXPANDINGWALL}:
                obj.spritex = 5
                obj.spritey = 0
                obj._tile = 5
        self.last_rockford_sprite = None # for end of level continuous animation
        self.keymap = KeyHelper.load_key_definitions() # load a custom key map if available
        self.gamestate = GameState(self)

    def determine_optimal_scale(self, integer_only) -> int:
        screen_width = tkinter.Tk.winfo_screenwidth(self)
        screen_height = tkinter.Tk.winfo_screenheight(self)
        for size in range(1, 10):
            scale = (size + 1) / 2
            if integer_only and scale != int(scale):
                continue
            playfield_width = self.visible_columns * 16 * scale
            playfield_height = (self.visible_rows + 2) * 16 * scale # +2 to account for the score bar
            if playfield_width > screen_width or playfield_height > screen_height:
                return size if not self.smallwindow else size - 1
        return 10 if not self.smallwindow else 9

    def destroy(self) -> None:
        audio.shutdown_audio()
        self.gamestate.destroy()
        super().destroy()
            
    def start(self) -> None:
        self.gfxupdate_starttime = time.perf_counter()
        self.game_update_dt = 0.0
        self.graphics_update_dt = 0.0
        self.graphics_frame = 0
        alignment = 22
        if self.smallwindow:
            alignment = 16
        elif self.visible_columns == 40:
            alignment = 24
        if not self.gamestate.playtesting:
            cs = self.gamestate.caveset
            playing = "Playing caveset:".center(alignment)
            name = TextHelper.center_string(cs.name, alignment) if len(cs.name) > alignment - 1 else cs.name.center(alignment)
            author = f"by {cs.author}".center(alignment)
            date = f"({cs.date})".center(alignment)
            if self.smallwindow:
                fmt = "{playing}\n\n{name}\n\n{author}\n\n{date}"
            else:
                fmt = "{playing}\n\n{name}\n\n{author}\n\n{date}"
            self.popup(fmt.format(playing=playing, name=name, author=author, date=date), duration=3, prealigned=True)
        self.gamestate.update_scorebar()
        self.tick_loop()
    
    def tick_loop(self) -> None:
        now = time.perf_counter()
        dt = now - self.gfxupdate_starttime
        self.game_update_dt += dt
        while self.game_update_dt > self.gamestate.update_timestep:
            self.game_update_dt -= self.gamestate.update_timestep
            self.update_game()
        self.graphics_update_dt += dt
        if self.gamestate.game_status in (GameStatus.REVEALING_DEMO, GameStatus.REVEALING_PLAY) and not self.popup_tiles_save:
            self.do_reveal()
        if self.graphics_update_dt > self.update_timestep:
            self.graphics_update_dt -= self.update_timestep
            #if self.graphics_update_dt >= self.update_timestep:
                #print("Gfx update too slow to reach {:d} fps!".format(self.update_fps))
            self.repaint()
        self.gfxupdate_starttime = now
        self.after(1000 // 60, self.tick_loop)

    def restart(self):
        if self.gamestate.playtesting:
            print("Exiting game because of playtest mode (returning to editor).")
            raise SystemExit
        self.create_canvas_playfield_and_tilesheet(40, 22)
        self.scrollxypixels(0, 0)
        self.gamestate.restart()

    def keypress(self, event) -> None:
        if self.keymap["snap"] == "Control" and (event.keysym.startswith("Control") or event.state & 4):
            self.gamestate.movement.start_grab()
        elif self.keymap["snap"] == "Alt" and event.keysym.startswith("Alt"):
            self.gamestate.movement.start_grab()
        if event.keysym == self.keymap["down"]:
            self.gamestate.movement.start_down()
        elif event.keysym == self.keymap["up"]:
            self.gamestate.movement.start_up()
        elif event.keysym == self.keymap["left"]:
            self.gamestate.movement.start_left()
            self.last_rockford_sprite = objects.ROCKFORD.left
        elif event.keysym == self.keymap["right"]:
            self.gamestate.movement.start_right()
            self.last_rockford_sprite = objects.ROCKFORD.right
        elif event.keysym == self.keymap["pause"]:
            self.gamestate.pause()
        elif event.keysym == "Escape" or event.keysym == self.keymap["suicide"]:
            self.popup_close()
            if self.gamestate.game_status in (GameStatus.LOST, GameStatus.WON):
                self.restart()
            elif self.gamestate.game_status == GameStatus.PLAYING and not self.gamestate.level_won:
                self.gamestate.life_lost() # used to be a suicide() call, which was non-authentic
            elif self.gamestate.game_status == GameStatus.OUT_OF_TIME:
                self.gamestate.life_lost()
            elif self.gamestate.game_status in (GameStatus.DEMO, GameStatus.HIGHSCORE):
                self.restart()
        elif event.keysym == self.keymap["start"] or event.keysym == "F1":
            self.popup_close()
            if self.gamestate.game_status in (GameStatus.LOST, GameStatus.WON):
                self.restart()
            elif self.gamestate.game_status in (GameStatus.DEMO, GameStatus.HIGHSCORE):
                self.restart()
            elif self.gamestate.game_status == GameStatus.PLAYING and not self.gamestate.rockford_cell:
                self.gamestate.life_lost() # used to be a suicide() call, which was non-authentic
            elif self.gamestate.game_status == GameStatus.OUT_OF_TIME:
                self.gamestate.life_lost()
            else:
                if self.gamestate.lives < 0:
                    self.restart()
                if self.gamestate.level < 1:
                    self.gamestate.level = self.gamestate.start_level_number - 1
                    self.gamestate.load_next_level()
        elif event.keysym == "F5":
            self.gamestate.cheat_used = True
            self.gamestate.add_extra_life()
        elif event.keysym == "F6":
            self.gamestate.cheat_used = True
            self.gamestate.add_extra_time(10)

    def keyrelease(self, event) -> None:
        if self.keymap["snap"] == "Control" and (event.keysym.startswith("Control") or not (event.state & 4)):
            self.gamestate.movement.stop_grab()
        elif self.keymap["snap"] == "Alt" and event.keysym.startswith("Alt"):
            self.gamestate.movement.stop_grab()
        if event.keysym == self.keymap["down"]:
            self.gamestate.movement.stop_down()
        elif event.keysym == self.keymap["up"]:
            self.gamestate.movement.stop_up()
        elif event.keysym == self.keymap["left"]:
            self.gamestate.movement.stop_left()
        elif event.keysym == self.keymap["right"]:
            self.gamestate.movement.stop_right()
        elif event.keysym == "F7":
            self.gamestate.cheat_skip_level()
        elif event.keysym == "F8":
            # choose a random color scheme (only works when using retro C-64 colors)
            colors = Palette()
            colors.randomize()
            print("random colors:", colors)
            self.create_colored_tiles(colors)
            self.set_screen_colors(colors.rgb_screen, colors.rgb_border)
            self.tilesheet.all_dirty()
        elif event.keysym == "F4":
            self.gamestate.show_highscores()
        elif event.keysym == "F9":
            self.gamestate.start_demo()
        elif event.keysym == "F10":
            print("Be seeing you!")
            self.destroy()
        elif event.keysym == "F12":
            # launch the editor in a separate process
            import subprocess
            from . import editor
            env = os.environ.copy()
            env["PYTHONPATH"] = sys.path[0]
            subprocess.Popen([sys.executable, "-m", editor.__name__], env=env)

    def repaint(self) -> None:
        self.graphics_frame += 1
        self.scroll_focuscell_into_view()
        if self.smallwindow and self.gamestate.game_status == GameStatus.WAITING and self.popup_frame < self.graphics_frame:
            # move the waiting screen (title screen) around so you can see it all :)
            wavew, waveh = tiles.tile2pixels(self.playfield_columns - self.visible_columns, self.playfield_rows - self.visible_rows)
            x = (1 + math.sin(1.5 * math.pi + self.graphics_frame / self.update_fps)) * wavew / 2
            y = (1 + math.cos(math.pi + self.graphics_frame / self.update_fps / 1.4)) * waveh / 2
            self.scrollxypixels(x, y)
        for index, tile in self.tilesheet_score.dirty():
            try:
                self.scorecanvas.itemconfigure(self.cscore_tiles[index], image=self.tile_images[tile])
            except:
                pass
        # smooth scroll
        if self.canvas.view_x != self.view_x:       # type: ignore
            self.canvas.xview_moveto(0)
            self.canvas.xview_scroll(self.view_x, tkinter.UNITS)
            self.canvas.view_x = self.view_x        # type: ignore
        if self.canvas.view_y != self.view_y:       # type: ignore
            self.canvas.yview_moveto(0)
            self.canvas.yview_scroll(self.view_y, tkinter.UNITS)
            self.canvas.view_y = self.view_y        # type: ignore
        self.tilesheet.set_view(self.view_x // 16, self.view_y // 16)

        if self.popup_frame > self.graphics_frame:
            for index, tile in self.tilesheet.dirty():
                try:
                    self.canvas.itemconfigure(self.c_tiles[index], image=self.tile_images[tile])
                except:
                    pass
            return
        elif self.popup_tiles_save:
            self.popup_close()

        if self.gamestate.game_status in (GameStatus.REVEALING_PLAY, GameStatus.REVEALING_DEMO):
            # Animate cells during reveal if the option is enabled
            if self.mirrored_border_size > 0:
                self.update_mirrored_border() # we need to update the mirrored borders here so they're also revealed
            if self.animatereveal:
                if (self.perf_optimization_level > 0 and self.graphics_frame % 2 == 0) or self.perf_optimization_level == 3:
                    return
                for cell in self.gamestate.cells_with_animations():
                    idx = cell.x + self.playfield_columns * cell.y
                    if self.tiles_revealed[idx] == 1:
                        obj = cell.obj
                        if obj.id == objects.MAGICWALL.id: # Do not animate the Magic Wall
                            if not self.gamestate.magicwall["active"]:
                                obj = objects.BRICK
                        animframe = int(obj.sfps / self.update_fps * (self.graphics_frame - cell.anim_start_gfx_frame))
                        self.tilesheet[cell.x, cell.y] = obj.tile(animframe)
                        self.tilesheet.dirty_tiles[cell.x + self.tilesheet.width * cell.y] = 1
                for index, tile in self.tilesheet.dirty():
                    self.canvas.itemconfigure(self.c_tiles[index], image=self.tile_images[tile])
            return

        if self.gamestate.rockford_cell:
            # is rockford moving or pushing left/right?
            rockford_sprite = objects.ROCKFORD   # type: objects.GameObject
            animframe = 0
            if self.gamestate.level_won:
                rockford_sprite = self.last_rockford_sprite
            else:
                if self.gamestate.movement.direction == Direction.LEFT or \
                        (self.gamestate.movement.direction in (Direction.UP, Direction.DOWN) and
                        self.gamestate.movement.lastXdir == Direction.LEFT):
                    if self.gamestate.movement.moving_this_update:
                        if self.gamestate.movement.pushing:
                            rockford_sprite = objects.ROCKFORD.pushleft
                        else:
                            rockford_sprite = objects.ROCKFORD.left
                elif self.gamestate.movement.direction == Direction.RIGHT or \
                        (self.gamestate.movement.direction in (Direction.UP, Direction.DOWN) and
                        self.gamestate.movement.lastXdir == Direction.RIGHT):
                    if self.gamestate.movement.moving_this_update:
                        if self.gamestate.movement.pushing:
                            rockford_sprite = objects.ROCKFORD.pushright
                        else:
                            rockford_sprite = objects.ROCKFORD.right
                # handle rockford idle state/animation
                elif self.gamestate.idle["tap"] and self.gamestate.idle["blink"]:
                    rockford_sprite = objects.ROCKFORD.tapblink
                elif self.gamestate.idle["tap"]:
                    rockford_sprite = objects.ROCKFORD.tap
                elif self.gamestate.idle["blink"]:
                    rockford_sprite = objects.ROCKFORD.blink
            if rockford_sprite is not None:
                animframe = int(rockford_sprite.sfps / self.update_fps *
                                (self.graphics_frame - self.gamestate.rockford_cell.anim_start_gfx_frame))
                self.tilesheet[self.gamestate.rockford_cell.x, self.gamestate.rockford_cell.y] = rockford_sprite.tile(animframe)
        # other animations:
        for cell in self.gamestate.cells_with_animations():
            obj = cell.obj
            if obj.id == objects.MAGICWALL.id:
                if not self.gamestate.magicwall["active"]:
                    obj = objects.BRICK
            animframe = int(obj.sfps / self.update_fps * (self.graphics_frame - cell.anim_start_gfx_frame))
            self.tilesheet[cell.x, cell.y] = obj.tile(animframe)
            if animframe >= obj.sframes and obj.anim_end_callback:
                # the animation reached the last frame
                obj.anim_end_callback(cell)
        # flash
        if self.gamestate.flash > self.gamestate.frame:
            self.gamestate.flash = self.gamestate.frame - 1
            self.canvas.create_rectangle(0, 0, self.gamestate.width * 16 * self.scalexy, self.gamestate.height * 16 * self.scalexy, fill='white', tags='flash')
            self.after(int(self.update_fps), lambda: self.canvas.delete('flash'))
        # update all the tiles that were marked as modified (dirty)
        for index, tile in self.tilesheet.dirty():
            self.canvas.itemconfigure(self.c_tiles[index], image=self.tile_images[tile])
        # update the mirrors
        if self.mirrored_border_size > 0:
            self.update_mirrored_border()

    def create_colored_tiles(self, colors: Palette) -> None:
        if self.c64colors:
            source_images = tiles.load_sprites(colors if self.c64colors else None, scale=self.scalexy,
                                               alt_c64tileset=self.c64_alternate_tiles, krissz_c64tileset=self.krissz_tileset)
            for i, image in enumerate(source_images):
                self.tile_images[i] = tkinter.PhotoImage(data=image)

    def create_tile_images(self) -> None:
        palette_choice = random.randint(1, 2)
        if palette_choice == 1:
            initial_palette = Palette(2, 4, 13, 5, 6)
        else:
            initial_palette = Palette(6, 14, 1, 1, 1)
        source_images = tiles.load_sprites(initial_palette if self.c64colors else None, scale=self.scalexy,
                                           alt_c64tileset=self.c64_alternate_tiles, krissz_c64tileset=self.krissz_tileset)
        self.tile_images = [tkinter.PhotoImage(data=image) for image in source_images]
        source_images = tiles.load_font(self.scalexy if self.smallwindow else 2 * self.scalexy)
        self.tile_images.extend([tkinter.PhotoImage(data=image) for image in source_images])

    def create_canvas_playfield_and_tilesheet(self, width: int, height: int) -> None:
        # create the images on the canvas for all tiles (fixed position):
        if width == self.playfield_columns and height == self.playfield_rows:
            return
        if width < 2 or width > 100 + self.mirrored_border_size or height < 2 or height > 100 + self.mirrored_border_size:
            raise ValueError("invalid playfield/cave width or height (2-100)")
        self.playfield_columns = width
        self.playfield_rows = height
        self.canvas.delete(tkinter.ALL)
        self.c_tiles.clear()
        for y in range(self.playfield_rows):
            for x in range(self.playfield_columns):
                sx, sy = self.physcoor(*tiles.tile2pixels(x, y))
                tile = self.canvas.create_image(sx, sy, image=self.tile_images[0], anchor=tkinter.NW, tags="tile")
                self.c_tiles.append(tile)
        # create the images on the score canvas for all tiles (fixed position):
        self.scorecanvas.delete(tkinter.ALL)
        self.cscore_tiles.clear()
        vcols = self.visible_columns if not self.smallwindow else 2 * self.visible_columns
        for y in range(2):
            for x in range(vcols):
                sx, sy = self.physcoor(*tiles.tile2pixels(x, y))
                if self.smallwindow:
                    sx //= 2
                    sy //= 2
                self.tilesheet_score[x, y] = 0
                tile = self.scorecanvas.create_image(sx, sy, image=None, anchor=tkinter.NW, tags="tile")
                self.cscore_tiles.append(tile)
        self.tilesheet = tiles.Tilesheet(self.playfield_columns, self.playfield_rows, self.visible_columns, self.visible_rows)

    def set_screen_colors(self, screencolorrgb: int, bordercolorrgb: int) -> None:
        if self.c64colors:
            self.configure(background="#{:06x}".format(bordercolorrgb))
            self.canvas.configure(background="#{:06x}".format(screencolorrgb))

    def set_canvas_tile(self, x: int, y: int, obj: objects.GameObject) -> None:
        self.tilesheet[x, y] = obj.tile()

    def set_scorebar_tiles(self, x: int, y: int, tiles: Sequence[int]) -> None:
        self.tilesheet_score.set_tiles(x, y, tiles)

    def clear_tilesheet(self) -> None:
        self.tilesheet.set_tiles(0, 0, [objects.DIRT2.tile()] * self.playfield_columns * self.playfield_rows)

    def prepare_reveal(self) -> None:
        c = objects.COVERED.tile()
        for c_tile in self.c_tiles:
            self.canvas.itemconfigure(c_tile, image=self.tile_images[c])
        self.tiles_revealed = bytearray(len(self.c_tiles))
        # uncover the tiles beyond the playfield if the cave is smaller than the playfield
        if self.playfield_rows > self.gamestate.cave_orig_width or self.playfield_columns > self.gamestate.cave_orig_height:
            for y in range(0, self.playfield_rows):
                for x in range(0, self.playfield_columns):
                    idx = x + self.playfield_columns * y
                    if self.gamestate.cave[idx].obj.id == objects.FILLERWALL.id:
                        self.tiles_revealed[idx] = 1
                        self.canvas.itemconfigure(self.c_tiles[idx], image=self.tile_images[self.gamestate.cave[idx].obj.tile()])
        # scroll the focus cell into view
        self.scroll_focuscell_into_view(center = True, immediate = self.perf_optimization_level > 2)

    def do_reveal(self) -> None:
        # reveal tiles during the reveal period
        if self.perf_optimization_level > 0 and self.graphics_frame % 2 == 0:
            return
        times = 1 if self.playfield_columns < 44 or self.perf_optimization_level > 1 else 2
        for _ in range(0, times):
            for y in range(0, self.playfield_rows):
                x = random.randrange(0, self.playfield_columns)
                tile = self.tilesheet[x, y]
                idx = x + self.playfield_columns * y
                # only do the actual reveal every other frame regardless of the optimization level, or it happens too fast, especially on smaller maps, at 60 fps with no optimization
                if self.tiles_revealed[idx] == 0 and (self.perf_optimization_level > 0 or self.graphics_frame % 2 == 0):
                    self.tiles_revealed[idx] = 1
                    self.canvas.itemconfigure(self.c_tiles[idx], image=self.tile_images[tile])
        # animate the cover-tiles
        cover_tile = objects.COVERED.tile(self.graphics_frame)
        viewx = self.view_x // 16
        viewy = self.view_y // 16
        curx, cury = viewx + self.visible_columns, viewy + self.visible_rows
        topx, topy = viewx - self.visible_columns / 2, viewy - self.visible_rows / 2
        for i, c_tile in enumerate(self.c_tiles):
            vy = i // self.gamestate.width
            vx = i % self.gamestate.width
            if self.tiles_revealed[i] == 0 and vy <= cury and vx <= curx and vy > topy and vx > topx:
                self.canvas.itemconfigure(c_tile, image=self.tile_images[cover_tile])

    def update_mirrored_border(self):
        cave_width = self.gamestate.cave_orig_width
        cave_height = self.gamestate.cave_orig_height
        viewx = self.view_x // 16
        viewy = self.view_y // 16
        curx, cury = viewx + self.visible_columns, viewy + self.visible_rows
        topx, topy = viewx - self.visible_columns / 2, viewy - self.visible_rows / 2
        for mirror in self.gamestate.mirror_border_tiles():
                if mirror.y <= cury and mirror.x <= curx and mirror.y > topy and mirror.x > topx:
                    mirror_target_x = mirror.x
                    mirror_target_y = mirror.y
                    mirror_idx = mirror.y * self.gamestate.width + mirror.x
                    try:
                        if self.tiles_revealed[mirror_idx] == 0 and self.gamestate.game_status in (GameStatus.REVEALING_DEMO, GameStatus.REVEALING_PLAY):
                            continue
                        elif self.tiles_revealed[mirror_idx] == 0:
                            self.tiles_revealed[mirror_idx] = 1
                    except:
                        pass
                    if mirror.x < self.gamestate.cave_delta_x:
                        mirror_target_x += cave_width
                    elif mirror.x >= cave_width + self.gamestate.cave_delta_x:
                        mirror_target_x -= cave_width
                    if mirror.y < self.gamestate.cave_delta_y:
                        mirror_target_y += cave_height
                    elif mirror.y >= cave_height + self.gamestate.cave_delta_y:
                        mirror_target_y -= cave_height
                    mirror_tile = self.tilesheet[mirror_target_x, mirror_target_y]
                    self.canvas.itemconfigure(self.c_tiles[mirror_idx], image=self.tile_images[mirror_tile])
                    if self.stippled_mirrored_border:
                        loc_x = mirror.x * 16 * self.scalexy
                        loc_y = mirror.y * 16 * self.scalexy
                        self.canvas.create_rectangle(loc_x, loc_y, loc_x + 16 * self.scalexy, loc_y + 16 * self.scalexy, fill="white", width=0, stipple="gray12", tags='mirrorborder')

    def physcoor(self, sx: int, sy: int) -> Tuple[int, int]:
        return int(sx * self.scalexy), int(sy * self.scalexy)

    def tkcolor(self, color: int) -> str:
        return "#{:06x}".format(colorpalette[color & len(colorpalette) - 1])

    def scrollxypixels(self, x: float, y: float) -> None:
        self.view_x, self.view_y = self.clamp_scroll_xy(x, y)

    def clamp_scroll_xy(self, x: float, y: float) -> Tuple[int, int]:
        xlimit, ylimit = tiles.tile2pixels(self.playfield_columns - self.visible_columns, self.playfield_rows - self.visible_rows)
        return min(max(0, round(x)), xlimit), min(max(0, round(y)), ylimit)

    def update_game(self) -> None:
        if self.popup_frame < self.graphics_frame:
            self.gamestate.update(self.graphics_frame)
        self.gamestate.update_scorebar()
        music_sample = audio.samples["music"]
        if self.gamestate.game_status == GameStatus.WAITING and \
                self.last_demo_or_highscore_frame + self.update_fps * max(15, music_sample.duration) < self.graphics_frame:
            self.gamestate.tile_music_ended()
            self.last_demo_or_highscore_frame = self.graphics_frame

    def scroll_focuscell_into_view(self, immediate: bool=False, center: bool=False) -> None:
        focus_cell = self.gamestate.focus_cell()
        if focus_cell:
            x, y = focus_cell.x, focus_cell.y
            curx, cury = self.view_x / 16 + self.visible_columns / 2, self.view_y / 16 + self.visible_rows / 2
            viewx, viewy = tiles.tile2pixels(x - self.visible_columns // 2, y - self.visible_rows // 2)
            if not self.scrolling_into_view and abs(curx - x) < self.visible_columns // 3 and abs(cury - y) < self.visible_rows // 3:
                if not center:
                    return  # don't always keep it exactly in the center at all times, add some movement slack area
            # scroll the view to the focus cell
            viewx, viewy = tiles.tile2pixels(x - self.visible_columns // 2, y - self.visible_rows // 2)
            viewx, viewy = self.clamp_scroll_xy(viewx, viewy)
            if immediate:
                # directly jump to new scroll position (no interpolation)
                self.scrollxypixels(viewx, viewy)
            else:
                if viewx == self.view_x and viewy == self.view_y:
                    # we reached the end
                    self.scrolling_into_view = False
                else:
                    # interpolate towards the new view position
                    self.scrolling_into_view = True
                    dx = (viewx - self.view_x) / self.update_fps * 2.0
                    dy = (viewy - self.view_y) / self.update_fps * 2.0
                    if dx:
                        viewx = int(self.view_x + math.copysign(max(1, abs(dx)), dx))
                    if dy:
                        viewy = int(self.view_y + math.copysign(max(1, abs(dy)), dy))
                    self.scrollxypixels(viewx, viewy)

    def popup(self, text: str, duration: float=5.0, on_close: Callable=None, prealigned: bool=False) -> None:
        self.popup_close()
        self.scroll_focuscell_into_view(immediate=True)   # snap the view to the focus cell otherwise popup may appear off-screen
        if self.mirrored_border_size > 0 and self.stippled_mirrored_border:
            self.canvas.delete('mirrorborder') # remove the stippled border overlay if it was present
        lines = []
        if self.smallwindow:
            width = self.visible_columns - 4
        elif self.window30x18:
            width = self.visible_columns - 8
        else:
            width = int(self.visible_columns * 0.6)
        for line in text.splitlines():
            if prealigned:
                lines.append(line)                
            else:
                output = ""
                for word in line.split():
                    if len(output) + len(word) < (width + 1):
                        output += word + " "
                    else:
                        lines.append(output.rstrip())
                        output = word + " "
                if output:
                    lines.append(output.rstrip())
                else:
                    lines.append("")
        if self.smallwindow or self.window30x18:
            bchar = ""
            popupwidth = width + 4
            popupheight = len(lines) + 3
        else:
            bchar = "\x0e"
            popupwidth = width + 6
            popupheight = len(lines) + 6
        x, y = (self.visible_columns - popupwidth) // 2, int((self.visible_rows - popupheight + 1) / 2)

        # move the popup inside the currently viewable portion of the playfield
        x += self.view_x // 16
        y += self.view_y // 16
        x = min(x, self.playfield_columns - popupwidth)
        y = min(y, self.playfield_rows - popupheight)

        self.popup_tiles_save = (
            x, y, popupwidth, popupheight,
            self.tilesheet.get_tiles(x, y, popupwidth, popupheight)
        )
        self.tilesheet.set_tiles(x, y, [objects.STEELSLOPEDUPLEFT.tile()] +
                                 [objects.STEEL.tile()] * (popupwidth - 2) + [objects.STEELSLOPEDUPRIGHT.tile()])
        y += 1
        if not self.smallwindow and not self.window30x18:
            self.tilesheet.set_tiles(x + 1, y, tiles.text2tiles(bchar * (popupwidth - 2)))
            self.tilesheet[x, y] = objects.STEEL.tile()
            self.tilesheet[x + popupwidth - 1, y] = objects.STEEL.tile()
            y += 1
        lines.insert(0, "")
        if not self.smallwindow and not self.window30x18:
            lines.append("")
        for line in lines:
            if not line:
                line = " "
            line_tiles = tiles.text2tiles(bchar + " " + line.ljust(width) + " " + bchar)
            self.tilesheet[x, y] = objects.STEEL.tile()
            self.tilesheet[x + popupwidth - 1, y] = objects.STEEL.tile()
            self.tilesheet.set_tiles(x + 1, y, line_tiles)
            y += 1
        if not self.smallwindow and not self.window30x18:
            self.tilesheet[x, y] = objects.STEEL.tile()
            self.tilesheet[x + popupwidth - 1, y] = objects.STEEL.tile()
            self.tilesheet.set_tiles(x + 1, y, tiles.text2tiles(bchar * (popupwidth - 2)))
            y += 1
        self.tilesheet.set_tiles(x, y, [objects.STEELSLOPEDDOWNLEFT.tile()] +
                                 [objects.STEEL.tile()] * (popupwidth - 2) + [objects.STEELSLOPEDDOWNRIGHT.tile()])
        self.popup_frame = int(self.graphics_frame + self.update_fps * duration)
        self.on_popup_closed = on_close

    def popup_close(self) -> None:
        if not self.popup_tiles_save:
            return
        x, y, width, height, saved_tiles = self.popup_tiles_save
        for tiles in saved_tiles:
            self.tilesheet.set_tiles(x, y, tiles)
            y += 1
        self.popup_tiles_save = None
        self.popup_frame = 0
        if self.gamestate.game_status in (GameStatus.REVEALING_PLAY, GameStatus.REVEALING_DEMO):
            # when going to reveal, now draw the actual cave
            self.gamestate.draw_new_cave(self.gamestate.level)
        if self.on_popup_closed:
            self.on_popup_closed()
            self.on_popup_closed = None

    def ask_highscore_name(self, score_pos: int, score: int) -> str:
        username = bdcff.get_system_username()[:HighScores.max_namelen]
        name = simpledialog.askstring("Enter your name", "Enter your name for the high-score table!\n\n"
                                        "#{:d} score:  {:d}\n\n(max {:d} letters)"
                                        .format(score_pos, score, HighScores.max_namelen),
                                        initialvalue=username, parent=self) or ""
        name = name.strip()
        if 0 < len(name) <= HighScores.max_namelen:
            return name
        elif len(name) > HighScores.max_namelen:
            return name[0:HighScores.max_namelen]
        else:
            return ""


def start(sargs: Sequence[str]=None) -> None:
    if sargs is None:
        sargs = sys.argv[1:]
    import argparse
    ap = argparse.ArgumentParser(description="Boulder Caves+ - a Krissz Engine-compatible Boulder Dash (tm) clone",
                                 epilog="This software is licensed under the GNU GPL 3.0, see https://www.gnu.org/licenses/gpl.html")
    ap.add_argument("-g", "--game", help="specify cave data file to play, leave empty to play original built-in BD1 caves.")
    ap.add_argument("-f", "--fps", type=int, help="frames per second (default=%(default)d).", default=30)
    ap.add_argument("-s", "--size", type=int, help="graphics size (default=%(default)d).", default=3, choices=(1, 2, 3, 4, 5, 6, 7, 8, 9, 10))
    ap.add_argument("-c", "--c64colors", help="use Commodore-64 colors.", action="store_true")
    ap.add_argument("-o", "--othertiles", help="use alternate Commodore-64 tileset.", action="store_true")
    ap.add_argument("-a", "--authentic", help="use C-64 colors AND limited window size.", action="store_true")
    ap.add_argument("-y", "--synth", help="use synthesized sounds instead of samples.", action="store_true")
    ap.add_argument("-l", "--level", help="select start level (cave number). When using this, no highscores will be recorded.", type=int, default=1)
    ap.add_argument("-x", "--nohidexwalls", help="don't hide expanding walls by drawing an ordinary wall instead (BoulderCaves specific behavior).", action="store_true")
    ap.add_argument("-w", "--window30x18", help="use the 30x18 playfield size as used in Krissz Engine.", action="store_true")
    ap.add_argument("-Y", "--altsoundsinsynth", help="use alternate Krissz Engine-style sounds from ogg files even when in synthesizer mode.", action="store_true")
    ap.add_argument("-r", "--noanimatereveal", help="[Deprecated, use --optimize instead] do not animate cells during reveal demo.", action="store_true")
    ap.add_argument("-k", "--krissz", help="enable Krissz Engine compatibility mode.", action="store_true")
    ap.add_argument("-m", "--mirrorborder", type=int, help="the number of tiles to show in a mirrored, see-through manner beyond the edge of an open border map, default=%(default)d, 100 for autodetect.", default=0)
    ap.add_argument("-M", "--stipplemirror", help="Indicate the open border boundary with a stipple pattern when using a see-through mirror mode (-m)", action="store_true")
    ap.add_argument("-T", "--nokrissztiles", help="Do not use the Krissz Engine-like tile set even if in Krissz Engine compatibility mode", action="store_true")
    ap.add_argument("-F", "--fullscreen", help="Start BoulderCaves+ in full screen mode", action="store_true")
    ap.add_argument("-O", "--optimize", type=int, help="Set optimization level (from 0 to 3), each level reduces visual accuracy in favor of performance gains.", default=0, choices=(0, 1, 2, 3))
    ap.add_argument("--editor", help="run the Construction Kit instead of the game.", action="store_true")
    ap.add_argument("--playtest", help="playtest the cave.", action="store_true")
    args = ap.parse_args(sargs)
    print("This software is licensed under the GNU GPL 3.0, see https://www.gnu.org/licenses/gpl.html")

    size_defined = "-s" in sargs or "--size" in sargs
        
    if args.editor:
        from . import editor
        editor.start()
        raise SystemExit

    # validate required libraries
    audio.check_api()
    args.c64colors |= args.authentic
    if args.c64colors or args.krissz:
        print("Using the original Commodore-64 colors.")
        print("Start without the '--c64colors', '--authentic', or '--krissz' arguments to use the multicolor replacement graphics.")
    else:
        print("Using multicolor replacement graphics.")
        print("You can use the '-c' or '--c64colors' argument to get the original C-64 colors.")

    if args.krissz:
        print("Enabling Krissz Engine-like game engine parameters.")
        
    # initialize the audio system
    samples = {
        "music": ("bdmusic.ogg", 1),
        "cover": ("cover.ogg", 1),
        "crack": ("crack.ogg", 2),
        "boulder": ("boulder.ogg", 16 if args.krissz else 4),
        "boulder2": ("boulder2.ogg", 16 if args.krissz else 4),
        "finished": ("finished.ogg", 1),
        "explosion": ("explosion.ogg", 2),
        "voodoo_explosion": ("voodoo_explosion.ogg", 2),
        "extra_life": ("bonus_life.ogg", 1),
        "walk_empty": ("walk_empty.ogg", 2),
        "walk_dirt": ("walk_dirt.ogg", 2),
        "collect_diamond": ("collectdiamond.ogg", 1),
        "box_push": ("box_push.ogg", 2),
        "amoeba": ("amoeba.ogg", 1),
        "slime": ("slime.ogg", 1),
        "magic_wall": ("magic_wall.ogg", 1),
        "game_over": ("game_over.ogg", 1),
        "diamond1": ("diamond1.ogg", 16 if args.krissz else 2),
        "diamond2": ("diamond2.ogg", 16 if args.krissz else 2),
        "diamond3": ("diamond3.ogg", 16 if args.krissz else 2),
        "diamond4": ("diamond4.ogg", 16 if args.krissz else 2),
        "diamond5": ("diamond5.ogg", 16 if args.krissz else 2),
        "diamond6": ("diamond6.ogg", 16 if args.krissz else 2),
        "timeout1": ("timeout1.ogg", 1),
        "timeout2": ("timeout2.ogg", 1),
        "timeout3": ("timeout3.ogg", 1),
        "timeout4": ("timeout4.ogg", 1),
        "timeout5": ("timeout5.ogg", 1),
        "timeout6": ("timeout6.ogg", 1),
        "timeout7": ("timeout7.ogg", 1),
        "timeout8": ("timeout8.ogg", 1),
        "timeout9": ("timeout9.ogg", 1),
    }

    if args.synth:
        print("Pre-synthesizing sounds...")
        diamond = synthsamples.Diamond()   # is randomized everytime it is played
        synthesized = {
            "music": synthsamples.TitleMusic(),
            "cover": synthsamples.Cover(),
            "crack": synthsamples.Crack(),
            "boulder": synthsamples.Boulder(),
            "boulder2": synthsamples.Boulder(),
            "amoeba": synthsamples.Amoeba(),
            "slime": synthsamples.Slime(),
            "magic_wall": synthsamples.MagicWall(),
            "finished": synthsamples.Finished(),
            "explosion": synthsamples.Explosion(),
            "voodoo_explosion": synthsamples.VoodooExplosion(),
            "collect_diamond": synthsamples.CollectDiamond(),
            "walk_empty": synthsamples.WalkEmpty(),
            "walk_dirt": synthsamples.WalkDirt(),
            "box_push": synthsamples.BoxPush(),
            "extra_life": synthsamples.ExtraLife(),
            "game_over": synthsamples.GameOver(),
            "diamond1": diamond,
            "diamond2": diamond,
            "diamond3": diamond,
            "diamond4": diamond,
            "diamond5": diamond,
            "diamond6": diamond,
            "timeout1": synthsamples.Timeout(1),
            "timeout2": synthsamples.Timeout(2),
            "timeout3": synthsamples.Timeout(3),
            "timeout4": synthsamples.Timeout(4),
            "timeout5": synthsamples.Timeout(5),
            "timeout6": synthsamples.Timeout(6),
            "timeout7": synthsamples.Timeout(7),
            "timeout8": synthsamples.Timeout(8),
            "timeout9": synthsamples.Timeout(9),
        }
        assert len(synthesized.keys() - samples.keys()) == 0
        missing = samples.keys() - synthesized.keys()
        if missing:
            raise SystemExit("Synths missing for: " + str(missing))
        for name, sample in synthesized.items():
            max_simul = samples[name][1]
            samples[name] = (sample, max_simul)     # type: ignore
        if args.altsoundsinsynth:
            # append Krissz Engine style samples that are not yet synthesized
            samples["boulder2"] = ("boulder2.ogg", 4)

    if os.name == "nt":
        audio.prepare_oggdec_exe()
    audio.init_audio(samples)
    title = "BoulderCaves+ {version:s} {sound:s} {playtest:s} - by Irmen de Jong, extended by Michael Kamensky"\
        .format(version=__version__,
                sound="[synth]" if args.synth else "",
                playtest="[playtesting]" if args.playtest else "")
    window = BoulderWindow(title, args.fps, args.size + 1,
                           c64colors=args.c64colors | args.authentic | args.krissz,
                           c64_alternate_tiles=args.othertiles,
                           smallwindow=args.authentic,
                           hidexwalls=not args.nohidexwalls,
                           window30x18=args.window30x18 | args.krissz,
                           animatereveal = not args.noanimatereveal,
                           krisszcompat=args.krissz,
                           krissztileset=args.krissz and not args.nokrissztiles,
                           fullscreen=args.fullscreen,
                           size_defined=size_defined,
                           optimize=args.optimize,
                           mirror_size=args.mirrorborder,
                           stipple_mirror=args.stipplemirror)
    if args.game:
        window.gamestate.use_bdcff(args.game)
    if args.level:
        window.gamestate.use_startlevel(args.level)
    if args.playtest:
        window.gamestate.use_playtesting()
    cs = window.gamestate.caveset
    print("Playing caveset '{name}' (by {author}, {date})".format(name=cs.name, author=cs.author, date=cs.date))
    if args.othertiles:
        print("Using alternate tileset (created by Marcel Sásik)")
    window.start()
    window.mainloop()


if __name__ == "__main__":
    start(sys.argv[1:])
