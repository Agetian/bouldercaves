#!/usr/bin/env python3

"""
Boulder Caves+ - a Boulder Dash (tm) clone.
Krissz Engine-compatible remake based on Boulder Caves 5.7.2.
Boulder Caves 5.7.2 is written by Irmen de Jong.

Tkinter-based game launcher with support for common game options.
Boulder Caves+ Launcher is written by Michael Kamensky

License: GNU GPL 3.0, see LICENSE
"""

import pkgutil
import os
import sys
import subprocess
import tkinter as tk
import tkinter.messagebox
from tkinter import ttk
from bouldercaves.helpers import KeyHelper

VERSION = "1.1.0"

DEFAULT_CAVE = "Boulder Dash I (by Peter Liepa)"
DEFAULT_FOLDER = "-- no folder --"

window = tk.Tk()

def get_folder_list():
    folder_list = [DEFAULT_FOLDER]
    for filename in os.listdir("caves"):
        if (os.path.isdir(os.path.join("caves", filename))):
            folder_list.append(filename)
    folder_list.sort()
    return folder_list
    
def get_cave_list(folder_name):
    cave_list = []
    if folder_name == DEFAULT_FOLDER:
        folder_name = ""
    for filename in os.listdir(os.path.join("caves", folder_name)):
        if (filename.endswith(".bd") or filename.endswith(".bdcff")):
            cave_list.append(filename[0:filename.rfind(".")])
    cave_list.sort()
    return cave_list

def load_settings():
    game_mode = "1"
    target_60fps = False
    synth_sounds = False
    game_scale = "2"
    folder_name = DEFAULT_FOLDER
    cave_name = DEFAULT_CAVE
    optimize_level = "0"
    ext_border = "0"
    if os.path.exists("launcher.ini"):
        with open("launcher.ini", "r") as f:
            for option in f.readlines():
                if option.find("=") == -1:
                    continue
                params = option.strip().split("=")
                if params[0] == "game_mode":
                    game_mode = params[1]
                elif params[0] == "target_60fps":
                    target_60fps = True if params[1].lower() == "true" else False
                elif params[0] == "synth_sounds":
                    synth_sounds = True if params[1].lower() == "true" else False
                elif params[0] == "game_scale":
                    game_scale = params[1]
                elif params[0] == "cave_name":
                    cave_name = params[1]
                elif params[0] == "folder_name":
                    folder_name = params[1]
                elif params[0] == "optimize_level":
                    optimize_level = params[1]
                elif params[0] == "ext_border":
                    ext_border = params[1]
                    
    return [folder_name, cave_name, game_mode, target_60fps, synth_sounds, game_scale, optimize_level, ext_border]
                
def save_settings(chosen_folder, chosen_cave, game_mode, target_60fps, synth_sounds, game_scale, full_screen, optimize_level, ext_border):
    with open("launcher.ini", "w") as f:
        f.write(f"folder_name={chosen_folder}\n")
        f.write(f"cave_name={chosen_cave}\n")
        f.write(f"game_mode={game_mode}\n")
        f.write(f"target_60fps={'true' if target_60fps else 'false'}\n")
        f.write(f"synth_sounds={'true' if synth_sounds else 'false'}\n")
        f.write(f"game_scale={game_scale}\n")
        f.write(f"full_screen={full_screen}\n")
        f.write(f"optimize_level={optimize_level}\n")
        f.write(f"ext_border={ext_border}\n")
    
