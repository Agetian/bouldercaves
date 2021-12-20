"""
Boulder Caves+ - a Boulder Dash (tm) clone.
Krissz Engine-compatible remake based on Boulder Caves 5.7.2.

This module contains the objects definitions.

Original version written by Irmen de Jong (irmen@razorvine.net)
Extended version by Michael Kamensky

License: GNU GPL 3.0, see LICENSE
"""

from enum import Enum
from typing import Callable, Optional


class GameObject:
    def __init__(self, name: str, rounded: bool, explodable: bool, consumable: bool,
                 spritex: int, spritey: int, sframes: int=0, sfps: int=0,
                 anim_end_callback: Callable=None, id: int=-1) -> None:
        self.name = name
        self.rounded = rounded
        self.explodable = explodable
        self.consumable = consumable
        self.spritex = spritex
        self.spritey = spritey
        self._tile = spritex + 8 * spritey
        self.sframes = sframes
        self.sfps = sfps
        self.anim_end_callback = anim_end_callback
        self.id = id

    def __repr__(self):
        return "<{cls} {name} (#{tile}) at {oid}>".format(cls=self.__class__.__name__, name=self.name, tile=self._tile, oid=hex(id(self)))

    def tile(self, animframe: int = 0) -> int:
        if self.sframes:
            return self._tile + animframe % self.sframes
        return self._tile


class RockfordGameObject(GameObject):
    def __init__(self, name: str, rounded: bool, explodable: bool, consumable: bool,
                 spritex: int, spritey: int, sframes: int=0, sfps: int=0,
                 anim_end_callback: Callable=None, id: int=-1) -> None:
        super().__init__(name, rounded, explodable, consumable,
                         spritex, spritey, sframes, sfps, anim_end_callback, id)
        dummy = GameObject("dummy", False, False, False, 0, 0)
        self.bomb = dummy
        self.blink = dummy
        self.tap = dummy
        self.tapblink = dummy
        self.left = dummy
        self.right = dummy
        self.stirring = dummy
        self.rocketlauncher = dummy
        self.pushleft = dummy
        self.pushright = dummy


class Direction(Enum):
    NOWHERE = ""
    LEFT = "l"
    RIGHT = "r"
    UP = "u"
    DOWN = "d"
    LEFTUP = "lu"
    RIGHTUP = "ru"
    LEFTDOWN = "ld"
    RIGHTDOWN = "rd"

    def rotate90left(self: 'Direction') -> 'Direction':
        return {
            Direction.NOWHERE: Direction.NOWHERE,
            Direction.UP: Direction.LEFT,
            Direction.LEFT: Direction.DOWN,
            Direction.DOWN: Direction.RIGHT,
            Direction.RIGHT: Direction.UP,
            Direction.LEFTUP: Direction.LEFTDOWN,
            Direction.LEFTDOWN: Direction.RIGHTDOWN,
            Direction.RIGHTDOWN: Direction.RIGHTUP,
            Direction.RIGHTUP: Direction.LEFTUP
        }[self]

    def rotate90right(self: 'Direction') -> 'Direction':
        return {
            Direction.NOWHERE: Direction.NOWHERE,
            Direction.UP: Direction.RIGHT,
            Direction.RIGHT: Direction.DOWN,
            Direction.DOWN: Direction.LEFT,
            Direction.LEFT: Direction.UP,
            Direction.LEFTUP: Direction.RIGHTUP,
            Direction.RIGHTUP: Direction.RIGHTDOWN,
            Direction.RIGHTDOWN: Direction.LEFTDOWN,
            Direction.LEFTDOWN: Direction.LEFTUP
        }[self]


