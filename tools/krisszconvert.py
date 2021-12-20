#!/usr/bin/env python3

# KrisszConvert v1.4 by Michael Kamensky
# This tool converts a PNG image exported from Krissz Engine into a BDCFF representation
# playable in Krissz Engine compatible clones such as BoulderCaves+.

# License: GNU GPL 3.0, see LICENSE

import argparse
import datetime
import itertools
import os
import PIL, PIL.Image
import sys

VERSION = "1.4.0"
HASH_LOOKUP = {}
HASH_LOOKUP_SMALL = {}

GDASH_OBJNAMES = {
    ' ': "SPACE",
    '.': "DIRT",
    'w': "WALL",
    'M': "MAGICWALL",
    'X': "OUTBOX",
    'H': "HIDDENOUTBOX",
    'W': "STEELWALL",
    'r': "BOULDER",
    'd': "DIAMOND",
    'P': "INBOX",
    'x': "HEXPANDINGWALL",
    'v': "VEXPANDINGWALL",
    'e': "EXPANDINGWALL",
    'a': "AMOEBA",
    'F': "DUMMY",
    's': "SLIME",
    'Q': "FIREFLYl",
    'o': "FIREFLYu",
    'O': "FIREFLYr",
    'q': "FIREFLYd",
    'C': "BUTTERFLYl",
    'b': "BUTTERFLYu",
    'B': "BUTTERFLYr",
    'c': "BUTTERFLYd",
    '%': "MEGABOULDER",
    '*': "LIGHTBOULDER" # does not exist in stock GDash!
}

def_color1 = "#000000"
def_color2 = "#ffffff"
def_color3 = "#646464"
def_color4 = "#a36e30"

def get_dimensions(image):
    return (int(image.size[0] / 32), int(image.size[1] / 32))
    
def get_color_code(r, g, b):
    return '#%02x%02x%02x' % (r, g, b)

def get_color_from_hexcode(hexcode):
    return ( (int(hexcode[1:3], base=16), int(hexcode[3:5], base=16), int(hexcode[5:7], base=16)) )
    
def get_block_hash(image, x, y, color1, color2, color3, color4):
    hash = 0
    for xloc in range(32):
        for yloc in range(32):
            color = PIL.Image.Image.getpixel(image, (x * 32 + xloc, y * 32 + yloc) )
            color_code = get_color_code(color[0], color[1], color[2])
            if color_code == color1:
                color = get_color_from_hexcode(def_color1)                
            if color_code == color2:
                color = get_color_from_hexcode(def_color2)
            if color_code == color3:
                color = get_color_from_hexcode(def_color3)
            if color_code == color4:
                color = get_color_from_hexcode(def_color4)
            hash += int((color[0] + 2 * color[1] + 4 * color[2]) / (yloc + 1) * xloc)
    return hash
    
def iterate_color_permutations(color_set, image, cave_width, cave_height, small_map):
    HASH_TABLE = HASH_LOOKUP_SMALL if small_map else HASH_LOOKUP
    perms = itertools.permutations(color_set)
    error = False
    for color_set in perms:
        color1 = color_set[0]
        color2 = color_set[1]
        color3 = color_set[2]
        color4 = color_set[3]
        error = False
        print("Trying: " + color1 + " " + color2 + " " + color3 + " " + color4)
        for y in range(cave_height):
            if error:
                break
            for x in range(cave_width):
                block_hash = get_block_hash(image, x, y, color1, color2, color3, color4)
                block_char = HASH_TABLE.get(block_hash)
                if block_char is None:
                    error = True
                    break
                else:
                    pass
        if not error:
            break
    return None if error else (color1, color2, color3, color4)
    
def determine_colors_from_image_cavescan(image, small_map):
    cave_width = get_dimensions(image)[0]
    cave_height = get_dimensions(image)[1]
    colors_in_image = []
    for y in range(cave_height * 32):
        for x in range(cave_width * 32):
            pixel_color = PIL.Image.Image.getpixel(image, (x, y))
            color_code = get_color_code(pixel_color[0], pixel_color[1], pixel_color[2])
            if color_code not in colors_in_image:
                colors_in_image.append(color_code)
            if len(colors_in_image) > 4:
                print("Illegal number of colors in the picture, make sure you use a sharp PNG image with 100% quality and no more than 4 unique colors (best exported directly from Krissz Engine Construction Kit).")
                exit(4)
    if len(colors_in_image) == 4:
        attempt = iterate_color_permutations(colors_in_image, image, cave_width, cave_height, small_map)
        if attempt is None:
            print("Unable to determine colors from picture using forward cave scan.")
        return attempt
    elif len(colors_in_image) == 3:
        perm1 = colors_in_image + [colors_in_image[0]]
        perm2 = colors_in_image + [colors_in_image[1]]
        perm3 = colors_in_image + [colors_in_image[2]]
        attempt = iterate_color_permutations(perm1, image, cave_width, cave_height, small_map)
        if attempt is None:
            attempt = iterate_color_permutations(perm2, image, cave_width, cave_height, small_map)
        if attempt is None:
            attempt = iterate_color_permutations(perm3, image, cave_width, cave_height, small_map)
        if attempt is None:
            print("Unable to determine colors from picture using forward cave scan.")
        return attempt
    elif len(colors_in_image) == 2:
        print("Caves with only two unique colors do not hash to a unique object representation. Please consider changing colors temporarily in Construction Kit to 4 unique colors and exporting a map again, if possible.")
        return None
    return None