def start_game(folder_cbbox, cave_listbox, game_mode, target_60fps, synth_sounds, game_scale, full_screen, optimize_level, ext_border):
    import bouldercaves.game
    global cheat_set_cave, cheat_set_cave_val
    exec_params = [sys.executable, "-m", bouldercaves.game.__name__]
    if not cave_listbox.curselection():
        cave_listbox.selection_set(0)
        cave_listbox.activate(0)
        cave_listbox.see(0)
    chosen_folder = folder_cbbox.get()
    if chosen_folder == DEFAULT_FOLDER:
        chosen_folder = ""
    chosen_cave = cave_listbox.get(cave_listbox.curselection())
    if os.path.exists(os.path.join('caves', chosen_folder, f'{chosen_cave}.bd')):
        chosen_cave_file = chosen_cave + ".bd"
    elif os.path.exists(os.path.join('caves', chosen_folder, f'{chosen_cave}.bdcff')):
        chosen_cave_file = chosen_cave + ".bdcff"
    if game_mode == "1":
        exec_params.append("-k")
    elif game_mode == "2":
        exec_params.append("--authentic")
    if synth_sounds:
        exec_params.append("--synth")
    if target_60fps:
        exec_params.append("-f")
        exec_params.append("60")
    if not full_screen:
        exec_params.append("-s")
        exec_params.append(game_scale)
    if optimize_level != "0":
        exec_params.append("-O")
        exec_params.append(optimize_level)
    if ext_border != "0":
        exec_params.append("-m")
        exec_params.append(ext_border)
    if ext_border != "100":
        exec_params.append("-M")
    if full_screen:
        exec_params.append("-F")
    if cheat_set_cave.get() and cheat_set_cave_val.get() != "1":
        exec_params.append("-l")
        exec_params.append(cheat_set_cave_val.get())
    if len(sys.argv) > 1:
        for n, arg in enumerate(sys.argv):
            if n > 0:
                exec_params.append(arg)
    if chosen_cave != DEFAULT_CAVE:
        exec_params.append("-g")
        exec_params.append(f"{os.path.join('caves', chosen_folder, chosen_cave_file)}")
    save_settings(chosen_folder, chosen_cave, game_mode, target_60fps, synth_sounds, game_scale, full_screen, optimize_level, ext_border)
    #window.destroy() -- uncomment this line to quit launcher at launch
    env = os.environ.copy()
    env["PYTHONPATH"] = sys.path[0]
    subprocess.Popen(exec_params, env=env)

def start_editor(krissz_mode, folder_cbbox, cave_listbox, game_mode, target_60fps, synth_sounds, game_scale, full_screen, optimize_level, ext_border):
    import bouldercaves.editor
    if not cave_listbox.curselection():
        cave_listbox.selection_set(0)
        cave_listbox.activate(0)
        cave_listbox.see(0)
    chosen_folder = folder_cbbox.get()
    if chosen_folder == DEFAULT_FOLDER:
        chosen_folder = ""
    chosen_cave = cave_listbox.get(cave_listbox.curselection())
    save_settings(chosen_folder, chosen_cave, game_mode, target_60fps, synth_sounds, game_scale, full_screen, optimize_level, ext_border)
    params = "-k" if krissz_mode else ""
    env = os.environ.copy()
    env["PYTHONPATH"] = sys.path[0]
    subprocess.Popen([sys.executable, "-m", bouldercaves.editor.__name__, params], env=env)

def quit_launcher(folder_cbbox, cave_listbox, game_mode, target_60fps, synth_sounds, game_scale, full_screen, optimize_level, ext_border):
    if not cave_listbox.curselection():
        cave_listbox.selection_set(0)
        cave_listbox.activate(0)
        cave_listbox.see(0)
    chosen_folder = folder_cbbox.get()
    chosen_cave = cave_listbox.get(cave_listbox.curselection())    
    save_settings(chosen_folder, chosen_cave, game_mode, target_60fps, synth_sounds, game_scale, full_screen, optimize_level, ext_border)
    window.quit()

