#!/usr/bin/env python3

# This tool can be used to produce a hash map initialization file for KrisszConvert.
# It requires the presence of two sample screenshots, large.png and small.png, taken
# from Krissz Engine with default colors (#000000 #ffffff #646464 #a36e30). These
# samples must contain the exact set of objects in the first row (see the default
# examples). The large sample must be taken from the Construction kit using the
# Preview Cave Image option, the small sample must be taken from the cave preview
# in the cave list browser. The tool will produce the file "krisszengine.ini" that
# contains the "training" data for KrisszConvert to use to determine the color set
# and the tiles present on the input map images.

# License: GNU GPL 3.0, see LICENSE

import PIL, PIL.Image
import os

HASH_ORDER = [' ', '.', 'r', '%', '*', 'd', 'W', 'w', 'M', 'x', 'v', 'e', 'O', 'o',
              'Q', 'q', 'b', 'c', 'C', 'B', 'a', 's', 'F', 'P', 'X', 'H']

HASH_ORDER_SMALL = [' ', '.', 'r', '%', '*', 'd', 'W', 'w', 'w', 'w', 'w', 'w', 'Q', 'Q',
                    'Q', 'Q', 'c', 'c', 'c', 'c', 'a', 's', 'F', 'F', 'W', 'W']

OUTPUT_HASH_FILE = "krisszconvert.ini"

DEFAULT_COLORS = [
    (0x00, 0x00 ,0x00),
    (0xFF, 0xFF, 0xFF),
    (0x64, 0x64, 0x64),
    (0xA3, 0x6E, 0x30)
]

COLOR_PERMUTATIONS = [
    [DEFAULT_COLORS[0], DEFAULT_COLORS[1], DEFAULT_COLORS[2], DEFAULT_COLORS[3]], # 4 unique colors
    [DEFAULT_COLORS[0], DEFAULT_COLORS[1], DEFAULT_COLORS[2], DEFAULT_COLORS[0]], # 3 unique colors, 4 = 1
    [DEFAULT_COLORS[0], DEFAULT_COLORS[1], DEFAULT_COLORS[2], DEFAULT_COLORS[1]], # 3 unique colors, 4 = 2
    [DEFAULT_COLORS[0], DEFAULT_COLORS[1], DEFAULT_COLORS[2], DEFAULT_COLORS[2]], # 3 unique colors, 4 = 3
    [DEFAULT_COLORS[0], DEFAULT_COLORS[1], DEFAULT_COLORS[0], DEFAULT_COLORS[3]], # 3 unique colors, 3 = 1
    [DEFAULT_COLORS[0], DEFAULT_COLORS[1], DEFAULT_COLORS[1], DEFAULT_COLORS[3]], # 3 unique colors, 3 = 2
    [DEFAULT_COLORS[0], DEFAULT_COLORS[1], DEFAULT_COLORS[3], DEFAULT_COLORS[3]], # 3 unique colors, 3 = 4
    [DEFAULT_COLORS[0], DEFAULT_COLORS[0], DEFAULT_COLORS[2], DEFAULT_COLORS[3]], # 3 unique colors, 2 = 1
    [DEFAULT_COLORS[0], DEFAULT_COLORS[2], DEFAULT_COLORS[2], DEFAULT_COLORS[3]], # 3 unique colors, 2 = 3
    [DEFAULT_COLORS[0], DEFAULT_COLORS[3], DEFAULT_COLORS[2], DEFAULT_COLORS[3]], # 3 unique colors, 2 = 4
    [DEFAULT_COLORS[1], DEFAULT_COLORS[1], DEFAULT_COLORS[2], DEFAULT_COLORS[3]], # 3 unique colors, 1 = 2
    [DEFAULT_COLORS[2], DEFAULT_COLORS[1], DEFAULT_COLORS[2], DEFAULT_COLORS[3]], # 3 unique colors, 1 = 3
    [DEFAULT_COLORS[3], DEFAULT_COLORS[1], DEFAULT_COLORS[2], DEFAULT_COLORS[3]], # 3 unique colors, 1 = 4
]

def get_converted_color(color, permutation):
    if color[0] == DEFAULT_COLORS[0][0] and color[1] == DEFAULT_COLORS[0][1] and color[2] == DEFAULT_COLORS[0][2]:
        return permutation[0]
    if color[0] == DEFAULT_COLORS[1][0] and color[1] == DEFAULT_COLORS[1][1] and color[2] == DEFAULT_COLORS[1][2]:
        return permutation[1]
    if color[0] == DEFAULT_COLORS[2][0] and color[1] == DEFAULT_COLORS[2][1] and color[2] == DEFAULT_COLORS[2][2]:
        return permutation[2]
    if color[0] == DEFAULT_COLORS[3][0] and color[1] == DEFAULT_COLORS[3][1] and color[2] == DEFAULT_COLORS[3][2]:
        return permutation[3]
    else:
        print(f"Unexpected behavior: queried a converted color {color} for permutation {permutation}. Hashing will fail.")
        return (0x00, 0x00, 0x00)
    
