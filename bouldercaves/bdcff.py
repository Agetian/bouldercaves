"""
Boulder Caves+ - a Boulder Dash (tm) clone.
Krissz Engine-compatible remake based on Boulder Caves 5.7.2.

Parser for 'Boulder Dash Common File Format' BDCFF cave files.
Implementation info:
https://www.boulder-dash.nl/
http://www.emeraldmines.net/BDCFF/    (offline now, unfortunately)
http://www.gratissaugen.de/erbsen/bdcff.html
http://www.gratissaugen.de/erbsen/BD-Inside-FAQ.html

Written by Irmen de Jong (irmen@razorvine.net)
Extended version by Michael Kamensky

License: GNU GPL 3.0, see LICENSE
"""

import sys
import datetime
from typing import Dict, List, Any, TextIO, Optional, Union


def get_system_username():
    import getpass
    username = getpass.getuser()
    try:
        import pwd
        fullname = (pwd.getpwnam(username).pw_gecos or "").split(',')[0]
        return fullname or username
    except ImportError:
        return username


class BdcffFormatError(Exception):
    pass


class BdcffCave:
    class Map:
        def __init__(self):
            self.maplines = []
            self.width = self.height = 0

        def postprocess(self):
            self.height = len(self.maplines)
            self.width = len(self.maplines[0])

    def __init__(self):
        # create a cave with the defaults from the Bdcff specification
        self.properties = {}
        self.map = self.Map()
        self.objects = []
        self.intermission = False
        self.cavetime = 200
        self.slimepermeability = 1.0
        self.amoebafactor = 0.2273
        self.amoebatime = 999
        self.magicwalltime = 999
        self.diamonds_required = 10
        self.diamondvalue_normal = self.diamondvalue_extra = 0
        self.width = self.map.width
        self.height = self.map.height
        self.wraparound = False
        self.color_screen, self.color_border, self.color_fg1, self.color_fg2, self.color_fg3, \
            self.color_amoeba, self.color_slime = [0, 0, 10, 12, 1, 5, 6]
        # substandard properties for extra features
        self.target_fps = 7
        self.lineshift = True
        self.magic_wall_stops_amoeba = False
        self.rockford_birth_time = -1
        self.amoeba_limit = -1
        self.amoeba_grows_before_spawn = False
        self.no_time_limit = False
        self.reverse_time = False
        self.open_horizontal_borders = False
        self.open_vertical_borders = False
        self.value_of_a_second = 1
        self.single_life = False
        self.krissz_slime_permeability = -1

    def postprocess(self):
        self.name = self.properties.pop("name")
        self.description = self.properties.pop("description", "")
        if not self.description:
            self.description = self.properties.pop("remark", "")
        self.cavetime = int(self.properties.pop("cavetime").split()[0])
        self.diamonds_required = int(self.properties.pop("diamondsrequired").split()[0])
        dvalue = self.properties.pop("diamondvalue")
        try:
            dv, dve = dvalue.split()
        except ValueError:
            dv = dve = dvalue
        self.diamondvalue_normal = int(dv)
        self.diamondvalue_extra = int(dve)
        self.amoebatime = int(self.properties.pop("amoebatime", str(self.amoebatime)).split()[0])
        self.amoebafactor = float(self.properties.pop("amoebathreshold", str(self.amoebafactor)))
        self.magicwalltime = int(self.properties.pop("magicwalltime", str(self.magicwalltime)).split()[0])
        self.slimepermeability = float(self.properties.pop("slimepermeability", str(self.slimepermeability)))
        slimep64 = int(self.properties.pop("slimepermeabilityc64", "-1").split()[0])
        if slimep64 >= 0:
            # SlimePermeabilityC64 see http://www.boulder-dash.nl/forum/viewtopic.php?p=2583#2583
            # we sort of simulate the behavior here by setting the factor depending on the number of bits.
            self.slimepermeability = bin(slimep64).count('1') / 8.0
        colors = []
        for c in self.properties.pop("colors").split():
            try:
                color = BdcffParser.COLORNAMES.index(c)
                colors.append(color)
            except (ValueError, LookupError) as x:
                if c.startswith('#'):
                    colors.append(c)
                else:
                    raise BdcffFormatError("color format unsupported: " + str(x))
        self.color_border = 0
        self.color_screen = 0
        self.color_amoeba = 5
        self.color_slime = 6
        if len(colors) == 3:
            self.color_fg1, self.color_fg2, self.color_fg3 = colors
        elif len(colors) == 5:
            self.color_border, self.color_screen, self.color_fg1, self.color_fg2, self.color_fg3 = colors
        elif len(colors) == 7:
            self.color_border, self.color_screen, self.color_fg1, self.color_fg2, self.color_fg3, \
                self.color_amoeba, self.color_slime = colors
        else:
            raise BdcffFormatError("invalid color spec: " + str(colors))
        self.intermission = self.properties.pop("intermission", "false") == "true"
        self.wraparound = self.properties.pop("borderproperties.wraparound", "false") == "true"
        self.lineshift = self.properties.pop("borderproperties.lineshift", "true") == "true"
        self.map.postprocess()
        self.height = self.map.height
        self.width = self.map.width
        psize = self.properties.pop("size", None)
        if psize:
            pwidth, pheight = psize.split()[:2]
            pwidth = int(pwidth)
            pheight = int(pheight)
            if pwidth != self.width or pheight != self.height:
                raise BdcffFormatError("cave width or height doesn't match map, in cave " + self.name)
        self.properties.pop("cavedelay", 0)
        self.properties.pop("frametime", 0)
        # substandard properties for this extended version
        self.target_fps = self.properties.pop("targetfps", 7)
        self.magic_wall_stops_amoeba = self.properties.pop("magicwallstopsamoeba", "false") == "true"
        if not self.magic_wall_stops_amoeba:
            self.magic_wall_stops_amoeba = self.properties.pop("magicwallproperties.breakscan", "false") == "true" # BDCFF standard alias
        else:
            self.properties.pop("magicwallproperties.breakscan", "false") # Krissz Engine variant takes priority
        self.amoeba_grows_before_spawn = self.properties.pop("amoebagrowsbeforespawn", "false") == "true"
        if not self.amoeba_grows_before_spawn:
            self.amoeba_grows_before_spawn = self.properties.pop("amoebaproperties.waitforhatching", "true") == "false" # BDCFF standard inverted alias
        else:
            self.properties.pop("amoebaproperties.waitforhatching", "true") # Krissz Engine variant takes priority
        self.krissz_slime_permeability = int(self.properties.pop("krisszslimepermeability", "-1"))
        self.rockford_birth_time = int(self.properties.pop("rockfordbirthtime", "-1"))
        self.amoeba_limit = int(self.properties.pop("amoebalimit", "-1"))
        self.no_time_limit = self.properties.pop("notimelimit", "false") == "true"
        self.reverse_time = self.properties.pop("reversetime", "false") == "true"
        self.open_horizontal_borders = self.properties.pop("openhorizontalborders", "false") == "true"
        self.open_vertical_borders = self.properties.pop("openverticalborders", "false") == "true"
        self.value_of_a_second = int(self.properties.pop("valueofasecond", "1"))
        if self.value_of_a_second == 1:
            self.value_of_a_second = int(self.properties.pop("timevalue", "1")) # BDCFF standard alias
        else:
            self.properties.pop("timevalue", "1") # Krissz Engine variant takes priority
        self.single_life = self.properties.pop("singlelife", "false") == "true"
        if self.properties:
            print("\nWARNING: unrecognised cave properties in cave " + self.name + " :")
            print(self.properties, "\n")
        del self.properties

    def validate(self):
        if self.objects:
            print(self.objects)
            raise BdcffFormatError("cave uses [objects] to create the map, we only support [map] right now")
        if self.width < 2 or self.width > 100 or self.height < 2 or self.height > 100:
            raise BdcffFormatError("invalid width and/or height (2-100)")
        if self.slimepermeability < 0 or self.slimepermeability > 1:
            raise BdcffFormatError("invalid SlimePermeability")
        if self.amoebafactor < 0 or self. amoebafactor > 1:
            raise BdcffFormatError("invalid AmoebaFactor")
        if self.cavetime <= 1 or self.cavetime > 999 or \
                self.magicwalltime < 0 or self.magicwalltime > 999 or\
                self.amoebatime < 0 or self.amoebatime > 999:
            raise BdcffFormatError("invalid time property")
        if self.diamondvalue_normal < 0 or self.diamondvalue_normal > 999 or self.diamondvalue_extra < 0 or self.diamondvalue_extra > 999:
            raise BdcffFormatError("invalid diamond value")
        if self.diamonds_required < -999 or self.diamonds_required > 999:
            raise BdcffFormatError("invalid DiamondsRequired")

    def write(self, out: TextIO) -> None:
        out.write("[cave]\n")
        out.write("Name={:s}\n".format(self.name))
        out.write("Description={:s}\n".format(self.description))
        out.write("Intermission={:s}\n".format("true" if self.intermission else "false"))
        out.write("FrameTime=150\n")
        out.write("CaveDelay={:d}\n".format(3 if self.intermission else 8))
        out.write("CaveTime={:d}\n".format(self.cavetime))
        out.write("TimeValue={:d}\n".format(self.value_of_a_second))
        out.write("DiamondsRequired={:d}\n".format(self.diamonds_required))
        out.write("DiamondValue={:d} {:d}\n".format(self.diamondvalue_normal, self.diamondvalue_extra))
        out.write("AmoebaTime={:d}\n".format(self.amoebatime))
        out.write("AmoebaThreshold={:f}\n".format(self.amoebafactor))
        out.write("AmoebaProperties.waitforhatching={:s}\n".format("true" if not self.amoeba_grows_before_spawn else "false"))
        out.write("MagicWallTime={:d}\n".format(self.magicwalltime))
        out.write("MagicWallProperties.breakscan={:s}\n".format("true" if self.magic_wall_stops_amoeba else "false"))
        out.write("SlimePermeability={:.3f}\n".format(self.slimepermeability))
        out.write("BorderProperties.wraparound={:s}\n".format("true" if self.wraparound else "false"))
        out.write("BorderProperties.lineshift={:s}\n".format("true" if self.lineshift else "false"))
        out.write("Size={:d} {:d}\n".format(self.width, self.height))
        # substandard properties for the extended version of Boulder Caves, matching Krissz Engine cave properties
        out.write("; Krissz Engine cave properties\n")
        out.write("TargetFps={:.1f}\n".format(self.target_fps))
        out.write("MagicWallStopsAmoeba={:s}\n".format("true" if self.magic_wall_stops_amoeba else "false"))
        out.write("RockfordBirthTime={:d}\n".format(self.rockford_birth_time))
        out.write("AmoebaLimit={:d}\n".format(self.amoeba_limit))
        out.write("AmoebaGrowsBeforeSpawn={:s}\n".format("true" if self.amoeba_grows_before_spawn else "false"))
        out.write("NoTimeLimit={:s}\n".format("true" if self.no_time_limit else "false"))
        out.write("ReverseTime={:s}\n".format("true" if self.reverse_time else "false"))
        out.write("OpenHorizontalBorders={:s}\n".format("true" if self.open_horizontal_borders else "false"))
        out.write("OpenVerticalBorders={:s}\n".format("true" if self.open_vertical_borders else "false"))
        out.write("ValueOfASecond={:d}\n".format(self.value_of_a_second))
        out.write("SingleLife={:s}\n".format("true" if self.single_life else "false"))
        out.write("KrisszSlimePermeability={:d}\n".format(self.krissz_slime_permeability))

        def outputcolor(color: Union[int, str]) -> str:
            if isinstance(color, str):
                return color
            return BdcffParser.COLORNAMES[color]

        out.write("Colors={:s} {:s} {:s} {:s} {:s} {:s} {:s}\n".format(
            outputcolor(self.color_border),
            outputcolor(self.color_screen),
            outputcolor(self.color_fg1),
            outputcolor(self.color_fg2),
            outputcolor(self.color_fg3),
            outputcolor(self.color_amoeba),
            outputcolor(self.color_slime)))
        out.write("\n[map]\n")
        if len(self.map.maplines) != self.height:
            raise BdcffFormatError("cave height differs from map")
        if len(self.map.maplines) == 0:
            raise BdcffFormatError("no map lines")
        for line in self.map.maplines:
            if len(line) != self.width:
                raise BdcffFormatError("cave width differs from map")
            out.write(line + "\n")
        out.write("[/map]\n")
        out.write("[/cave]\n")


