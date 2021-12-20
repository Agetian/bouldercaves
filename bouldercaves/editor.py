"""
Boulder Caves+ - a Boulder Dash (tm) clone.
Krissz Engine-compatible remake based on Boulder Caves 5.7.2.

Boulder Caves+ Construction Kit.

Cave Set editor

Original version written by Irmen de Jong (irmen@razorvine.net)
Extended version by Michael Kamensky

License: GNU GPL 3.0, see LICENSE
"""

import os
import sys
import random
import datetime
import tkinter
import tkinter.messagebox
from tkinter.simpledialog import Dialog
import tkinter.ttk
import tkinter.filedialog
import tkinter.colorchooser
import pkgutil
from typing import Tuple, List, Dict, Optional
from .game import __version__
from .caves import colorpalette, C64Cave, Cave as BaseCave, CaveSet, Palette, BDCFFOBJECTS
from .objects import GameObject, Direction
from .helpers import CaveStatsHelper
from . import tiles, objects, bdcff


class ScrollableImageSelector(tkinter.Frame):
    def __init__(self, master: tkinter.Widget, listener: 'EditorWindow') -> None:
        super().__init__(master)
        self.listener = listener
        self.treeview = tkinter.ttk.Treeview(self, columns=("tile",), displaycolumns=("tile",), height="5", selectmode=tkinter.BROWSE)
        self.treeview.heading("tile", text="Tile")
        self.treeview.column("#0", stretch=False, minwidth=40, width=40)
        self.treeview.column("tile", stretch=True, width=200)
        tkinter.ttk.Style(self).configure("Treeview", rowheight=24, background="#201000", foreground="#e0e0e0")
        sy = tkinter.Scrollbar(self, orient=tkinter.VERTICAL, command=self.treeview.yview)
        sy.pack(side=tkinter.RIGHT, expand=1, fill=tkinter.Y)
        self.treeview.configure(yscrollcommand=sy.set)
        self.treeview.pack(expand=1, fill=tkinter.Y)
        self.treeview.bind("<<TreeviewSelect>>", self.on_selected)
        self.treeview.bind("<Double-Button-1>", self.on_selected_doubleclick)
        self.selected_object = objects.BOULDER
        self.selected_erase_object = objects.EMPTY
        f = tkinter.Frame(master)
        tkinter.Label(f, text=" Draw: \n(Lmb)").grid(row=0, column=0)
        self.draw_label = tkinter.Label(f)
        self.draw_label.grid(row=0, column=1)
        tkinter.Label(f, text=" Erase: \n(Rmb)").grid(row=0, column=2)
        self.erase_label = tkinter.Label(f)
        self.erase_label.grid(row=0, column=3)
        tkinter.Label(f, text="Left click to set draw,\ndouble left click to set erase.").grid(row=1, column=0, columnspan=4)
        self.direction_var = tkinter.StringVar()
        self.direction_var.set("U")
        self.direction_buttons = []
        tkinter.Label(f, text="Direction:").grid(row=3, column=0)
        self.dirbtn_up = tkinter.Radiobutton(f, text = "\u2191", variable = self.direction_var, value = "U")
        self.dirbtn_up.grid(row=3, column=1)
        self.direction_buttons.append(self.dirbtn_up)
        self.dirbtn_down = tkinter.Radiobutton(f, text = "\u2193", variable = self.direction_var, value = "D")
        self.dirbtn_down.grid(row=3, column=2)
        self.direction_buttons.append(self.dirbtn_down)
        self.dirbtn_left = tkinter.Radiobutton(f, text = "\u2190", variable = self.direction_var, value = "L")
        self.dirbtn_left.grid(row=3, column=3)
        self.direction_buttons.append(self.dirbtn_left)
        self.dirbtn_right = tkinter.Radiobutton(f, text = "\u2192", variable = self.direction_var, value = "R")
        self.dirbtn_right.grid(row=3, column=4)
        self.direction_buttons.append(self.dirbtn_right)
        self.set_direction_button_state(False)
        f.pack(side=tkinter.BOTTOM, pady=4)

    def set_direction_button_state(self, btn_state):
        for button in self.direction_buttons:
            button.configure(state=tkinter.DISABLED if not btn_state else tkinter.NORMAL)

    def on_selected_doubleclick(self, event) -> None:
        item = self.treeview.focus()
        item = self.treeview.item(item)
        selected_name = item["values"][0].lower()
        self.selected_erase_object = objects.EMPTY
        for obj, displaytile in EDITOR_OBJECTS.items():
            if EDITOR_OBJECT_NAMES[obj].lower() == selected_name:
                self.selected_erase_object = obj
                self.erase_label.configure(image=self.listener.tile_images[EDITOR_OBJECTS[obj]])
                self.listener.tile_erase_selection_changed(obj, displaytile)
                break

    def on_selected(self, event) -> None:
        item = self.treeview.focus()
        item = self.treeview.item(item)
        selected_name = item["values"][0].lower() if len(item["values"]) > 0 else None
        self.selected_object = objects.BOULDER
        for obj, displaytile in EDITOR_OBJECTS.items():
            if EDITOR_OBJECT_NAMES[obj].lower() == selected_name:
                self.selected_object = obj
                self.draw_label.configure(image=self.listener.tile_images[EDITOR_OBJECTS[obj]])
                self.listener.tile_selection_changed(obj, displaytile)
                if obj == objects.FIREFLY or obj == objects.ALTFIREFLY:
                    self.direction_var.set("L")
                    self.set_direction_button_state(True)
                elif obj == objects.BUTTERFLY or obj == objects.ALTBUTTERFLY:
                    self.direction_var.set("D")
                    self.set_direction_button_state(True)
                else:
                    self.set_direction_button_state(False)
                break

    def populate(self, rows: List) -> None:
        for row in self.treeview.get_children():
            self.treeview.delete(row)
        for image, name in rows:
            self.treeview.insert("", tkinter.END, image=image, values=(name,))
        self.treeview.configure(height=min(18, len(rows)))
        self.draw_label.configure(image=self.listener.tile_images[EDITOR_OBJECTS[self.selected_object]])
        self.erase_label.configure(image=self.listener.tile_images[EDITOR_OBJECTS[self.selected_erase_object]])


class Cave(BaseCave):
    def init_for_editor(self, editor: 'EditorWindow', erase_map: bool) -> None:
        self.editor = editor
        if not self.map or erase_map:
            self.map = [(objects.EMPTY, Direction.NOWHERE)] * self.width * self.height
        self.snapshot()
        # draw the map into the canvas.
        for y in range(0, self.height):
            for x in range(0, self.width):
                self.editor.set_canvas_tile(x, y, EDITOR_OBJECTS[self.map[x + self.width * y][0]])

    def __setitem__(self, xy: Tuple[int, int], thing: Tuple[GameObject, Direction]) -> None:
        x, y = xy
        obj, direction = thing
        assert isinstance(obj, GameObject) and isinstance(direction, Direction)
        if direction == Direction.NOWHERE:
            if obj in (objects.BUTTERFLY, objects.ALTBUTTERFLY):
                direction = Direction.DOWN
            elif obj in (objects.FIREFLY, objects.ALTFIREFLY):
                direction = Direction.LEFT
        self.map[x + self.width * y] = (obj, direction)
        self.editor.set_canvas_tile(x, y, EDITOR_OBJECTS[obj])

    def __getitem__(self, xy: Tuple[int, int]) -> Tuple[GameObject, Direction]:
        x, y = xy
        return self.map[x + self.width * y]

    def horiz_line(self, x: int, y: int, length: int, thing: Tuple[GameObject, Direction]) -> None:
        for xx in range(x, x + length):
            self[xx, y] = thing

    def vert_line(self, x: int, y: int, length: int, thing: Tuple[GameObject, Direction]) -> None:
        for yy in range(y, y + length):
            self[x, yy] = thing

    def snapshot(self) -> None:
        self.map_snapshot = self.map.copy()

    def restore(self) -> None:
        if self.map_snapshot:
            for y in range(self.height):
                for x in range(self.width):
                    obj, direction = self.map_snapshot[x + self.width * y]
                    self[x, y] = (obj, direction)
                    self.editor.set_canvas_tile(x, y, EDITOR_OBJECTS[obj])