def determine_colors_from_image(image):
    image_width = get_dimensions(image)[0]
    image_height = get_dimensions(image)[1]
    for y in range(image_height):
        for x in range(image_width):
            block_y = y * 32
            block_x = x * 32
            def px_color(x, y):
                pixel_color = PIL.Image.Image.getpixel(image, (block_x + x, block_y + y) )
                return get_color_code(pixel_color[0], pixel_color[1], pixel_color[2])

            # Scenario 1: Boulder
            color1 = px_color(0, 0)
            color2 = px_color(8, 0)
            color3 = px_color(8, 2)
            color4 = px_color(4, 4)
            if color1 != color2 and color2 != color3 and color3 != color4 and color1 != color3 and color1 != color4 and color2 != color4:
                if (color1 == px_color(0, 3) == px_color(9, 18)):
                    if (color2 == px_color(9, 0) == px_color(4, 6) == px_color(24, 12) == px_color(29, 14)):
                        if (color3 == px_color(0, 7) == px_color(1, 8) == px_color(17, 23)):
                            if (color4 == px_color(4, 5) == px_color(8, 7) == px_color(9, 6)):
                                print("Attempted to determine correct colors from a Boulder image.")
                                return (color1, color2, color3, color4)
            # Scenario 2: Diamond
            color1 = px_color(8, 0)
            color2 = px_color(17, 1)
            color3 = px_color(9, 19)
            color4 = px_color(9, 7)
            if color1 != color2 and color2 != color3 and color3 != color4 and color1 != color3 and color1 != color4 and color2 != color4:
                if (color1 == px_color(9, 13) == px_color(25, 15) == px_color(11, 29)):
                    if (color2 == px_color(18, 7) == px_color(10, 21) == px_color(22, 25)):
                        if (color3 == px_color(25, 11) == px_color(17, 19) == px_color(18, 29)):
                            if (color4 == px_color(14, 11) == px_color(26, 17) == px_color(19, 31)):
                                print("Attempted to determine correct colors from a Diamond image.")
                                return (color1, color2, color3, color4)
    print("Unable to determine colors from picture using selective color-matching.")
    return None
            
def process_border_heuristics(cave_def):
    # Determines if the horizontal and the vertical border are likely to be open, returns a tuple
    # of booleans (horizontal_border_open, vertical_border_open).
    open_horizontal_border = False
    open_vertical_border = False
    passable_objects = [' ', '.']
    cave_rows = cave_def.split('\n')
    x = y = 0
    cave_width = cave_height = 0
    # Create a scannable representation of the cave
    cave_scannable = ""
    for row in cave_rows:
        if len(row) < 2:
            continue
        for obj in row:
            if obj != "\n":
                cave_scannable += obj
            x += 1
        if cave_width == 0:
            cave_width = x
        y += 1
    cave_height = y
    # Determine the first impassable object X and Y
    imp_x = cave_width
    imp_y = cave_height
    for y in range(cave_height):
        for x in range(cave_width):
            idx = y * cave_width + x
            if cave_scannable[idx] not in passable_objects:
                if x < imp_x:
                    imp_x = x
                if y < imp_y:
                    imp_y = y
                break
        if imp_x != -1 and imp_y != -1:
            break
    # Determine the last impassable object X and Y
    imp_last_x = imp_last_y = -1
    for y in range(cave_height - 1, -1, -1):
        for x in range(cave_width - 1, -1, -1):
            idx = y * cave_width + x
            if cave_scannable[idx] not in passable_objects:
                if x > imp_last_x:
                    imp_last_x = x
                if y > imp_last_y:
                    imp_last_y = y
                break
        if imp_last_x != -1 and imp_last_y != -1:
            break
    # Scan the border rows and columns to see if they're passable at
    # the same endpoints.
    endpoint1 = endpoint2 = False
    for x in range(cave_width):
        # open vertical border
        idx = imp_y * cave_width + x
        idx2 = imp_last_y * cave_width + x
        if cave_scannable[idx] in passable_objects:
            endpoint1 = True
            endpoint1_x = x
            endpoint1_y = imp_y
        if cave_scannable[idx2] in passable_objects:
            endpoint2 = True
            endpoint2_x = x
            endpoint2_y = imp_last_y
    if endpoint1 and endpoint2:
        print(f"Detected possible open vertical border through coords {endpoint1_x}, {endpoint1_y} and {endpoint2_x}, {endpoint2_y}")
        open_vertical_border = True    
    endpoint1 = endpoint2 = False
    for y in range(cave_height):
        # open horizontal border
        idx = y * cave_width + imp_x
        idx2 = y * cave_width + imp_last_x
        if cave_scannable[idx] in passable_objects:
            endpoint1 = True
            endpoint1_x = imp_x
            endpoint1_y = y
        if cave_scannable[idx2] in passable_objects:
            endpoint2 = True
            endpoint2_x = imp_last_x
            endpoint2_y = y
    if endpoint1 and endpoint2:
        print(f"Detected possible open horizontal border through coords {endpoint1_x}, {endpoint1_y} and {endpoint2_x}, {endpoint2_y}")
        open_horizontal_border = True
    return (open_horizontal_border, open_vertical_border)
    