def define_keys():
    global defwnd, key_up, key_down, key_left, key_right, key_snap, key_pause, key_start, key_suicide
    key_up = tk.StringVar()
    key_down = tk.StringVar()
    key_left = tk.StringVar()
    key_right = tk.StringVar()
    key_snap = tk.StringVar()
    key_pause = tk.StringVar()
    key_start = tk.StringVar()
    key_suicide = tk.StringVar()
    load_keymap()
    defwnd = tk.Toplevel(window)
    defwnd.title("Define Keys")
    defwnd.resizable(False, False)
    defwnd.grab_set()
    label = tk.Label(defwnd, text="Game Controls:")
    label.grid(row=0, column=0, pady=4)
    
    def normalize_key_name(keysym):
        return keysym.split("_")[0].title()
    
    tk.Frame(defwnd)
    tk.Label(defwnd, text="Up").grid(row=1, column=0, padx=4, pady=2)
    entry_up = tk.Entry(defwnd, textvariable=key_up, width=10)
    entry_up.grid(row=1, column=1, padx=4, pady=2)
    def entry_up_clear(event): key_up.set("")
    def entry_up_input(event):
        key_up.set(normalize_key_name(event.keysym))
    entry_up.bind("<Button-1>", entry_up_clear)
    entry_up.bind("<KeyPress>", entry_up_clear)
    entry_up.bind("<KeyRelease>", entry_up_input)
    tk.Label(defwnd, text="Down").grid(row=2, column=0, padx=4, pady=2)
    entry_down = tk.Entry(defwnd, textvariable=key_down, width=10)
    entry_down.grid(row=2, column=1, padx=4, pady=2)
    def entry_down_clear(event): key_down.set("")
    def entry_down_input(event):
        key_down.set(normalize_key_name(event.keysym))
    entry_down.bind("<Button-1>", entry_down_clear)
    entry_down.bind("<KeyPress>", entry_down_clear)
    entry_down.bind("<KeyRelease>", entry_down_input)
    tk.Label(defwnd, text="Left").grid(row=3, column=0, padx=4, pady=2)
    entry_left = tk.Entry(defwnd, textvariable=key_left, width=10)
    entry_left.grid(row=3, column=1, padx=4, pady=2)
    def entry_left_clear(event): key_left.set("")
    def entry_left_input(event):
        key_left.set(normalize_key_name(event.keysym))
    entry_left.bind("<Button-1>", entry_left_clear)
    entry_left.bind("<KeyPress>", entry_left_clear)
    entry_left.bind("<KeyRelease>", entry_left_input)
    tk.Label(defwnd, text="Right").grid(row=4, column=0, padx=4, pady=2)
    entry_right = tk.Entry(defwnd, textvariable=key_right, width=10)
    entry_right.grid(row=4, column=1, padx=4, pady=2)
    def entry_right_clear(event): key_right.set("")
    def entry_right_input(event):
        key_right.set(normalize_key_name(event.keysym))
    entry_right.bind("<Button-1>", entry_right_clear)
    entry_right.bind("<KeyPress>", entry_right_clear)
    entry_right.bind("<KeyRelease>", entry_right_input)
    tk.Label(defwnd, text="Snap").grid(row=5, column=0, padx=4, pady=2)
    entry_snap = tk.Entry(defwnd, textvariable=key_snap, width=10)
    entry_snap.grid(row=5, column=1, padx=4, pady=2)
    def entry_snap_clear(event): key_snap.set("")
    def entry_snap_input(event):
        key_snap.set(normalize_key_name(event.keysym))
    entry_snap.bind("<Button-1>", entry_snap_clear)
    entry_snap.bind("<KeyPress>", entry_snap_clear)
    entry_snap.bind("<KeyRelease>", entry_snap_input)
    tk.Label(defwnd, text="Pause").grid(row=6, column=0, padx=4, pady=2)
    entry_pause = tk.Entry(defwnd, textvariable=key_pause, width=10)
    entry_pause.grid(row=6, column=1, padx=4, pady=2)
    def entry_pause_clear(event): key_pause.set("")
    def entry_pause_input(event):
        key_pause.set(normalize_key_name(event.keysym))
    entry_pause.bind("<Button-1>", entry_pause_clear)
    entry_pause.bind("<KeyPress>", entry_pause_clear)
    entry_pause.bind("<KeyRelease>", entry_pause_input)
    tk.Label(defwnd, text="Start").grid(row=7, column=0, padx=4, pady=2)
    entry_start = tk.Entry(defwnd, textvariable=key_start, width=10)
    entry_start.grid(row=7, column=1, padx=4, pady=2)
    def entry_start_clear(event): key_start.set("")
    def entry_start_input(event):
        key_start.set(normalize_key_name(event.keysym))
    entry_start.bind("<Button-1>", entry_start_clear)
    entry_start.bind("<KeyPress>", entry_start_clear)
    entry_start.bind("<KeyRelease>", entry_start_input)
    tk.Label(defwnd, text="Suicide").grid(row=8, column=0, padx=4, pady=2)
    entry_suicide = tk.Entry(defwnd, textvariable=key_suicide, width=10)
    entry_suicide.grid(row=8, column=1, padx=4, pady=2)
    def entry_suicide_clear(event): key_suicide.set("")
    def entry_suicide_input(event):
        key_suicide.set(normalize_key_name(event.keysym))
    entry_suicide.bind("<Button-1>", entry_suicide_clear)
    entry_suicide.bind("<KeyPress>", entry_suicide_clear)
    entry_suicide.bind("<KeyRelease>", entry_suicide_input)
    tk.Button(defwnd, text="Save", command=save_keymap, width=10).grid(row=9, column=0)
    tk.Button(defwnd, text="Cancel", command=close_keymap, width=10).grid(row=9, column=1)