# the objects available in the editor, with their tile number that is displayed
# (not all objects are properly recognizable in the editor by their default tile)
EDITOR_OBJECTS = {
    objects.EMPTY: objects.EMPTY.tile(),
    objects.DIRT: objects.DIRT.tile(),
    objects.BOULDER: objects.BOULDER.tile(),
    objects.MEGABOULDER: objects.MEGABOULDER.tile(), # Krissz Engine Heavy Boulder
    objects.LIGHTBOULDER: objects.LIGHTBOULDER.tile(), # Krissz Engine Light Boulder
    objects.DIAMOND: objects.DIAMOND.tile(),
    objects.STEEL: objects.STEEL.tile(),
    objects.BRICK: objects.BRICK.tile(),
    objects.MAGICWALL: objects.MAGICWALL.tile(2),
    objects.HEXPANDINGWALL: objects.HEXPANDINGWALL.tile(),
    objects.VEXPANDINGWALL: objects.VEXPANDINGWALL.tile(),
    objects.EXPANDINGWALL: objects.EXPANDINGWALL.tile(), # Krissz Engine Expanding Wall Both Ways
    objects.FIREFLY: objects.FIREFLY.tile(1),
    objects.BUTTERFLY: objects.BUTTERFLY.tile(2),
    objects.AMOEBA: objects.AMOEBA.tile(),
    objects.SLIME: objects.SLIME_EDITMODE.tile(),
    objects.VOODOO: objects.ROCKFORD.tile(),   
    objects.INBOXBLINKING: objects.INBOX_EDITMODE.tile(),
    objects.OUTBOXCLOSED: objects.OUTBOX_EDITMODE.tile(1),
    objects.OUTBOXHIDDEN: objects.HIDDEN_OUTBOX_EDITMODE.tile(1)
}

EDITOR_OBJECT_NAMES = {
    objects.AMOEBA: "Amoeba",
    objects.BOULDER: "Boulder",
    objects.BRICK: "Brick Wall",
    objects.BUTTERFLY: "Butterfly",
    objects.DIAMOND: "Diamond",
    objects.DIRT: "Dirt",
    objects.EMPTY: "Space",
    objects.FIREFLY: "Firefly",
    objects.HEXPANDINGWALL: "Expanding Wall Horizontal",
    objects.INBOXBLINKING: "Inbox",
    objects.MAGICWALL: "Magic Wall",
    objects.OUTBOXCLOSED: "Outbox",
    objects.OUTBOXHIDDEN: "Hidden Outbox",
    objects.SLIME: "Slime",
    objects.STEEL: "Titanium Wall",
    objects.VEXPANDINGWALL: "Expanding Wall Vertical",
    objects.VOODOO: "Voodoo Rockford",
    # substandard objects from Krissz's implementation
    objects.MEGABOULDER: "Heavy Boulder",
    objects.LIGHTBOULDER: "Light Boulder",
    objects.EXPANDINGWALL: "Expanding Wall Both Ways"
}


