# Boulder Caves+
An extended version of Boulder Caves, a Boulder Dash (tm) clone written by Irmen de Jong.
Extended version by Michael Kamensky, based on the original Boulder Caves v5.7.2 source code.

Boulder Dash (tm) is (C) 1984 First Star Software, created by Peter Liepa and Chris Gray.
The Boulder Dash franchise currently belongs to BBG Entertainment GmbH, all rights reserved.
Boulder Caves+ is a free and open source, non-commercial, non-profit fan made software released under GNU GPL v3.

Boulder Caves+ aims for maximum possible compatibility with Krissz Engine - specifically the New Engine currently live at Krissz's online remake website. Please note that the compatibility with the Old Krissz Engine is not the aim of this project, there's very limited information available about how Old Engine functioned and there is no reliable way to test its inner workings. However, even with that in mind, many Old Engine maps should be playable in Boulder Caves+, as long as they don't rely on specific timings or features unique to the Old Engine, especially the substandard multi-pass cave scanning algorithm that was implemented there.

Standard Boulder Dash tile set is based on the original graphics of Boulder Dash by Peter Liepa and Chris Gray.
Modern tile set is from MIT-licensed GDash and is based on Boulder Rush by Michael Kowalski / Miksoft.
Krissz Engine tile set extensions, as well as the extra boulder sound, are by Krissz.
All fan-made object artwork is courtesy of its original authors.

# System Requirements

Boulder Caves+ is a Python game based on Boulder Caves, written with the Tkinter and Pillow toolkits. While the game has been optimized by now compared to the original implementation, it still requires a good amount of CPU processing power to perform at full speed. I eventually plan to port the game to SDL 2 (Pygame 2.x), which may bring about some performance increase, although the exact extent to which the game can be optimized in this way is unknown, since for the most part, it's not the drawing routine that takes the most processing speed, but the cave scanning routine.

That said, through current testing, the absolute minimum hardware you can expect to be able to run the game on and play most caves in either 30 fps or 60 fps mode is a Raspberry Pi 4, preferably with a 2 GHz overclock. You may need to either use Pypy3 or to disable certain game settings or enable optimizations to reach full speed in the bigger caves, but standard-sized and small caves will be playable with little to no optimization applied.

Any office-class Core i3/Ryzen 3 or Core i5/Ryzen 5 PC from the last 5 years or so should be able to play most or all caves with little to no optimization applied in 60 fps, with extended open border set to 3 or infinite.

Any modern Core i7/Ryzen 7 PC from the last 7 years or so should be able to play most or all caves with no optimization in 60 fps mode with infinite scrolling enabled.

Boulder Caves+ can run on any machine architecture and operating system capable of running Python v3.6 or newer. It was developed and tested on a Linux operating system (Linux Mint), but is compatible with Microsoft Windows (tested on Windows 10) and should be compatible with MacOS as well.

Boulder Caves+ requires Python v3.6 (or newer) and the following Python libraries installed (you can install them using the pip package manager for Python):
   - Tkinter
   - Pillow (or PIL)
   - Miniaudio, PyAudio, Soundcard, or SoundDevice
   - Synthplayer

# Launching the Game

You can start Boulder Caves+ or its integrated Construction Kit using a window-based launcher by starting the "launcher.py" file from the game installation folder. This is the recommended way of starting Boulder Caves+.

Be sure to check out the available settings and configure them as you see fit. Generally, it is recommended to start with the settings that involve the least possible optimization - you can try turning the 60 fps mode on and keeping Performance Optimization on "None". If you have a modern, fast PC, you shouldn't encounter problems when running with these settings. If you find the game intolerably slow with these settings applied, progressively change the settings towards more optimization (switch "Open Border Extended View" down to 1 tile or disabled, disable 60 fps mode, change Performance Optimization to Light, Medium, or Heavy) until you reach satisfactory results. Note that each subsequent optimization makes the game less visually rich and correct and also less smooth in certain respects.