def load_keymap():
    global key_up, key_down, key_left, key_right, key_snap, key_pause, key_start, key_suicide
    keymap = KeyHelper.load_key_definitions()
    key_up.set(keymap["up"].title())
    key_down.set(keymap["down"].title())
    key_left.set(keymap["left"].title())
    key_right.set(keymap["right"].title())
    key_pause.set(keymap["pause"].title())
    key_snap.set(keymap["snap"].title())
    key_start.set(keymap["start"].title())
    key_suicide.set(keymap["suicide"].title())
    
def save_keymap():
    global defwnd, key_up, key_down, key_left, key_right, key_snap, key_pause, key_start, key_suicide
    snap_mode = key_snap.get()
    if snap_mode.lower() not in ("control", "alt"):
        tkinter.messagebox.showerror("Error", "Only Control or Alt are supported for the Snap action.")
        defwnd.destroy()
        return
    with open("controls.ini", "w") as keymap_file:
        if key_up.get() == "":
            key_up.set("Up")
        if key_down.get() == "":
            key_down.set("Down")
        if key_left.get() == "":
            key_left.set("Left")
        if key_right.get() == "":
            key_right.set("Right")
        if key_snap.get() == "":
            key_snap.set("Control")
        if key_pause.get() == "":
            key_pause.set("Space")
        if key_start.get() == "":
            key_start.set("F1")
        if key_suicide.get() == "":
            key_suicide.set("Escape")
        keymap_file.write(f"Up={key_up.get()}\n")
        keymap_file.write(f"Down={key_down.get()}\n")
        keymap_file.write(f"Left={key_left.get()}\n")
        keymap_file.write(f"Right={key_right.get()}\n")
        keymap_file.write(f"Snap={key_snap.get()}\n")
        keymap_file.write(f"Pause={key_pause.get()}\n")
        keymap_file.write(f"Start={key_start.get()}\n")
        keymap_file.write(f"Suicide={key_suicide.get()}\n")
    tkinter.messagebox.showinfo("Done", "Game controls saved.")
    defwnd.destroy()

def close_keymap():
    global defwnd
    defwnd.destroy()
    