class EditorWindow(tkinter.Tk):
    visible_columns = 40
    visible_rows = 22
    canvas_scale = 2

    def __init__(self, show_active_elem: bool = False, krissz_engine_defaults: bool = False) -> None:
        super().__init__()
        self.geometry("+200+40")
        title = "BoulderCaves+ Construction Kit {version:s} - by Irmen de Jong, extended by Michael Kamensky".format(version=__version__)
        self.wm_title(title)
        self.appicon = tkinter.PhotoImage(data=pkgutil.get_data(__name__, "gfx/gdash_icon_48.gif"))
        self.wm_iconphoto(self, self.appicon)
        if sys.platform == "win32":
            # tell windows to use a new toolbar icon
            import ctypes
            myappid = 'net.Razorvine.Bouldercaves.editor'  # arbitrary string
            try:
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
            except AttributeError:
                pass    # that function is not available on windows versions older than win7
        self.playfield_columns = self.visible_columns
        self.playfield_rows = self.visible_rows
        self.showing_impermeable_slime = False # show slime impermeability with special icons
        self.show_active_element = show_active_elem # show active element when mousing over the canvas
        rightframe = tkinter.Frame(self)
        cf = tkinter.Frame(rightframe)
        w, h = tiles.tile2pixels(self.visible_columns, self.visible_rows)
        maxw, maxh = tiles.tile2pixels(40, 22)   # the most common cave size should be visible without scrolling
        self.canvas = tkinter.Canvas(cf, width=self.canvas_scale * min(w, maxw), height=self.canvas_scale * (min(h, maxh)),
                                     borderwidth=16, background="black", highlightthickness=1)
        self.canvas.grid(row=0, column=0)
        sy = tkinter.Scrollbar(cf, orient=tkinter.VERTICAL, command=self.canvas.yview)
        sx = tkinter.Scrollbar(cf, orient=tkinter.HORIZONTAL, command=self.canvas.xview)
        self.canvas.configure(xscrollcommand=sx.set, yscrollcommand=sy.set)
        sy.grid(row=0, column=1, sticky=tkinter.N + tkinter.S)
        sx.grid(row=1, column=0, sticky=tkinter.E + tkinter.W)
        cf.pack()
        self.bottomframe = tkinter.Frame(rightframe)

        f = tkinter.Frame(self.bottomframe)
        tkinter.Label(f, text="Cave Name:").grid(column=0, row=0, sticky=tkinter.E, pady=0)
        tkinter.Label(f, text="Description:").grid(column=0, row=1, sticky=tkinter.E, pady=0)
        tkinter.Label(f, text="Author:").grid(column=0, row=2, sticky=tkinter.E, pady=0)
        tkinter.Label(f, text="Website:").grid(column=0, row=3, sticky=tkinter.E, pady=0)
        tkinter.Label(f, text="Date:").grid(column=0, row=4, sticky=tkinter.E, pady=0)
        self.cavename_var = tkinter.StringVar(value="Untitled")
        self.cavedescr_var = tkinter.StringVar(value="A new cave.")
        self.cavesetauthor_var = tkinter.StringVar(value=bdcff.get_system_username())
        self.cavesetwww_var = tkinter.StringVar()
        self.cavesetdate_var = tkinter.StringVar(value=datetime.datetime.now().date())
        tkinter.Entry(f, textvariable=self.cavename_var).grid(column=1, row=0, pady=0)
        tkinter.Entry(f, textvariable=self.cavedescr_var).grid(column=1, row=1, pady=0)
        tkinter.Entry(f, textvariable=self.cavesetauthor_var).grid(column=1, row=2, pady=0)
        tkinter.Entry(f, textvariable=self.cavesetwww_var).grid(column=1, row=3, pady=0)
        tkinter.Entry(f, textvariable=self.cavesetdate_var).grid(column=1, row=4, pady=0)
        f.pack(side=tkinter.LEFT, anchor=tkinter.N)

        defaults = bdcff.BdcffCave()
        f = tkinter.Frame(self.bottomframe)
        tkinter.Label(f, text="Time Limit:").grid(column=0, row=0, sticky=tkinter.E, pady=0)
        tkinter.Label(f, text="Magic Wall Time:").grid(column=0, row=1, sticky=tkinter.E, pady=0)
        tkinter.Label(f, text="Amoeba Limit Factor:").grid(column=0, row=2, sticky=tkinter.E, pady=0)
        tkinter.Label(f, text="Amoeba Slow Time:").grid(column=0, row=3, sticky=tkinter.E, pady=0)
        tkinter.Label(f, text="Amoeba Limit:").grid(column=0, row=4, sticky=tkinter.E, pady=0)
        self.cavetimelimit_var = tkinter.IntVar(value=defaults.cavetime)
        self.amoeba_limit_var = tkinter.IntVar(value=defaults.amoeba_limit)
        self.caveamoebatime_var = tkinter.IntVar(value=defaults.amoebatime)
        self.cavemagicwalltime_var = tkinter.IntVar(value=defaults.magicwalltime)
        self.caveamoebafactor_var = tkinter.DoubleVar(value=defaults.amoebafactor)
        self.caveslimepermeability_var = tkinter.DoubleVar(value=defaults.slimepermeability)
        self.krissz_slime_permeability_var = tkinter.IntVar(value=defaults.krissz_slime_permeability)
        tkinter.Entry(f, width=8, textvariable=self.cavetimelimit_var).grid(column=1, row=0, pady=0)
        tkinter.Entry(f, width=8, textvariable=self.cavemagicwalltime_var).grid(column=1, row=1, pady=0)
        tkinter.Entry(f, width=8, textvariable=self.caveamoebafactor_var).grid(column=1, row=2, pady=0)
        tkinter.Entry(f, width=8, textvariable=self.caveamoebatime_var).grid(column=1, row=3, pady=0)
        tkinter.Entry(f, width=8, textvariable=self.amoeba_limit_var).grid(column=1, row=4, pady=0)
        f.pack(side=tkinter.LEFT, padx=4, anchor=tkinter.N)
        
        f = tkinter.Frame(self.bottomframe)
        self.target_fps_var = tkinter.DoubleVar(value=defaults.target_fps)
        self.rockford_birth_time_var = tkinter.IntVar(value=defaults.rockford_birth_time)
        self.magic_wall_stops_amoeba_var = tkinter.BooleanVar()
        self.amoeba_grows_before_spawn_var = tkinter.BooleanVar()
        self.no_time_limit_var = tkinter.BooleanVar()
        self.reverse_time_var = tkinter.BooleanVar()
        self.value_of_a_second_var = tkinter.IntVar(value=defaults.value_of_a_second)
        tkinter.Label(f, text="Game Speed (Frame/Sec):").grid(column=0, row=0, sticky=tkinter.E, pady=0)
        tkinter.Label(f, text="Rockford Birth Time:").grid(column=0, row=1, sticky=tkinter.E, pady=0)
        tkinter.Label(f, text="Value of a Second:").grid(column=0, row=2, sticky=tkinter.E, pady=0)
        tkinter.Label(f, text="Slime Perm., unpred.:").grid(column=0, row=3, sticky=tkinter.E, pady=0)
        tkinter.Label(f, text="Slime Perm., 0-8:").grid(column=0, row=4, sticky=tkinter.E, pady=0)
        tkinter.Entry(f, width=8, textvariable=self.target_fps_var).grid(column=1, row=0, pady=0)
        tkinter.Entry(f, width=8, textvariable=self.rockford_birth_time_var).grid(column=1, row=1, pady=0)
        tkinter.Entry(f, width=8, textvariable=self.value_of_a_second_var).grid(column=1, row=2, pady=0)
        tkinter.Entry(f, width=8, textvariable=self.caveslimepermeability_var).grid(column=1, row=3, pady=0)
        tkinter.Entry(f, width=8, textvariable=self.krissz_slime_permeability_var).grid(column=1, row=4, pady=0)
        f.pack(side=tkinter.LEFT, padx=2, anchor=tkinter.N)

        f = tkinter.Frame(self.bottomframe)
        self.cavediamondsrequired_var = tkinter.IntVar(value=defaults.diamonds_required)
        self.cavediamondvaluenorm_var = tkinter.IntVar(value=defaults.diamondvalue_normal)
        self.cavediamondvalueextra_var = tkinter.IntVar(value=defaults.diamondvalue_extra)
        self.single_life_var = tkinter.BooleanVar() # Substandard feature from Krissz's engine that only offers a single attempt
        self.bonus_life_pts_var = tkinter.IntVar(value=500)
        tkinter.Label(f, text="Required Diamonds:").grid(column=0, row=0, sticky=tkinter.E, pady=0)
        tkinter.Label(f, text="Diamond Value:").grid(column=0, row=1, sticky=tkinter.E, pady=0)
        tkinter.Label(f, text="Bonus Diamond Value:").grid(column=0, row=2, sticky=tkinter.E, pady=0)
        tkinter.Label(f, text="Bonus Life Score:").grid(column=0, row=3, sticky=tkinter.E, pady=0)
        tkinter.Entry(f, width=8, textvariable=self.cavediamondsrequired_var).grid(column=1, row=0, pady=0)
        tkinter.Entry(f, width=8, textvariable=self.cavediamondvaluenorm_var).grid(column=1, row=1, pady=0)
        tkinter.Entry(f, width=8, textvariable=self.cavediamondvalueextra_var).grid(column=1, row=2, pady=0)
        tkinter.Entry(f, width=8, textvariable=self.bonus_life_pts_var).grid(column=1, row=3, pady=0)
        tkinter.Checkbutton(f, text="Single Life Only", variable=self.single_life_var,
                            selectcolor=self.cget("background")).grid(column=0, row=4, sticky=tkinter.W, pady=0)
        f.pack(side=tkinter.LEFT, padx=2, anchor=tkinter.N)

        f = tkinter.Frame(self.bottomframe)
        self.cavewidth_var = tkinter.IntVar(value=self.playfield_columns)
        self.caveheight_var = tkinter.IntVar(value=self.playfield_rows)
        self.open_horizontal_borders_var = tkinter.BooleanVar() # Substandard Open Borders feature (Krissz)
        self.open_vertical_borders_var = tkinter.BooleanVar() # Substandard Open Borders feature (Krissz)
        tkinter.Checkbutton(f, text="No Time Limit", variable=self.no_time_limit_var,
                            selectcolor=self.cget("background")).grid(column=0, row=1, sticky=tkinter.W, pady=0)
        tkinter.Checkbutton(f, text="Reverse Time", variable=self.reverse_time_var,
                            selectcolor=self.cget("background")).grid(column=0, row=2, sticky=tkinter.W, pady=0)
        tkinter.Checkbutton(f, text="Open Horizontal Borders", variable=self.open_horizontal_borders_var,
                            selectcolor=self.cget("background")).grid(column=0, row=3, sticky=tkinter.W, pady=0)
        tkinter.Checkbutton(f, text="Open Vertical Borders", variable=self.open_vertical_borders_var,
                            selectcolor=self.cget("background")).grid(column=0, row=4, sticky=tkinter.W, pady=0)
        tkinter.Checkbutton(f, text="Magic Wall Stops Amoeba", variable=self.magic_wall_stops_amoeba_var,
                            selectcolor=self.cget("background")).grid(column=0, row=5, sticky=tkinter.W, pady=0)
        f.pack(side=tkinter.LEFT, padx=2, anchor=tkinter.N)

        f = tkinter.Frame(self.bottomframe)
        self.cavewraparound_var = tkinter.BooleanVar()
        self.cavelineshift_var = tkinter.BooleanVar()
        self.caveintermission_var = tkinter.BooleanVar()
        tkinter.Checkbutton(f, text="Amoeba Early Start", variable=self.amoeba_grows_before_spawn_var,
                            selectcolor=self.cget("background")).grid(column=0, row=1, sticky=tkinter.W, pady=0)
        tkinter.Checkbutton(f, text="Border Wraparound", variable=self.cavewraparound_var,
                            selectcolor=self.cget("background")).grid(column=0, row=2, sticky=tkinter.W, pady=0)
        tkinter.Checkbutton(f, text="Line Shift", variable=self.cavelineshift_var,
                            selectcolor=self.cget("background")).grid(column=0, row=3, sticky=tkinter.W, pady=0)
        tkinter.Checkbutton(f, text="Intermission", variable=self.caveintermission_var,
                            selectcolor=self.cget("background")).grid(column=0, row=3, sticky=tkinter.W, pady=0)
        f.pack(side=tkinter.LEFT, padx=2, anchor=tkinter.N)

        self.bottomframe.pack(side=tkinter.TOP, fill=tkinter.X)
        rightframe.pack(side=tkinter.RIGHT, padx=1, pady=1, fill=tkinter.BOTH, expand=1)

        buttonsframe = tkinter.Frame(self)
        lf = tkinter.LabelFrame(buttonsframe, text="Select object")
        self.imageselector = ScrollableImageSelector(lf, self)
        self.imageselector.pack(padx=1, pady=1)

        lf.pack(expand=1, fill=tkinter.BOTH)
        lf = tkinter.LabelFrame(buttonsframe, text="Misc. edit")
        self.btn_show_imperm_text = tkinter.StringVar()
        self.btn_show_imperm_text.set("Show Imprm")
        tkinter.Button(lf, text="Load", command=self.load, width=8).grid(column=0, row=0)
        tkinter.Button(lf, text="Save", command=self.save, width=8).grid(column=1, row=0)
        tkinter.Button(lf, text="Randomize", command=self.randomize, width=8).grid(column=0, row=1)
        tkinter.Button(lf, text="KE Defaults", command=self.set_krissz_defaults, width=8).grid(column=1, row=1)
        tkinter.Button(lf, text="Wipe", command=self.wipe, width=9).grid(column=2, row=0)
        tkinter.Button(lf, text="Playtest", command=self.playtest, width=8).grid(column=0, row=2)
        tkinter.Button(lf, text="BC Defaults", command=self.set_defaults, width=8).grid(column=1, row=2)
        tkinter.Button(lf, textvariable=self.btn_show_imperm_text, command=self.show_impermeable_slime, width=9).grid(column=2, row=1)
        tkinter.Button(lf, text="Cave Stats", command=self.show_cave_stats, width=9).grid(column=2, row=2)
        lf.pack(fill=tkinter.X, pady=2)
        lf = tkinter.LabelFrame(buttonsframe, text="Commodore-64 colors")
        self.c64colors_var = tkinter.IntVar()
        c64_check = tkinter.Checkbutton(lf, text="Enable retro palette", variable=self.c64colors_var, selectcolor=self.cget("background"),
                                        command=lambda: self.c64_colors_switched(self.c64colors_var.get()))
        c64_check.grid(column=0, row=0)
        self.c64random_button = tkinter.Button(lf, text="Random", state=tkinter.DISABLED, command=self.c64_colors_randomize)
        self.c64random_button.grid(column=0, row=1)
        tkinter.Button(lf, text="Edit", command=self.palette_edit).grid(column=1, row=1)
        lf.pack(fill=tkinter.X, pady=2)
        lf = tkinter.LabelFrame(buttonsframe, text="Cave Size")
        tkinter.Label(lf, text="Cave Width:").grid(column=0, row=0, sticky=tkinter.E, pady=0)
        tkinter.Label(lf, text="Cave Height:").grid(column=0, row=1, sticky=tkinter.E, pady=0)
        tkinter.Entry(lf, width=8, textvariable=self.cavewidth_var).grid(column=1, row=0, pady=0)
        tkinter.Entry(lf, width=8, textvariable=self.caveheight_var).grid(column=1, row=1, pady=0)
        tkinter.Button(lf, text="Resize Cave", command=lambda: self.do_resize_cave(self.cavewidth_var.get(), self.caveheight_var.get()))\
            .grid(column=0, row=2, padx=4)
        tkinter.Button(lf, text="Show Help", command=lambda: self.show_help())\
            .grid(column=1, row=2, padx=4)
        lf.pack(fill=tkinter.X, pady=1)

        buttonsframe.pack(side=tkinter.LEFT, anchor=tkinter.N)
        self.buttonsframe = buttonsframe
        self.snap_tile_xy = self.snap_tile_diagonal = None   # type: Optional[Tuple[int, int]]
        self.bind("<KeyPress>", self.keypress_mainwindow)
        self.canvas.bind("<KeyPress>", self.keypress)
        self.canvas.bind("<KeyRelease>", self.keyrelease)
        self.canvas.bind("<Button-1>", self.mousebutton_left)
        self.canvas.bind("<Button-2>", self.mousebutton_middle)
        self.canvas.bind("<Button-3>", self.mousebutton_right)
        self.canvas.bind("<Motion>", self.mouse_motion)
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.c_tiles = []      # type: List[str]
        self.tile_images = []  # type: List[tkinter.PhotoImage]
        self.tile_images_small = []   # type: List[tkinter.PhotoImage]
        self.canvas_tag_to_tilexy = {}      # type: Dict[int, Tuple[int, int]]
        self.c64colors = krissz_engine_defaults
        self.c64colors_var.set(krissz_engine_defaults)
        self.create_tile_images(Palette())
        self.wipe(False)
        self.create_canvas_playfield(self.playfield_columns, self.playfield_rows)
        w, h = tiles.tile2pixels(self.playfield_columns, self.playfield_rows)
        self.canvas.configure(scrollregion=(0, 0, w * self.canvas_scale, h * self.canvas_scale))
        self.canvas.xview_moveto(0)
        self.canvas.yview_moveto(0)
        self.populate_imageselector()
        self.randomize_initial_values = None    # type: Optional[Tuple]
        # Direction for butterfly/firefly
        self.active_direction = Direction.NOWHERE
        self.center_on_screen()
        # Engine defaults
        self.krissz_engine_defaults = krissz_engine_defaults
        if self.krissz_engine_defaults:
            self.c64_colors_switched(True)
            self.set_krissz_defaults(True)

    def show_help(self):
        help = """
Keyboard shortcuts:
F1 - focus on the map
F - fill area
R - drop 10 objects randomly
S/U - make/restore snapshot
Shift - Fixed horizontal/vertical placement
Ctrl - Fixed diagonal placement
You may need to focus on the map first (F1) before issuing other commands.

When making Krissz Engine-compatible caves, turn off Border Wraparound and Line Shift (use Open Horizontal/Vertical Border instead), consider using Amoeba Limit instead of Amoeba Limit Factor, and the predictable 0-8 Slime Permeability instead of the "unpredictable" fractional one. It's best to start with Krissz Engine defaults by clicking the "KE Defaults" button. Note that you can show impermeable slime on the map by using the Show Imprm button.

BoulderCaves+ supports all possible Krissz Engine cave sizes between 2*2 and 100*100. Standard cave sizes are 40*22 and 20*12.
"""
        tkinter.messagebox.showinfo("BoulderCaves+ Construction Kit", help)

    def center_on_screen(self):
        self.update_idletasks()
        width = self.winfo_width()
        frm_width = self.winfo_rootx() - self.winfo_x()
        self_width = width + 2 * frm_width
        height = self.winfo_height()
        titlebar_height = self.winfo_rooty() - self.winfo_y()
        self_height = height + titlebar_height + frm_width
        x = self.winfo_screenwidth() // 2 - self_width // 2
        y = self.winfo_screenheight() // 2 - self_height // 2
        self.geometry('{}x{}+{}+{}'.format(width, height, x, y))
        self.deiconify()

    def _use_active_image(self):
        return self.show_active_element and self.playfield_columns * self.playfield_rows <= 4096

    def init_new_cave(self, width: int, height: int) -> None:
        if width < 2 or width > 100 or height < 2 or height > 100:
            raise ValueError("invalid playfield/cave width or height (2-100)")
        self.playfield_columns = width
        self.playfield_rows = height
        self.bonus_life_points = 500
        self.cave = Cave(0, self.cavename_var.get(), self.cavedescr_var.get(), width, height)
        self.cave.init_for_editor(self, True)
        self.cave_steel_border()
        self.flood_fill(1, 1, (objects.DIRT, Direction.NOWHERE))
        # add an inbox and an outbox as on Krissz
        self.cave[1, 1] = (objects.INBOXBLINKING, Direction.NOWHERE)
        self.cave[self.cave.width - 1, self.cave.height - 2] = (objects.OUTBOXCLOSED, Direction.NOWHERE)

    def cave_steel_border(self) -> None:
        steel = (objects.STEEL, Direction.NOWHERE)
        self.cave.horiz_line(0, 0, self.playfield_columns, steel)
        self.cave.horiz_line(0, self.playfield_rows - 1, self.playfield_columns, steel)
        self.cave.vert_line(0, 1, self.playfield_rows - 2, steel)
        self.cave.vert_line(self.playfield_columns - 1, 1, self.playfield_rows - 2, steel)

    def get_active_direction(self, object) -> Direction:
        if object == objects.BUTTERFLY or object == objects.FIREFLY \
            or object == objects.ALTBUTTERFLY or object == objects.ALTFIREFLY:
                dirn = self.imageselector.direction_var.get()
                if dirn == "U":
                    return Direction.UP
                elif dirn == "D":
                    return Direction.DOWN
                elif dirn == "L":
                    return Direction.LEFT
                elif dirn == "R":
                    return Direction.RIGHT
                else:
                    return Direction.NOWHERE
        else:
            return Direction.NOWHERE

    def populate_imageselector(self) -> None:
        rows = []
        for obj, displaytile in EDITOR_OBJECTS.items():
            rows.append((self.tile_images_small[displaytile], EDITOR_OBJECT_NAMES[obj]))
        self.imageselector.populate(rows)

    def destroy(self) -> None:
        super().destroy()

    def keypress_mainwindow(self, event) -> None:
        if event.keysym == "F1":
            self.canvas.focus_set()

    def keypress(self, event) -> None:
        self.end_show_impermeable_slime()
        if event.char == 'f':
            current = self.canvas.find_withtag(tkinter.CURRENT)
            if current:
                tx, ty = self.canvas_tag_to_tilexy[current[0]]
                self.flood_fill(tx, ty, (self.imageselector.selected_object, \
                    self.get_active_direction(self.imageselector.selected_object)))
        elif event.char == 'r':
            obj, direction = self.imageselector.selected_object, \
                self.get_active_direction(self.imageselector.selected_object)
            for _ in range(10):
                x = random.randrange(1, self.cave.width - 1)
                y = random.randrange(1, self.cave.height - 1)
                self.cave[x, y] = (obj, direction)
        elif event.char == 's':
            self.snapshot()
        elif event.char == 'u':
            self.restore()
        elif event.keysym.startswith("Shift") or event.keycode == 50 or event.keycode == 62:
            current = self.canvas.find_withtag(tkinter.CURRENT)
            if current:
                self.snap_tile_xy = self.canvas_tag_to_tilexy[current[0]]
        elif event.keysym.startswith("Control"):
            current = self.canvas.find_withtag(tkinter.CURRENT)
            if current:
                self.snap_tile_diagonal = self.canvas_tag_to_tilexy[current[0]]

    def keyrelease(self, event) -> None:
        if event.keysym.startswith("Shift") or event.keycode == 50 or event.keycode == 62:
            self.snap_tile_xy = None
        elif event.keysym.startswith("Control"):
            self.snap_tile_diagonal = None

    def mousebutton_left(self, event) -> None:
        self.canvas.focus_set()
        self.end_show_impermeable_slime()
        current = self.canvas.find_withtag(tkinter.CURRENT)
        if current:
            if event.state & 1:
                self.snap_tile_xy = self.canvas_tag_to_tilexy[current[0]]
            if event.state & 4:
                self.snap_tile_diagonal = self.canvas_tag_to_tilexy[current[0]]
            if self.imageselector.selected_object:
                x, y = self.canvas_tag_to_tilexy[current[0]]
                if self.selected_tile_allowed(x, y):
                    self.cave[x, y] = (self.imageselector.selected_object, \
                        self.get_active_direction(self.imageselector.selected_object))
                    self.set_editor_title(x, y)

    def mousebutton_middle(self, event) -> None:
        pass

    def mousebutton_right(self, event) -> None:
        self.end_show_impermeable_slime()
        current = self.canvas.find_withtag(tkinter.CURRENT)
        if current:
            x, y = self.canvas_tag_to_tilexy[current[0]]
            if self.selected_tile_allowed(x, y):
                self.cave[x, y] = (self.imageselector.selected_erase_object, \
                    self.get_active_direction(self.imageselector.selected_object))

    def set_editor_title(self, x, y) -> None:
        obj = self.cave[x, y][0]
        dirn = self.cave[x, y][1]
        objID = f"object: {EDITOR_OBJECT_NAMES[obj].upper()}"
        if dirn != Direction.NOWHERE:
            objID += f" ({dirn.name})"
        title = f"BoulderCaves+ Construction Kit - X: {x}, Y: {y}, {objID}"
        self.wm_title(title)

    def mouse_motion(self, event) -> None:
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        current = self.canvas.find_closest(cx, cy)
        if current:
            x, y = self.canvas_tag_to_tilexy[current[0]]
            self.set_editor_title(x, y)
            if self.selected_tile_allowed(x, y):
                if event.state & 0x100:
                    # left mouse button drag
                    self.cave[x, y] = (self.imageselector.selected_object, \
                        self.get_active_direction(self.imageselector.selected_object))
                elif event.state & 0x600:
                    # right / middle mouse button drag
                    self.cave[x, y] = (self.imageselector.selected_erase_object, Direction.NOWHERE)
                else:
                    if not self._use_active_image() and self.show_active_element:
                        orig_tile = EDITOR_OBJECTS[self.cave[x, y][0]]
                        self.canvas.itemconfigure(current[0], image=self.tile_images[EDITOR_OBJECTS[self.imageselector.selected_object]])
                        self.after(60, lambda ot=orig_tile, ci=current[0]: self.canvas.itemconfigure(ci, image=self.tile_images[ot]))
            else:
                # show the 'denied' tile briefly
                orig_tile = EDITOR_OBJECTS[self.cave[x, y][0]]
                self.canvas.itemconfigure(current[0], image=self.tile_images[objects.EDIT_CROSS.tile()])
                self.after(60, lambda: self.canvas.itemconfigure(current[0], image=self.tile_images[orig_tile]))
        else:
            title = "BoulderCaves+ Construction Kit {version:s} - by Irmen de Jong, extended by Michael Kamensky".format(version=__version__)
            self.wm_title(title)

    def selected_tile_allowed(self, x: int, y: int) -> bool:
        if self.snap_tile_xy:
            return x == self.snap_tile_xy[0] or y == self.snap_tile_xy[1]
        elif self.snap_tile_diagonal:
            dx, dy = self.snap_tile_diagonal[0] - x, self.snap_tile_diagonal[1] - y
            return abs(dx) == abs(dy)
        return True

    def create_tile_images(self, colors: Palette) -> None:
        source_images = tiles.load_sprites(colors if self.c64colors else None, scale=self.canvas_scale, krissz_c64tileset = self.c64colors)
        self.tile_images = [tkinter.PhotoImage(data=image) for image in source_images]
        source_images = tiles.load_sprites(colors if self.c64colors else None, scale=1, krissz_c64tileset=self.c64colors)
        self.tile_images_small = [tkinter.PhotoImage(data=image) for image in source_images]

    def create_canvas_playfield(self, width: int, height: int) -> None:
        # create the images on the canvas for all tiles (fixed position)
        if width < 2 or width > 100 or height < 2 or height > 100:
            raise ValueError("invalid playfield/cave width or height (2-100)")
        self.playfield_columns = width
        self.playfield_rows = height
        self.canvas.delete(tkinter.ALL)
        self.c_tiles.clear()
        self.canvas_tag_to_tilexy.clear()
        selected_tile = EDITOR_OBJECTS[self.imageselector.selected_object]
        active_image = self.tile_images[selected_tile] if self._use_active_image() else None
        for y in range(self.playfield_rows):
            for x in range(self.playfield_columns):
                sx, sy = tiles.tile2pixels(x, y)
                obj, direction = self.cave[x, y]
                ctile = self.canvas.create_image(sx * self.canvas_scale, sy * self.canvas_scale,
                                                 image=self.tile_images[EDITOR_OBJECTS[obj]],
                                                 activeimage=active_image, anchor=tkinter.NW, tags="tile")
                self.c_tiles.append(ctile)
                self.canvas_tag_to_tilexy[ctile] = (x, y)

    def tile_selection_changed(self, object: GameObject, tile: int) -> None:
        self.canvas.focus_set()
        if self._use_active_image():
            self.config(cursor="watch")
            self.update()
            image = self.tile_images[tile]
            for c_tile in self.c_tiles:
                self.canvas.itemconfigure(c_tile, activeimage=image)
            self.config(cursor="")

    def tile_erase_selection_changed(self, object: GameObject, tile: int) -> None:
        pass

    def set_canvas_tile(self, x: int, y: int, tile: int) -> None:
        c_tile = self.canvas.find_closest(x * 16 * self.canvas_scale, y * 16 * self.canvas_scale)
        self.canvas.itemconfigure(c_tile, image=self.tile_images[tile])

    def flood_fill(self, x: int, y: int, newthing: Tuple[GameObject, Direction]) -> None:
        # scanline floodfill algorithm using a stack
        oldthing = self.cave[x, y][0]
        if oldthing == newthing[0]:
            return
        self.config(cursor="watch")
        self.update()
        stack = [(x, y)]
        while stack:
            x, y = stack.pop()
            x1 = x
            while x1 >= 0 and self.cave[x1, y][0] == oldthing:
                x1 -= 1
            x1 += 1
            span_above = span_below = False
            while x1 < self.cave.width and self.cave[x1, y][0] == oldthing:
                self.cave[x1, y] = newthing
                if not span_above and y > 0 and self.cave[x1, y-1][0] == oldthing:
                    stack.append((x1, y-1))
                    span_above = True
                elif span_above and y > 0 and self.cave[x1, y-1][0] != oldthing:
                    span_above = False
                if not span_below and y < self.cave.height - 1 and self.cave[x1, y+1][0] == oldthing:
                    stack.append((x1, y+1))
                    span_below = True
                elif span_below and y < self.cave.height - 1 and self.cave[x1, y+1][0] != oldthing:
                    span_below = False
                x1 += 1
        self.config(cursor="")

    def snapshot(self) -> None:
        self.cave.snapshot()

    def restore(self) -> None:
        self.cave.restore()

    def wipe(self, confirm=True) -> None:
        if confirm and not tkinter.messagebox.askokcancel("Confirm", "Wipe cave?", parent=self.buttonsframe):
            return
        self.init_new_cave(self.playfield_columns, self.playfield_rows)
        self.snapshot()

    def randomize(self) -> None:
        RandomizeDialog(self.buttonsframe, "Randomize Cave", self, self.randomize_initial_values)

    def palette_edit(self) -> None:
        original_palette = self.cave.colors.copy()
        palette = PaletteDialog(self.buttonsframe, "Edit Palette", self, self.cave.colors).result
        if palette:
            self.cave.colors = palette
        else:
            self.cave.colors = original_palette
            self.apply_new_palette(original_palette)

    def do_random_fill(self, rseed: int, randomprobs: Tuple[int, int, int, int], randomobjs: Tuple[str, str, str, str]) -> None:
        editor_objects_by_name = {EDITOR_OBJECT_NAMES[obj]: obj for obj in EDITOR_OBJECTS}
        randomseeds = [0, rseed]
        for y in range(1, self.playfield_rows - 1):
            for x in range(0, self.playfield_columns):
                objname = EDITOR_OBJECT_NAMES[objects.DIRT]
                C64Cave.bdrandom(randomseeds)
                for randomobj, randomprob in zip(randomobjs, randomprobs):
                    if randomseeds[0] < randomprob:
                        objname = randomobj
                self.cave[x, y] = (editor_objects_by_name[objname], Direction.NOWHERE)
        self.cave_steel_border()
        self.randomize_initial_values = (rseed, randomprobs, randomobjs)

    def do_resize_cave(self, width: int, height: int) -> None:
        if width == self.playfield_columns and height == self.playfield_rows:
            return
        if not tkinter.messagebox.askokcancel("Confirm resize",
                                              "Resize cave?\nYou will lose all of your current work.", parent=self.bottomframe):
            return
        try:
            self.init_new_cave(width, height)
            self.create_canvas_playfield(width, height)
        except ValueError as x:
            tkinter.messagebox.showerror("Error resizing cave", str(x), parent=self.bottomframe)
            return
        self.reconfigure_scroll_area()

    def reconfigure_scroll_area(self):
        w, h = tiles.tile2pixels(self.playfield_columns, self.playfield_rows)
        self.canvas.configure(scrollregion=(0, 0, w * self.canvas_scale, h * self.canvas_scale))

    def c64_colors_switched(self, switch: bool) -> None:
        self.c64random_button.configure(state=tkinter.NORMAL if switch else tkinter.DISABLED)
        self.c64colors = bool(switch)
        self.create_tile_images(self.cave.colors)
        self.imageselector.selected_object = objects.BOULDER
        self.imageselector.selected_erase_object = objects.EMPTY
        self.populate_imageselector()
        self.create_canvas_playfield(self.playfield_columns, self.playfield_rows)
        self.end_show_impermeable_slime()

    def c64_colors_randomize(self) -> None:
        if self.c64colors:
            self.cave.colors.randomize()
            self.apply_new_palette(self.cave.colors)

    def apply_new_palette(self, colors: Palette) -> None:
        if self.c64colors:
            self.create_tile_images(colors)
            self.populate_imageselector()
            self.create_canvas_playfield(self.playfield_columns, self.playfield_rows)
            self.canvas.configure(background="#{:06x}".format(colors.rgb_border))

    def load(self):
        if not tkinter.messagebox.askokcancel("Confirm", "Load cave and lose current one?", parent=self.buttonsframe):
            return
        gamefile = tkinter.filedialog.askopenfilename(title="Load caveset file", defaultextension=".bdcff",
                                                      filetypes=[("Boulder Dash BDCFF File", ".bdcff"),
                                                                 ("Boulder Dash BDCFF File", ".bd"),
                                                                 ("Plain Text", ".txt")],
                                                      parent=self.buttonsframe)
        if len(gamefile) == 0:
            return
        caveset = CaveSet(gamefile, caveclass=Cave)
        if caveset.num_caves > 1:
            cavenum = CaveSelectionDialog(self.buttonsframe, caveset.cave_names(), self).result
            if cavenum is None:
                return
        else:
            cavenum = 1
        cave = caveset.cave(cavenum)
        cave.init_for_editor(self, False)
        self.cave = cave
        self.playfield_columns = cave.width
        self.playfield_rows = cave.height
        self.bonus_life_points = caveset.bonus_life_points
        self.bonus_life_pts_var.set(self.bonus_life_points)
        self.set_cave_properties(self.cave)
        self.c64_colors_switched(self.c64colors)  # make sure tiles are redrawn
        self.reconfigure_scroll_area()

    def set_cave_properties(self, cave: Cave) -> None:
        self.cavename_var.set(cave.name)
        self.cavedescr_var.set(cave.description)
        self.cavesetauthor_var.set(cave.author or bdcff.get_system_username())
        self.cavesetdate_var.set(cave.date or str(datetime.datetime.now().date()))
        self.cavesetwww_var.set(cave.www)
        self.cavediamondsrequired_var.set(cave.diamonds_required)
        self.cavediamondvaluenorm_var.set(cave.diamondvalue_normal)
        self.cavediamondvalueextra_var.set(cave.diamondvalue_extra)
        self.caveamoebafactor_var.set(cave.amoebafactor)
        self.caveamoebatime_var.set(cave.amoeba_slowgrowthtime)
        self.cavemagicwalltime_var.set(cave.magicwall_millingtime)
        self.caveintermission_var.set(cave.intermission)
        self.cavetimelimit_var.set(cave.time)
        self.caveslimepermeability_var.set(cave.slime_permeability)
        self.cavewraparound_var.set(cave.wraparound)
        self.cavelineshift_var.set(cave.lineshift)
        self.cavewidth_var.set(cave.width)
        self.caveheight_var.set(cave.height)
        # Substandard features (Krissz)
        self.target_fps_var.set(cave.target_fps)
        self.rockford_birth_time_var.set(cave.rockford_birth_time)
        self.amoeba_limit_var.set(cave.amoeba_limit)
        self.magic_wall_stops_amoeba_var.set(cave.magic_wall_stops_amoeba)
        self.amoeba_grows_before_spawn_var.set(cave.amoeba_grows_before_spawn)
        self.no_time_limit_var.set(cave.no_time_limit)
        self.reverse_time_var.set(cave.reverse_time)
        self.open_horizontal_borders_var.set(cave.open_horizontal_borders)
        self.open_vertical_borders_var.set(cave.open_vertical_borders)
        self.value_of_a_second_var.set(cave.value_of_a_second)
        self.single_life_var.set(cave.single_life)
        self.krissz_slime_permeability_var.set(cave.krissz_slime_permeability)

    def save(self, gamefile: Optional[str]=None) -> bool:
        if not self.sanitycheck():
            return False
        caveset = bdcff.BdcffParser()
        caveset.num_caves = 1
        caveset.name = self.cavename_var.get()
        caveset.author = self.cavesetauthor_var.get()
        caveset.www = self.cavesetwww_var.get()
        caveset.date = self.cavesetdate_var.get()
        caveset.description = self.cavedescr_var.get()
        caveset.bonus_life_points = self.bonus_life_pts_var.get()
        cave = bdcff.BdcffCave()
        cave.name = self.cavename_var.get()
        cave.description = self.cavedescr_var.get()
        cave.width = self.cave.width
        cave.height = self.cave.height
        cave.cavetime = self.cavetimelimit_var.get()
        cave.diamonds_required = self.cavediamondsrequired_var.get()
        cave.diamondvalue_normal = self.cavediamondvaluenorm_var.get()
        cave.diamondvalue_extra = self.cavediamondvalueextra_var.get()
        cave.amoebatime = self.caveamoebatime_var.get()
        cave.amoebafactor = self.caveamoebafactor_var.get()
        cave.magicwalltime = self.cavemagicwalltime_var.get()
        cave.slimepermeability = self.caveslimepermeability_var.get()
        cave.intermission = self.caveintermission_var.get()
        cave.wraparound = self.cavewraparound_var.get()
        cave.lineshift = self.cavelineshift_var.get()
        # + Substandard features (Krissz) +
        cave.target_fps = self.target_fps_var.get()
        cave.rockford_birth_time = self.rockford_birth_time_var.get()
        cave.amoeba_limit = self.amoeba_limit_var.get()
        cave.magic_wall_stops_amoeba = self.magic_wall_stops_amoeba_var.get()
        cave.amoeba_grows_before_spawn = self.amoeba_grows_before_spawn_var.get()
        cave.no_time_limit = self.no_time_limit_var.get()
        cave.reverse_time = self.reverse_time_var.get()
        cave.open_horizontal_borders = self.open_horizontal_borders_var.get()
        cave.open_vertical_borders = self.open_vertical_borders_var.get()
        cave.value_of_a_second = self.value_of_a_second_var.get()
        cave.single_life = self.single_life_var.get()
        cave.krissz_slime_permeability = self.krissz_slime_permeability_var.get()
        # - Substandard features (Krissz) -
        c = self.cave.colors
        cave.color_border, cave.color_screen, cave.color_fg1, cave.color_fg2, cave.color_fg3, cave.color_amoeba, cave.color_slime = \
            c.border, c.screen, c.fg1, c.fg2, c.fg3, c.amoeba, c.slime
        BDCFFSYMBOL = {(obj, direction): symbol for symbol, (obj, direction) in BDCFFOBJECTS.items()}
        for y in range(0, self.cave.height):
            mapline = ""
            for x in range(0, self.cave.width):
                obj, direction = self.cave[x, y]
                mapline += BDCFFSYMBOL[obj, direction]
            cave.map.maplines.append(mapline)
        caveset.caves.append(cave)
        gamefile = gamefile or tkinter.filedialog.asksaveasfilename(title="Save single cave as", defaultextension=".bdcff",
                                                                    filetypes=[("Boulder Dash BDCFF File", ".bdcff"),
                                                                               ("Boulder Dash BDCFF File", ".bd"),
                                                                               ("Plain Text", ".txt")],
                                                                    parent=self.buttonsframe)
        if gamefile:
            with open(gamefile, "wt") as out:
                caveset.write(out)
            return True
        return False

    def sanitycheck(self):
        # check that the level is sane:
        # we should have at least 1 inbox and at least 1 outbox.
        # (edge is no longer checked, you should take care of a closed cave yourself!)
        inbox_count = len([x for x, _ in self.cave.map if x == objects.INBOXBLINKING])
        outbox_count = len([x for x, _ in self.cave.map if x in (objects.OUTBOXCLOSED, objects.OUTBOXBLINKING, objects.OUTBOXHIDDEN)])
        messages = []
        if inbox_count <= 0:
            messages.append("There should be at least one INBOX.")
        if outbox_count <= 0:
            messages.append("There should be at least one OUTBOX.")
        if messages:
            messages.insert(0, "There are some problems with the current cave:")
            tkinter.messagebox.showerror("Cave sanity check failed", "\n\n".join(messages), parent=self.buttonsframe)
            return False
        return True

    def playtest(self) -> None:
        print("\n\nPLAYTESTING: saving temporary cave file...")
        gamefile = os.path.expanduser("~/.bcplus/_playtest_cave.bdcff")
        if self.save(gamefile):
            # launch the game in a separate process
            import subprocess
            from . import game
            env = os.environ.copy()
            env["PYTHONPATH"] = sys.path[0]
            if self.krissz_engine_defaults:
                parameters = [sys.executable, "-m", game.__name__, "--krissz", "--playtest", "--game", gamefile]
            else:
                parameters = [sys.executable, "-m", game.__name__, "--synth", "--playtest", "--game", gamefile]
                if self.c64colors_var.get():
                    parameters.append("--c64colors")
            print("PLAYTESTING: launching game in playtest mode...\n")
            subprocess.Popen(parameters, env=env)

    def set_defaults(self) -> None:
        if not tkinter.messagebox.askokcancel("Confirm", "Set all cave parameters to their BoulderCaves defaults?", parent=self.buttonsframe):
            return
        self.set_cave_properties(Cave(0, "Test.", "A test cave.", self.visible_columns, self.visible_rows))

    def set_krissz_defaults(self, forced: bool = False) -> None:
        if not forced and not tkinter.messagebox.askokcancel("Confirm", "Set all cave parameters to their Krissz Engine defaults?", parent=self.buttonsframe):
            return
        self.set_cave_properties(Cave(0, "Untitled", "A new cave", self.visible_columns, self.visible_rows))
        self.cavewraparound_var.set(False)
        self.cavelineshift_var.set(False)
        self.target_fps_var.set(7.5)
        self.rockford_birth_time_var.set(20)
        self.amoeba_limit_var.set(200)
        self.magic_wall_stops_amoeba_var.set(True)
        self.amoeba_grows_before_spawn_var.set(True)
        self.no_time_limit_var.set(False)
        self.reverse_time_var.set(False)
        self.open_horizontal_borders_var.set(False)
        self.open_vertical_borders_var.set(False)
        self.value_of_a_second_var.set(1)
        self.caveamoebatime_var.set(60)
        self.cavemagicwalltime_var.set(20)
        self.cavediamondsrequired_var.set(5)
        self.cavediamondvaluenorm_var.set(10)
        self.cavediamondvalueextra_var.set(20)
        self.cavetimelimit_var.set(150)
        self.caveslimepermeability_var.set(0.0) # Not used, Krissz Slime Permeability is used instead
        self.single_life_var.set(True)
        self.krissz_slime_permeability_var.set(6) # Slime permeability 6 in Krissz engine
        self.caveamoebafactor_var.set(0.0) # Not used, Amoeba Limit is used instead
        # reset colors
        if not forced and not tkinter.messagebox.askokcancel("Confirm", "Set the color palette to Krissz Engine defaults?", parent=self.buttonsframe):
            return
        default_palette = Palette("#a36e30", "#646464", "#ffffff", "#ffffff", "#ffffff", "#000000", "#000000")
        self.cave.colors = default_palette
        self.apply_new_palette(default_palette)
    
    def show_cave_stats(self) -> None:
        CaveStatsHelper.show_cave_stats(self.cave, self.krissz_slime_permeability_var.get(), self.caveslimepermeability_var.get())

    def show_impermeable_slime(self) -> None:
        self.showing_impermeable_slime = not self.showing_impermeable_slime
        if self.showing_impermeable_slime:
            permeability = CaveStatsHelper.get_c64_permeability(-1, -1, self.cave, self.krissz_slime_permeability_var.get(), True)
            for y in range(0, self.cave.height):
                for x in range(0, self.cave.width):
                    if (self.cave.map[x + self.cave.width * y][0] == objects.SLIME):
                        if 0 <= self.krissz_slime_permeability_var.get() <= 8:
                            permeable = permeability[(x, y)]
                        else:
                            permeable = self.caveslimepermeability_var.get() != 0.0
                        if not permeable:
                            self.set_canvas_tile(x, y, objects.SLIME_IMPERMEABLE.tile())
                        else:
                            self.set_canvas_tile(x, y, EDITOR_OBJECTS[objects.SLIME])
            self.btn_show_imperm_text.set("Hide Imprm")
        else:
            self.end_show_impermeable_slime(True)
    
    def end_show_impermeable_slime(self, force = False) -> None:
        if self.showing_impermeable_slime or force:
            for y in range(0, self.cave.height):
                for x in range(0, self.cave.width):
                    if (self.cave.map[x + self.cave.width * y][0] == objects.SLIME):
                        self.set_canvas_tile(x, y, EDITOR_OBJECTS[objects.SLIME])
        self.showing_impermeable_slime = False
        self.btn_show_imperm_text.set("Show Imprm")