def write_output_txt(filename, cave_def, gdash_objects_def, width, height, color1, color2, color3, color4, gdash_mode, openhorz, openvert, author):
    dt = datetime.datetime.today().strftime("%Y-%m-%d")
    str_openhorz = "false" if not openhorz else "true"
    str_openvert = "false" if not openvert else "true"
    name = filename.split('.')[0] if filename.find('/') == -1 and filename.find('\\') == -1 else \
        filename[filename.rfind('/') + 1:].split('.')[0] if filename.find('/') != -1 else \
            filename[filename.rfind('\\') + 1:].split('.')[0]
    with open(filename, "w") as f:
        f.write("; converted using KrisszConvert by Michael Kamensky\n")
        f.write(f"; colors used: {color1} {color2} {color3} {color4}\n")
        f.write("\n")
        f.write("[BDCFF]\n")
        f.write("[game]\n")
        f.write(f"Name={name}\n")
        f.write("Description=A converted Krissz Engine cave\n")
        f.write(f"Author={author}\n")
        f.write("WWW=\n")
        f.write(f"Date={dt}\n")
        f.write("Charset=Original\n")
        f.write("Fontset=Original\n")
        f.write("Levels=1\n")
        f.write("Caves=1\n")
        f.write("\n")
        f.write("[cave]\n")
        f.write(f"Name={name}\n")        
        f.write("Intermission=false\n")        
        if gdash_mode:
            f.write("FrameTime=150\n")  # UNUSED in BoulderCaves+, use TargetFps instead
            f.write("CaveDelay=8\n")    # UNUSED in BoulderCaves+, use TargetFps instead
        f.write("CaveTime=150\n")
        f.write("TimeValue=1\n") # BDCFF standard equivalent to ValueOfASecond
        f.write("DiamondsRequired=5\n")        
        f.write("DiamondValue=10 20\n")
        f.write("AmoebaTime=60\n")
        if gdash_mode:
            f.write("AmoebaThreshold=0.227300\n") # UNUSED in Krissz Engine compatible caves, AmoebaLimit is used
        f.write("AmoebaProperties.waitforhatching=false\n") # BDCFF standard inverse equivalent to AmoebaGrowsBeforeSpawn
        f.write("MagicWallTime=20\n")
        f.write(f"MagicWallProperties.breakscan=true\n") # BDCFF standard equivalent for MagicWallStopsAmoeba
        if gdash_mode:
            f.write(f"SlimePermeabilityC64=126\n") # equivalent to Krissz Engine permeability setting of 6
            f.write(f"BorderProperties.wraparound={str_openvert}\n") # GDash treats wraparound as open vertical border
        else:
            f.write("BorderProperties.wraparound=false\n")
        f.write("BorderProperties.lineshift=false\n")
        f.write(f"Size={width} {height}\n")
        if not gdash_mode:
            f.write("; Krissz Engine cave properties for BoulderCaves+\n")
            f.write("TargetFps=7.5\n")
            f.write("MagicWallStopsAmoeba=true\n")
            f.write("RockfordBirthTime=20\n")
            f.write("AmoebaLimit=200\n")
            f.write("AmoebaGrowsBeforeSpawn=true\n")
            f.write("NoTimeLimit=false\n")
            f.write("ReverseTime=false\n")        
            f.write(f"OpenHorizontalBorders={str_openhorz}\n")
            f.write(f"OpenVerticalBorders={str_openvert}\n")
            f.write("ValueOfASecond=1\n")
            f.write("SingleLife=true\n")
            f.write("KrisszSlimePermeability=6\n")
        f.write(f"Colors=#000000 {color1} {color4} {color3} {color2} {color2} {color2}\n")        
        f.write("\n")
        f.write("[map]")
        f.write(cave_def)
        f.write("\n[/map]\n")
        if gdash_mode:
            f.write("\n[objects]\n")
            f.write(gdash_objects_def)
            f.write("[/objects]\n")
        f.write("[/cave]\n")
        f.write("\n")
        f.write("[/game]\n")
        f.write("[/BDCFF]\n")