class BdcffParser:
    SECT_BDCFF = 1
    SECT_GAME = 2
    SECT_CAVE = 3
    SECT_MAP = 4
    SECT_HIGHSCOREG = 5
    SECT_HIGHSCORE = 6
    SECT_OBJECTS = 7
    SECT_REPLAY = 8
    COLORNAMES = ["Black", "White", "Red", "Cyan", "Purple", "Green", "Blue", "Yellow",
                  "Orange", "Brown", "LightRed", "Gray1", "Gray2", "LightGreen", "LightBlue", "Gray3"]

    def __init__(self, filename: Optional[str]=None) -> None:
        self.state = 0
        self.bdcff_version = ""
        self.game_properties = {}   # type: Dict[str, Any]
        self.caves = []     # type: List[BdcffCave]
        self.current_cave = None    # type: Optional[BdcffCave]
        self.num_levels = 1
        self.num_caves = 0
        self.charset = self.fontset = "Original"
        self.author = get_system_username()
        self.www = ""
        self.date = str(datetime.datetime.now().date())
        self.name = "Unnamed"
        self.description = ""
        if filename:
            with open(filename, "r") as f:
                for line in f:
                    line = line.rstrip('\n')
                    if line and not line.startswith(';'):
                        self.parse(line)
            self.postprocess()
            self.validate()

    def write(self, out: TextIO) -> None:
        if self.num_levels != 1:
            raise BdcffFormatError("only supports files with 1 difficulty level")
        if self.num_caves != len(self.caves):
            raise BdcffFormatError("number of caves differs from game property")
        out.write("; written by Bouldercaves.Bdcff by Irmen de Jong\n")
        out.write("; last modified {:s}\n".format(str(datetime.datetime.now().date())))
        out.write("\n[BDCFF]\n[game]\n")
        out.write("Name={:s}\n".format(self.name))
        if self.description:
            out.write("Description={:s}\n".format(self.name))
        out.write("Author={:s}\n".format(self.author))
        out.write("WWW={:s}\n".format(self.www))
        out.write("Date={:s}\n".format(self.date))
        out.write("Charset={:s}\n".format(self.charset))
        out.write("Fontset={:s}\n".format(self.fontset))
        out.write("Levels={:d}\n".format(self.num_levels))
        out.write("Caves={:d}\n".format(self.num_caves))
        out.write("BonusLife={:d}\n".format(self.bonus_life_points))
        out.write("\n")
        for cave in self.caves:
            cave.write(out)
            out.write("")
        out.write("\n[/game]\n[/BDCFF]\n")

    def postprocess(self) -> None:
        self.num_levels = int(self.game_properties.pop("levels", 1))
        self.num_caves = int(self.game_properties.pop("caves", 0))
        self.name = self.game_properties.pop("name")
        self.description = self.game_properties.pop("description", "")
        if not self.description:
            self.description = self.game_properties.pop("remark", "")
        self.author = self.game_properties.pop("author", "<unknown>")
        self.www = self.game_properties.pop("www", "")
        self.date = self.game_properties.pop("date", "")
        self.charset = self.game_properties.pop("charset", "Original")
        self.fontset = self.game_properties.pop("fontset", "Original")
        self.bonus_life_points = int(self.game_properties.pop("bonuslife", 500))
        if self.game_properties:
            print("\nWARNING: unrecognised bdcff properties:")
            print(self.game_properties, "\n")
        del self.game_properties
        for cave in self.caves:
            cave.postprocess()
            cave.validate()
        self.num_caves = self.num_caves or len(self.caves)
        del self.current_cave
        del self.state

    def validate(self) -> None:
        if self.charset != "Original" or self.fontset != "Original":
            raise BdcffFormatError("invalid or unsupported cave data")
        if self.num_caves <= 0 or self.num_caves != len(self.caves):
            raise BdcffFormatError("invalid number of caves")
        if self.num_levels != 1:
            print("WARNING: only supports loading the first difficulty level")

    def parse(self, line: str) -> None:
        if line == '[BDCFF]' and self.state == 0:
            self.state = self.SECT_BDCFF
        elif line == '[game]' and self.state == self.SECT_BDCFF:
            self.state = self.SECT_GAME
        elif line == '[highscore]' and self.state == self.SECT_GAME:
            self.state = self.SECT_HIGHSCOREG
            # we're ignoring the highscore table from the game file, as we use our own
        elif line == '[highscore]' and self.state == self.SECT_CAVE:
            self.state = self.SECT_HIGHSCORE
            # we're ignoring the highscore table from the game file, as we use our own
        elif line == '[/highscore]':
            if self.state == self.SECT_HIGHSCOREG:
                self.state = self.SECT_GAME
            elif self.state == self.SECT_HIGHSCORE:
                self.state = self.SECT_CAVE
        elif line == '[cave]' and self.state == self.SECT_GAME:
            self.current_cave = BdcffCave()
            self.caves.append(self.current_cave)
            self.state = self.SECT_CAVE
        elif line == '[map]' and self.state == self.SECT_CAVE:
            self.state = self.SECT_MAP
        elif line == '[/map]' and self.state == self.SECT_MAP:
            self.state = self.SECT_CAVE
        elif line == '[objects]' and self.state == self.SECT_CAVE:
            self.state = self.SECT_OBJECTS
        elif line == '[/objects]' and self.state == self.SECT_OBJECTS:
            self.state = self.SECT_CAVE
        elif line == '[replay]' and self.state == self.SECT_CAVE:
            self.state = self.SECT_REPLAY
            # we ignore the cave replays they're in a format we don't support
        elif line == '[/replay]' and self.state == self.SECT_REPLAY:
            self.state = self.SECT_CAVE
        elif line == '[/cave]' and self.state == self.SECT_CAVE:
            self.current_cave = None
            self.state = self.SECT_GAME
        elif line == '[/game]' and self.state == self.SECT_GAME:
            self.state = self.SECT_BDCFF
        elif line == '[/BDCFF]' and self.state == self.SECT_BDCFF:
            pass
        elif self.state == self.SECT_OBJECTS and line.startswith(("[Level", "[/Level")):
            raise BdcffFormatError("no support for multiple levels in [objects]")
        elif line.startswith('[') and line.endswith(']'):
            raise BdcffFormatError("invalid tag: " + line + " state=" + str(self.state))
        else:
            self.process_line(line)

    def process_line(self, line: str) -> None:
        if self.state == self.SECT_BDCFF:
            if line.startswith("Version="):
                self.bdcff_version = line.split("=")[1]
            else:
                raise BdcffFormatError("bdcff parse error, state=" + str(self.state) + " line=" + line)
        elif self.state == self.SECT_GAME:
            if line.startswith("TitleScreen"):
                return
            prop, value = line.split("=")
            self.game_properties[prop.lower()] = value
        elif self.state == self.SECT_CAVE:
            prop, value = line.split("=")
            assert self.current_cave
            self.current_cave.properties[prop.lower()] = value
        elif self.state == self.SECT_MAP:
            assert self.current_cave
            self.current_cave.map.maplines.append(line)
        elif self.state == self.SECT_OBJECTS:
            instruction, arguments = line.split('=')
            assert self.current_cave
            self.current_cave.objects.append((instruction, arguments))
        elif self.state in (self.SECT_HIGHSCORE, self.SECT_HIGHSCOREG, self.SECT_REPLAY):
            return
        else:
            raise BdcffFormatError("bdcff parse error, state=" + str(self.state) + " line=" + line)


if __name__ == "__main__":
    cave = BdcffParser(sys.argv[1])
    cave.write(sys.stdout)