def get_permutation_def(permutation):
    color1 = get_color_code(permutation[0][0], permutation[0][1], permutation[0][2])
    color2 = get_color_code(permutation[1][0], permutation[1][1], permutation[1][2])
    color3 = get_color_code(permutation[2][0], permutation[2][1], permutation[2][2])
    color4 = get_color_code(permutation[3][0], permutation[3][1], permutation[3][2])
    return f"{color1} {color2} {color3} {color4}"

def get_dimensions(image):
    return (int(image.size[0] / 32), int(image.size[1] / 32))
    
def get_color_code(r, g, b):
    return '#%02x%02x%02x' % (r, g, b)

def get_color_from_hexcode(hexcode):
    return ( (int(hexcode[1:3], base=16), int(hexcode[3:5], base=16), int(hexcode[5:7], base=16)) )
    
def get_block_hash(image, x, y, permutation):
    hash = 0
    for xloc in range(32):
        for yloc in range(32):
            color = PIL.Image.Image.getpixel(image, (x * 32 + xloc, y * 32 + yloc) )
            color = get_converted_color(color, permutation)
            hash += int((color[0] + 2 * color[1] + 4 * color[2]) / (yloc + 1) * xloc)
    return hash

def run():
    if not os.path.exists("large.png"):
        print("Source PNG file not found: large.png, hashing will fail.")
        exit(1)
    if not os.path.exists("small.png"):
        print("Source PNG file not found: small.png, hashing will fail.")
        exit(1)

    LARGE_HASH_SET = {}
    SMALL_HASH_SET = {}

    f = open(OUTPUT_HASH_FILE, "w")
    f.write("; This file contains training data for Krissz Engine cave image conversion.\n")
    f.write("; It is not meant for manual editing. Changing this file will likely make the conversion fail.\n\n")

    # Hash the "large.png" set
    print("Hashing 32x32 (large) sample - large.png")
    f.write("[large]\n")
    cave_image = PIL.Image.open("large.png").convert("RGB")
    cave_dim = get_dimensions(cave_image)
    cave_width = cave_dim[0]
    for colorset in COLOR_PERMUTATIONS:
        colorset_def = get_permutation_def(colorset)
        print(f"Hashing permutation: {colorset_def}")
        hash_id = 0
        hashed_for_this_set = {}
        for x in range(cave_width):
            block_hash = get_block_hash(cave_image, x, 0, colorset)
            block_char = HASH_ORDER[hash_id]
            if block_hash in LARGE_HASH_SET.keys():
                if LARGE_HASH_SET[block_hash] != block_char:
                    #print(f"-- Duplicate hash: {block_hash}. The set does not hash to a unique representation.")
                    continue
            hash_id += 1
            hashed_for_this_set[block_hash] = block_char
            if hash_id >= len(HASH_ORDER):
                break
        for hash in hashed_for_this_set.keys():
            LARGE_HASH_SET[hash] = hashed_for_this_set[hash]
    for hash in LARGE_HASH_SET.keys():
        f.write(f"{hash}={LARGE_HASH_SET[hash]}\n")
    f.write("\n")

    # Hash the "small.png" set
    print("Hashing 16x16 (small) sample - small.png")
    f.write("[small]\n")
    cave_image = PIL.Image.open("small.png").convert("RGB")
    cave_image = cave_image.resize((cave_image.width * 2, cave_image.height * 2), PIL.Image.NEAREST)
    cave_dim = get_dimensions(cave_image)
    cave_width = cave_dim[0]
    for colorset in COLOR_PERMUTATIONS:
        colorset_def = get_permutation_def(colorset)
        print(f"Hashing permutation: {colorset_def}")
        hash_id = 0
        hashed_for_this_set = {}
        for x in range(cave_width):
            block_hash = get_block_hash(cave_image, x, 0, colorset)
            block_char = HASH_ORDER_SMALL[hash_id]
            if block_hash in SMALL_HASH_SET.keys():
                if SMALL_HASH_SET[block_hash] != block_char:
                    #print(f"-- Duplicate hash: {block_hash}. The set does not hash to a unique representation.")
                    continue
            hash_id += 1
            hashed_for_this_set[block_hash] = block_char
            if hash_id >= len(HASH_ORDER_SMALL):
                break
        for hash in hashed_for_this_set.keys():
            SMALL_HASH_SET[hash] = hashed_for_this_set[hash]
    for hash in SMALL_HASH_SET.keys():
        f.write(f"{hash}={SMALL_HASH_SET[hash]}\n")
    f.close()

    print(f"Created a hash table containing {len(LARGE_HASH_SET) + len(SMALL_HASH_SET)} tile hashes.")

if __name__ == '__main__':
    run()