You can pass additional parameters to Boulder Caves+ by specifying them on the command line when you invoke the launcher. In most circumstances, it would not be necessary to toggle any of them, but you can use the following command (invoked from the command line terminal) to learn about all the options that are currently available in Boulder Caves+:

   ./launcher.py --help

If the game doesn't start when you double click the launcher file, indicating that you're missing some of the required libraries, please install the packages outlined above using Pip (please check the official website for Python and for Pip to learn how to do it). Usually, the following command is enough to fetch everything you need, though sometimes (e.g. on some Linux distributions) you may need to also install Tkinter for Python 3 separately:

   pip install pillow miniaudio synthplayer

If you're using Linux and the game still doesn't start after following the steps outlined above, please ensure that you have FFMPEG installed, which is used indirectly by one of the game's dependencies for high quality sound resampling. Not having FFMPEG installed on a Linux system may cause the game to fail to start without any visible error message unless you're running it in a terminal.

# Game Launcher Options

Boulder Caves+ Launcher allows to choose a cave or a cave set that you would like to play (from the ones available in the "caves" folder or one of its subfolders). On top of that, it allows to define several common game options which will be automatically saved when the game is started or the "Quit" button is pressed.

Game Variant - allows to choose one of the three game variants supported by Boulder Caves+. The variants are:
  * Krissz Engine - the default and the main recommended mode of Boulder Caves+, which tries to mimic the behavior of Krissz Engine as closely as currently possible. A 30*18 game window is used in this mode.
  * Retro Commodore 64 Style - one of the original Boulder Caves modes, which uses a smaller window reminiscent of the old C64 games. Several Krissz Engine-specific behavior options are disabled while the game is in this mode. Also, some behavior specific to Boulder Caves is enabled while in this mode, such as the border flash when reaching the necessary diamond count or the fact that a sound is played when an object goes through a slime. This behavior, some of which is not actually authentic to the C64 games, may be changed or removed in a later version.
  * Modern Boulder Rush Style - one of the original Boulder Caves modes, which uses a large 40*22 window that encompasses a full standard-sized cave and uses the Boulder Rush multi-color tile set with fixed colors. In this mode, just like in the Retro C64 Style mode, the Krissz Engine-specific behavior is disabled and some behavior specific to the original Boulder Caves is enabled (also subject to change).

60 FPS (Fast PC Recommended) - when this option is enabled, the game will try to reach 60 fps instead of the 30 fps frame per second limit when displaying animations. It is recommended that you try this option, but if the game is slow for you or you experience lag or unnecessary delays, you may have to disabled it, as it requires a relatively fast CPU due to the fact that processing is done in Python. You may also try running the game through Pypy3 (see below) with this option enabled to see if the optimizations conveyed by Pypy3 are enough to make this mode work adequately fast on your machine.

Use Synthesized Sounds - enabling this option will make the game synthesize the sound effects instead of using the pre-recorded .ogg sound samples.

Performance Optimizations - this option determines the level of visual optimization applied to the game. Note that each subsequent level trades a bit of visual accuracy for more speed. Therefore, ideally, you want to keep this option on None (or Light at maximum) if your PC allows you to run the game adequately quickly. If you experience slowdowns, consider increasing this option by one level and seeing each time whether the optimization is enough to make the game work at full speed. Note that as of this version of Boulder Caves+, most of these optimizations apply to the reveal demo before the level more than to the gameplay itself (but the reveal demo is also commonly the most CPU-intensive part of the level).

