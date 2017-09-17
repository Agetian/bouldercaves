"""
Boulder Caves Editor.

Cave Set editor

Written by Irmen de Jong (irmen@razorvine.net)
License: MIT open-source.
"""

import sys
import tkinter
import tkinter.messagebox
import tkinter.simpledialog
import tkinter.ttk
import pkgutil
from typing import Tuple, Optional
from ..gfxwindow import __version__
from ..caves import colorpalette
from ..game import Objects, GameObject
from .. import tiles


class ScrollableImageSelector(tkinter.Frame):
    def __init__(self, master, listener):
        super().__init__(master)
        self.treeview = tkinter.ttk.Treeview(self, columns=("tile",), displaycolumns=("tile",))
        self.treeview.heading("tile", text="Tile")
        self.treeview.column("#0", stretch=False, minwidth=50, width=50, anchor=tkinter.W)
        self.treeview.column("tile", stretch=True, width=120)
        tkinter.ttk.Style(self).configure("Treeview", rowheight=36, background="#201000", foreground="#e0e0e0")
        sy = tkinter.Scrollbar(self, orient=tkinter.VERTICAL, command=self.treeview.yview)
        sy.pack(side=tkinter.RIGHT, expand=1, fill=tkinter.Y)
        self.treeview["yscrollcommand"] = sy.set
        self.treeview.pack(expand=1, fill=tkinter.Y)
        self.treeview.bind("<<TreeviewSelect>>", self.on_selected)
        self.selected_tile = None
        self.listener = listener

    def on_selected(self, event):
        item = self.treeview.focus()
        item = self.treeview.item(item)
        self.selected_tile = item["values"][0]
        self.listener.tile_selection_changed(self.selected_tile)

    def populate(self, rows):
        for row in self.treeview.get_children():
            self.treeview.delete(row)
        for image, name in rows:
            print(self.treeview.insert("", tkinter.END, image=image, values=(name,)))


SUPPORTED_OBJECTS = {
    Objects.AMOEBA,
    Objects.BOULDER,
    Objects.BRICK,
    Objects.BUTTERFLY,
    Objects.DIAMOND,
    Objects.DIRT,
    Objects.EMPTY,
    Objects.FIREFLY,
    Objects.HEXPANDINGWALL,
    Objects.INBOXBLINKING,
    Objects.MAGICWALL,
    Objects.OUTBOXBLINKING,
    Objects.SLIME,
    Objects.STEEL,
    Objects.VEXPANDINGWALL,
    Objects.VOODOO
}


