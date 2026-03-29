"""Ortho4XP configuration window."""

import ast
import logging
import os
from math import ceil

import tkinter as tk
import tkinter.ttk as ttk
from tkinter import E, N, S, W, filedialog, messagebox

import O4_Cfg_Vars as CFG
import O4_DEM_Utils as DEM
import O4_File_Names as FNAMES
import O4_Imagery_Utils as IMG
import O4_OSM_Utils as OSM
import O4_Overlay_Utils as OVL
import O4_Tile_Utils as TILE
import O4_UI_Utils as UI
import O4_Vector_Map as VMAP
from O4_Cfg_Vars import (
    cfg_app_vars,
    cfg_global_tile_vars,
    cfg_tile_vars,
    cfg_vars,
    global_prefix,
    gui_app_vars_long,
    gui_app_vars_short,
    list_app_vars,
    list_cfg_vars,
    list_dsf_vars,
    list_global_dsf_vars,
    list_global_mask_vars,
    list_global_mesh_vars,
    list_global_tile_vars,
    list_global_vector_vars,
    list_mask_vars,
    list_mesh_vars,
    list_tile_vars,
    list_vector_vars,
)

_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.INFO)
handler = logging.StreamHandler()
_LOGGER.addHandler(handler)

global_cfg_file = FNAMES.resource_path("Ortho4XP.cfg")
global_cfg_bak_file = FNAMES.resource_path("Ortho4XP.cfg.bak")


def set_global_variables(var: str, value: str) -> None:
    """
    Set global Python variables for the application.
    
    :param str var: variable name
    :param str value: value for variable
    :returns: None
    """
    # There are no global_* variables for the app config settings so skip them
    if var.startswith(global_prefix):
        var_without_global = var[len(global_prefix):]
        if var_without_global in cfg_app_vars:
            return
    target = (
        cfg_vars[var]["module"] + "." + var
        if "module" in cfg_vars[var]
        else "globals()['" + var + "']"
        )
    if cfg_vars[var]["type"] in (bool, list):
        cmd = target + "=" + value
    else:
        cmd = target + "=cfg_vars['" + var + "']['type'](value)"
    exec(cmd)

def config_compatibility(value) -> str:
    """
    Check for compatibility with config files from version <= 1.20.
    
    :param str value: value to check
    :returns: value in format based on cfg_vars
    :return type: str
    """
    if value and value[0] in ('"', "'"):
        value = value[1:]
    if value and value[-1] in ('"', "'"):
        value = value[:-1]
    return value

################################################################################
# Initialization to default values
# Some variables are set using simply their name
# Others are set using the module name and the variable name because
# they are defined in a different module and overriden when the config is loaded (below)
# hence the reason this module is loaded last in O4_GUI_Utils.py
for var in cfg_vars:
    target = (
        cfg_vars[var]["module"] + "." + var
        if "module" in cfg_vars[var]
        else var
    )
    exec(target + "=cfg_vars['" + var + "']['default']")

################################################################################
# Update from Global Ortho4XP.cfg
try:
    f = open(global_cfg_file, "r")
    for line in f.readlines():
        line = line.strip()
        if not line:
            continue
        if line[0] == "#":
            continue
        try:
            (var, value) = line.split("=")
            value = config_compatibility(value)
            # Set all tile and app config variables
            set_global_variables(var, value)
            # Set all global tile config variables
            var = global_prefix + var
            set_global_variables(var, value)
        except:
            UI.lvprint(1, "Global config file contains an invalid line:", line)
            pass
    f.close()
except FileNotFoundError:
    # Create a new global config file using default values
    with open(global_cfg_file, "w") as file:
        for var, value in cfg_global_tile_vars.items():
            # Remove global_ prefix from cfg_global_tile_vars since that's not
            # how they are stored in the global config file
            _var = var.replace(global_prefix, "")
            file.write(_var + "=" + str(value["default"]) + "\n")
        for var, value in cfg_app_vars.items():
            file.write(var + "=" + str(value["default"]) + "\n")
    _LOGGER.info("No global config file found. New config created using defaults.")
except Exception as e:
    _LOGGER.error("Error accessing global config file: %s", e)


################################################################################
class Tile:
    """Class for building tiles."""
    def __init__(self, lat, lon, custom_build_dir):

        self.lat = lat
        self.lon = lon
        self.custom_build_dir = custom_build_dir
        self.grouped = (
            True
            if custom_build_dir and not custom_build_dir.endswith(("/", "\\"))
            else False
        )
        self.build_dir = FNAMES.build_dir(lat, lon, custom_build_dir)
        self.dem = None
        for var in list_tile_vars:
            exec("self." + var + "=" + var)

    def make_dirs(self):
        if os.path.isdir(self.build_dir):
            if not os.access(self.build_dir, os.W_OK):
                UI.vprint(
                    0,
                    "OS error: Tile directory",
                    self.build_dir,
                    " is write protected.",
                )
                raise Exception
        else:
            try:
                os.makedirs(self.build_dir)
            except:
                UI.vprint(
                    0,
                    "OS error: Cannot create tile directory",
                    self.build_dir,
                    " check file permissions.",
                )
                raise Exception

    def read_from_config(self, config_file=None, use_global=False):
        """
        Read tile config from config file and update class variables.

        :params str config_file: path to config file; unknown use case
        :params bool use_global: force use of global config file
        
        :returns: 1 if successful, 0 if not
        :return type: int
        """
        if not config_file:
            config_file = os.path.join(
                self.build_dir,
                "Ortho4XP_" + FNAMES.short_latlon(self.lat, self.lon) + ".cfg",
            )
            if not os.path.isfile(config_file) or use_global:
                config_file = global_cfg_file

                if not os.path.isfile(config_file):
                    
                    UI.lvprint(
                        0,
                        "CFG error: No tile or global config file found.",
                        FNAMES.short_latlon(self.lat, self.lon),
                    )
                    return 0
        try:
            f = open(config_file, "r")
            for line in f.readlines():
                line = line.strip()
                if not line:
                    continue
                if line[0] == "#":
                    continue
                try:
                    (var, value) = line.split("=")
                    # compatibility with config files from version <= 1.20
                    value = config_compatibility(value)
                    if cfg_vars[var]["type"] in (bool, list):
                        cmd = "self." + var + "=" + value
                    else:
                        cmd = (
                            "self."
                            + var
                            + "=cfg_vars['"
                            + var
                            + "']['type'](value)"
                        )
                    exec(cmd)
                except Exception as e:
                    # compatibility with zone_list config files from
                    # version <= 1.20
                    if "zone_list.append" in line:
                        try:
                            exec("self." + line)
                        except:
                            pass
                    else:
                        UI.vprint(2, e)
                        pass
            f.close()
            return 1
        except:
            UI.lvprint(
                0,
                "CFG error: Could not read config file for tile",
                FNAMES.short_latlon(self.lat, self.lon),
            )
            return 0

    def write_to_config(self, config_file = None):
        """
        Create tile config file from class variables.

        :params str config_file: path to config file; unknown use case
        
        :returns: 1 if successful, 0 if not
        :return type: int
        """
        if not config_file:
            config_file = os.path.join(
                self.build_dir,
                "Ortho4XP_" + FNAMES.short_latlon(self.lat, self.lon) + ".cfg",
            )
            config_file_bak = config_file + ".bak"
        try:
            os.replace(config_file, config_file_bak)
        except:
            pass
        try:
            f = open(config_file, "w")
            for var in list_tile_vars:
                tile_zones = []
                lat = self.lat
                lon = self.lon
                if lat < 0:
                    lat = lat + 1
                if lon < 0:
                    lon = lon + 1
                for zone in globals()["zone_list"]:
                    _zone_list = [int(coord) for coord in zone[0]]
                    _zone_list = set(_zone_list)
                    if lat in _zone_list and lon in _zone_list:
                        tile_zones.append(zone)
                        _LOGGER.debug("Zones in tile found: %s", tile_zones)
                if var == "zone_list":
                    f.write(var + "=" + str(tile_zones) + "\n")
                else:
                    f.write(var + "=" + str(eval("self." + var)) + "\n")
            f.close()
            return 1
        except Exception as e:
            UI.vprint(2, e)
            UI.lvprint(
                0,
                "CFG error: Could not write config file for tile",
                FNAMES.short_latlon(self.lat, self.lon),
            )
            return 0