Open Border Extended View - for levels with open border(s), this option defines how the area beyond the border is displayed. For caves that are smaller than the window/screen size, the open border is always displayed as empty, which is the same as Krissz Engine (in Retro C64 and Modernized game styles, the area beyond the border is displayed as Titanium Wall tiles, which is a Boulder Caves original behavior). For caves that are bigger than the window/screen, if Open Border Extended View is disabled (None), there is nothing displayed behind the border, and you simply cross the border and immediately appear on the othe side. If the option is set to 1, 2, or 3 (which is measured in tiles), the game will display a row and/or a column of 1, 2, or 3 (respectively) tiles behind the border with a hatched pattern applied to these tiles to indicate that this is beyond the scope of the cave. You also immediately cross to the other side when you cross the border in this mide. If set to Infinite, Boulder Caves+ will attempt to imitate the "infinite scroll" behavior of Krissz Engine, with the area beyond the border mirroring the opposite side of the cave and with Rockford transitioning relatively smoothly through the border. Note that the original infinite scroll algorithm used in Krissz Engine is unknown due to the closed source character of the game, and the algorithm used in Boulder Caves+ is an imperfect approximation. Until it is polished and updated to be more smooth, you will feel the transition through the border with a slightly jerky repositioning of the view. Also please note that each subsequent option value is more CPU-intensive than the previous one, with the Infinite mode requiring almost double the processing power compared to None. Using this option, especially in conjunction with the 60 FPS mode, is only recommended on fast and modern PCs for the moment.

Game Screen Size - defines either the window scale (from 1 to 5, as applied to the tile set), or sets the game to try to expand to fit the full screen (when set to Full Screen). Note that in Full Screen mode, the only tested resolutions are the ones that are either 16:9 or 16:10 in ratio. Using a screen with a different ratio may work correctly, but has not been tested, and may exhibit certain issues (needs more testing). Other than that, the game should expand correctly to fit even very large (e.g. 2K, possibly 4K) screen resolutions.

Start - saves the settings and starts the game. Note that it may take a bit of time to start the game on slower or legacy hardware, especially on something like a Raspberry Pi. Be patient in case the game doesn't start immediately and don't click the button again unless you're absolutely sure that the game did not start for any reason.

Editor - starts the bundled Boulder Caves+ Construction Kit, which allows to create and edit caves. Note that as of right now, it only supports editing a single cave (either standalone or chosen from a cave set). If you want to make a full BDCFF cave set, you will need to "stitch" the individual .bd files manually to form a complete cave set definition. Note that if the game variant is set to Krissz Engine, the Construction Kit will start with Krissz Engine defaults. If any other game variant is chosen, the Construction Kit will start with the original Boulder Caves defaults.

Define Keys - allows you to redefine the keys used to control the game. By default, the game is controlled with the cursor keys, Control to snap-activate a tile, Space to pause the game, and F1 to start the game. However, these keys can be redefined. Note that as of right now, you need to type in the name of the key that you wish to assign to each action. For the "Snap" action, there are only two allowed choices at the moment - Control and Alt. Trying to assign any other key to this action will result in an error message. If for any reason your key map ends up not working correctly and you can't control the game anymore, delete the file "controls.ini" in the game folder and start the launcher again (redefine the keys again if necessary).

Quit - saves the settings and quits the launcher.

# Supported Caves

Boulder Caves+ is primarily designed to support Krissz Engine caves. Most New Engine caves should work in Boulder Caves+ either identical or very similar to how things behave, look, and sound in Krissz Engine. Note that due to the closed source nature of Krissz Engine, it's impossible to be sure that the game mechanics and features are replicated in Boulder Caves+ in exactly the same way as they are implemented in the original engine. As such, you may expect certain incompatibilities or broken corner cases, which may be addressed in the future versions of the game.

Boulder Caves+ comes with several converted Krissz Engine caves as a demonstration of what is supported and what can be played. However, Krissz Engine itself is a closed source, restricted access website that does not contain an integrated cave exporter or download options beyond a way to make a cave image. Therefore, authors of the caves who make caves for Krissz Engine would need to make BDCFF conversions from cave images taken from the Krissz Engine Construction Kit if they desire to make them publicly available for playing via Boulder Caves+ or another possible future compatible engine. A converter is bundled with the game to allow conversion of caves from Krissz Engine cave images to a format supported by Boulder Caves+, please check the README file in the "tools" folder for additional information on how to convert caves in order to be able to play them in Boulder Caves+.