class EditorWindow(tkinter.Tk):
    visible_columns = 40
    visible_rows = 22
    max_columns = 200
    max_rows = 200
    scalexy = 2.0

    def __init__(self) -> None:
        super().__init__()
        self.geometry("+200+40")
        title = "Boulder Caves Editor {version:s} - created by Irmen de Jong - irmen@razorvine.net".format(version=__version__)
        self.wm_title(title)
        self.appicon = tkinter.PhotoImage(data=pkgutil.get_data(__name__, "../gfx/gdash_icon_48.gif"))
        self.wm_iconphoto(self, self.appicon)
        if sys.platform == "win32":
            # tell windows to use a new toolbar icon
            import ctypes
            myappid = 'net.Razorvine.Bouldercaves.editor'  # arbitrary string
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        cf = tkinter.Frame(self)
        w, h = self.physcoor(*tiles.tile2pixels(self.visible_columns, self.visible_rows))
        self.canvas = tkinter.Canvas(cf, width=w, height=h, borderwidth=8, highlightthickness=6, background="red", highlightcolor="#206040")
        self.canvas.grid(row=0, column=0)
        sy = tkinter.Scrollbar(cf, orient=tkinter.VERTICAL, command=self.canvas.yview)
        sx = tkinter.Scrollbar(cf, orient=tkinter.HORIZONTAL, command=self.canvas.xview)
        self.canvas["xscrollcommand"] = sx.set
        self.canvas["yscrollcommand"] = sy.set
        sy.grid(row=0, column=1, sticky=tkinter.N + tkinter.S)
        sx.grid(row=1, column=0, sticky=tkinter.E + tkinter.W)
        cf.pack(side=tkinter.RIGHT, padx=4, pady=4, fill=tkinter.BOTH, expand=1)
        f = tkinter.Frame(self)
        lf = tkinter.LabelFrame(f, text="text")
        b = tkinter.Button(lf, text="sdfsdf")
        self.imageselector = ScrollableImageSelector(lf, self)
        self.imageselector.pack(expand=1, fill=tkinter.Y)
        b.pack()
        lf.pack(expand=1, fill=tkinter.Y)
        f.pack(side=tkinter.LEFT, anchor=tkinter.N, expand=1, fill=tkinter.Y)
        self.canvas.bind("<KeyPress>", self.keypress)
        self.canvas.bind("<KeyRelease>", self.keyrelease)
        self.canvas.bind("<Button-1>", self.mousebutton_left)
        self.canvas.bind("<Button-2>", self.mousebutton_middle)
        self.canvas.bind("<Button-3>", self.mousebutton_right)
        self.canvas.bind("<Motion>", self.mouse_motion)
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.c_tiles = []      # type: List[str]
        self.tile_images = []  # type: List[tkinter.PhotoImage]
        self.c64colors = False
        self.sprites = tiles.Sprites(self.scalexy)
        self.playfield_rows = self.playfield_columns = 0
        self.canvas_tag_to_tilexy = {}
        self.create_tile_images()
        self.create_canvas_playfield_and_tilesheet(40, 22)
        w, h = self.physcoor(*tiles.tile2pixels(self.playfield_columns, self.playfield_rows))
        self.canvas.configure(scrollregion=(0, 0, w, h))
        self.canvas.xview_moveto(0)
        self.canvas.yview_moveto(0)
        self.populate_imageselector()

    def populate_imageselector(self):
        rows = []
        for obj in sorted(SUPPORTED_OBJECTS, key=lambda o: o.name):
            tile = self.sprites.sprite2tile(obj)
            rows.append((self.tile_images[tile], obj.name))
        self.imageselector.populate(rows)

    def destroy(self) -> None:
        super().destroy()

    def keypress(self, event) -> None:
        print("keypress", event)  # XXX

    def keyrelease(self, event) -> None:
        print("keyrelease", event)  # XXX

    def mousebutton_left(self, event) -> None:
        print("mouse left", event)  # XXX
        self.canvas.focus_set()
        current = self.canvas.find_withtag(tkinter.CURRENT)
        if current:
            current = current[0]
            if self.canvas_tag_to_tilexy:
                print("tilexy:", self.canvas_tag_to_tilexy[current])   # XXX
            selected_object, selected_tile = self.get_selected_tile()
            if selected_object:
                self.canvas.itemconfigure(current, image=self.tile_images[selected_tile])

    def mousebutton_middle(self, event) -> None:
        print("mouse middle", event)  # XXX

    def mousebutton_right(self, event) -> None:
        print("mouse right", event)  # XXX
        current = self.canvas.find_withtag(tkinter.CURRENT)
        if current:
            current = current[0]
            if self.canvas_tag_to_tilexy:
                print("tilexy:", self.canvas_tag_to_tilexy[current])   # XXX
            self.canvas.itemconfigure(current, image=self.tile_images[self.sprites.sprite2tile(Objects.EMPTY)])

    def mouse_motion(self, event) -> None:
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        current = self.canvas.find_closest(cx, cy)
        if current:
            current = current[0]
            if self.canvas_tag_to_tilexy:
                print("tilexy:", self.canvas_tag_to_tilexy[current])   # XXX
        if event.state & 0x100:
            # left mouse button drag
            selected_object, selected_tile = self.get_selected_tile()
            if selected_object:
                self.canvas.itemconfigure(current, image=self.tile_images[selected_tile])
        if event.state & 0x400:
            # right mouse button drag
            self.canvas.itemconfigure(current, image=self.tile_images[self.sprites.sprite2tile(Objects.EMPTY)])

    def physcoor(self, sx: int, sy: int) -> Tuple[int, int]:
        return int(sx * self.scalexy), int(sy * self.scalexy)

    def create_tile_images(self) -> None:
        source_images = self.sprites.load_sprites(self.c64colors, colorpalette[2], colorpalette[14], colorpalette[13], 0)
        self.tile_images = [tkinter.PhotoImage(data=image) for image in source_images]
        print(vars(self.tile_images[0]))
        source_images = self.sprites.load_font(False)
        self.tile_images.extend([tkinter.PhotoImage(data=image) for image in source_images])

    def create_canvas_playfield_and_tilesheet(self, width: int, height: int) -> None:
        # create the images on the canvas for all tiles (fixed position):
        if width == self.playfield_columns and height == self.playfield_rows:
            return
        if width < 4 or width > 200 or height < 4 or height > 200:
            raise ValueError("invalid playfield/cave width or height")
        self.playfield_columns = width
        self.playfield_rows = height
        self.canvas.delete(tkinter.ALL)
        self.c_tiles.clear()
        self.canvas_tag_to_tilexy.clear()
        boulder_tile = self.sprites.sprite2tile(Objects.DIRT2)
        selected_object, selected_tile = self.get_selected_tile(Objects.EDIT_CROSS)
        for y in range(self.playfield_rows):
            for x in range(self.playfield_columns):
                sx, sy = self.physcoor(*tiles.tile2pixels(x, y))
                tile = self.canvas.create_image(sx, sy, image=self.tile_images[boulder_tile], activeimage=self.tile_images[selected_tile],
                                                anchor=tkinter.NW, tags="tile")
                self.c_tiles.append(tile)
                self.canvas_tag_to_tilexy[tile] = (x, y)
        print(self.canvas_tag_to_tilexy)
        self.tilesheet = tiles.Tilesheet(self.playfield_columns, self.playfield_rows, self.visible_columns, self.visible_rows)

    def get_selected_tile(self, fallback: GameObject=None) -> Tuple[GameObject, Optional[int]]:
        if not self.imageselector.selected_tile:
            if fallback:
                fallback_tile = self.sprites.sprite2tile(fallback)
                return fallback, fallback_tile
            return None, None
        for obj in SUPPORTED_OBJECTS:
            if obj.name == self.imageselector.selected_tile:
                return obj, self.sprites.sprite2tile(obj)
        if fallback:
            fallback_tile = self.sprites.sprite2tile(fallback)
            return fallback, fallback_tile
        return None, None

    def tile_selection_changed(self, selected: str) -> None:
        selected_object, selected_tile = self.get_selected_tile(Objects.EDIT_CROSS)
        for c_tile in self.c_tiles:
            self.canvas.itemconfigure(c_tile, activeimage=self.tile_images[selected_tile])


def start() -> None:
    window = EditorWindow()
    window.mainloop()


if __name__ == "__main__":
    start()