def run():
    # +++ TK interface +++
    global cheat_set_cave, cheat_set_cave_val
    window.title(f"Boulder Caves+ v{VERSION}")
    window.resizable(False, False)
    appicon = tk.PhotoImage(data=pkgutil.get_data("bouldercaves", "gfx/gdash_icon_48.gif"))
    window.tk.call("wm", "iconphoto", window._w, appicon)

    frame = tk.Frame(master=window, width=400, height=100)
    tk.Label(master=frame, text=f"Choose a cave or cave set:").grid(row=0, column=0)

    frame_caveList = tk.Frame(master=window)
    scrollbar = tk.Scrollbar(frame_caveList)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def update_cavelist(eventinfo):
        cave_listbox.delete(0, tk.END)
        cave_list = get_cave_list(folders_cbbox.get())
        if folders_cbbox.get() == DEFAULT_FOLDER:
            cave_listbox.insert(tk.END, DEFAULT_CAVE)
        for cave_file in cave_list:
            cave_listbox.insert(tk.END, cave_file)
        cave_listbox.selection_set(0)
        
    cave_listbox_height = 8 if window.winfo_screenheight() >= 720 else 5
    folders_cbbox = tk.ttk.Combobox(frame_caveList, width=28, state="readonly")
    folders_cbbox.bind("<<ComboboxSelected>>", update_cavelist)
    folders_cbbox.pack()
    cave_listbox = tk.Listbox(frame_caveList, yscrollcommand=scrollbar.set, width=30, height=cave_listbox_height)
    cave_listbox.pack()
    scrollbar.config(command=cave_listbox.yview)

    separator = ttk.Separator(window, orient='horizontal')
    separator.pack(fill='x', pady=2)

    game_mode = tk.StringVar(window, "1")
    target_60fps = tk.BooleanVar()
    synth_sounds = tk.BooleanVar()
    game_scale = tk.StringVar(window, "2")
    ext_border = tk.StringVar(window, "0")
    optimize_perf = tk.StringVar(window, "0")
    cheat_set_cave = tk.BooleanVar()
    cheat_set_cave_val = tk.StringVar(window, "1")
    
    frame_radiobtns = tk.Frame(master=window)
    tk.Label(frame_radiobtns, text="Game Variant:", width=40).pack(side=tk.TOP, ipady=3)
    # Dictionary to create multiple buttons
    radio_btn_elements = {"Krissz Engine (Recommended)" : "1",
                          "Retro Commodore 64 Style" : "2",
                          "Modern Boulder Rush Style" : "3"}
    
    # Loop is used to create multiple Radiobuttons
    # rather than creating each button separately
    for (text, value) in radio_btn_elements.items():
        tk.Radiobutton(frame_radiobtns, text = text, variable = game_mode,
            value = value).pack(side = tk.TOP)

    separator2 = ttk.Separator(frame_radiobtns, orient='horizontal')
    separator2.pack(fill='x', pady=2)

    tk.Checkbutton(frame_radiobtns, text="60 FPS (Fast PC Recommended)", variable=target_60fps,
                            ).pack(side = tk.TOP)
    tk.Checkbutton(frame_radiobtns, text="Use Synthesized Sounds", variable=synth_sounds,
                            ).pack(side = tk.TOP)

    start_cave_frame = tk.Frame(master=window)

    def update_set_cave_entry():
        set_cave_entrybox.configure(state=tkinter.NORMAL if cheat_set_cave.get() else tkinter.DISABLED)

    tk.Checkbutton(start_cave_frame, text="Set Starting Cave (Cheat):", variable=cheat_set_cave, command=update_set_cave_entry).grid(row=0, column=0)
    set_cave_entrybox = tk.Entry(start_cave_frame, textvariable=cheat_set_cave_val, width=4)
    set_cave_entrybox.grid(row=0, column=1)
    set_cave_entrybox.configure(state=tkinter.DISABLED)

    separator3 = ttk.Separator(frame_radiobtns, orient='horizontal')
    separator3.pack(fill='x', pady=2)

    frame_optimize = tk.Frame(master=window)
    separator_opt = ttk.Separator(frame_optimize, orient='horizontal')
    separator_opt.pack(fill='x', pady=2)
    tk.Label(frame_optimize, text="Performance Optimizations:", width=36).pack(side=tk.TOP)
    tk.Label(frame_optimize, text="(Keep on None or Light if able)", width=36).pack(side=tk.TOP)
    tk.Radiobutton(frame_optimize, text = "None", variable = optimize_perf, value = "0").pack(side = tk.LEFT)
    tk.Radiobutton(frame_optimize, text = "Light", variable = optimize_perf, value = "1").pack(side = tk.LEFT)
    tk.Radiobutton(frame_optimize, text = "Medium", variable = optimize_perf, value = "2").pack(side = tk.LEFT)
    tk.Radiobutton(frame_optimize, text = "Heavy", variable = optimize_perf, value = "3").pack(side = tk.LEFT)   
  
    frame_scale = tk.Frame(master=window)
    separator4 = ttk.Separator(frame_scale, orient='horizontal')
    separator4.pack(fill='x', pady=2)
    tk.Label(frame_scale, text = "Game Screen Size:", width=36).pack(side = tk.TOP, ipady = 1)
    tk.Radiobutton(frame_scale, text = "1", variable = game_scale, value = "1").pack(side = tk.LEFT, ipadx = 1)
    tk.Radiobutton(frame_scale, text = "2", variable = game_scale, value = "2").pack(side = tk.LEFT, ipadx = 1)
    tk.Radiobutton(frame_scale, text = "3", variable = game_scale, value = "3").pack(side = tk.LEFT, ipadx = 1)
    tk.Radiobutton(frame_scale, text = "4", variable = game_scale, value = "4").pack(side = tk.LEFT, ipadx = 1)
    tk.Radiobutton(frame_scale, text = "5", variable = game_scale, value = "5").pack(side = tk.LEFT, ipadx = 1)
    tk.Radiobutton(frame_scale, text = "Full Screen", variable=game_scale, value = "F").pack(side = tk.LEFT, ipadx = 1)
    
    frame_border = tk.Frame(master=window)
    separator5 = ttk.Separator(frame_border, orient='horizontal')
    separator5.pack(fill='x', pady=2)
    tk.Label(frame_border, text = "Open Border Extended View (Fast PC):", width=34).pack(side = tk.TOP, ipady = 1)
    tk.Radiobutton(frame_border, text = "Off", variable = ext_border, value = "0").pack(side = tk.LEFT, ipadx = 1)
    tk.Radiobutton(frame_border, text = "1", variable = ext_border, value = "1").pack(side = tk.LEFT, ipadx = 1)
    tk.Radiobutton(frame_border, text = "2", variable = ext_border, value = "2").pack(side = tk.LEFT, ipadx = 1)
    tk.Radiobutton(frame_border, text = "3", variable = ext_border, value = "3").pack(side = tk.LEFT, ipadx = 1)
    tk.Radiobutton(frame_border, text = "Infinite", variable = ext_border, value = "100").pack(side = tk.LEFT, ipadx = 1)

    frame.pack(side=tk.TOP, expand=True, padx=5, pady=2)
    frame_caveList.pack(side=tk.TOP, expand=True, padx=5, pady=2)
    frame_radiobtns.pack(side=tk.TOP, expand=True, padx=5, pady=2)
    start_cave_frame.pack(side=tk.TOP, expand=True, padx=5, pady=2)
    frame_optimize.pack(side=tk.TOP, expand=True, padx=5, pady=2)
    frame_border.pack(expand=True, padx=5, pady=2)
    frame_scale.pack(expand=True, padx=5, pady=2)

    frame_buttons = tk.Frame(master=window)
    tk.Button(master=frame_buttons, text="Start", command=lambda: start_game(folders_cbbox, cave_listbox, game_mode.get(), target_60fps.get(), synth_sounds.get(), game_scale.get(), game_scale.get() == "F", optimize_perf.get(), ext_border.get())).grid(row=0, column=0)
    tk.Button(master=frame_buttons, text="Editor", command=lambda: start_editor(game_mode.get() == "1", folders_cbbox, cave_listbox, game_mode.get(), target_60fps.get(), synth_sounds.get(), game_scale.get(), game_scale.get() == "F", optimize_perf.get(), ext_border.get())).grid(row=0, column=1)
    tk.Button(master=frame_buttons, text="Define Keys", command=lambda: define_keys()).grid(row=0, column=2)
    tk.Button(master=frame_buttons, text="Quit", command=lambda: quit_launcher(folders_cbbox, cave_listbox, game_mode.get(), target_60fps.get(), synth_sounds.get(), game_scale.get(), game_scale.get() == "F", optimize_perf.get(), ext_border.get())).grid(row=0, column=3)
    separator6 = ttk.Separator(window, orient='horizontal')
    separator6.pack(fill='x', pady=2)
    frame_buttons.pack(side=tk.BOTTOM, expand=True, padx=5, pady=5)
    # --- TK interface ---
    
    folder_list = get_folder_list()
    folders_cbbox["values"] = folder_list
    folders_cbbox.current(0)

    update_cavelist(None)

    ini_folder_name, ini_cave_name, ini_game_mode, ini_target_60fps, ini_synth_sounds, ini_game_scale, ini_optimize_level, ini_ext_border = load_settings()

    game_mode.set(ini_game_mode)
    target_60fps.set(ini_target_60fps)
    synth_sounds.set(ini_synth_sounds)
    game_scale.set(ini_game_scale)
    optimize_perf.set(ini_optimize_level)
    ext_border.set(ini_ext_border)
    
    if ini_folder_name == "":
        ini_folder_name = DEFAULT_FOLDER
    folders_cbbox.set(ini_folder_name)
    update_cavelist(ini_folder_name)
    for cave_id in range(cave_listbox.size()):
        if cave_listbox.get(cave_id) == ini_cave_name.strip():
            cave_listbox.selection_clear(0, cave_listbox.size())
            cave_listbox.selection_set(cave_id)
            cave_listbox.activate(cave_id)
            cave_listbox.see(cave_id)
            break
                    
    window.mainloop()