On top of that, Boulder Caves+ can play the original Boulder Dash I by Peter Liepa and Chris Gray and comes with the BD1 caves integrated into the game. Boulder Dash I can be selected from the Launcher menu, along with the other caves currently present.

The engine also supports an assortment of caves in standard BDCFF format that follow the official BDCFF specification and do not use any additional and "unofficial" elements on top of the ones supported by Krissz Engine and the original Boulder Caves. Not all BDCFF features are supported, so certain caves with complex specifications may not work as intended. You may check out Arno's Boulder Dash fan site for some amazing BDCFF format cave sets and you can try and see if they would work in Boulder Caves+. Do note that many of them were designed with extended features and objects in mind that Boulder Caves+ do not support (they are supported e.g. in GDash). These cave sets will not work correctly or at all in Boulder Caves+.

Any new caves you may want to play in Boulder Caves+, whether from Krissz Engine or from another source, should be placed in the "caves" folder of the game and will be visible from the Launcher menu as long as they are in the BDCFF format and have either the .bd or the .bdcff extension. If you have many caves/cave sets, you can categorize them further by placing them inside subfolders in the "caves" folder, similar to how the bundled caves are placed.

# Known issues

Even though Boulder Caves+ fixes many bugs with the original game and editor and improves it in a variety of ways, also adding support for Krissz Engine features, it's definitely not a perfect implementation of Boulder Dash or Krissz Engine, at least yet. First of all, Krissz Engine itself is a closed source game, so certain features had to be deduced, determined through frame-by-frame testing, or implemented in a way that I believe would be a close enough representation of how things are implemented in it. Also, the original Boulder Caves made some concessions and simplifications for BD physics, which made it not a very precise engine when it comes to CSO corner cases. While many of those have already been figured out and fixed (most of them according to GDash source code as one of the best available reference BD clone implementations), there might still be certain things that do not work as expected, especially in certain rare conditions.

The following issues are long-standing and they're known. While I expect to figure out a way to fix them eventually, so far they are in dire need of improvement:

1. Infinite scroll implementation. The current implementation for infinite scroll is slightly jerky when the border is crossed, "thanks" to imperfect math. If anyone would like to contribute some code improvement to make the infinite scroll smooth and seamless, check out the code circa line 529 in game.py, the update_border_mirror method. Also, perhaps there's a better/faster/simpler implementation possible for this, I'm not sure yet.
2. Rockford blinking and tapping animation. The original Boulder Caves implementation isn't synced up properly to match the animation cycles, which is why Rockford blinks and taps feet in a jerky, disjointed way, and too quickly. Boulder Caves+ improves it by attempting to sync up and delay the animations not to interfere with each other according to the GDash source, but it seems like there's still a corner case where a blink animation would be cut short by the beginning or the ending tap animation. This needs more work on synchronization. It's not very noticeable, but it's there.

# BDCFF File Format Extensions