class RandomizeDialog(Dialog):
    def __init__(self, parent, title: str, editor: EditorWindow, initial_values: Optional[Tuple]) -> None:
        self.editor = editor
        self.initial_values = initial_values
        super().__init__(parent=parent, title=title)

    def body(self, master: tkinter.Widget) -> tkinter.Widget:
        if not self.initial_values:
            self.initial_values = (199, (100, 60, 25, 15),
                                   (EDITOR_OBJECT_NAMES[objects.EMPTY], EDITOR_OBJECT_NAMES[objects.BOULDER],
                                    EDITOR_OBJECT_NAMES[objects.DIAMOND], EDITOR_OBJECT_NAMES[objects.FIREFLY]))
        self.rseed_var = tkinter.IntVar(value=self.initial_values[0])
        self.rp1_var = tkinter.IntVar(value=self.initial_values[1][0])
        self.rp2_var = tkinter.IntVar(value=self.initial_values[1][1])
        self.rp3_var = tkinter.IntVar(value=self.initial_values[1][2])
        self.rp4_var = tkinter.IntVar(value=self.initial_values[1][3])
        self.robj1_var = tkinter.StringVar(value=self.initial_values[2][0].title())
        self.robj2_var = tkinter.StringVar(value=self.initial_values[2][1].title())
        self.robj3_var = tkinter.StringVar(value=self.initial_values[2][2].title())
        self.robj4_var = tkinter.StringVar(value=self.initial_values[2][3].title())
        tkinter.Label(master, text="Fill the cave with randomized stuff, using the C-64 BD randomizer.\n").pack()
        f = tkinter.Frame(master)
        tkinter.Label(f, text="Random seed (0-255): ").grid(row=0, column=0)
        tkinter.Label(f, text="Random probability (0-255): ").grid(row=1, column=0)
        tkinter.Label(f, text="Random probability (0-255): ").grid(row=2, column=0)
        tkinter.Label(f, text="Random probability (0-255): ").grid(row=3, column=0)
        tkinter.Label(f, text="Random probability (0-255): ").grid(row=4, column=0)
        rseed = tkinter.Entry(f, textvariable=self.rseed_var, width=4, font="fixed")
        rp1 = tkinter.Entry(f, textvariable=self.rp1_var, width=4, font="fixed")
        rp2 = tkinter.Entry(f, textvariable=self.rp2_var, width=4, font="fixed")
        rp3 = tkinter.Entry(f, textvariable=self.rp3_var, width=4, font="fixed")
        rp4 = tkinter.Entry(f, textvariable=self.rp4_var, width=4, font="fixed")
        rseed.grid(row=0, column=1)
        rp1.grid(row=1, column=1)
        rp2.grid(row=2, column=1)
        rp3.grid(row=3, column=1)
        rp4.grid(row=4, column=1)
        options = sorted([EDITOR_OBJECT_NAMES[obj] for obj in EDITOR_OBJECTS])
        tkinter.OptionMenu(f, self.robj1_var, *options).grid(row=1, column=2, stick=tkinter.W)
        tkinter.OptionMenu(f, self.robj2_var, *options).grid(row=2, column=2, stick=tkinter.W)
        tkinter.OptionMenu(f, self.robj3_var, *options).grid(row=3, column=2, stick=tkinter.W)
        tkinter.OptionMenu(f, self.robj4_var, *options).grid(row=4, column=2, stick=tkinter.W)
        f.pack()
        tkinter.Label(master, text="\n\nWARNING: DOING THIS WILL WIPE THE CURRENT CAVE!").pack()
        return rp1

    def validate(self) -> bool:
        try:
            vs = self.rseed_var.get()
            v1 = self.rp1_var.get()
            v2 = self.rp1_var.get()
            v3 = self.rp1_var.get()
            v4 = self.rp1_var.get()
        except tkinter.TclError as x:
            tkinter.messagebox.showerror("Invalid entry", str(x), parent=self)
            return False
        else:
            if not (0 <= vs <= 255) or not (0 <= v1 <= 255) or not(0 <= v2 <= 255) or not(0 <= v3 <= 255) or not(0 <= v4 <= 255):
                tkinter.messagebox.showerror("Invalid entry", "One or more of the values is invalid.", parent=self)
                return False
        return True

    def apply(self) -> None:
        vs = self.rseed_var.get()
        v1 = self.rp1_var.get()
        v2 = self.rp2_var.get()
        v3 = self.rp3_var.get()
        v4 = self.rp4_var.get()
        o1 = self.robj1_var.get()
        o2 = self.robj2_var.get()
        o3 = self.robj3_var.get()
        o4 = self.robj4_var.get()
        self.editor.do_random_fill(vs, (v1, v2, v3, v4), (o1, o2, o3, o4))