def load_hash_data():
    load_small = False
    if not os.path.exists("krisszconvert.ini"):
        print("Error: unable to find krisszconvert.ini, conversion won't work. Exiting.")
        exit(3)
    with open("krisszconvert.ini", "r") as init:
        data = init.readlines()
        for initline in data:
            if initline.strip().lower() == "[large]":
                load_small = False
            elif initline.strip().lower() == "[small]":
                load_small = True
            elif initline.find("=") != -1:
                hashinfo = initline.replace("\n", "").split("=")
                hash = int(hashinfo[0])
                objchar = hashinfo[1]
                if load_small:
                    HASH_LOOKUP_SMALL[hash] = objchar
                else:
                    HASH_LOOKUP[hash] = objchar
    
def convert(src_file, dest_file, args):
    if not os.path.exists(src_file):    
        print(f"Error: file {src_file} does not exist, please check if you specified the input file correctly.")
        exit(1)

    small_map = args.smallmap
    gdash_mode = args.gdash
    border_heuristics = args.openborder
    author = args.author

    if small_map:
        print("Small map (16 x 16 tiles) mode selected, will pre-resize the map before converting.")
    if gdash_mode:
        print("GDash mode selected, will not use any substandard features that GDash doesn't support, Light Boulder issues a warning.")
        
    load_hash_data() # Load the hash map which shows the correspondence of tile hashes to BDCFF characters

    cave_image = PIL.Image.open(src_file).convert("RGB")

    if small_map:
        cave_image = cave_image.resize((cave_image.width * 2, cave_image.height * 2), PIL.Image.NEAREST)

    cave_dim = get_dimensions(cave_image)
    cave_width = cave_dim[0]
    cave_height = cave_dim[1]
    
    print(f"Cave dimensions: {cave_width} x {cave_height}")

    HASH_TABLE = HASH_LOOKUP_SMALL if small_map else HASH_LOOKUP
    
    color1 = f"#{args.color1}".lower() if args.color1 is not None else def_color1
    color2 = f"#{args.color2}".lower() if args.color2 is not None else def_color2
    color3 = f"#{args.color3}".lower() if args.color3 is not None else def_color3
    color4 = f"#{args.color4}".lower() if args.color4 is not None else def_color4
        
    if args.color1 is not None:
        print(f"Assumed cave colors (left to right): {color1} {color2} {color3} {color4}")
    else:
        print(f"Default colors (left to right): {color1} {color2} {color3} {color4}")

    if args.color1 is None:
        print(f"Will attempt to deduce actual colors from image.")
        det_colors = determine_colors_from_image_cavescan(cave_image, small_map)
        if det_colors is None:
            det_colors = determine_colors_from_image(cave_image)
        if det_colors is not None:
            print("Successfully determined colors from image: " + det_colors[0] + " " + det_colors[1] + " " + det_colors[2] + " " + det_colors[3])
            color1 = det_colors[0]
            color2 = det_colors[1]
            color3 = det_colors[2]
            color4 = det_colors[3]

        if det_colors is None and not small_map:
            print("Could not determine the colors, let's see if maybe this is a small map.")
            cave_image = cave_image.resize((cave_image.width * 2, cave_image.height * 2), PIL.Image.NEAREST)
            HASH_TABLE = HASH_LOOKUP_SMALL
            small_map = True
            cave_dim = get_dimensions(cave_image)
            cave_width = cave_dim[0]
            cave_height = cave_dim[1]
            print(f"Restarting forward cave scan with new dimensions: {cave_width} x {cave_height}")
            det_colors = determine_colors_from_image_cavescan(cave_image, small_map)
            if det_colors is not None:
                print("Successfully determined colors from image: " + det_colors[0] + " " + det_colors[1] + " " + det_colors[2] + " " + det_colors[3])
                color1 = det_colors[0]
                color2 = det_colors[1]
                color3 = det_colors[2]
                color4 = det_colors[3]
            else:
                print("Still couldn't determine the color scheme, giving up because the process will fail.")
                print(f"Conversion failed: {src_file}")
                exit(2)
    
    print("Looking for an Inbox...")
    rockford_found = False
    for y in range(cave_height):
        for x in range(cave_width):
            block_hash = get_block_hash(cave_image, x, y, color1, color2, color3, color4)
            block_char = HASH_TABLE.get(block_hash)
            if block_char == 'P':
                rockford_found = True
                print("Inbox found, all good.")
                break
    if not rockford_found:
        print("Inbox NOT found, the first Rockford object encountered will be treated as an Inbox, the rest will be Voodoo Rockfords - please double check the map after conversion!")

    gdash_cave_def = ""
    bcp_cave_def = ""
    warning = False
    open_borders = (False, False)
    for y in range(cave_height):
        bcp_cave_def += "\n"
        for x in range(cave_width):
            block_hash = get_block_hash(cave_image, x, y, color1, color2, color3, color4)
            block_char = HASH_TABLE.get(block_hash)
            if block_char is not None:
                if block_char == 'F' and not rockford_found:
                    block_char = 'P'
                    rockford_found = True
                if block_char == '*' and gdash_mode:
                    print(f"Warning: Light Boulder found at x={x}, y={y}. GDash doesn't currently support this object.")
                    warning = True
                bcp_cave_def += block_char
                if gdash_mode and block_char == '%': # only store Megaboulders (Heavy Boulders) this way for GDash
                    gdash_cave_def += f"Point={x} {y} {GDASH_OBJNAMES[block_char]}\n"
            else:
                print(f"Error: unidentified block at x={x}, y={y}, hash={block_hash}. Check if the colors are defaulted or correctly specified.")
                print(f"Conversion failed: {src_file}")
                exit(2)
    
    if border_heuristics:
        print("Border heuristics: attempting to detect open horizontal and vertical borders...")
        open_borders = process_border_heuristics(bcp_cave_def)

    write_output_txt(dest_file, bcp_cave_def, gdash_cave_def, cave_width, cave_height, \
        color1, color2, color3, color4, gdash_mode, open_borders[0], open_borders[1], author)

    if warning:
        print(f"Conversion successful (with warnings): {src_file}\n")
    else:
        print(f"Conversion successful: {src_file}\n")
    