Boulder Caves+ uses its own, extended version of the BDCFF file format for storing cave data. While largely compatible with the original BDCFF specification, the Boulder Caves+ version (let's call in BDCFF+ for simplicity) contains some additional options and characters not found in the original specification (mostly for Krissz engine-specific features and objects). Thus, any original BDCFF file within the limits of what is supported by Boulder Caves+ should still be a valid BDCFF+ file, but not every BDCFF+ file is backwards compatible with the original BDCFF.

The following characters are used in addition to the BDCFF spec in the [map] section of the file:
``%`` - indicates a Heavy Boulder (an object known as Megaboulder in GDash)
``*`` - indicates a Light Boulder (an object unique to Krissz Engine and its compatible clones)

The following cave properties are used in addition to the BDCFF spec in the [cave] section of the file:
``TargetFps`` - tries to match the Game Speed (Frames Per Second) property in Krissz Engine
``MagicWallStopsAmoeba`` - tries to match the Magic Wall Stops Amoeba property in Krissz Engine
``RockfordBirthTime`` - tries to match the Rockford Birth Time property in Krissz Engine
``AmoebaLimit`` - tries to match the Amoeba Limit property in Krissz Engine
``AmoebaGrowsBeforeSpawn`` - when enabled, tries to mimic the behavior of Krissz Engine where the amoeba starts growing before Rockford spawns
``NoTimeLimit`` - tries to match the No Time Limit property in Krissz Engine
``ReverseTime`` - tries to match the Reverse Time property in Krissz Engine where the timer counts up instead of down
``OpenHorizontalBorders`` - tries to match the Open Horizontal Borders property in Krissz Engine with a horizontal wraparound
``OpenVerticalBorders`` - tries to match the Open Vertical Borders property in Krissz Engine with a vertical wraparound
``ValueOfASecond`` - tries to match the Value of a Second (Bonus/Penalty) property in Krissz Engine, applied as a bonus on time-limited maps and as a penalty on maps with Reverse Time set
``SingleLife`` - when enabled, only gives the player a single life and doesn't offer any bonus lives, mimicking Krissz Engine functionality

Many of these cave properties are disabled (either by setting their value to "false" or to "-1") if they're not present in the BDCFF file.

The following BDCFF properties are not used by the Boulder Caves+ engine and are ignored, at least for now:
``CaveDelay`` - not implemented, use TargetFps to set the desired cave FPS Krissz Engine-style instead
``FrameTime`` - not implemented, use TargetFps to set the desired cave FPS Krissz Engine-style instead

Also, anything not supported by the original Boulder Caves that is not mentioned above is not yet supported as well.

Please note that when working with the Open Horizontal/Vertical Borders (either option or both at the same time), it is recommended to set both ``BorderProperties.wraparound`` and ``BorderProperties.lineshift`` to ``false`` to avoid unexpected behavior and to match the Krissz Engine behavior as closely as currently possible with the Boulder Caves+ engine. In general, when aiming for Krissz engine compatibility, it's recommended to use the ``OpenHorizontalBorders`` and ``OpenVerticalBorders`` properties instead of ``BorderProperties.wraparound`` and ``BorderProperties.lineshift``.


# Boulder Caves+ Specific Construction Kit Cave Options

Boulder Caves+ Construction Kit allows to specify all standard and Krissz Engine specific cave parameters, as outlined above, and also contains several cave options that are specific to Boulder Caves+ at least in name, but possibly also in function. The options are:

Amoeba Early Start - if this option is checked, amoeba will start growing immediately when the cave is loaded, before Rockford is born. Krissz Engine seems to use this approach based on my tests, so this option is recommended for caves that are compatible with Krissz Engine.
Single Life - if this option is checked, the player will be given only a single life, there will be no life indicator in the status bar, and there is no way to earn a bonus life. This mimics the behavior of Krissz Engine, where caves are designed to be played with one life only, then you either lose the game or you get your high score recorded if you win. If this option is not checked, Boulder Caves+ will play more like a standard Boulder Dash game, giving the player 3 lives and an opportunity to earn a bonus life (or lives) as they play and earn enough points. Playing Krissz Engine caves without Single Life checked will most likely unbalance many of them, as many caves are designed for very high scores that may technically yield nearly infinite lives to the player.

Note that also there are two different ways to specify Amoeba Limit and Slime Permeability. The first, non-Krissz Engine compatible way, utilizes fractional options "Amoeba Limit Factor" (which defines the ratio of amoeba allowed, compared to the cave size) and "Slime Perm., unpred.", which defines an unpredictable slime permeability as a fractional, floating point value between 0.0 and 1.0. The second, Krissz-Engine compatible way, utilizes decimal optims "Amoeba Limit" (which mimics the option with the same name in Krissz Engine) and "Slime Perm., 0-8", which matches the behavior of the original C64 Construction Kit (PLCK) when it comes to predictable C64-style permeability, and the values from 0 to 8 match the permeability patterns used in both PLCK and Krissz Engine.

When both options of the same type are enabled (e.g. Amoeba Limit Factor and Amoeba Limit), the Krissz Engine compatible options take priority. Disabling a Krissz Engine compatible option means setting its value to -1.

# Running on Pypy3

Boulder Caves+ is fully compatible with the amazing high-speed CPython implementation called Pypy3 - check out www.pypy.org for more information. Playing Boulder Caves+ on Pypy3 gives a rather significant frame per second boost on legacy hardware, allowing large caves with multiple explosions and dynamic objects to play with minimal or no noticeable delays.

In order to play Boulder Caves+ on Pypy3, you would need to either install Pypy3 and all the dependencies (e.g. pillow, synthplayer, miniaudio) using pip for Pypy3, or make a virtual environment for Pypy3 and install the dependencies there.

The latter seems to produce better results and be easier to accomplish on operating systems such as Ubuntu or Linux Mint, thus, it is detailed below.

First, install Pypy3, the development headers (to install compiled pip dependencies) and the tkinter library for Pypy3 on your system, as well as virtualenv which is used to create Python virtual environments. For example, on Linux Mint, you can use the following:

   ``sudo apt install pypy3 pypy3-dev pypy3-tk virtualenv``

Then, create a new virtual environment. For example, it's possible to make one inside the Boulder Caves+ folder by switching to its directory and then issuing this command:

   ``virtualenv -p pypy3 pypy3-env``

(where "pypy3-env" is the name of the directory that will contain the environment).
Once that is done, activate the environment:

   ``source pypy3-env/bin/activate``

Install all the dependencies if you haven't done so before, e.g.:

   ``pip3 install pillow``
   ``pip3 install miniaudio``
   ``pip3 install synthplayer``

Now you're ready to play the game from this environment by launching the relevant .py file (e.g. startgame.py or startgame-quiet.py) while in this environment. You can make a simple shell script file (e.g. start-bouldercaves.sh) to automatically activate the environment and start the game. For example:

   ``#!/bin/bash``
   ``source pypy3-env/bin/activate``
   ``./launcher.py "$@"``

To install Pypy3 on Microsoft Windows on MacOS, please refer to the system-specific instructions on the official Pypy3 website and possibly read up on how to install/use Pip for Pypy3 on your operating system. Unfortunately, I'm a pure Linux user, so I can't provide reliable installation instructions for other operating systems.

================================================================

The README instructions for the original Boulder Caves, modified to fit some terminology changes, follow below.
Please note that the things which no longer apply to Boulder Caves+ were removed from the README so as not to confuse the reader.

# Boulder Caves
A Boulder Dash (tm) clone in pure python. Includes a Construction Kit (cave editor) so you can make your own game!

Requirements to run this:
- Python 3.6 or newer
- ``pillow`` (to deal with images)
- ``synthplayer`` (software FM synthesizer)
- one of the supported audio playback libraries:
    - ``miniaudio``
    - ``soundcard``
    - ``sounddevice``

*Detailed instructions how to run the game are [at the bottom of this text.](#how-to-install-and-run-this-game)*

This software is licensed under the [GNU GPL 3.0](https://www.gnu.org/licenses/gpl.html).
Graphics and sampled sounds are used from the MIT-licensed [GDash](https://bitbucket.org/czirkoszoltan/gdash). 


Inspired by the [javascript version from Jake Gordon](http://codeincomplete.com/posts/javascript-boulderdash/)


Much technical info about Boulder Dash can be found here https://www.elmerproductions.com/sp/peterb/
and here https://www.boulder-dash.nl/


There are a few command line options to control the graphics of the game, the zoom level,
and the graphics update speed (fps).
On Linux the game runs very well, it was also tested to run on Windows 10.
If you experience graphics slowdown issues, try enabling optimization options in the game
launcher or adjusting the parameters on the command line.

## Objective and rules of the game

- Collect enough diamonds to open the exit to go to the next level!
- Extra diamonds grant bonus points, and time left is added to your score as well.
- Avoid monsters or use them to your advantage.
- Some brick walls are not simply what they seem. 
- Amoeba grows and grows but it is often worthwhile to contain it. Sometimes you have
  to set it free first.
- Slime is permeable to boulders and diamonds but you cannot go through it yourself.  
- *Intermission* levels are bonus stages where you have one chance to complete them.
You won't lose a life here if you die, but you only have one attempt at solving it.
- A small high score table is saved. 


## Controls

You control the game via the keyboard:

- Cursorkeys UP, DOWN, LEFT, RIGHT: move your hero.
- with CONTROL: grab or push something in adjacent place without moving yourself.
- ESC: lose a life and restart the level. When game over, returns to title screen.
- Space: pause/continue the game.
- F1: start a new game, or skip popup screen wait.
- F5: cheat and add an extra life.  No highscore will be recorded if you use this.
- F6: cheat and add 10 seconds extra time.   No highscore will be recorded if you use this.
- F7: cheat and skip to the next level.   No highscore will be recorded if you use this.
- F8: randomize colors (only when using Commodore-64 colors).
- F9: replay prerecorded demo (from title screen).
- F10: quit the game.
- F12: launch cave editor (Boulder Caves+ Construction Kit).


## Sound

You can choose between *sampled sounds* and *synthesized sounds* via a command line option.

The sampled sounds require the 'oggdec' tool and the sound files. If you use the 
sound synthesizer however, both of these are not needed at all - all sounds are generated
by the program.

The Python zip app script creates two versions of this game, one with the sound files included,
and another one (that is much smaller) without the sound files because it uses the synthesizer.

### Hearing no sound? Configure the correct output audio device
On some systems, the lowlevel system audio library seems to report a wrong 
default output audio device. In this case, you may get an ``IOError``
(describing the problem). You can also get another error (or no sound output at all,
without any errors at all...) If this happens, you can configure the output audio device
that should be used:

Either set the ``PY_SYNTHPLAYER_AUDIO_DEVICE`` environment variable to the correct device number,
or set the ``synthplayer.playback.default_audio_device`` parameter at the start of your code.
(The environment variable has priority over the code parameter)

To find the correct device number you can use the command ``python -m sounddevice``.


## How to install and run this game

All platforms: if you just want to *play* the game, simply start the launcher (launcher.py),
set the desired options and use the "Play" button to play the game.

If you run the game from a command prompt, you are able to tweak some command line settings.
To see what is available just use the ``--help`` argument.


**Mac OS, Linux, ...**

Make sure you have Python 3.6 or newer installed, with Tkinter (Python's default GUI toolkit).
On Linux it's probably easiest to install these via your distribution's package manager.
On Mac OS, personally I'm using [Homebrew](https://brew.sh) to install things
(I've used the "``brew install python3 --with-tcl-tk``" command to make sure it doesn't use Apple's
own version of the tcl/tk library, which is buggy, but a newer version).

Alternatively:

1. make sure you have installed the python libraries: ``pillow``,  ``synthplayer`` and ``miniaudio``
   (or one of the other supported sound libraries). You can often find them in your package manager or install them with pip.
   This can be done easily with ``pip install -r requirements.txt``
2. if you want to play the version with synthesized sounds, you're all set.
3. if you want to play the version with sampled sounds, make sure you're using the ``miniaudio``
   library (which has ogg decoding built in). Otherwise you'll need the external 
   ``oggdec`` tool (usually available as part of the ``vorbis-tools`` package).
4. type ``python3 launcher.py`` to launch the game. If ``python3`` doesn't work 
just try ``python`` instead. 