class PaletteDialog(Dialog):
    def __init__(self, parent, title: str, editor: EditorWindow, colors: Palette) -> None:
        self.editor = editor
        self.colors = colors
        self.result = Palette()
        self.palettergblabels = {}   # type: Dict[str, tkinter.Label]
        self.color_vars = {}   # type: Dict[str, tkinter.Variable]
        self.rgb_vars = {}   # type: Dict[str, tkinter.Variable]
        super().__init__(parent=parent, title=title)

    def body(self, master: tkinter.Widget) -> Optional[tkinter.Widget]:
        colors = [("fg1", self.colors.fg1), ("fg2", self.colors.fg2), ("fg3", self.colors.fg3),
                  ("amoeba", self.colors.amoeba), ("slime", self.colors.slime),
                  ("screen", self.colors.screen), ("border", self.colors.border)]
        for colornum, (name, value) in enumerate(colors):
            color_var = tkinter.StringVar(value=value)
            self.color_vars[name] = color_var
            tkinter.Label(master, text="{:s} color: ".format(name.title())).grid(row=colornum, sticky=tkinter.E)
            rf = tkinter.Frame(master)
            for num, color in enumerate(colorpalette):
                tkcolor = "#{:06x}".format(color)
                rb = tkinter.Radiobutton(rf, variable=color_var, indicatoron=False, value=num,
                                         activebackground=tkcolor, command=lambda n=name: self.palette_color_chosen(n),
                                         offrelief=tkinter.FLAT, relief=tkinter.FLAT, overrelief=tkinter.RIDGE,
                                         bd=5, bg=tkcolor, selectcolor=tkcolor, width=2, height=1)
                rb.pack(side=tkinter.LEFT)
                if num == value:
                    rb.select()
            tkinter.Label(rf, text=" or: ").pack(side=tkinter.LEFT)
            tkinter.Button(rf, text="select", command=lambda n=name: self.rgb_color_chosen(n)).pack(side=tkinter.LEFT)
            rgb_var = tkinter.IntVar()
            self.rgb_vars[name] = rgb_var
            rgb_label = tkinter.Label(rf, text="any RGB color")
            if isinstance(value, str):
                fgtkcolor = "#{:06x}".format(0xffffff ^ int(value[1:], 16))
                rgb_label.configure(bg=value, fg=fgtkcolor)
            rgb_label.pack(side=tkinter.LEFT, expand=True, fill=tkinter.Y)
            self.palettergblabels[name] = rgb_label
            rf.grid(row=colornum, column=1, pady=4, sticky=tkinter.W)
        return None

    def palette_color_chosen(self, colorname: str) -> None:
        # reset the rgb button of this color row
        dummylabel = tkinter.Label(self)
        self.palettergblabels[colorname].configure(bg=dummylabel.cget("bg"), fg=dummylabel.cget("fg"))
        self.editor.apply_new_palette(self.palette)

    def rgb_color_chosen(self, colorname: str) -> None:
        color = self.color_vars[colorname].get()
        if not color.startswith("#"):
            color = "#{:06x}".format(colorpalette[int(color)])
        rgbcolor = tkinter.colorchooser.askcolor(title="Choose a RGB color", parent=self, initialcolor=color)
        if rgbcolor[1] is not None:
            tkcolor = rgbcolor[1]
            fgtkcolor = "#{:06x}".format(0xffffff ^ int(tkcolor[1:], 16))
            self.color_vars[colorname].set(tkcolor)
            self.palettergblabels[colorname].configure(bg=tkcolor, fg=fgtkcolor)
            self.editor.apply_new_palette(self.palette)

    def apply(self) -> None:
        self.result = self.palette

    @property
    def palette(self) -> Palette:
        return Palette(self.color_vars["fg1"].get(),
                       self.color_vars["fg2"].get(),
                       self.color_vars["fg3"].get(),
                       self.color_vars["amoeba"].get(),
                       self.color_vars["slime"].get(),
                       self.color_vars["screen"].get(),
                       self.color_vars["border"].get())