################################################################################

################################################################################
class Ortho4XP_Config(tk.Toplevel):
    """Ortho4XP configuration window."""
    def __init__(self, parent):

        tk.Toplevel.__init__(self)
        self.option_add("*Font", "TkFixedFont")
        self.title("Ortho4XP Config")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        if self.winfo_screenheight() >= 1024:
            self.pady = 5
        else:
            self.pady = 1

        self.folder_icon = tk.PhotoImage(
            file=os.path.join(FNAMES.Utils_dir, "Folder.gif")
        )
        # Ortho4XP main window reference
        self.parent = parent

        # Catch window close using operating system close button
        self.protocol("WM_DELETE_WINDOW", self.close_window)

        # Create a notebook which provides a tabbed interface
        self.notebook = ttk.Notebook(self)
        self.notebook.grid(row=0, column=0, sticky=N + S + W + E)
        # Fixes issue where sometimes tab content is not displayed until mouse is moved
        self.notebook.bind('<<NotebookTabChanged>>', lambda event: self.update_idletasks())

        # Create frames for each tab
        self.tile_config_frame = tk.Frame(self.notebook, bg="light green")
        self.global_config_frame = tk.Frame(self.notebook, bg="light green")
        self.app_config_frame = tk.Frame(self.notebook, bg="light green")

        # Add frames to the notebook
        self.notebook.add(self.tile_config_frame, text="Tile Config")
        self.notebook.add(self.global_config_frame, text="Global Config")
        self.notebook.add(self.app_config_frame, text="Application Config")

        # Initialize Tkinter objects
        self.v_ = {}
        for item in cfg_vars:
            self.v_[item] = tk.StringVar()

        self.tile_cfg_msg = tk.StringVar()

        # Set values for Tkinter objects for GUI display
        self.v_["default_website"] = self.parent.default_website
        self.v_["default_zl"] = self.parent.default_zl
        self.load_interface_from_variables()

        # Initialize content for each tab
        self.tile_config(self.tile_config_frame)
        self.global_config(self.global_config_frame)
        self.app_config(self.app_config_frame)

        self.tile_cfg_status()

    def tile_cfg_status(self, *args) -> None:
        """Update the tile configuration status message and widget states."""
        if self.parent.tile_cfg_exists.get():
            self.tile_cfg_msg.set(
                f"Tile configuration loaded for " \
                f"{self.parent.lat.get()} {self.parent.lon.get()}"
            )
            state = "normal"
            for _, value in self.tile_entry_.items():
                value.config(state=state)

            self.btn_tile_dem.config(state=state)
            self.btn_reset_tile_cfg.config(state=state)
            self.btn_restore_tile_cfg.config(state=state)
            self.btn_load_tile_cfg.config(state=state)
            self.btn_write_tile_cfg.config(state=state)
        else:
            self.tile_cfg_msg.set(
                f"No tile configuration for " \
                f"{self.parent.lat.get()}{self.parent.lon.get()}. " \
                f"Using global configuration settings."
            )
            state = "disabled"
            for _, value in self.tile_entry_.items():                
                value.config(state=state)

            self.btn_tile_dem.config(state=state)
            self.btn_reset_tile_cfg.config(state=state)
            self.btn_restore_tile_cfg.config(state=state)
            self.btn_load_tile_cfg.config(state=state)

    def tile_config(self, frame: tk.Frame) -> None:
        """Tile configuration section."""
        # Allow base frame to expand with window resize
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        main_frame = tk.Frame(frame, border=4, bg="light green")
        frame_status = tk.Frame(main_frame, border=0, padx=5, pady=0, bg="light green")
        frame_cfg = tk.Frame(main_frame, border=0, padx=5, pady=0, bg="light green")
        frame_dem = tk.Frame(frame_cfg, border=0, padx=0, pady=self.pady, bg="light green")
        frame_lastbtn = tk.Frame(main_frame, border=0, padx=5, pady=self.pady, bg="light green")
        # Allow widgets to shrink and expand with window resize
        frame_status.columnconfigure(0, weight=0)
        frame_status.rowconfigure(0, weight=0)
        for j in range(8):
            frame_cfg.columnconfigure(j, weight=1)

        frame_cfg.rowconfigure(0, weight=1)

        for j in range(6):
            frame_lastbtn.columnconfigure(j, weight=1)

        frame_lastbtn.rowconfigure(0, weight=1)

        main_frame.grid(row=0, column=0, sticky=N + S + W + E)
        frame_status.grid(row=0, column=0, pady=10, sticky=N + S + E + W)
        frame_cfg.grid(row=1, column=0, pady=10, sticky=N + S + E + W)
        frame_lastbtn.grid(row=2, column=0, pady=10, sticky=S + E + W)
        # Add a row with weight 1 to push frame_lastbtn to the bottom with window resize
        main_frame.rowconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=0)
        main_frame.columnconfigure(0, weight=1)

        self.tile_entry_ = {}

        col = 0
        next_row = 0

        tk.Label(
            frame_status,
            textvariable=self.tile_cfg_msg,   
            bg="light green",
            fg="black",
            font="TKFixedFont 15",
        ).grid(row=0, column=0, pady=0, sticky=N + S + W + E)

        for (title, sub_list) in (
            ("Vector data", list_vector_vars),
            ("Mesh", list_mesh_vars),
            ("Masks", list_mask_vars),
            ("DSF/Imagery", list_dsf_vars),
        ):
            tk.Label(
                frame_cfg,
                text=title,
                bg="light green",
                anchor=W,
                font="TKFixedFont 15",
            ).grid(
                row=1,
                column=col,
                columnspan=2,
                pady=(0, 10),
                sticky=N + S + E + W,
            )
            row = 2
            for item in sub_list:
                text = (
                    item
                    if "short_name" not in cfg_tile_vars[item]
                    else cfg_tile_vars[item]["short_name"]
                )
                ttk.Button(
                    frame_cfg,
                    text=text,
                    takefocus=False,
                    command=lambda item=item: self.popup(
                        item, cfg_tile_vars[item]["hint"]
                    ),
                ).grid(
                    row=row, column=col, padx=2, pady=2, sticky=E + W + N + S
                )
                if cfg_tile_vars[item]["type"] == bool or "values" in cfg_tile_vars[item]:
                    values = (
                        [True, False]
                        if cfg_tile_vars[item]["type"] == bool
                        else [str(x) for x in cfg_tile_vars[item]["values"]]
                    )
                    self.tile_entry_[item] = ttk.Combobox(
                        frame_cfg,
                        values=values,
                        textvariable=self.v_[item],
                        width=6,
                        state="readonly",
                        style="O4.TCombobox",
                    )
                else:
                    self.tile_entry_[item] = ttk.Entry(
                        frame_cfg, textvariable=self.v_[item], width=7
                    )
                self.tile_entry_[item].grid(
                    row=row,
                    column=col + 1,
                    padx=(0, 20),
                    pady=2,
                    sticky=N + S + W,
                )
                row += 1
            next_row = max(next_row, row)
            col += 2
        row = next_row

        frame_dem.grid(
            row=row, column=0, columnspan=6, sticky=N + S + W + E
        )

        item = "custom_dem"

        ttk.Button(
            frame_dem,
            text=item,
            takefocus=False,
            command=lambda item=item: self.popup(item, cfg_tile_vars[item]["hint"]),
        ).grid(row=0, column=0, padx=2, pady=2, sticky=E + W)

        values = DEM.available_sources[1::2]

        self.tile_entry_[item] = ttk.Combobox(
            frame_dem,
            values=values,
            textvariable=self.v_[item],
            width=80,
            style="O4.TCombobox",
        )
        self.tile_entry_[item].grid(
            row=0, column=1, padx=(2, 0), pady=8, sticky=N + S + W + E
        )

        self.btn_tile_dem = ttk.Button(
            frame_dem,
            image=self.folder_icon,
            command=lambda: self.choose_dem(),
            style="Flat.TButton",
        )
        self.btn_tile_dem.grid(row=0, column=2, padx=2, pady=0, sticky=W)
        self.btn_tile_dem.bind("<Shift-ButtonPress-1>", lambda event: self.add_dem())

        item = "fill_nodata"

        ttk.Button(
            frame_cfg,
            text=item,
            takefocus=False,
            command=lambda item=item: self.popup(item, cfg_tile_vars[item]["hint"]),
        ).grid(row=row, column=6, padx=2, pady=2, sticky=E + W)

        values = [True, False]

        self.tile_entry_[item] = ttk.Combobox(
            frame_cfg,
            values=values,
            textvariable=self.v_[item],
            width=6,
            state="readonly",
            style="O4.TCombobox",
        )
        self.tile_entry_[item].grid(row=row, column=7, padx=2, pady=2, sticky=W)
        row += 1

        # Bottom row buttons
        self.btn_reset_tile_cfg = ttk.Button(
            frame_lastbtn,
            text="Reset to Global",
            command=self.reset_tile_cfg,
        )
        self.btn_reset_tile_cfg.grid(
            row=0, column=1, padx=5, pady=self.pady, sticky=N + S + E + W
        )

        self.btn_restore_tile_cfg = ttk.Button(
            frame_lastbtn,
            text="Load Backup Cfg",
            command=self.load_backup_tile_cfg,
        )
        self.btn_restore_tile_cfg.grid(
            row=0, column=2, padx=5, pady=self.pady, sticky=N + S + E + W
        )

        self.btn_load_tile_cfg = ttk.Button(
            frame_lastbtn,
            text="Load Tile Cfg ",
            command=self.load_tile_cfg,
        )
        self.btn_load_tile_cfg.grid(
            row=0, column=3, padx=5, pady=self.pady, sticky=N + S + E + W
        )

        self.btn_write_tile_cfg = ttk.Button(
            frame_lastbtn,
            text="Save Tile Config",
            command=self.write_tile_cfg,
        )
        self.btn_write_tile_cfg.grid(
            row=0, column=4, padx=5, pady=self.pady, sticky=N + S + E + W
        )

        self.btn_exit =ttk.Button(
            frame_lastbtn, text="Exit", command=self.close_window
        )
        self.btn_exit.grid(
            row=0, column=5, padx=5, pady=self.pady, sticky=N + S + E + W
        )

    def global_config(self, frame: tk.Frame) -> None:
        """Global tile configuration frame."""
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        main_frame = tk.Frame(frame, border=4, bg="light green")
        frame_cfg = tk.Frame(main_frame, border=0, padx=5, pady=self.pady, bg="light green")
        frame_dem = tk.Frame(frame_cfg, border=0, padx=0, pady=self.pady, bg="light green")
        frame_lastbtn = tk.Frame(main_frame, border=0, padx=5, pady=self.pady, bg="light green")

        for j in range(8):
            frame_cfg.columnconfigure(j, weight=1)

        frame_cfg.rowconfigure(0, weight=1)

        for j in range(6):
            frame_lastbtn.columnconfigure(j, weight=1)

        frame_lastbtn.rowconfigure(0, weight=1)

        main_frame.grid(row=0, column=0, sticky=N + S + W + E)
        frame_cfg.grid(row=0, column=0, pady=10, sticky=N + S + E + W)
        frame_lastbtn.grid(row=1, column=0, pady=10, sticky=S + E + W)

        main_frame.rowconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=0)
        main_frame.columnconfigure(0, weight=1)

        self.global_entry_ = {}

        col = 0
        next_row = 0

        for (title, sub_list) in (
            ("Vector data", list_global_vector_vars),
            ("Mesh", list_global_mesh_vars),
            ("Masks", list_global_mask_vars),
            ("DSF/Imagery", list_global_dsf_vars),
        ):
            tk.Label(
                frame_cfg,
                text=title,
                bg="light green",
                anchor=W,
                font="TKFixedFont 15",
            ).grid(
                row=0,
                column=col,
                columnspan=2,
                pady=(0, 10),
                sticky=N + S + E + W,
            )
            row = 1
            for item in sub_list:
                text = (
                    item
                    if "short_name" not in cfg_global_tile_vars[item]
                    else cfg_global_tile_vars[item]["short_name"]
                )
                text = text.replace(global_prefix, "")
                ttk.Button(
                    frame_cfg,
                    text=text,
                    takefocus=False,
                    command=lambda item=item: self.popup(
                        item, cfg_global_tile_vars[item]["hint"]
                    ),
                ).grid(
                    row=row, column=col, padx=2, pady=2, sticky=E + W + N + S
                )
                if cfg_global_tile_vars[item]["type"] == bool or "values" in cfg_global_tile_vars[item]:
                    values = (
                        [True, False]
                        if cfg_global_tile_vars[item]["type"] == bool
                        else [str(x) for x in cfg_global_tile_vars[item]["values"]]
                    )
                    self.global_entry_[item] = ttk.Combobox(
                        frame_cfg,
                        values=values,
                        textvariable=self.v_[item],
                        width=6,
                        state="readonly",
                        style="O4.TCombobox",
                    )
                else:
                    self.global_entry_[item] = ttk.Entry(
                        frame_cfg, textvariable=self.v_[item], width=7
                    )
                self.global_entry_[item].grid(
                    row=row,
                    column=col + 1,
                    padx=(0, 20),
                    pady=2,
                    sticky=N + S + W,
                )
                row += 1
            next_row = max(next_row, row)
            col += 2

        row = next_row

        frame_dem.grid(
            row=row, column=0, columnspan=6, sticky=N + S + W + E
        )

        text = "custom_dem"
        item = "global_custom_dem"

        ttk.Button(
            frame_dem,
            text=text,
            takefocus=False,
            command=lambda item=item: self.popup(item, cfg_global_tile_vars[item]["hint"]),
        ).grid(row=0, column=0, padx=2, pady=2, sticky=E + W)

        values = DEM.available_sources[1::2]
        self.global_entry_[item] = ttk.Combobox(
            frame_dem,
            values=values,
            textvariable=self.v_[item],
            width=80,
            style="O4.TCombobox",
        )
        self.global_entry_[item].grid(
            row=0, column=1, padx=(2, 0), pady=8, sticky=N + S + W + E
        )

        self.btn_global_dem = ttk.Button(
            frame_dem,
            image=self.folder_icon,
            command=lambda: self.choose_dem(global_config=True),
            style="Flat.TButton",
        )
        self.btn_global_dem.grid(row=0, column=2, padx=2, pady=0, sticky=W)
        self.btn_global_dem.bind("<Shift-ButtonPress-1>", lambda event: self.add_dem(global_config=True))

        text = "fill_nodata"
        item = "global_fill_nodata"

        ttk.Button(
            frame_cfg,
            text=text,
            takefocus=False,
            command=lambda item=item: self.popup(item, cfg_global_tile_vars[item]["hint"]),
        ).grid(row=row, column=6, padx=2, pady=2, sticky=E + W)

        values = [True, False]

        self.global_entry_[item] = ttk.Combobox(
            frame_cfg,
            values=values,
            textvariable=self.v_[item],
            width=6,
            state="readonly",
            style="O4.TCombobox",
        )
        self.global_entry_[item].grid(row=row, column=7, padx=2, pady=2, sticky=W)
        row += 1

        # Bottom row buttons
        self.btn_reset_global_cfg = ttk.Button(
            frame_lastbtn,
            text="Reset to Defaults",
            command=self.reset_global_cfg,
        )
        self.btn_reset_global_cfg.grid(
            row=0, column=2, padx=5, pady=self.pady, sticky=N + S + E + W
        )

        self.btn_load_backup_global_tile_cfg = ttk.Button(
            frame_lastbtn,
            text="Load Backup Cfg",
            command=self.load_backup_global_tile_cfg,
        )
        self.btn_load_backup_global_tile_cfg.grid(
            row=0, column=3, padx=5, pady=self.pady, sticky=N + S + E + W
        )

        self.btn_save_global_cfg = ttk.Button(
            frame_lastbtn,
            text="Save Global Config",
            command=self.write_global_cfg,
        )
        self.btn_save_global_cfg.grid(
            row=0, column=4, padx=5, pady=self.pady, sticky=N + S + E + W
        )

        self.btn_exit =ttk.Button(
            frame_lastbtn, text="Exit", command=self.close_window
        )
        self.btn_exit.grid(
            row=0, column=5, padx=5, pady=self.pady, sticky=N + S + E + W
        )

    def app_config(self, frame: tk.Frame) -> None:
        """Application configuration frame."""
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        main_frame = tk.Frame(frame, border=4, bg="light green")
        frame_cfg = tk.Frame(main_frame, border=0, padx=5, pady=self.pady, bg="light green")
        frame_lastbtn = tk.Frame(main_frame, border=0, padx=5, pady=self.pady, bg="light green")

        for j in range(8):
            frame_cfg.columnconfigure(j, weight=1)

        frame_cfg.rowconfigure(0, weight=1)

        for j in range(6):
            frame_lastbtn.columnconfigure(j, weight=1)

        frame_lastbtn.rowconfigure(0, weight=1)

        main_frame.grid(row=0, column=0, sticky=N + S + W + E)
        frame_cfg.grid(row=0, column=0, pady=10, sticky=N + S + E + W)
        frame_lastbtn.grid(row=1, column=0, pady=10, sticky=S + E + W)

        main_frame.rowconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=0)
        main_frame.columnconfigure(0, weight=1)

        self.app_entry_ = {}

        row = 2
        col = 0

        l = ceil((len(gui_app_vars_short)) / 4)
        this_row = row
        j = 0

        for item in gui_app_vars_short:
            col = 2 * (j // l)
            row = this_row + j % l
            text = (
                item
                if "short_name" not in cfg_app_vars[item]
                else cfg_app_vars[item]["short_name"]
            )
            ttk.Button(
                frame_cfg,
                text=text,
                takefocus=False,
                command=lambda item=item: self.popup(
                    item, cfg_app_vars[item]["hint"]
                ),
            ).grid(row=row, column=col, padx=2, pady=2, sticky=E + W + N + S)
            if cfg_app_vars[item]["type"] == bool or "values" in cfg_app_vars[item]:
                values = (
                    ["True", "False"]
                    if cfg_app_vars[item]["type"] == bool
                    else [str(x) for x in cfg_app_vars[item]["values"]]
                )
                self.app_entry_[item] = ttk.Combobox(
                    frame_cfg,
                    values=values,
                    textvariable=self.v_[item],
                    width=6,
                    state="readonly",
                    style="O4.TCombobox",
                )
            else:
                self.app_entry_[item] = tk.Entry(
                    frame_cfg,
                    textvariable=self.v_[item],
                    width=7,
                    bg="white",
                    fg="blue",
                )
            self.app_entry_[item].grid(
                row=row, column=col + 1, padx=(0, 20), pady=2, sticky=N + S + W
            )
            j += 1

        row = this_row + l

        for item in gui_app_vars_long:
            ttk.Button(
                frame_cfg,
                text=item,
                takefocus=False,
                command=lambda item=item: self.popup(
                    item, cfg_vars[item]["hint"]
                ),
            ).grid(row=row, column=0, padx=2, pady=2, sticky=E + W + N + S)

            self.app_entry_[item] = tk.Entry(
                frame_cfg,
                textvariable=self.v_[item],
                bg="white",
                fg="blue",
            )
            self.app_entry_[item].grid(
                row=row,
                column=1,
                columnspan=5,
                padx=(2, 0),
                pady=2,
                sticky=N + S + E + W,
            )

            ttk.Button(
                frame_cfg,
                image=self.folder_icon,
                command=lambda item=item: self.choose_dir(item),
                style="Flat.TButton",
            ).grid(row=row, column=6, padx=2, pady=0, sticky=N + S + W)
            row += 1

        # Bottom row buttons
        self.btn_reload_app_cfg = ttk.Button(
            frame_lastbtn,
            text="Reset to Defaults",
            command=self.reset_app_cfg,
        )
        self.btn_reload_app_cfg.grid(
            row=0, column=2, padx=5, pady=self.pady, sticky=N + S + E + W
        )

        self.btn_load_backup_app_cfg = ttk.Button(
            frame_lastbtn,
            text="Load Backup Cfg",
            command=self.load_backup_app_cfg,
        )
        self.btn_load_backup_app_cfg.grid(
            row=0, column=3, padx=5, pady=self.pady, sticky=N + S + E + W
        )

        self.btn_save_app_cfg = ttk.Button(
            frame_lastbtn,
            text="Save App Config",
            command=self.write_app_cfg,
        )
        self.btn_save_app_cfg.grid(
            row=0, column=4, padx=5, pady=self.pady, sticky=N + S + E + W
        )

        self.btn_exit = ttk.Button(
            frame_lastbtn, text="Exit", command=self.close_window
        )
        self.btn_exit.grid(
            row=0, column=5, padx=5, pady=self.pady, sticky=N + S + E + W
        )

    def load_interface_from_variables(self) -> None:
        """Load the configuration interface values for all tabs."""
        for var in list_cfg_vars:
            target = (
                cfg_vars[var]["module"] + "." + var
                if "module" in cfg_vars[var]
                else "globals()['" + var + "']"
            )
            self.v_[var].set(str(eval(target)))

    def reset_tile_cfg(self) -> None:
        """Reset tile settings to global tile settings."""
        try:
            (lat, lon) = self.parent.get_lat_lon()
        except:
            return 0
        # Find all the zones for the active tile
        tile_zones = []
        if lat < 0:
            lat = lat + 1
        if lon < 0:
            lon = lon + 1
        for zone in globals()["zone_list"]:
            _zone_list = [int(coord) for coord in zone[0]]
            _zone_list = set(_zone_list)
            if lat in _zone_list and lon in _zone_list:
                tile_zones.append(zone)
        if tile_zones:
            response = messagebox.askyesnocancel("Confirmation", "Save tile zones?", parent=self)
            if response is None:
                return
            # Remove the current tile zones from global zone_list
            if response is False:
                # Only remove the active tiles from the global zone_list
                globals()["zone_list"] = [
                    zone for zone in globals()["zone_list"] if zone not in tile_zones
                ]
        for var in list_tile_vars:
            # Skip zone_list in list_tile_vars since zone_list is not in global config
            if var == "zone_list":
                continue
            # default_website is not stored in global config
            if var == "default_website":
                self.v_["zone_list"].set(self.parent.default_website.get())
                continue
            # default_zl is not stored in global config
            if var == "default_zl":
                self.v_["zone_list"].set(self.parent.default_zl.get())
                continue
            # Since we're looping through list_tile_vars, we need to prefix the key for getting
            # the value from the global config tab
            _global_var = global_prefix + var
            self.v_[var].set(self.v_[_global_var].get())
        UI.vprint(1, "Tile settings reset to global tile settings.")

    def load_backup_tile_cfg(self) -> None:
        """Load backup tile configuration settings."""
        try:
            (lat, lon) = self.parent.get_lat_lon()
        except:
            return 0
        custom_build_dir = self.parent.custom_build_dir_entry.get()
        build_dir = FNAMES.build_dir(lat, lon, custom_build_dir)
        try:
            f = open(
                os.path.join(
                    build_dir,
                    "Ortho4XP_" + FNAMES.short_latlon(lat, lon) + ".cfg.bak",
                ),
                "r",
            )
        except FileNotFoundError:
            messagebox.showinfo("Not found", "No backup tile configuration found.")
            return

        for line in f.readlines():
            line = line.strip()
            if not line or line[0] == "#":
                continue
            try:
                (var, value) = line.split("=")
                value = config_compatibility(value)
                self.v_[var].set(value)
            except Exception as e:
                # compatibility with zone_list config files from version <= 1.20
                if "zone_list.append" in line:
                    try:
                        exec(line)
                    except Exception as e:
                        print(e)
                        pass
                else:
                    UI.vprint(2, e)
                    pass
        # Apply changes to update global variables
        self.apply_changes("tile")
        UI.vprint(0, f"Backup configuration loaded for tile at {lat} {lon}")
        f.close()

    def load_tile_cfg(self) -> None:
        """Load tile configuration settings for active tile."""
        zone_list = []
        try:
            (lat, lon) = self.parent.get_lat_lon()
        except:
            return 0
        custom_build_dir = self.parent.custom_build_dir_entry.get()
        build_dir = FNAMES.build_dir(lat, lon, custom_build_dir)
        try:
            f = open(
                os.path.join(
                    build_dir,
                    "Ortho4XP_" + FNAMES.short_latlon(lat, lon) + ".cfg",
                ),
                "r",
            )
        except:
            try:
                f = open(os.path.join(build_dir, "Ortho4XP.cfg"), "r")
            except:
                messagebox.showinfo("Not found", "No tile configuration found.")
                return 0
        for line in f.readlines():
            line = line.strip()
            if not line:
                continue
            if line[0] == "#":
                continue
            try:
                (var, value) = line.split("=")
                value = config_compatibility(value)
                self.v_[var].set(value)
            except Exception as e:
                # compatibility with zone_list config files from version <= 1.20
                if "zone_list.append" in line:
                    try:
                        exec(line)
                    except Exception as e:
                        print(e)
                        pass
                else:
                    UI.vprint(2, e)
                    pass
        if not self.v_["zone_list"].get():
            self.v_["zone_list"].set(str(zone_list))
        self.parent.tile_cfg_exists.set(True)
        # Apply changes to update global variables
        self.apply_changes("tile")
        UI.vprint(0, f"Configuration loaded for tile at {lat} {lon}")
        f.close()

    def write_tile_cfg(self) -> None:
        """Save tile configuration settings for active tile."""
        try:
            (lat, lon) = self.parent.get_lat_lon()
        except:
            return 0
        custom_build_dir = self.parent.custom_build_dir_entry.get()
        build_dir = FNAMES.build_dir(lat, lon, custom_build_dir)
        tile_cfg_file = os.path.join(
            build_dir, "Ortho4XP_" + FNAMES.short_latlon(lat, lon) + ".cfg"
        )
        try:
            os.makedirs(build_dir, exist_ok=True)
        except:
            self.popup("ERROR", "Cannot write into " + str(build_dir))
            return 0
        # Make a backup of the existing tile config file
        if os.path.isfile(tile_cfg_file):
            tile_cfg_file_bak = tile_cfg_file + ".bak"
            try:
                os.replace(tile_cfg_file, tile_cfg_file_bak)
            except:
                pass
        with open(tile_cfg_file, "w") as f:
            # Required for when the config window is left open to make sure
            # we retain any zone modifications
            self.v_["zone_list"].set(str(globals()["zone_list"]))
            # Apply changes to update global variables
            self.apply_changes("tile")
            # Get zones only for the tile
            tile_zones = []
            if lat < 0:
                lat = lat + 1
            if lon < 0:
                lon = lon + 1
            for zone in globals()["zone_list"]:
                _zone_list = [int(coord) for coord in zone[0]]
                _zone_list = set(_zone_list)
                if lat in _zone_list and lon in _zone_list:
                    tile_zones.append(zone)
                    _LOGGER.debug("Zones saved for tile at %s %s: %s", lat, lon, tile_zones)
            for var in list_tile_vars:
                if var == "zone_list":
                    f.write(var + "=" + str(tile_zones) + "\n")
                else:
                    f.write(var + "=" + self.v_[var].get() + "\n")
        self.load_tile_cfg()
        self.tile_cfg_status()
        UI.vprint(
            1,
            f"Configuration saved for tile at {self.parent.lat.get()} {self.parent.lon.get()}",
        )
        return

    def reset_global_cfg(self) -> None:
        """Reset global tile settings to defaults."""
        # This does not reset the default_website and default_zl
        for var in cfg_global_tile_vars:
            # Update GUI Tkinter objects
            self.v_[var].set(str(cfg_global_tile_vars[var]["default"]))

        UI.vprint(1, "Global tile settings reset to defaults.")

    def load_backup_global_tile_cfg(self) -> None:
        """Load backup global tile configuration settings."""
        try:
            with open(global_cfg_bak_file, "r") as f:
                for line in f.readlines():
                    line = line.strip()
                    if not line or line[0] == "#":
                        continue
                    (var, value) = line.split("=")
                    # Ignore list_app_vars
                    if var in list_app_vars:
                        continue
                    var = global_prefix + var
                    value = config_compatibility(value)
                    self.v_[var].set(value)
                # Apply changes to update global variables
                self.apply_changes("tile")
                UI.vprint(0, f"Backup configuration loaded for global tile settings.")
        except FileNotFoundError:
            messagebox.showinfo("Not found", "No backup global configuration found.")
            return

    def write_global_cfg(self):
        """Write global configuration settings to Ortho4XP.cfg."""
        self.apply_changes("global")
        try:
            # Make a copy of the existing global config file
            if (os.path.exists(global_cfg_file)):
                os.replace(global_cfg_file, global_cfg_bak_file)
            # Get current GUI global tile settings as a dict
            # Remove global prefix since the cfg file doesn't use it
            current_config = {
                var.replace(global_prefix, ""): self.v_[var].get()
                for var in list_global_tile_vars
            }
            # Get current GUI app settings and add to the dict
            current_config.update({var: self.v_[var].get() for var in list_app_vars})
            # Get settings in existing config file returned as a dict
            config_file = self.cfg_to_dict(global_cfg_bak_file)
            # Update existing file with current app settings
            config_file.update(current_config)
            # Write to new configuration file
            with open(global_cfg_file, 'w') as file:
                for key, value in config_file.items():
                    file.write(f"{key}={value}\n")
            # Load the tile config since it now exists
            if not self.parent.tile_cfg_exists.get():
                self.parent.load_tile_cfg(
                    int(self.parent.lat.get()), int(self.parent.lon.get())
                )
            UI.vprint(1, "Global tile configuration settings saved.")
        except Exception as e:
            UI.lvprint(1, "Could not write global config.")
            _LOGGER.exception("Could not write global config: %s", e)
        return

    def reset_app_cfg(self) -> None:
        """Reset app settings to defaults."""
        for var in cfg_app_vars:
            # Update GUI Tkinter objects
            self.v_[var].set(str(cfg_app_vars[var]["default"]))
        UI.vprint(1, "Application settings reset to defaults.")

    def load_backup_app_cfg(self) -> None:
        """Load backup app configuration settings."""
        try:
            with open(global_cfg_bak_file, "r") as f:
                for line in f.readlines():
                    line = line.strip()
                    if not line or line[0] == "#":
                        continue
                    (var, value) = line.split("=")
                    # Ignore global tile vars
                    if var in list_global_tile_vars:
                        continue
                    value = config_compatibility(value)
                    self.v_[var].set(value)
                # Apply changes to update global variables
                self.apply_changes("tile")
                UI.vprint(0, f"Backup configuration loaded for application settings.")
        except FileNotFoundError:
            messagebox.showinfo("Not found", "No backup application configuration found.")
            return

    def write_app_cfg(self) -> None:
        """Save application settings to global configuration."""
        # Apply changes first to update global variables
        self.apply_changes("app")

        current_config = {}
        config_file = {}

        # Get current app settings and add to dict
        for var in list_app_vars:
            current_config[var] = self.v_[var].get()
        try:
            if (os.path.exists(global_cfg_file)):
                # Make a backup of the existing global config file
                os.replace(global_cfg_file, global_cfg_bak_file)
                # Get settings in existing config file returned as a dict
                config_file = self.cfg_to_dict(global_cfg_bak_file)
                # Update existing file with current app settings
                config_file.update(current_config)
                # Write to new configuration file
                self.dict_to_cfg(global_cfg_file, config_file)
            else:
                self.dict_to_cfg(global_cfg_file, current_config)

            UI.vprint(1, "Application configuration settings saved.")
        except Exception as e:
            UI.lvprint(1, "Could not write application settings to global config.")
            _LOGGER.exception(
                "Could not write application settings to global config: %s", e
            )
        return

    def apply_changes(self, tab: str) -> None:
        """
        Apply changes to update global variables.

        :param str tab: "tile", "global" or "app" for each tab
        :return: None
        """
        errors = []

        if tab == "global":
            for var in list_global_tile_vars:
                target = "globals()['" + var + "']"
                try:
                    if cfg_global_tile_vars[var]["type"] in (bool, list):
                        value = self.v_[var].get()
                        cmd = target + "=" + value
                    else:
                        value = cfg_global_tile_vars[var]["type"](self.v_[var].get())
                        cmd = (
                            target
                            + "=cfg_global_tile_vars['"
                            + var
                            + "']['type'](self.v_['"
                            + var
                            + "'].get())"
                        )
                    exec(cmd)
                except:
                    exec(
                        target
                        + "=cfg_global_tile_vars['"
                        + var
                        + "']['type'](cfg_global_tile_vars['"
                        + var
                        + "']['default'])"
                    )
                    if tab == "app":
                        self.v_[var].set(str(cfg_global_tile_vars[var]["default"]))
                    errors.append(var)
            if errors:
                error_text = (
                    "The following variables had wrong type\nand were reset " + 
                    "to their default value!\n\n* "
                    + "\n* ".join(errors)
                )
                self.popup("ERROR", error_text)
        else:
            if tab == "tile":
                list_vars = list_tile_vars
                # Make sure existing zones in global zone_list are retained
                # and check for any duplicates before adding new zones
                for zone in ast.literal_eval(self.v_["zone_list"].get()):
                    if zone not in globals()["zone_list"]:
                        globals()["zone_list"].append(zone)
            if tab == "app":
                list_vars = list_app_vars
            for var in list_vars:
                # We don't want to update the global zone_list here
                # since it's already been updated by the save_zone_list in O4_GUI_Utils.py
                # and also by the code above
                if var == "zone_list":
                    continue
                try:
                    target = (
                        cfg_vars[var]["module"] + "." + var
                        if "module" in cfg_vars[var]
                        else "globals()['" + var + "']"
                    )
                    if cfg_vars[var]["type"] in (bool, list):
                        value = self.v_[var].get()
                        cmd = target + "=" + value
                    else:
                        value = cfg_vars[var]["type"](self.v_[var].get())
                        cmd = (
                            target
                            + "=cfg_vars['"
                            + var
                            + "']['type'](self.v_['"
                            + var
                            + "'].get())"
                        )
                    exec(cmd)
                except:
                    target = (
                        cfg_vars[var]["module"] + "." + var
                        if "module" in cfg_vars[var]
                        else "globals()['" + var + "']"
                    )
                    exec(
                        target
                        + "=cfg_vars['"
                        + var
                        + "']['type'](cfg_vars['"
                        + var
                        + "']['default'])"
                    )
                    if tab == "app":
                        self.v_[var].set(str(cfg_vars[var]["default"]))
                    errors.append(var)
            if errors:
                error_text = (
                    "The following variables had wrong type\nand were reset " + 
                    "to their default value!\n\n* "
                    + "\n* ".join(errors)
                )
                self.popup("ERROR", error_text)

    def check_unsaved_changes(self, select_tile=False) -> str:
        """
        Check for unsaved changes and prompt user to save.

        :param bool select_tile: Used with select_tile method in O4_OrthoXP_Earth_Preview class
        :return: Only returns "cancel" if user cancels the save prompt
        :rtype: str
        """
        try:
            (lat, lon) = self.parent.get_lat_lon()
        except Exception as e:
            _LOGGER.exception("Could not get lat/lon coordinates: %s", e)
            return

        custom_build_dir = self.parent.custom_build_dir_entry.get()
        build_dir = FNAMES.build_dir(lat, lon, custom_build_dir)

        unsaved_changes = {"tile": False, "global": False, "application": False}
        # Check Tile Config tab values against values in the tile config file
        try:
            with open(
                os.path.join(
                    build_dir, "Ortho4XP_" + FNAMES.short_latlon(lat, lon) + ".cfg"
                ),
                "r",
            ) as f:
                file_dict = dict(line.strip().split("=") for line in f if line.strip())
                for var in list_tile_vars:
                    # Skip default_website and default_zl since they're not a part of the tab settings
                    if var == "default_website" or var == "default_zl":
                        continue
                    # Skip zone_list since we're only checking config tab values and default_website + default_zl
                    if var == "zone_list":
                        continue
                    tab_value = self.set_value_type(var, self.v_[var].get())
                    if var not in file_dict:
                        UI.lvprint(
                            1,
                            f"Setting {var} is missing from config, setting default value: {tab_value}",
                        )
                    file_value = self.set_value_type(var, file_dict.get(var, tab_value))

                    # Compare tab_value with value in file_dict
                    if file_value != tab_value:
                        _LOGGER.debug(
                            "Unsaved changes in tile config for %s - current value: %s, config file value: %s",
                            var,
                            tab_value,
                            file_value,
                        )
                        unsaved_changes["tile"] = True
                        break
        except FileNotFoundError:
            # Check Tile Config tab values against tile config values in the global config file
            try:
                with open(global_cfg_file, "r") as f:
                    file_dict = dict(
                        line.strip().split("=") for line in f if line.strip()
                    )
                    for var in list_global_tile_vars:
                        # Config file doesn't have global_ prefix so we need to remove it
                        _var = var.replace(global_prefix, "")
                        tab_value = self.set_value_type(_var, self.v_[_var].get())
                        if _var not in file_dict:
                            UI.lvprint(
                                1,
                                f"Setting {_var} is missing from config, setting default value: {tab_value}",
                            )
                        file_value = self.set_value_type(_var, file_dict.get(_var, tab_value))

                        if file_value != tab_value:
                            _LOGGER.debug(
                                "Unsaved changes in global config for %s - current value: %s, config file value: %s",
                                var,
                                tab_value,
                                file_value,
                            )
                            unsaved_changes["tile"] = True
                            break
            except FileNotFoundError:
                pass

        except Exception as e:
            _LOGGER.exception(e)

        if not select_tile:
            # Check Global Config tab values against the global config file
            try:
                with open(global_cfg_file, "r") as f:
                    file_dict = dict(
                        line.strip().split("=") for line in f if line.strip()
                    )
                    for var in list_global_tile_vars:
                        # Config file does not have global_ prefix so we need to remove it
                        _var = var.replace(global_prefix, "")
                        tab_value = self.set_value_type(_var, self.v_[var].get())
                        if _var not in file_dict:
                            UI.lvprint(
                                1,
                                f"Setting {_var} is missing from config, setting default value: {tab_value}",
                            )
                        file_value = self.set_value_type(_var, file_dict.get(_var, tab_value))

                        if file_value != tab_value:
                            _LOGGER.debug(
                                "Unsaved changes in global config for %s - current value: %s, config file value: %s",
                                var,
                                tab_value,
                                file_value,
                            )
                            unsaved_changes["global"] = True
                            break
                    # Check App Config tab values against the global config file
                    for var in list_app_vars:
                        tab_value = self.set_value_type(var, self.v_[var].get())
                        if var not in file_dict:
                            UI.lvprint(
                                1,
                                f"Setting {var} is missing from config, setting default value: {tab_value}",
                            )
                        file_value = self.set_value_type(var, file_dict.get(var, tab_value))

                        if file_value != tab_value:
                            _LOGGER.debug(
                                "Unsaved changes in global config for %s - current value: %s, config file value: %s",
                                var,
                                tab_value,
                                file_value,
                            )
                            unsaved_changes["application"] = True
                            break
            except FileNotFoundError:
                _LOGGER.error("Global configuration file (Ortho4XP.cfg) not found.")
            except Exception as e:
                _LOGGER.exception(e)

        if any(unsaved_changes.values()):
            message = ""
            count = sum(unsaved_changes.values())
            if count == 1:
                key = next(key for key, value in unsaved_changes.items() if value)
                message = f"{key.capitalize()} Config tab has unsaved changes.\n"
            elif count == 2:
                keys = [
                    key.capitalize() for key, value in unsaved_changes.items() if value
                ]
                message = f"{', '.join(keys[:-1])} and {keys[-1]} Config tabs have unsaved changes.\n"
            elif count == 3:
                message = (
                    f"Tile, Global, and Application Config tabs have unsaved changes.\n"
                )
            # Appears to be an issue with macOS and using "Cancel" as sometimes it will present
            # the messagebox twice. Also happens rarely with "Yes/No".
            response = messagebox.askyesnocancel(
                "Unsaved Changes", f"{message}\nSave changes?", parent=self
            )
            if response is None:
                return "cancel"
            elif response:
                self.write_tile_cfg()
                self.write_global_cfg()
                self.write_app_cfg()

    def set_value_type(self, var: str, value) -> float | bool | str | list:
        """
        Return string based on type in cfg_vars except ints which
        will be returned as floats since this is used for comparing values.
        
        :param str value: value to be converted.
        :return: value in type based on cfg_vars
        """
        # Using floats for both int and float since we're going to compare them
        if cfg_vars[var]["type"] == int or cfg_vars[var]["type"] == float:
            return float(value)
        if cfg_vars[var]["type"] == bool:
            return ast.literal_eval(value)
        if cfg_vars[var]["type"] == str:
            return str(value)
        if cfg_vars[var]["type"] == list:
            return ast.literal_eval(value)

    def dict_to_cfg(self, file:str, cfg_dict: dict) -> None:
        """
        Convert dictionary to key=value format and write to file.

        :param str file: path to config file
        :param dict cfg_dict: dictionary to write to file
        :return: None
        """
        with open(file, 'w') as file:
            for key, value in cfg_dict.items():
                file.write(f"{key}={value}\n")

    def cfg_to_dict(self, file: str) -> dict:
        """
        Read config file and return as a dictionary.

        :param str file: path to config file
        :return: dict
        """
        config_dict = {}
        with open(file, 'r') as file:
            for line in file:
                line = line.strip()
                if line and '=' in line:
                    key, value = line.split('=', 1)
                    config_dict[key.strip()] = value.strip()
        return config_dict

    def choose_dem(self, global_config=False):
        tmp = filedialog.askopenfilename(
            parent=self,
            title="Choose DEM file",
            filetypes=[
                ("DEM files", (".tif", ".hgt", ".raw", ".img")),
                ("all files", ".*"),
            ],
        )
        if tmp:
            custom_dem = "global_custom_dem" if global_config else "custom_dem"
            if not self.v_[custom_dem].get():
                self.v_[custom_dem].set(str(tmp))
            else:
                self.v_[custom_dem].set(self.v_[custom_dem].get() + ";" + str(tmp))

    def add_dem(self, global_config=False):
        tmp = filedialog.askopenfilename(
            parent=self,
            title="Choose DEM file",
            filetypes=[
                ("DEM files", (".tif", ".hgt", ".raw", ".img")),
                ("all files", ".*"),
            ],
        )
        if tmp:
            custom_dem = "global_custom_dem" if global_config else "custom_dem"
            if not self.v_[custom_dem].get():
                self.v_[custom_dem].set(str(tmp))
            else:
                self.v_[custom_dem].set(self.v_[custom_dem].get() + ";" + str(tmp))

    def choose_dir(self, item):
        tmp = filedialog.askdirectory(parent=self)
        if tmp:
            self.v_[item].set(str(tmp))

    def close_window(self) -> None:
        """Close the configuration window."""
        result = self.check_unsaved_changes()
        if result == "cancel":
            return
        self.destroy()

    def popup(self, header: str, input_text: str) -> None:
        """
        Popup window for hints.
        
        :param str header: top line of the body of the popup window
        :param str input_text: body of the popup window
        :return: None
        """
        self.popupwindow = tk.Toplevel()
        self.popupwindow.wm_title("Hint!")
        self.popupwindow.configure(background="light gray")

        ttk.Label(
            self.popupwindow, text=header, anchor=W, font=("TkBoldFont", 14), background="light gray"
        ).pack(side="top", fill="x", padx=5, pady=3)
        ttk.Label(
            self.popupwindow, text=input_text, wraplength=600, anchor=W, background="light gray"
        ).pack(side="top", fill="x", padx=5, pady=0)
        ttk.Button(
            self.popupwindow, text="Ok", command=self.popupwindow.destroy
        ).pack(pady=5)
        return
