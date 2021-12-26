"""
Boulder Caves+ - a Boulder Dash (tm) clone.
Krissz Engine-compatible remake based on Boulder Caves 5.7.2.

Helper routines that don't belong in Game or GameLogic.
These routines are written by Michael Kamensky.

License: GNU GPL 3.0, see LICENSE
"""

import os
import tkinter
from .caves import C64Cave
from . import objects

class KeyHelper():
    def load_key_definitions():
        keymap = {
            "up": "Up",
            "down": "Down",
            "left": "Left",
            "right": "Right",
            "pause": "space",
            "snap": "Control",
            "start": "F1",
            "suicide": "Escape"
        }
        mapped = []
        if os.path.exists("controls.ini"):
            with open("controls.ini", "r") as keymap_file:
                lines = keymap_file.readlines()
                for line in lines:
                    data = line.strip().split("=")
                    keydef = data[0].strip().lower()
                    key = data[1].strip()
                    # normalize some key names
                    if key.lower() == "up":
                        key = "Up"
                    elif key.lower() == "down":
                        key = "Down"
                    elif key.lower() == "left":
                        key = "Left"
                    elif key.lower() == "right":
                        key = "Right"
                    elif key.lower() == "space":
                        key = "space"
                    elif key.lower() == "control":
                        key = "Control"
                    elif key.lower() == "shift":
                        key = "Shift"
                    elif key.lower() == "alt":
                        key = "Alt"
                    elif key.lower() == "escape":
                        key = "Escape"
                    elif len(key) == 2:
                        key = key.upper() # e.g. F1, F2
                    elif len(key) == 1:
                        key = key.lower() # e.g. w, a, s, d
                    else:
                        key = key.title() # try to title-case the other keys (e.g. Escape)
                    if keydef not in keymap.keys():
                        print(f"Warning: invalid key definition: key '{key}' is mapped to an unknown action '{keydef}'")
                    elif key in mapped:
                        print(f"Warning: attempted a duplicate assignment of key '{key}' to action '{keydef}', already mapped.")
                    elif keydef == "snap" and key.lower() not in ("control", "alt"):
                        print(f"Warning: key assignment for the action 'snap' only permits Control or Alt. Defaulting to Control.")
                    else:
                        keymap[keydef] = key
                        mapped.extend([key])
        return keymap


class CaveStatsHelper():
    def get_c64_permeability(x, y, cave, permeability, return_all = False):
        if not 0 <= permeability <= 8:
            return True
        
        seeds = [0x00, 0x1E]
        slime_permeability_patterns = [0b00000000, 0b00010000, 0b00011000, 
                                       0b00111000, 0b00111100, 0b01111100,
                                       0b01111110, 0b11111110, 0b11111111]

        num_passes = 949        # 949 passes total
        detected_slimes = []
        for scan_y in range(cave.height):
            for scan_x in range(cave.width):
                if cave.map[scan_y * cave.width + scan_x][0].id == objects.SLIME.id:
                    detected_slimes.append( (scan_x, scan_y) )
        
        detected_permeability = {}
        permeability_pattern = slime_permeability_patterns[permeability]
        for p in range(num_passes):
            for slime in detected_slimes:
                # generate a new random number for the slime
                C64Cave.bdrandom(seeds)
                rand_value = seeds[0]
                # test permeability and output if permeable
                if (slime in detected_permeability.keys()):
                    detected_permeability[slime] |= (rand_value & permeability_pattern) == 0
                else:
                    detected_permeability[slime] = (rand_value & permeability_pattern) == 0
        
        if (return_all):
            return detected_permeability
        return detected_permeability[ (x, y) ]
    
    def show_cave_stats(cave, c64_permeability, float_permeability):
        detected_diamonds = 0
        detected_slimes = 0
        detected_amoeba = 0
        detected_fireflies = 0
        detected_butterflies = 0
        detected_boulders = 0
        detected_lightboulders = 0
        detected_heavyboulders = 0
        impermeable_slimes = 0
        
        permeability_data = CaveStatsHelper.get_c64_permeability(-1, -1, cave, c64_permeability, True)

        for scan_y in range(cave.height):
            for scan_x in range(cave.width):
                object = cave.map[scan_y * cave.width + scan_x][0]
                if object.id == objects.SLIME.id:
                    detected_slimes += 1
                    if 0 <= c64_permeability <= 8:
                        permeability_check = permeability_data[(scan_x, scan_y)]
                    else:
                        permeability_check = float_permeability > 0
                    if not permeability_check:
                        impermeable_slimes += 1
                elif object.id == objects.DIAMOND.id:
                    detected_diamonds += 1
                elif object.id == objects.AMOEBA.id:
                    detected_amoeba += 1
                elif object.id == objects.FIREFLY.id or object.id == objects.ALTFIREFLY.id:
                    detected_fireflies += 1
                elif object.id == objects.BUTTERFLY.id or object.id == objects.ALTBUTTERFLY.id:
                    detected_butterflies += 1
                elif object.id == objects.BOULDER.id:
                    detected_boulders += 1
                elif object.id == objects.MEGABOULDER.id:
                    detected_heavyboulders += 1
                elif object.id == objects.LIGHTBOULDER.id:
                    detected_lightboulders += 1

        cave_stats = f"Diamonds: {detected_diamonds}\n"
        cave_stats += f"Boulders: {detected_boulders}\n"
        cave_stats += f"Heavy Boulders: {detected_heavyboulders}\n"
        cave_stats += f"Light Boulders: {detected_lightboulders}\n"
        cave_stats += f"Fireflies: {detected_fireflies}\n"
        cave_stats += f"Butterflies: {detected_fireflies}\n"
        cave_stats += f"Amoeba: {detected_amoeba}\n"
        cave_stats += f"Total slime: {detected_slimes}\n"
        cave_stats += f"Impermeable slime: {impermeable_slimes}"
        tkinter.messagebox.showinfo("Cave statistics", cave_stats)


class TextHelper:
    def center_string(string, width):
        if string.find(" ") == -1 or len(string) < width:
            return string.center(width)
        midpoint = int(len(string) / 2)
        space_pos_L = string[0:midpoint].rfind(" ")
        space_pos_R = string[midpoint:].find(" ") + midpoint - 1
        dist_L = midpoint - space_pos_L
        dist_R = space_pos_R - midpoint
        space_pos = space_pos_L if dist_L < dist_R else space_pos_R
        string_L = string[0:space_pos+1].center(width)
        string_R = string[space_pos+1:].center(width)
        return f"{string_L}\n{string_R}"