class CaveSelectionDialog(Dialog):
    def __init__(self, parent, cavenames: List[str], editor: EditorWindow) -> None:
        self.editor = editor
        self.cavenames = cavenames
        self.result = None
        super().__init__(parent=parent, title="Select the cave to load")

    def body(self, master: tkinter.Widget) -> tkinter.Widget:
        tkinter.Label(master, text="Currently you can only edit a single cave.\nThe selected file contains multiple caves:").pack()
        f = tkinter.Frame(master)
        self.lb = tkinter.Listbox(f, bd=1, font="fixed", height=min(25, len(self.cavenames)),
                                  width=max(10, max(len(name) for name in self.cavenames)))
        for name in self.cavenames:
            self.lb.insert(tkinter.END, name)
        sy = tkinter.Scrollbar(f, orient=tkinter.VERTICAL, command=self.lb.yview)
        self.lb.configure(yscrollcommand=sy.set)
        self.lb.pack(side=tkinter.LEFT)
        sy.pack(side=tkinter.RIGHT, expand=1, fill=tkinter.Y)
        f.pack(pady=8)
        tkinter.Label(master, text="Select the single cave to load from this caveset file.").pack()
        return self.lb

    def apply(self) -> None:
        selection = self.lb.curselection()
        self.result = (selection[0] + 1) if selection else None


def start() -> None:
    print(f"BoulderCaves+ Construction Kit v. {__version__}. Original by Irmen de Jong, extended by Michael Kamensky.")
    print("This software is licensed under the GNU GPL 3.0, see https://www.gnu.org/licenses/gpl.html")

    # Enable the BoulderCaves 5.7.2 style behavior showing the active element
    show_active_elem = "-a" in sys.argv or "--active" in sys.argv
    use_krissz_engine_defs = "-k" in sys.argv or "--krissz" in sys.argv
    show_help = "-h" in sys.argv or "--help" in sys.argv
    
    if show_help:
        print("\nAvailable options:\n")
        print("  -a (--active) - enable the visibility of the active selected element under cursor")
        print("  -h (--help) - show this help")
        exit(0)
    
    window = EditorWindow(show_active_elem, use_krissz_engine_defs)
    window.mainloop()


if __name__ == "__main__":
    start()