if __name__ == '__main__':
    # Check to see if all the dependencies are satisfied.
    error = False
    no_pil = False
    no_synthplayer = False
    no_audio = False
    
    try:
        import tkinter
    except ImportError:
        print("Missing Python Library: the 'tkinter' Python library is required.")
        raise SystemExit
    
    try:
        from PIL import Image
    except ImportError:
        error = no_pil = True
    try:
        import synthplayer
    except ImportError:
        error = no_synthplayer = False
    try:
        import miniaudio
    except ImportError:
        try:
            import sounddevice
        except ImportError:
            try:
                import soundcard
            except ImportError:
                error = no_audio = True
    
    if error:
        import tkinter
        import tkinter.messagebox
        r = tkinter.Tk()
        r.withdraw()
        if no_pil:
            tkinter.messagebox.showerror("Missing Python Library", "The 'pillow' or 'pil' Python library is required.")
        if no_synthplayer:
            tkinter.messagebox.showerror("Missing Python Library", "The 'synthplayer' Python library is required.")
        if no_audio:
            tkinter.messagebox.showerror("Missing Python Library", "The 'miniaudio', 'sounddevice', or 'soundcard' Python library is required.")
        raise SystemExit

    # Display help if requested
    if "-h" in sys.argv or "--help" in sys.argv:
        python_executable = sys.executable
        run_params = f"{python_executable} -m bouldercaves --help"
        os.system(run_params)
        exit(0)
        
    # Launch the main interface
    run()