# row 0
g = GameObject
EMPTY = g("EMPTY", False, False, True, 0, 0, id=0)
BOULDER = g("BOULDER", True, False, True, 1, 0, id=1)
DIRT = g("DIRT", False, False, True, 2, 0, id=2)
DIRT2 = g("DIRT2", False, False, True, 3, 0, id=3)
STEEL = g("STEEL", False, False, False, 4, 0, id=4)
BRICK = g("BRICK", True, False, True, 5, 0, id=5)
BLADDERSPENDER = g("BLADDERSPENDER", False, False, False, 6, 0, id=6)
VOODOO = g("VOODOO", False, True, True, 7, 0, id=7)
# row 1
SWEET = g("SWEET", True, False, True, 0, 1, id=8)
GRAVESTONE = g("GRAVESTONE", True, False, False, 1, 1, id=9)
TRAPPEDDIAMOND = g("TRAPPEDDIAMOND", False, False, False, 2, 1, id=10)
DIAMONDKEY = g("DIAMONDKEY", True, True, True, 3, 1, id=11)
BITERSWITCH1 = g("BITERSWITCH1", False, False, True, 4, 1, id=12)
BITERSWITCH2 = g("BITERSWITCH2", False, False, True, 5, 1, id=13)
BITERSWITCH3 = g("BITERSWITCH3", False, False, True, 6, 1, id=14)
BITERSWITCH4 = g("BITERSWITCH4", False, False, True, 7, 1, id=15)
# row 2
CLOCK = g("CLOCK", True, False, True, 0, 2, id=16)
CHASINGBOULDER = g("CHASINGBOULDER", True, False, True, 1, 2, id=17)
CREATURESWITCH = g("CREATURESWITCH", False, False, False, 2, 2, id=18)
CREATURESWITCHON = g("CREATURESWITCHON", False, False, False, 3, 2, id=19)
ACID = g("ACID", False, False, False, 4, 2, id=20)
SOKOBANBOX = g("SOKOBANBOX", False, False, False, 5, 2, id=21)
INBOXBLINKING = g("INBOXBLINKING", False, False, False, 6, 2, id=22)
INBOXBLINKING_1 = g("INBOXBLINKING_1", False, False, False, 6, 2, id=220) # blinking stages for inbox
INBOXBLINKING_2 = g("INBOXBLINKING_2", False, False, False, 7, 2, id=221)
OUTBOXBLINKING = g("OUTBOXBLINKING", False, False, False, 6, 2, id=23)
OUTBOXBLINKING_1 = g("OUTBOXBLINKING_1", False, False, False, 6, 2, id=230) # blinking stages for outbox
OUTBOXBLINKING_2 = g("OUTBOXBLINKING_2", False, False, False, 7, 2, id=231)
OUTBOXCLOSED = g("OUTBOXCLOSED", False, False, False, 6, 2, id=24)
OUTBOXHIDDEN = g("OUTBOXHIDDEN", False, False, False, 6, 2, id=25)
OUTBOXHIDDENOPEN = g("OUTBOXHIDDENOPEN", False, False, False, 6, 2, id=26)
# row 3
STEELWALLBIRTH = g("STEELWALLBIRTH", False, False, False, 0, 3, sframes=4, sfps=10, id=27)
CLOCKBIRTH = g("CLOCKBIRTH", False, False, False, 4, 3, sframes=4, sfps=10, id=28)
# row 4
ROCKFORDBIRTH = g("ROCKFORDBIRTH", False, False, False, 0, 4, sframes=4, sfps=10, id=29)
# stages of Rockford Birth, RockfordBirth1 is configured at run time because it needs not still appear as the inbox
ROCKFORDBIRTH_1 = g("ROCKFORDBIRTH_1", False, False, False, 0, 4, id=290)
ROCKFORDBIRTH_2 = g("ROCKFORDBIRTH_2", False, False, False, 0, 4, id=291)
ROCKFORDBIRTH_3 = g("ROCKFORDBIRTH_3", False, False, False, 1, 4, id=292)
ROCKFORDBIRTH_4 = g("ROCKFORDBIRTH_4", False, False, False, 2, 4, id=293)
ROCKFORD = RockfordGameObject("ROCKFORD", False, True, True, 3, 4, id=30)  # standing still
BOULDERBIRTH = g("BOULDERBIRTH", False, False, False, 4, 4, sframes=4, sfps=10, id=31)
# row 5
HEXPANDINGWALL = g("HEXPANDINGWALL", False, False, True, 0, 5, id=32)
VEXPANDINGWALL = g("VEXPANDINGWALL", False, False, True, 1, 5, id=33)
ROCKFORD.bomb = g("ROCKFORD.BOMB", False, True, True, 2, 5, id=30)
EXPLOSION = g("EXPLOSION", False, False, False, 3, 5, sframes=5, sfps=10, id=34)
# row 6
BOMB = g("BOMB", True, False, True, 0, 6, id=35)
IGNITEDBOMB = g("IGNITEDBOMB", True, False, True, 1, 6, sframes=7, sfps=10, id=36)
# row 7
DIAMONDBIRTH = g("DIAMONDBIRTH", False, False, False, 0, 7, sframes=5, sfps=10, id=37)
TELEPORTER = g("TELEPORTER", False, False, False, 5, 7, id=38)
HAMMER = g("HAMMER", True, False, False, 6, 7, id=39)
POT = g("POT", True, False, False, 7, 7, id=40)
# row 8
DOOR1 = g("DOOR1", False, False, False, 0, 8, id=41)
DOOR2 = g("DOOR2", False, False, False, 1, 8, id=42)
DOOR3 = g("DOOR3", False, False, False, 2, 8, id=43)
KEY1 = g("KEY1", False, False, False, 3, 8, id=44)
KEY2 = g("KEY2", False, False, False, 4, 8, id=45)
KEY3 = g("KEY3", False, False, False, 5, 8, id=46)
EDIT_QUESTION = g("E_QUESTION", False, False, False, 6, 8, id=47)
EDIT_EAT = g("E_EAT", False, False, False, 7, 8, id=48)
# row 9
STEELWALLDESTRUCTABLE = g("STEELWALLDESTRUCTABLE", False, False, True, 0, 9, id=49)
EDIT_DOWN_ARROW = g("E_DOWNARROW", False, False, False, 1, 9, id=50)
EDIT_LEFTRIGHT_ARROW = g("E_LEFTRIGHTARROW", False, False, False, 2, 9, id=51)
EDIT_EVERYDIR_ARROW = g("E_EVERYDIRARROW", False, False, False, 3, 9, id=52)
EDIT_LOCKED = g("E_LOCKED", False, False, False, 4, 9, id=53)
EDIT_OUT = g("E_OUIT", False, False, False, 5, 9, id=54)
EDIT_EXCLAM = g("E_EXCLAM", False, False, False, 6, 9, id=55)
EDIT_CROSS = g("E_CROSS", False, False, False, 7, 9, id=56)
# row 10
GHOSTEXPLODE = g("GHOSTEXPLODE", False, False, False, 0, 10, sframes=4, sfps=10, id=57)
BOMBEXPLODE = g("BOMBEXPLODE", False, False, False, 4, 10, sframes=4, sfps=10, id=58)
# row 11
COW = g("COW", False, True, True, 0, 11, sframes=8, sfps=10, id=59)
# row 12
WATER = g("WATER", False, False, True, 0, 12, sframes=8, sfps=20, id=60)
# row 13
ALTFIREFLY = g("ALTFIREFLY", False, True, True, 0, 13, sframes=8, sfps=20, id=61)
# row 14
ALTBUTTERFLY = g("ALTBUTTERFLY", False, True, True, 0, 14, sframes=8, sfps=20, id=62)
# row 15
BONUSBG = g("BONUSBG", False, False, True, 0, 15, sframes=8, sfps=10, id=63)
# row 16
COVERED = g("COVERED", False, False, False, 0, 16, sframes=8, sfps=20, id=64)
# row 17
FIREFLY = g("FIREFLY", False, True, True, 0, 17, sframes=8, sfps=20, id=611)
# row 18
BUTTERFLY = g("BUTTERFLY", False, True, True, 0, 18, sframes=8, sfps=20, id=621)
# row 19
STONEFLY = g("STONEFLY", False, True, True, 0, 19, sframes=8, sfps=20, id=65)
# row 20
GHOST = g("GHOST", False, True, True, 0, 20, sframes=8, sfps=20, id=66)
# row 21
BITER = g("BITER", False, True, True, 0, 21, sframes=8, sfps=20, id=67)
# row 22
BLADDER = g("BLADDER", False, True, True, 0, 22, sframes=8, sfps=20, id=68)
# row 23
MAGICWALL = g("MAGICWALL", False, False, True, 0, 23, sframes=8, sfps=20, id=69)
# row 24
AMOEBA = g("AMOEBA", False, False, True, 0, 24, sframes=8, sfps=20, id=70)
# row 25
SLIME = g("SLIME", False, False, True, 0, 25, sframes=8, sfps=20, id=71)
# row 26 - 30
ROCKFORD.blink = g("ROCKFORD.BLINK", False, True, True, 0, 26, sframes=8, sfps=20, id=30)
ROCKFORD.tap = g("ROCKFORD.TAP", False, True, True, 0, 27, sframes=8, sfps=20, id=30)
ROCKFORD.tapblink = g("ROCKFORD.TAPBLINK", False, True, True, 0, 28, sframes=8, sfps=20, id=30)
ROCKFORD.left = g("ROCKFORD.LEFT", False, True, True, 0, 29, sframes=8, sfps=20, id=30)
ROCKFORD.right = g("ROCKFORD.RIGHT", False, True, True, 0, 30, sframes=8, sfps=20, id=30)
# row 31
DIAMOND = g("DIAMOND", True, False, True, 0, 31, sframes=8, sfps=20, id=72)
# row 32
ROCKFORD.stirring = g("ROCKFORD.STIRRING", False, True, True, 0, 32, sframes=8, sfps=20, id=30)
# row 33   # ...contains hammer
# row 34
MEGABOULDER = g("MEGABOULDER", True, False, True, 0, 34, id=73)
SKELETON = g("SKELETON", True, False, True, 1, 34, id=74)
GRAVITYSWITCH = g("GRAVITYSWITCH", False, False, False, 2, 34, id=75)
GRAVITYSWITCHON = g("GRAVITYSWITCHON", False, False, False, 3, 34, id=76)
BRICKSLOPEDUPRIGHT = g("BRICKSLOPEDUPRIGHT", True, False, True, 4, 34, id=77)
BRICKSLOPEDUPLEFT = g("BRICKSLOPEDUPLEFT", True, False, True, 5, 34, id=78)
BRICKSLOPEDDOWNLEFT = g("BRICKSLOPEDDOWNLEFT", True, False, True, 6, 34, id=79)
BRICKSLOPEDDOWNRIGHT = g("BRICKSLOPEDDOWNRIGHT", True, False, True, 7, 34, id=80)
# row 35
DIRTSLOPEDUPRIGHT = g("DIRTSLOPEDUPRIGHT", True, False, True, 0, 35, id=81)
DIRTSLOPEDUPLEFT = g("DIRTSLOPEDUPLEFT", True, False, True, 1, 35, id=82)
DIRTSLOPEDDOWNLEFT = g("DIRTSLOPEDDOWNLEFT", True, False, True, 2, 35, id=83)
DIRTSLOPEDDOWNRIGHT = g("DIRTSLOPEDDOWNRIGHT", True, False, True, 3, 35, id=84)
STEELSLOPEDUPRIGHT = g("STEELSLOPEDUPRIGHT", True, False, True, 4, 35, id=85)
STEELSLOPEDUPLEFT = g("STEELSLOPEDUPLEFT", True, False, True, 5, 35, id=86)
STEELSLOPEDDOWNLEFT = g("STEELSLOPEDDOWNLEFT", True, False, True, 6, 35, id=87)
STEELSLOPEDDOWNRIGHT = g("STEELSLOPEDDOWNRIGHT", True, False, True, 7, 35, id=88)
# row 36
NITROFLASK = g("NITROFLASK", True, False, True, 0, 36, id=89)
DIRTBALL = g("DIRTBALL", True, False, True, 1, 36, id=90)
REPLICATORSWITCHON = g("REPLICATORSWITCHON", False, False, False, 2, 36, id=91)
REPLICATORSWITCHOFF = g("REPLICATORSWITCHOFF", False, False, False, 3, 36, id=92)
AMOEBAEXPLODE = g("AMOEBAEXPLODE", False, False, False, 4, 36, sframes=4, sfps=10, id=93)
# row 37
AMOEBARECTANGLE = g("AMOEBARECTANGLE", False, True, True, 0, 37, sframes=8, sfps=10, id=701)
# row 38
REPLICATOR = g("REPLICATOR", False, False, False, 0, 38, sframes=8, sfps=20, id=95)
# row 39
LAVA = g("LAVA", False, False, True, 0, 39, sframes=8, sfps=20, id=96)
# row 40
CONVEYORRIGHT = g("CONVEYORRIGHT", False, False, True, 0, 40, sframes=8, sfps=20, id=97)
# row 41
CONVEYORLEFT = g("CONVEYORLEFT", False, False, True, 0, 41, sframes=8, sfps=20, id=98)
# row 42
DRAGONFLY = g("DRAGONFLY", False, True, True, 0, 42, sframes=8, sfps=20, id=99)
# row 43
FLYINGDIAMOND = g("FLYINGDIAMOND", True, False, True, 0, 43, sframes=8, sfps=20, id=721)
# row 44
DIRTLOOSE = g("DIRTLOOSE", False, False, True, 0, 44, id=101)
CONVEYORDIRECTIONSWITCHNORMAL = g("CONVEYORDIRECTIONSWITCHNORMAL", False, False, False, 1, 44, id=102)
CONVEYORDIRECTIONSWITCHCHANGED = g("CONVEYORDIRECTIONSWITCHCHANGED", False, False, False, 2, 44, id=103)
CONVEYORDIRECTIONSWITCHOFF = g("CONVEYORDIRECTIONSWITCHOFF", False, False, False, 3, 44, id=104)
CONVEYORDIRECTIONSWITCHON = g("CONVEYORDIRECTIONSWITCHON", False, False, False, 4, 44, id=105)
FLYINGBOULDER = g("FLYINGBOULDER", False, True, True, 5, 44, id=106)
COCONUT = g("COCONUT", False, False, True, 6, 44, id=107)
# row 45
NUTCRACK = g("NUTCRACK", False, False, False, 0, 45, sframes=4, sfps=10, id=108)
ROCKETRIGHT = g("ROCKETRIGHT", False, False, True, 4, 45, id=109)
ROCKETUP = g("ROCKETUP", False, False, True, 5, 45, id=110)
ROCKETLEFT = g("ROCKETLEFT", False, False, True, 6, 45, id=111)
ROCKETDOWN = g("ROCKETDOWN", False, False, True, 7, 45, id=112)
# row 46
ROCKETLAUNCHER = g("ROCKETLAUNCHER", False, False, True, 0, 46, id=113)
ROCKFORD.rocketlauncher = g("ROCKFORD.ROCKETLAUNCHER", False, True, True, 1, 46, sframes=0, sfps=0, id=30)
# row 49 - 50
ROCKFORD.pushleft = g("ROCKFORD.PUSHLEFT", False, True, True, 0, 49, sframes=8, sfps=20, id=30)
ROCKFORD.pushright = g("ROCKFORD.PUSHRIGHT", False, True, True, 0, 50, sframes=8, sfps=20, id=30)
# row 53 - Krissz Engine and BoulderCaves+ specific objects and variants
LIGHTBOULDER = g("LIGHTBOULDER", True, False, True, 0, 53, id=114) # a no-delay boulder object
EXPANDINGWALL = g("EXPANDINGWALL", False, False, True, 1, 53, id=115) # a bidirectional expanding wall (Krissz Engine/GDash)
FILLERWALL = g("FILLERWALL", False, False, False, 2, 53, id=116) # a special "empty" object that's used as a filler for smaller caves
SLIME_EDITMODE = g("SLIME_EDITMODE", False, False, False, 3, 53, id=117) # a representation of slime in the game editor (Krissz Engine like)
INBOX_EDITMODE = g("INBOX_EDITMODE", False, False, False, 4, 53, id=118) # a representation of inbox in the game editor (Krissz Engine like)
OUTBOX_EDITMODE = g("OUTBOX_EDITMODE", False, False, False, 5, 53, id=119) # a representation of outbox in the game editor (Krissz Engine like)
HIDDEN_OUTBOX_EDITMODE = g("HIDDEN_OUTBOX_EDITMODE", False, False, False, 6, 53, id=120) # a representation of hidden outbox in the game editor (Krissz Engine like)
SLIME_IMPERMEABLE = g("SLIME_IMPERMEABLE", False, False, False, 7, 53, id=121) # an editor marker for the impermeable slime
# virtual objects that change into other things during the gameplay
BORDER_MIRROR = g("BORDER_MIRROR", False, False, False, 2, 53, id=122) # an extended border visualization marker object