def run():
    ap = argparse.ArgumentParser(description=f"KrisszConvert {VERSION} - a cave converter for PNG cave snapshots and preview images exported from Krissz Engine",
                                 epilog="This software is licensed under the GNU GPL 3.0, see https://www.gnu.org/licenses/gpl.html")
    ap.add_argument("-s", "--smallmap", help="convert small 16x16 tile images (cave snapshots)", action="store_true")
    ap.add_argument("-g", "--gdash", help="produce a GDash-compatible output BDCFF file (will warn about Light Boulders which do not exist in standard GDash)", action="store_true")
    ap.add_argument("-o", "--openborder", help="use heuristics to detect potentially open borders and set the relevant cave properties", action="store_true")
    ap.add_argument("-b", "--batch", help="batch convert all the files in the specified source folder and save them into the specified target folder", action="store_true")
    ap.add_argument("-a", "--author", type=str, help="specify the name of the author in the output BDCFF file", default="Unspecified Author")
    ap.add_argument("input_file", help="input cave image file (.png), or source folder when in batch mode")
    ap.add_argument("output_file", help="output BDCFF file (.bd), or target folder when in batch mode")
    ap.add_argument("color1", nargs="?", help="first color in the Krissz Engine palette")
    ap.add_argument("color2", nargs="?", help="second color in the Krissz Engine palette")
    ap.add_argument("color3", nargs="?", help="third color in the Krissz Engine palette")
    ap.add_argument("color4", nargs="?", help="fourth color in the Krissz Engine palette")
    args = ap.parse_args(sys.argv[1:])

    batch_mode = args.batch

    if not batch_mode:
        src_file = args.input_file
        dest_file = args.output_file
        convert(src_file, dest_file, args)
    else: # batch mode
        src_folder = args.input_file
        dest_folder = args.output_file
        for filename in os.listdir(src_folder):
            if filename.endswith(".png"):
                src_file = os.path.join(src_folder, filename)
                dest_file = os.path.join(dest_folder, filename[0:filename.rfind(".")] + ".bd")
                print(f"Converting {src_file} to {dest_file}...")
                convert(src_file, dest_file, args)
        print("Batch conversion complete.")

if __name__ == '__main__':
    run()