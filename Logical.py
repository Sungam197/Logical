import sys
import math
import pygame
import json
import os
import tkinter as tk
from tkinter import filedialog
import heapq

pygame.init()
pygame.key.set_repeat(350, 35)

FPS = 60
CLOCK = pygame.time.Clock()


def resource_path(name):
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, name)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), name)

display_info = pygame.display.Info()
screen = pygame.display.set_mode((display_info.current_w, display_info.current_h), pygame.NOFRAME)
WIDTH, HEIGHT = screen.get_size()


def apply_window_branding():
    pygame.display.set_caption("Logical")
    for icon_name in ("logo.ico", "logo.png"):
        try:
            pygame.display.set_icon(pygame.image.load(resource_path(icon_name)))
            break
        except Exception:
            continue


apply_window_branding()

BG = (18, 18, 22)
PANEL = (28, 30, 36)
GRID = (40, 40, 48)
WHITE = (230, 230, 235)
GRAY = (140, 140, 150)
GREEN = (60, 220, 120)
RED = (220, 80, 80)
YELLOW = (240, 220, 120)
BLUE = (90, 160, 255)
ACCENT = (70, 200, 255)
HOVER = (120, 190, 255)
HOVER_PIN = (255, 220, 150)
WIRE_ON = YELLOW
WIRE_OFF = (160, 160, 175)
MCOL_RED = (235, 90, 90)
MCOL_GREEN = (95, 220, 120)
MCOL_BLUE = (95, 155, 240)
MCOLORS = [MCOL_RED, MCOL_GREEN, MCOL_BLUE]
DIALOG_BORDER = (90, 90, 110)
DIALOG_BORDER_SOFT = (110, 110, 130)
TOGGLE_OFF = (90, 90, 110)
TOGGLE_ON = (70, 150, 110)
TOGGLE_KNOB = (230, 230, 235)
SLIDER_TRACK = (80, 80, 95)
SLIDER_KNOB = (170, 190, 230)
BUTTON_NEUTRAL = (80, 80, 100)
BUTTON_ACCENT = (80, 90, 110)
BUTTON_CLOCK = (95, 85, 70)
BUTTON_CLOCK_HOVER = (120, 105, 85)
BUTTON_DANGER = (120, 70, 70)
MENU_TILE = (60, 60, 70)
MENU_TILE_HOVER = (80, 90, 110)
MENU_SPLIT = (110, 110, 125)
MENU_BORDER = (90, 90, 105)

PIN_RADIUS = 8
PIN_HIT = 16
DRAG_THRESHOLD = 6
SHOW_TEXT_MIN = 0.7
SHOW_PINS_MIN = 0.7
NOTE_MAX_W = 240

ANIM_HOVER = 0.2
ANIM_SELECT = 0.18
ANIM_DELETE = 0.18
ANIM_PREVIEW = 0.2
ANIM_SELECT_RECT = 0.2

base_font = pygame.font.SysFont("consolas", 16)
base_small = pygame.font.SysFont("consolas", 14)

GATE_TYPES = [
    "INPUT",
    "BUTTON",
    "CLOCK",
    "DELAY",
    "OUTPUT",
    "BUFFER",
    "NOT",
    "AND",
    "NAND",
    "OR",
    "NOR",
    "XOR",
    "XNOR",
]

TWO_INPUT = {"AND", "NAND", "OR", "NOR", "XOR", "XNOR"}
ONE_INPUT = {"NOT", "OUTPUT", "DELAY", "BUFFER"}
TRADITIONAL_GATES = {"AND", "NAND", "OR", "NOR", "XOR", "XNOR"}

next_id = 1
custom_gate_defs_user = {}
custom_gate_defs_file = {}


def all_custom_gate_defs():
    merged = {}
    merged.update(custom_gate_defs_file)
    merged.update(custom_gate_defs_user)
    return merged


def get_custom_gate_def(custom_key):
    if custom_key in custom_gate_defs_user:
        return custom_gate_defs_user[custom_key]
    if custom_key in custom_gate_defs_file:
        return custom_gate_defs_file[custom_key]
    return None

def new_id():
    global next_id
    nid = next_id
    next_id += 1
    return nid

class Gate:
    def __init__(self, gtype, x, y, custom_key=None):
        self.id = new_id()
        self.type = gtype
        self.x = x
        self.y = y
        self.draw_x = x
        self.draw_y = y
        self.spawn_t = 0.0
        self.custom_key = custom_key
        self.custom_name = "CUSTOM"
        self.custom_w = 80.0
        self.custom_h = 50.0
        self.custom_inputs = []
        self.custom_outputs = []
        self.custom_labels = []
        self.custom_outputs_state = [False]
        self.custom_runtime = {}
        self.custom_locked = False
        self.locked_io = False
        if gtype == "CUSTOM":
            self.apply_custom_definition(custom_key)
        elif gtype in TWO_INPUT:
            self.inputs = [None, None]
        elif gtype == "OUTPUT" and multicolor_outputs:
            self.inputs = [None, None, None]
        elif gtype in ONE_INPUT:
            self.inputs = [None]
        else:
            self.inputs = []
        self.output = False
        self.input_state = False  # for INPUT gate
        self.clock_interval = 1.0
        self.clock_running = False
        self.clock_elapsed = 0.0
        self.delay_interval = 0.5
        self.buffer_prev_input = False
        self.buffer_pulse = 0.0
        self.buffer_flash_time = 0.15
        self.output_color = RED
        self.hover_t = 0.0
        self.select_t = 0.0
        self.delete_t = 0.0
        self.deleting = False
        self.pin_orient = 0

    def apply_custom_definition(self, custom_key):
        self.custom_key = custom_key
        definition = get_custom_gate_def(custom_key) or {}
        shape = definition.get("shape", {})
        self.custom_name = definition.get("name", "CUSTOM")
        self.custom_w = float(shape.get("w", 80.0))
        self.custom_h = float(shape.get("h", 50.0))
        if self.custom_w < 40:
            self.custom_w = 40.0
        if self.custom_h < 30:
            self.custom_h = 30.0

        def _norm_pin(pin, default_x):
            px = float(pin.get("x", default_x))
            py = float(pin.get("y", 0.0))
            lbl = str(pin.get("label", ""))
            return {"x": px, "y": py, "label": lbl}

        self.custom_inputs = [_norm_pin(p, -self.custom_w / 2.0) for p in shape.get("inputs", [])]
        self.custom_outputs = [_norm_pin(p, self.custom_w / 2.0) for p in shape.get("outputs", [])]
        self.custom_labels = []
        for lbl in shape.get("labels", []):
            self.custom_labels.append({
                "x": float(lbl.get("x", 0.0)),
                "y": float(lbl.get("y", 0.0)),
                "text": str(lbl.get("text", "")),
            })
        if not self.custom_inputs:
            self.custom_inputs = [{"x": -self.custom_w / 2.0, "y": 0.0, "label": "IN1"}]
        if not self.custom_outputs:
            self.custom_outputs = [{"x": self.custom_w / 2.0, "y": 0.0, "label": "OUT1"}]
        self.inputs = [None for _ in self.custom_inputs]
        self.custom_outputs_state = [False for _ in self.custom_outputs]
        self.custom_runtime = {}

    def rect(self):
        if self.type == "CUSTOM":
            return pygame.Rect(
                int(self.x - self.custom_w / 2.0),
                int(self.y - self.custom_h / 2.0),
                int(self.custom_w),
                int(self.custom_h),
            )
        return pygame.Rect(self.x - 40, self.y - 25, 80, 50)

    def rect_draw(self, scale):
        if self.type == "CUSTOM":
            w = self.custom_w * scale
            h = self.custom_h * scale
        else:
            w = 80 * scale
            h = 50 * scale
        return (self.draw_x - w / 2, self.draw_y - h / 2, w, h)

    def input_pos_draw(self, idx):
        if self.type == "CUSTOM":
            idx = max(0, min(idx, len(self.custom_inputs) - 1))
            pin = self.custom_inputs[idx]
            return (self.draw_x + pin["x"], self.draw_y + pin["y"])

        dx_edge = 40
        dy_edge = 25
        spread = 12

        if len(self.inputs) == 2:
            if self.pin_orient == 0:  # inputs left
                return (self.draw_x - dx_edge, self.draw_y - spread if idx == 0 else self.draw_y + spread)
            if self.pin_orient == 1:  # inputs bottom
                return (self.draw_x - spread if idx == 0 else self.draw_x + spread, self.draw_y + dy_edge)
            if self.pin_orient == 2:  # inputs right
                return (self.draw_x + dx_edge, self.draw_y - spread if idx == 0 else self.draw_y + spread)
            # inputs top
            return (self.draw_x - spread if idx == 0 else self.draw_x + spread, self.draw_y - dy_edge)

        if len(self.inputs) > 2:
            offset = (idx - (len(self.inputs) - 1) / 2.0) * 12
            if self.pin_orient == 0:
                return (self.draw_x - dx_edge, self.draw_y + offset)
            if self.pin_orient == 1:
                return (self.draw_x + offset, self.draw_y + dy_edge)
            if self.pin_orient == 2:
                return (self.draw_x + dx_edge, self.draw_y + offset)
            return (self.draw_x + offset, self.draw_y - dy_edge)

        # ONE_INPUT
        if self.pin_orient == 0:
            return (self.draw_x - dx_edge, self.draw_y)
        if self.pin_orient == 1:
            return (self.draw_x, self.draw_y + dy_edge)
        if self.pin_orient == 2:
            return (self.draw_x + dx_edge, self.draw_y)
        return (self.draw_x, self.draw_y - dy_edge)

    def output_pos_draw_idx(self, idx=0):
        if self.type == "CUSTOM":
            if not self.custom_outputs:
                return (self.draw_x + self.custom_w / 2.0, self.draw_y)
            idx = max(0, min(idx, len(self.custom_outputs) - 1))
            pin = self.custom_outputs[idx]
            return (self.draw_x + pin["x"], self.draw_y + pin["y"])

        dx_edge = 40
        dy_edge = 25
        if self.pin_orient == 0:
            return (self.draw_x + dx_edge, self.draw_y)
        if self.pin_orient == 1:
            return (self.draw_x, self.draw_y - dy_edge)
        if self.pin_orient == 2:
            return (self.draw_x - dx_edge, self.draw_y)
        return (self.draw_x, self.draw_y + dy_edge)

    def output_pos_draw(self):
        return self.output_pos_draw_idx(0)

    def eval(self, gates_by_id):
        if self.type in ("INPUT", "BUTTON", "CLOCK"):
            self.output = self.input_state
            return
        if self.type == "CUSTOM":
            self.custom_outputs_state = compute_custom_gate_outputs(self, gates_by_id)
            self.output = self.custom_outputs_state[0] if self.custom_outputs_state else False
            return

        vals = []
        for i in range(len(self.inputs)):
            conn = self.inputs[i]
            if conn is None:
                vals.append(False)
            else:
                vals.append(conn_output_state(conn, gates_by_id))

        if self.type == "OUTPUT":
            self.output = vals[0] if vals else False
        elif self.type == "DELAY":
            self.output = vals[0] if vals else False
        elif self.type == "NOT":
            self.output = not vals[0]
        elif self.type == "AND":
            self.output = vals[0] and vals[1]
        elif self.type == "NAND":
            self.output = not (vals[0] and vals[1])
        elif self.type == "OR":
            self.output = vals[0] or vals[1]
        elif self.type == "NOR":
            self.output = not (vals[0] or vals[1])
        elif self.type == "XOR":
            self.output = (vals[0] != vals[1])
        elif self.type == "XNOR":
            self.output = (vals[0] == vals[1])


gates = []
selected_gate = None
wire_from = None
notes = []
selected_note_ids = set()

note_edit_id = None
note_edit_text = ""
note_edit_cursor = 0
note_edit_original = ""
note_blink_t = 0.0
note_edit_anim_t = 1.0
note_edit_anim_index = None

last_click_time = 0
last_click_note_id = None
last_click_gate_id = None
last_click_gate_time = 0

is_dragging = False
_drag_gate = None
_drag_dx = 0
_drag_dy = 0
_drag_start = (0, 0)
_drag_pending = False
_drag_snapshot = None
_drag_world_start = (0.0, 0.0)
_drag_group_start = None
_drag_note_snapshot = None
_drag_note_pending = False
_drag_note = None
_drag_note_world_start = (0.0, 0.0)
_drag_note_group_start = None

preview_x, preview_y = 0, 0
preview_t = 0.0

menu_open = False
menu_pos = (0, 0)
menu_t = 0.0
menu_target = 0.0

confirm_open = False
confirm_t = 0.0
confirm_target = 0.0
exit_confirm_open = False
exit_confirm_t = 0.0
exit_confirm_target = 0.0
save_scope_open = False
save_scope_t = 0.0
save_scope_target = 0.0

help_open = False
help_t = 0.0
help_target = 0.0

clock_menu_open = False
clock_menu_t = 0.0
clock_menu_target = 0.0
clock_menu_gate_id = None
delay_menu_open = False
delay_menu_t = 0.0
delay_menu_target = 0.0
delay_menu_gate_id = None

settings_open = False
settings_t = 0.0
settings_target = 0.0
straight_wires = True
settings_toggle_t = 0.0
light_mode = False

grid_step = 25
snap_to_grid = True
zoom_min = 0.4
zoom_max = 2.5
gate_label_scale = 1.0
note_font_scale = 1.0
show_pins_always = False
selection_brightness = 1.0
auto_center = True
wire_thickness = 1.0
signal_delay_enabled = False
signal_delay_seconds = 0.08
multicolor_outputs = False
settings_anim = {}
settings_slider_rects = {}
settings_drag_slider = None
settings_scroll = 0.0
settings_scroll_target = 0.0
settings_scroll_max = 0.0
help_scroll = 0.0
help_scroll_target = 0.0
help_scroll_max = 0.0
settings_dirty = False
keybinds_dirty = False

keybinds_open = False
keybinds_t = 0.0
keybinds_target = 0.0
keybind_capture_action = None
keybind_capture_started_ms = 0
keybinds_scroll = 0.0
keybinds_scroll_target = 0.0
keybinds_scroll_max = 0.0

APP_BASE_DIR = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
SETTINGS_CACHE_DIR = os.path.join(APP_BASE_DIR, "settings-cache")
SETTINGS_CACHE_FILE = os.path.join(SETTINGS_CACHE_DIR, "settings.json")

KEYBIND_ITEMS = [
    ("open_settings", "Open settings"),
    ("new_file_prompt", "New file prompt"),
    ("exit_prompt", "Exit prompt"),
    ("save", "Save"),
    ("load", "Load"),
    ("undo", "Undo"),
    ("redo", "Redo"),
    ("copy", "Copy"),
    ("paste", "Paste"),
    ("paste_segment", "Paste segment file"),
    ("rotate_cw", "Rotate clockwise"),
    ("rotate_ccw", "Rotate counter-clockwise"),
    ("delete", "Delete selected"),
    ("clear_all", "Clear all gates"),
]

DEFAULT_KEYBINDS = {
    "open_settings": {"key": pygame.K_TAB, "ctrl": False, "shift": False, "alt": False},
    "new_file_prompt": {"key": pygame.K_ESCAPE, "ctrl": False, "shift": False, "alt": False},
    "exit_prompt": {"key": pygame.K_SPACE, "ctrl": False, "shift": False, "alt": False},
    "save": {"key": pygame.K_s, "ctrl": True, "shift": False, "alt": False},
    "load": {"key": pygame.K_l, "ctrl": True, "shift": False, "alt": False},
    "undo": {"key": pygame.K_z, "ctrl": True, "shift": False, "alt": False},
    "redo": {"key": pygame.K_y, "ctrl": True, "shift": False, "alt": False},
    "copy": {"key": pygame.K_c, "ctrl": True, "shift": False, "alt": False},
    "paste": {"key": pygame.K_v, "ctrl": True, "shift": False, "alt": False},
    "paste_segment": {"key": pygame.K_v, "ctrl": True, "shift": True, "alt": False},
    "rotate_cw": {"key": pygame.K_r, "ctrl": False, "shift": False, "alt": False},
    "rotate_ccw": {"key": pygame.K_t, "ctrl": False, "shift": False, "alt": False},
    "delete": {"key": pygame.K_BACKSPACE, "ctrl": False, "shift": False, "alt": False},
    "clear_all": {"key": pygame.K_c, "ctrl": False, "shift": False, "alt": False},
}
keybinds = {k: dict(v) for k, v in DEFAULT_KEYBINDS.items()}

custom_menu_open = False
custom_menu_t = 0.0
custom_menu_target = 0.0
custom_menu_scroll = 0.0
custom_menu_scroll_target = 0.0
custom_menu_scroll_max = 0.0

selecting = False
select_start = (0, 0)
select_rect = None
selected_ids = set()
select_t = 0.0

copy_buffer = []

undo_stack = []
redo_stack = []
wire_cache = {}
layout_version = 0
signal_pending = {}
dialog_open = False

# Camera
cam_x = 0.0
cam_y = 0.0
zoom = 1.0
pan_pending = False
panning = False
pan_start = (0, 0)
cam_start = (0.0, 0.0)
pan_moved = False
last_mid_click = 0
held_button_gate_id = None


def scaled_font(size):
    return pygame.font.SysFont("consolas", max(8, int(size * zoom)))

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def lerp(a, b, t):
    return a + (b - a) * t

def lerp_color(c1, c2, t):
    return (int(lerp(c1[0], c2[0], t)), int(lerp(c1[1], c2[1], t)), int(lerp(c1[2], c2[2], t)))


def ease_to(current, target, speed, dt=None):
    if dt is None:
        dt = frame_dt if "frame_dt" in globals() else (1.0 / FPS)
    if dt <= 0.0:
        return current
    s = max(0.0, float(speed))
    if s <= 0.0:
        return target
    if abs(target - current) <= 1e-4:
        return target
    t = 1.0 - math.exp(-s * dt)
    return current + (target - current) * t


def conn_parts(conn):
    if conn is None:
        return (None, 0)
    if isinstance(conn, int):
        return (conn, 0)
    if isinstance(conn, (list, tuple)) and len(conn) >= 1:
        gid = conn[0]
        if not isinstance(gid, int):
            return (None, 0)
        oidx = 0
        if len(conn) > 1:
            try:
                oidx = max(0, int(conn[1]))
            except Exception:
                oidx = 0
        return (gid, oidx)
    return (None, 0)


def make_conn(gate_id, out_idx=0):
    return (int(gate_id), max(0, int(out_idx)))


def gate_output_count(g):
    if g is None:
        return 0
    if g.type == "CUSTOM":
        shape_count = len(getattr(g, "custom_outputs", []))
        if shape_count > 0:
            return shape_count
        return max(1, len(getattr(g, "custom_outputs_state", [])))
    return 1


def gate_output_state(g, out_idx=0):
    if g is None:
        return False
    if g.type == "CUSTOM":
        outs = getattr(g, "custom_outputs_state", [])
        if not outs:
            return bool(g.output) if int(out_idx) == 0 else False
        idx = max(0, min(int(out_idx), len(outs) - 1))
        return bool(outs[idx])
    return bool(g.output)


def conn_output_state(conn, gates_by_id):
    gid, oidx = conn_parts(conn)
    if gid is None:
        return False
    src = gates_by_id.get(gid)
    return gate_output_state(src, oidx)


def conn_source_id(conn):
    gid, _ = conn_parts(conn)
    return gid


def normalize_conn(conn):
    gid, oidx = conn_parts(conn)
    if gid is None:
        return None
    return make_conn(gid, oidx)


def apply_theme():
    global BG, PANEL, GRID, WHITE, GRAY, GREEN, RED, YELLOW, BLUE, ACCENT, HOVER, HOVER_PIN, WIRE_ON, WIRE_OFF
    global DIALOG_BORDER, DIALOG_BORDER_SOFT, TOGGLE_OFF, TOGGLE_ON, TOGGLE_KNOB, SLIDER_TRACK, SLIDER_KNOB
    global BUTTON_NEUTRAL, BUTTON_ACCENT, BUTTON_CLOCK, BUTTON_CLOCK_HOVER, BUTTON_DANGER
    global MENU_TILE, MENU_TILE_HOVER, MENU_SPLIT, MENU_BORDER
    if light_mode:
        BG = (252, 252, 244)
        PANEL = (255, 251, 225)
        GRID = (236, 230, 188)
        WHITE = (36, 36, 28)
        GRAY = (108, 104, 88)
        GREEN = (55, 165, 95)
        RED = (210, 80, 75)
        YELLOW = (243, 198, 72)
        BLUE = (205, 165, 55)
        ACCENT = (233, 188, 58)
        HOVER = (250, 212, 95)
        HOVER_PIN = (255, 200, 95)
        WIRE_ON = (244, 188, 52)
        WIRE_OFF = (150, 145, 128)
        DIALOG_BORDER = (196, 176, 104)
        DIALOG_BORDER_SOFT = (214, 194, 120)
        TOGGLE_OFF = (176, 164, 124)
        TOGGLE_ON = (226, 182, 56)
        TOGGLE_KNOB = (255, 251, 240)
        SLIDER_TRACK = (188, 176, 130)
        SLIDER_KNOB = (236, 194, 74)
        BUTTON_NEUTRAL = (205, 186, 118)
        BUTTON_ACCENT = (222, 190, 84)
        BUTTON_CLOCK = (221, 180, 76)
        BUTTON_CLOCK_HOVER = (236, 194, 92)
        BUTTON_DANGER = (214, 122, 102)
        MENU_TILE = (242, 224, 152)
        MENU_TILE_HOVER = (247, 205, 98)
        MENU_SPLIT = (206, 176, 88)
        MENU_BORDER = (205, 178, 102)
    else:
        BG = (18, 18, 22)
        PANEL = (28, 30, 36)
        GRID = (40, 40, 48)
        WHITE = (230, 230, 235)
        GRAY = (140, 140, 150)
        GREEN = (60, 220, 120)
        RED = (220, 80, 80)
        YELLOW = (240, 220, 120)
        BLUE = (90, 160, 255)
        ACCENT = (70, 200, 255)
        HOVER = (120, 190, 255)
        HOVER_PIN = (255, 220, 150)
        WIRE_ON = YELLOW
        WIRE_OFF = (160, 160, 175)
        DIALOG_BORDER = (90, 90, 110)
        DIALOG_BORDER_SOFT = (110, 110, 130)
        TOGGLE_OFF = (90, 90, 110)
        TOGGLE_ON = (70, 150, 110)
        TOGGLE_KNOB = (230, 230, 235)
        SLIDER_TRACK = (80, 80, 95)
        SLIDER_KNOB = (170, 190, 230)
        BUTTON_NEUTRAL = (80, 80, 100)
        BUTTON_ACCENT = (80, 90, 110)
        BUTTON_CLOCK = (95, 85, 70)
        BUTTON_CLOCK_HOVER = (120, 105, 85)
        BUTTON_DANGER = (120, 70, 70)
        MENU_TILE = (60, 60, 70)
        MENU_TILE_HOVER = (80, 90, 110)
        MENU_SPLIT = (110, 110, 125)
        MENU_BORDER = (90, 90, 105)


apply_theme()


def collect_settings():
    return {
        "light_mode": light_mode,
        "straight_wires": straight_wires,
        "snap_to_grid": snap_to_grid,
        "zoom_min": zoom_min,
        "zoom_max": zoom_max,
        "gate_label_scale": gate_label_scale,
        "note_font_scale": note_font_scale,
        "show_pins_always": show_pins_always,
        "selection_brightness": selection_brightness,
        "auto_center": auto_center,
        "wire_thickness": wire_thickness,
        "signal_delay_enabled": signal_delay_enabled,
        "multicolor_outputs": multicolor_outputs,
    }


def mark_settings_dirty():
    global settings_dirty
    settings_dirty = True


def mark_keybinds_dirty():
    global keybinds_dirty
    keybinds_dirty = True


def binding_from_event(event):
    mods = event.mod
    return {
        "key": int(event.key),
        "ctrl": bool(mods & pygame.KMOD_CTRL),
        "shift": bool(mods & pygame.KMOD_SHIFT),
        "alt": bool(mods & pygame.KMOD_ALT),
    }


def normalize_binding(raw):
    if not isinstance(raw, dict):
        return None
    key = raw.get("key")
    if not isinstance(key, int):
        return None
    return {
        "key": key,
        "ctrl": bool(raw.get("ctrl", False)),
        "shift": bool(raw.get("shift", False)),
        "alt": bool(raw.get("alt", False)),
    }


def normalize_keybinds(raw):
    data = {k: dict(v) for k, v in DEFAULT_KEYBINDS.items()}
    if not isinstance(raw, dict):
        return data
    for action, _ in KEYBIND_ITEMS:
        nb = normalize_binding(raw.get(action))
        if nb is not None:
            data[action] = nb
    return data


def bindings_equal(a, b):
    na = normalize_binding(a)
    nb = normalize_binding(b)
    if na is None or nb is None:
        return False
    return (
        na["key"] == nb["key"]
        and na["ctrl"] == nb["ctrl"]
        and na["shift"] == nb["shift"]
        and na["alt"] == nb["alt"]
    )


def keybind_to_text(binding):
    if not binding:
        return "Unbound"
    parts = []
    if binding.get("ctrl"):
        parts.append("Ctrl")
    if binding.get("shift"):
        parts.append("Shift")
    if binding.get("alt"):
        parts.append("Alt")
    key_name = pygame.key.name(binding.get("key", 0)).upper()
    if key_name == "":
        key_name = "UNKNOWN"
    parts.append(key_name)
    return "+".join(parts)


def action_pressed(event, action):
    bind = keybinds.get(action)
    if not bind or event.type != pygame.KEYDOWN:
        return False
    if event.key != bind["key"]:
        return False
    mods = event.mod
    ctrl = bool(mods & pygame.KMOD_CTRL)
    shift = bool(mods & pygame.KMOD_SHIFT)
    alt = bool(mods & pygame.KMOD_ALT)
    return ctrl == bind.get("ctrl", False) and shift == bind.get("shift", False) and alt == bind.get("alt", False)


def normalize_custom_block(raw, source="user"):
    if not isinstance(raw, dict):
        return None
    name = str(raw.get("name", "Custom Block")).strip()
    if not name:
        name = "Custom Block"
    shape = raw.get("shape", {})
    if not isinstance(shape, dict):
        shape = {}
    w = float(shape.get("w", 80.0))
    h = float(shape.get("h", 50.0))
    if w < 40:
        w = 40.0
    if h < 30:
        h = 30.0

    def _pins(items, default_x):
        out = []
        for item in items if isinstance(items, list) else []:
            if not isinstance(item, dict):
                continue
            out.append({
                "x": float(item.get("x", default_x)),
                "y": float(item.get("y", 0.0)),
                "label": str(item.get("label", "")),
            })
        return out

    inputs = _pins(shape.get("inputs", []), -w / 2.0)
    outputs = _pins(shape.get("outputs", []), w / 2.0)
    labels = []
    for item in shape.get("labels", []) if isinstance(shape.get("labels", []), list) else []:
        if not isinstance(item, dict):
            continue
        labels.append({
            "x": float(item.get("x", 0.0)),
            "y": float(item.get("y", 0.0)),
            "text": str(item.get("text", "")),
        })
    if not inputs:
        inputs = [{"x": -w / 2.0, "y": 0.0, "label": "IN1"}]
    if not outputs:
        outputs = [{"x": w / 2.0, "y": 0.0, "label": "OUT1"}]

    logic = raw.get("logic", {})
    if not isinstance(logic, dict):
        logic = {}
    gates_data = []
    for node in logic.get("gates", []) if isinstance(logic.get("gates", []), list) else []:
        if not isinstance(node, dict):
            continue
        try:
            nid = int(node.get("id"))
        except Exception:
            continue
        ntype = str(node.get("type", "NOT"))
        ninputs = [normalize_conn(v) for v in node.get("inputs", []) if True]
        if ntype == "INPUT":
            ninputs = []
        elif ntype == "OUTPUT":
            ninputs = [ninputs[0] if ninputs else None]
        gates_data.append({
            "id": nid,
            "type": ntype,
            "x": float(node.get("x", 0.0)),
            "y": float(node.get("y", 0.0)),
            "pin_orient": int(node.get("pin_orient", 0)) % 4,
            "inputs": ninputs,
            "custom_key": node.get("custom_key", None),
            "delay_interval": float(node.get("delay_interval", 0.5)),
            "buffer_flash_time": float(node.get("buffer_flash_time", 0.15)),
        })

    data = {
        "name": name,
        "source": source,
        "shape": {
            "w": w,
            "h": h,
            "inputs": inputs,
            "outputs": outputs,
            "labels": labels,
        },
        "logic": {
            "gates": gates_data,
            "input_ids": [int(v) for v in logic.get("input_ids", []) if isinstance(v, int)],
            "output_ids": [int(v) for v in logic.get("output_ids", []) if isinstance(v, int)],
        },
    }
    key = str(raw.get("key", "")).strip()
    if key:
        data["key"] = key
    return data


def normalize_custom_user_blocks(raw):
    out = {}
    if not isinstance(raw, dict):
        return out
    for key, block in raw.items():
        nb = normalize_custom_block(block, source="user")
        if nb is None:
            continue
        k = str(key).strip()
        if not k:
            continue
        nb["key"] = k
        out[k] = nb
    return out


def slugify_block_name(name):
    cleaned = "".join(ch if ch.isalnum() else "_" for ch in name.strip())
    cleaned = cleaned.strip("_")
    if not cleaned:
        cleaned = "custom_block"
    return cleaned.lower()


def new_user_block_key(name):
    base = f"user:{slugify_block_name(name)}"
    key = base
    i = 2
    while key in custom_gate_defs_user:
        key = f"{base}_{i}"
        i += 1
    return key


def copy_custom_block(defn):
    return json.loads(json.dumps(defn))


def prompt_text_dialog(title, prompt, initial=""):
    text = str(initial if initial is not None else "")
    cursor = len(text)
    blink_t = 0.0
    char_anim_t = 1.0
    char_anim_index = None
    open_t = 0.0
    scroll_x = 0.0
    backdrop = screen.copy()

    while True:
        open_t = min(1.0, open_t + 0.14)
        blink_t += 1.0 / FPS
        char_anim_t = min(1.0, char_anim_t + 0.12)

        w, h = 640, 210
        x0 = WIDTH // 2 - w // 2
        y0 = HEIGHT // 2 - h // 2
        input_rect = pygame.Rect(x0 + 24, y0 + 86, w - 48, 54)
        cancel_rect = pygame.Rect(x0 + w - 300, y0 + h - 48, 120, 34)
        ok_rect = pygame.Rect(x0 + w - 160, y0 + h - 48, 120, 34)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.KEYDOWN:
                mods = pygame.key.get_mods()
                if event.key == pygame.K_ESCAPE:
                    return None
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    return text
                if event.key == pygame.K_BACKSPACE:
                    if mods & pygame.KMOD_CTRL:
                        if cursor > 0:
                            cut = text[:cursor].rstrip()
                            new_len = cut.rfind(" ")
                            if new_len == -1:
                                text = text[cursor:]
                                cursor = 0
                            else:
                                text = text[: new_len + 1] + text[cursor:]
                                cursor = new_len + 1
                            char_anim_t = 0.0
                            char_anim_index = None
                        continue
                    if cursor > 0:
                        text = text[: cursor - 1] + text[cursor:]
                        cursor -= 1
                        char_anim_t = 0.0
                        char_anim_index = None
                    continue
                if event.key == pygame.K_DELETE:
                    if cursor < len(text):
                        text = text[:cursor] + text[cursor + 1 :]
                        char_anim_t = 0.0
                        char_anim_index = None
                    continue
                if event.key == pygame.K_LEFT:
                    cursor = max(0, cursor - 1)
                    continue
                if event.key == pygame.K_RIGHT:
                    cursor = min(len(text), cursor + 1)
                    continue
                if event.key == pygame.K_HOME:
                    cursor = 0
                    continue
                if event.key == pygame.K_END:
                    cursor = len(text)
                    continue
                if event.unicode and not (mods & (pygame.KMOD_CTRL | pygame.KMOD_ALT)):
                    ch = event.unicode
                    if ch not in ("\r", "\n"):
                        text = text[:cursor] + ch + text[cursor:]
                        cursor += 1
                        char_anim_t = 0.0
                        char_anim_index = cursor - 1
                continue

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if cancel_rect.collidepoint(event.pos):
                    return None
                if ok_rect.collidepoint(event.pos):
                    return text
                if input_rect.collidepoint(event.pos):
                    font = base_font
                    pad_x = 10
                    local_x = max(0.0, event.pos[0] - (input_rect.x + pad_x) + scroll_x)
                    best_idx = 0
                    best_d = None
                    for i in range(len(text) + 1):
                        d = abs(font.size(text[:i])[0] - local_x)
                        if best_d is None or d < best_d:
                            best_d = d
                            best_idx = i
                    cursor = best_idx

        font = base_font
        pad_x = 10
        cursor_px = font.size(text[:cursor])[0]
        visible_w = max(8, input_rect.w - pad_x * 2)
        if cursor_px - scroll_x > visible_w - 6:
            scroll_x = cursor_px - (visible_w - 6)
        if cursor_px - scroll_x < 0:
            scroll_x = cursor_px
        scroll_x = max(0.0, scroll_x)

        screen.blit(backdrop, (0, 0))
        ease = open_t * (2 - open_t)
        alpha = int(225 * open_t)

        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, int(120 * open_t)))
        screen.blit(overlay, (0, 0))

        panel = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(panel, (*PANEL, alpha), (0, 0, w, h), border_radius=14)
        pygame.draw.rect(panel, (*DIALOG_BORDER, alpha), (0, 0, w, h), 2, border_radius=14)

        t_surf = base_font.render(title, True, WHITE)
        p_surf = base_small.render(prompt, True, GRAY)
        t_surf.set_alpha(alpha)
        p_surf.set_alpha(alpha)
        panel.blit(t_surf, (20, 16))
        panel.blit(p_surf, (20, 48))

        local_input = pygame.Rect(input_rect.x - x0, input_rect.y - y0, input_rect.w, input_rect.h)
        pygame.draw.rect(panel, (*GRID, int(alpha * 0.95)), local_input, border_radius=10)
        pygame.draw.rect(panel, (*DIALOG_BORDER_SOFT, alpha), local_input, 1, border_radius=10)

        prev_clip = panel.get_clip()
        clip_rect = local_input.inflate(-8, -8)
        panel.set_clip(clip_rect)
        tx = clip_rect.x + 4 - int(scroll_x)
        ty = clip_rect.y + (clip_rect.h - font.get_height()) // 2
        if text:
            if char_anim_index is not None and 0 <= char_anim_index < len(text):
                pre = text[:char_anim_index]
                ch = text[char_anim_index : char_anim_index + 1]
                post = text[char_anim_index + 1 :]
                x = tx
                if pre:
                    s = font.render(pre, True, WHITE)
                    s.set_alpha(alpha)
                    panel.blit(s, (x, ty))
                    x += s.get_width()
                if ch:
                    ch_alpha = int(alpha * (0.3 + 0.7 * (char_anim_t * (2 - char_anim_t))))
                    s = font.render(ch, True, WHITE)
                    s.set_alpha(ch_alpha)
                    panel.blit(s, (x, ty))
                    x += s.get_width()
                if post:
                    s = font.render(post, True, WHITE)
                    s.set_alpha(alpha)
                    panel.blit(s, (x, ty))
            else:
                s = font.render(text, True, WHITE)
                s.set_alpha(alpha)
                panel.blit(s, (tx, ty))
        panel.set_clip(prev_clip)

        if int(blink_t * 2) % 2 == 0:
            cx = tx + cursor_px
            cy0 = clip_rect.y + 5
            cy1 = clip_rect.bottom - 5
            pygame.draw.line(panel, WHITE, (cx, cy0), (cx, cy1), 2)

        hint = base_small.render("Enter: save   Esc: cancel", True, GRAY)
        hint.set_alpha(alpha)
        panel.blit(hint, (24, h - 38))

        mx, my = pygame.mouse.get_pos()
        for key, rect, color, label in (
            ("cancel", pygame.Rect(cancel_rect.x - x0, cancel_rect.y - y0, cancel_rect.w, cancel_rect.h), BUTTON_NEUTRAL, "Cancel"),
            ("ok", pygame.Rect(ok_rect.x - x0, ok_rect.y - y0, ok_rect.w, ok_rect.h), TOGGLE_ON, "Save"),
        ):
            hover = rect.move(x0, y0).collidepoint(mx, my)
            c = color if not hover else tuple(min(v + 15, 255) for v in color)
            pygame.draw.rect(panel, (*c, alpha), rect, border_radius=8)
            pygame.draw.rect(panel, (*DIALOG_BORDER_SOFT, alpha), rect, 1, border_radius=8)
            ts = base_small.render(label, True, WHITE)
            ts.set_alpha(alpha)
            panel.blit(ts, (rect.centerx - ts.get_width() // 2, rect.centery - ts.get_height() // 2))

        scale = 0.94 + 0.06 * ease
        panel = pygame.transform.smoothscale(panel, (int(w * scale), int(h * scale)))
        px = x0 + (w - panel.get_width()) // 2
        py = y0 + (h - panel.get_height()) // 2
        screen.blit(panel, (px, py))
        pygame.display.flip()
        CLOCK.tick(FPS)


def is_custom_gate_token(token):
    return isinstance(token, str) and token.startswith("CUSTOM::")


def custom_key_from_token(token):
    if is_custom_gate_token(token):
        return token.split("::", 1)[1]
    return None


def custom_token_from_key(custom_key):
    return f"CUSTOM::{custom_key}"


def refresh_custom_gate_instances(custom_key):
    changed = False
    for g in gates:
        if g.type != "CUSTOM" or g.custom_key != custom_key:
            continue
        old_inputs = list(g.inputs)
        old_pin_orient = g.pin_orient
        g.apply_custom_definition(custom_key)
        for i in range(min(len(old_inputs), len(g.inputs))):
            g.inputs[i] = normalize_conn(old_inputs[i])
        g.pin_orient = old_pin_orient
        changed = True
    if changed:
        wire_cache.clear()
        bump_layout()


def nearest_point_on_rect_outline(rect, pos):
    x, y = pos
    left = rect.left
    right = rect.right
    top = rect.top
    bottom = rect.bottom
    candidates = [
        (clamp(x, left, right), top),
        (clamp(x, left, right), bottom),
        (left, clamp(y, top, bottom)),
        (right, clamp(y, top, bottom)),
    ]
    best = candidates[0]
    best_d = (best[0] - x) ** 2 + (best[1] - y) ** 2
    for c in candidates[1:]:
        d = (c[0] - x) ** 2 + (c[1] - y) ** 2
        if d < best_d:
            best = c
            best_d = d
    return best


def save_cached_settings():
    try:
        os.makedirs(SETTINGS_CACHE_DIR, exist_ok=True)
        user_blocks = {k: copy_custom_block(v) for k, v in custom_gate_defs_user.items()}
        with open(SETTINGS_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(
                {"settings": collect_settings(), "keybinds": keybinds, "custom_user_blocks": user_blocks},
                f,
                indent=2,
            )
        return True
    except Exception:
        return False


def flush_cached_settings():
    global settings_dirty, keybinds_dirty
    if not settings_dirty and not keybinds_dirty:
        return
    if save_cached_settings():
        settings_dirty = False
        keybinds_dirty = False


def load_cached_settings():
    global light_mode, straight_wires, snap_to_grid, zoom_min, zoom_max, gate_label_scale, note_font_scale
    global show_pins_always, selection_brightness, auto_center, wire_thickness, signal_delay_enabled, multicolor_outputs
    global zoom, keybinds, custom_gate_defs_user
    try:
        if not os.path.exists(SETTINGS_CACHE_FILE):
            os.makedirs(SETTINGS_CACHE_DIR, exist_ok=True)
            return
        with open(SETTINGS_CACHE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
        settings = state.get("settings", state) if isinstance(state, dict) else {}
        if not isinstance(settings, dict):
            return
        keybinds = normalize_keybinds(state.get("keybinds", {}))
        custom_gate_defs_user = normalize_custom_user_blocks(state.get("custom_user_blocks", {}))
        light_mode = settings.get("light_mode", light_mode)
        apply_theme()
        straight_wires = settings.get("straight_wires", straight_wires)
        snap_to_grid = settings.get("snap_to_grid", snap_to_grid)
        zoom_min = settings.get("zoom_min", zoom_min)
        zoom_max = settings.get("zoom_max", zoom_max)
        gate_label_scale = settings.get("gate_label_scale", gate_label_scale)
        note_font_scale = settings.get("note_font_scale", note_font_scale)
        show_pins_always = settings.get("show_pins_always", show_pins_always)
        selection_brightness = settings.get("selection_brightness", selection_brightness)
        auto_center = settings.get("auto_center", auto_center)
        wire_thickness = settings.get("wire_thickness", wire_thickness)
        signal_delay_enabled = settings.get("signal_delay_enabled", signal_delay_enabled)
        multicolor_outputs = settings.get("multicolor_outputs", multicolor_outputs)
        remap_output_gate_inputs(multicolor_outputs)
        zoom = clamp(zoom, zoom_min, zoom_max)
    except Exception:
        pass


def snap_world(pos):
    if not snap_to_grid or grid_step <= 0:
        return pos
    x, y = pos
    return (round(x / grid_step) * grid_step, round(y / grid_step) * grid_step)


def bump_layout():
    global layout_version
    layout_version += 1


def screen_to_world(pos):
    sx, sy = pos
    wx = (sx - WIDTH / 2) / zoom + cam_x
    wy = (sy - HEIGHT / 2) / zoom + cam_y
    return (wx, wy)


def world_to_screen(pos):
    wx, wy = pos
    sx = (wx - cam_x) * zoom + WIDTH / 2
    sy = (wy - cam_y) * zoom + HEIGHT / 2
    return (sx, sy)


def gate_at(pos_world):
    for g in reversed(gates):
        if g.deleting:
            continue
        if g.rect().collidepoint(pos_world):
            return g
    return None


def output_hit(g, pos_world):
    out_count = gate_output_count(g)
    best = None
    best_d = None
    for i in range(out_count):
        ox, oy = g.output_pos_draw_idx(i)
        d = (pos_world[0] - ox) ** 2 + (pos_world[1] - oy) ** 2
        if d <= PIN_HIT ** 2 and (best_d is None or d < best_d):
            best = i
            best_d = d
    return best


def input_hit(g, pos_world):
    best = None
    best_d = None
    for i in range(len(g.inputs)):
        ix, iy = g.input_pos_draw(i)
        d = (pos_world[0] - ix) ** 2 + (pos_world[1] - iy) ** 2
        if d <= PIN_HIT ** 2 and (best_d is None or d < best_d):
            best = i
            best_d = d
    return best


def find_pin_hit(pos_world):
    for g in reversed(gates):
        if g.deleting:
            continue
        oidx = output_hit(g, pos_world)
        if oidx is not None:
            return (g, "out", oidx)
        idx = input_hit(g, pos_world)
        if idx is not None:
            return (g, "in", idx)
    return (None, None, None)


def draw_grid():
    step = grid_step
    top_left = screen_to_world((0, 0))
    bottom_right = screen_to_world((WIDTH, HEIGHT))
    x0 = int(math.floor(top_left[0] / step) * step)
    x1 = int(math.ceil(bottom_right[0] / step) * step)
    y0 = int(math.floor(top_left[1] / step) * step)
    y1 = int(math.ceil(bottom_right[1] / step) * step)

    for x in range(x0, x1 + step, step):
        sx, sy0 = world_to_screen((x, y0))
        _, sy1 = world_to_screen((x, y1))
        pygame.draw.line(screen, GRID, (sx, sy0), (sx, sy1), 1)
    for y in range(y0, y1 + step, step):
        sx0, sy = world_to_screen((x0, y))
        sx1, _ = world_to_screen((x1, y))
        pygame.draw.line(screen, GRID, (sx0, sy), (sx1, sy), 1)


def draw_label():
    label = base_font.render("Logical v2.6.0", True, ACCENT)
    screen.blit(label, (12, 12))


def remap_output_gate_inputs(enable_multicolor):
    changed = False
    for g in gates:
        if g.deleting or g.type != "OUTPUT":
            continue
        if enable_multicolor:
            if len(g.inputs) != 3:
                first = g.inputs[0] if g.inputs else None
                g.inputs = [first, None, None]
                changed = True
        else:
            if len(g.inputs) != 1:
                first = next((inp for inp in g.inputs if inp is not None), None)
                g.inputs = [first]
                changed = True
    if changed:
        bump_layout()


def output_logic_info(g, gates_by_id):
    vals = []
    for i in range(len(g.inputs)):
        conn = g.inputs[i]
        vals.append(conn_output_state(conn, gates_by_id))
    if multicolor_outputs and len(vals) >= 3:
        active = [MCOLORS[idx] for idx in range(3) if vals[idx]]
        if active:
            r = int(sum(c[0] for c in active) / len(active))
            gg = int(sum(c[1] for c in active) / len(active))
            b = int(sum(c[2] for c in active) / len(active))
            return True, (r, gg, b)
        return False, RED
    return (vals[0] if vals else False), RED


def evaluate_logic_nodes(definition, input_values, runtime=None, dt=0.0):
    logic = definition.get("logic", {})
    nodes = logic.get("gates", [])
    input_ids = [int(v) for v in logic.get("input_ids", [])]
    output_ids = [int(v) for v in logic.get("output_ids", [])]
    if not nodes or not output_ids:
        out_n = max(1, len(definition.get("shape", {}).get("outputs", [])))
        base = bool(input_values[0]) if input_values else False
        return [base for _ in range(out_n)]

    by_id = {}
    for n in nodes:
        try:
            nid = int(n.get("id"))
        except Exception:
            continue
        by_id[nid] = n

    if runtime is None or not isinstance(runtime, dict):
        runtime = {}
    values = runtime.get("values")
    if not isinstance(values, dict):
        values = {}
    for nid in by_id.keys():
        values[nid] = bool(values.get(nid, False))
    runtime["values"] = values

    buffer_prev = runtime.get("buffer_prev")
    if not isinstance(buffer_prev, dict):
        buffer_prev = {}
    buffer_pulse = runtime.get("buffer_pulse")
    if not isinstance(buffer_pulse, dict):
        buffer_pulse = {}
    delay_pending = runtime.get("delay_pending")
    if not isinstance(delay_pending, dict):
        delay_pending = {}

    for i, nid in enumerate(input_ids):
        if nid in values:
            values[nid] = bool(input_values[i]) if i < len(input_values) else False

    def node_val(conn):
        gid, _ = conn_parts(conn)
        if gid is None:
            return False
        return bool(values.get(gid, False))

    def compute_node(n):
        gtype = n.get("type", "")
        if gtype == "INPUT":
            return values.get(int(n.get("id", -1)), False)
        vals = [node_val(c) for c in n.get("inputs", [])]
        if gtype == "OUTPUT":
            return vals[0] if vals else False
        if gtype == "NOT":
            return not (vals[0] if vals else False)
        if gtype == "AND":
            return all(vals) if vals else False
        if gtype == "NAND":
            return not (all(vals) if vals else False)
        if gtype == "OR":
            return any(vals) if vals else False
        if gtype == "NOR":
            return not (any(vals) if vals else False)
        if gtype == "XOR":
            return sum(1 for v in vals if v) == 1
        if gtype == "XNOR":
            return sum(1 for v in vals if v) != 1
        return values.get(int(n.get("id", -1)), False)

    def eval_combinational():
        for _ in range(30):
            changed = False
            for nid, node in by_id.items():
                if nid in input_ids:
                    continue
                gtype = str(node.get("type", ""))
                if gtype in ("BUFFER", "DELAY"):
                    continue
                nv = bool(compute_node(node))
                if values.get(nid, False) != nv:
                    values[nid] = nv
                    changed = True
            if not changed:
                break

    eval_combinational()

    # Stateful BUFFER behavior: pulse on rising edge only.
    live_buffer_ids = set()
    for nid, node in by_id.items():
        if str(node.get("type", "")) != "BUFFER":
            continue
        live_buffer_ids.add(nid)
        vals = [node_val(c) for c in node.get("inputs", [])]
        incoming = bool(vals[0]) if vals else False
        prev = bool(buffer_prev.get(nid, False))
        if incoming and not prev:
            flash = max(0.01, float(node.get("buffer_flash_time", 0.15)))
            buffer_pulse[nid] = max(float(buffer_pulse.get(nid, 0.0)), flash)
        buffer_prev[nid] = incoming
        pulse = max(0.0, float(buffer_pulse.get(nid, 0.0)) - max(0.0, dt))
        buffer_pulse[nid] = pulse
        values[nid] = pulse > 0.0

    # Stateful DELAY behavior: apply transition after interval.
    live_delay_ids = set()
    for nid, node in by_id.items():
        if str(node.get("type", "")) != "DELAY":
            continue
        live_delay_ids.add(nid)
        vals = [node_val(c) for c in node.get("inputs", [])]
        desired = bool(vals[0]) if vals else False
        current = bool(values.get(nid, False))
        pending = delay_pending.get(nid)
        if desired != current:
            if not (isinstance(pending, (list, tuple)) and len(pending) == 2 and bool(pending[0]) == desired):
                interval = max(0.1, float(node.get("delay_interval", 0.5)))
                delay_pending[nid] = [desired, interval]
                pending = delay_pending[nid]
        else:
            delay_pending.pop(nid, None)
            pending = None
        if isinstance(pending, (list, tuple)) and len(pending) == 2:
            remain = float(pending[1]) - max(0.0, dt)
            if remain <= 0.0:
                values[nid] = bool(pending[0])
                delay_pending.pop(nid, None)
            else:
                delay_pending[nid] = [bool(pending[0]), remain]

    for nid in list(buffer_prev.keys()):
        if nid not in live_buffer_ids:
            buffer_prev.pop(nid, None)
    for nid in list(buffer_pulse.keys()):
        if nid not in live_buffer_ids:
            buffer_pulse.pop(nid, None)
    for nid in list(delay_pending.keys()):
        if nid not in live_delay_ids:
            delay_pending.pop(nid, None)

    runtime["buffer_prev"] = buffer_prev
    runtime["buffer_pulse"] = buffer_pulse
    runtime["delay_pending"] = delay_pending
    runtime["values"] = values

    eval_combinational()

    outs = []
    for oid in output_ids:
        outs.append(bool(values.get(oid, False)))
    if not outs:
        out_n = max(1, len(definition.get("shape", {}).get("outputs", [])))
        base = bool(input_values[0]) if input_values else False
        outs = [base for _ in range(out_n)]
    return outs


def compute_custom_gate_outputs(g, gates_by_id, dt=0.0):
    definition = get_custom_gate_def(getattr(g, "custom_key", None))
    out_n = max(1, len(getattr(g, "custom_outputs", [])))
    if definition is None:
        base = conn_output_state(g.inputs[0], gates_by_id) if g.inputs else False
        return [base for _ in range(out_n)]
    input_values = [conn_output_state(c, gates_by_id) for c in g.inputs]
    runtime = getattr(g, "custom_runtime", None)
    if not isinstance(runtime, dict):
        runtime = {}
        g.custom_runtime = runtime
    outs = evaluate_logic_nodes(definition, input_values, runtime=runtime, dt=dt)
    if len(outs) < out_n:
        outs += [False] * (out_n - len(outs))
    elif len(outs) > out_n:
        outs = outs[:out_n]
    return [bool(v) for v in outs]


def compute_gate_output(g, gates_by_id):
    vals = []
    for i in range(len(g.inputs)):
        conn = g.inputs[i]
        vals.append(conn_output_state(conn, gates_by_id))

    if g.type == "OUTPUT":
        out_val, _ = output_logic_info(g, gates_by_id)
        return out_val
    if g.type == "CUSTOM":
        outs = compute_custom_gate_outputs(g, gates_by_id)
        g.custom_outputs_state = outs
        return outs[0] if outs else False
    if g.type == "DELAY":
        return vals[0] if vals else False
    if g.type == "NOT":
        return not vals[0]
    if g.type == "AND":
        return all(vals) if vals else False
    if g.type == "NAND":
        return not (all(vals) if vals else False)
    if g.type == "OR":
        return any(vals) if vals else False
    if g.type == "NOR":
        return not (any(vals) if vals else False)
    if g.type == "XOR":
        return sum(1 for v in vals if v) == 1
    if g.type == "XNOR":
        return sum(1 for v in vals if v) != 1
    return g.output


def eval_all(dt=0.0):
    global signal_pending
    gates_by_id = {g.id: g for g in gates if not g.deleting}

    # Source gates update instantly; all others update on delay.
    for g in gates:
        if g.deleting:
            signal_pending.pop(g.id, None)
            continue
        if g.type in ("INPUT", "BUTTON", "CLOCK"):
            g.output = g.input_state
            signal_pending.pop(g.id, None)
        if g.type == "BUFFER":
            signal_pending.pop(g.id, None)
        if g.type == "CUSTOM":
            signal_pending.pop(g.id, None)

    for gid in list(signal_pending.keys()):
        g = gates_by_id.get(gid)
        if g is None:
            signal_pending.pop(gid, None)
            continue
        pending = signal_pending[gid]
        if len(pending) == 3:
            target, remain, out_color = pending
        else:
            target, remain = pending
            out_color = None
        remain -= max(0.0, dt)
        if remain <= 0.0:
            g.output = target
            if g.type == "OUTPUT" and out_color is not None:
                g.output_color = out_color
            signal_pending.pop(gid, None)
        else:
            signal_pending[gid] = (target, remain, out_color)

    max_iters = 25
    for _ in range(max_iters):
        changed = False
        for g in gates:
            if g.deleting:
                continue
            if g.type in ("INPUT", "BUTTON", "CLOCK", "BUFFER"):
                continue
            if g.type == "CUSTOM":
                desired_outs = compute_custom_gate_outputs(g, gates_by_id, dt)
                if desired_outs != g.custom_outputs_state:
                    g.custom_outputs_state = list(desired_outs)
                    changed = True
                first_out = g.custom_outputs_state[0] if g.custom_outputs_state else False
                if g.output != first_out:
                    g.output = first_out
                    changed = True
                continue
            desired = compute_gate_output(g, gates_by_id)
            desired_color = None
            if g.type == "OUTPUT":
                desired, desired_color = output_logic_info(g, gates_by_id)
            prev_pending = signal_pending.get(g.id)
            gate_delay = max(0.1, g.delay_interval) if g.type == "DELAY" else signal_delay_seconds
            use_delay = (g.type == "DELAY") or signal_delay_enabled
            if desired != g.output:
                if use_delay:
                    prev_target = prev_pending[0] if prev_pending is not None else None
                    prev_color = prev_pending[2] if prev_pending is not None and len(prev_pending) == 3 else None
                    if prev_pending is None or prev_target != desired or prev_color != desired_color:
                        signal_pending[g.id] = (desired, gate_delay, desired_color)
                        changed = True
                else:
                    g.output = desired
                    if g.type == "OUTPUT" and desired_color is not None:
                        g.output_color = desired_color
                    signal_pending.pop(g.id, None)
                    changed = True
            elif prev_pending is not None:
                signal_pending.pop(g.id, None)
                changed = True
            elif g.type == "OUTPUT" and desired_color is not None:
                g.output_color = desired_color
        if not changed:
            break


def update_buffers(dt):
    gates_by_id = {g.id: g for g in gates if not g.deleting}
    for g in gates:
        if g.deleting or g.type != "BUFFER":
            continue
        incoming = False
        if g.inputs:
            conn = g.inputs[0]
            incoming = conn_output_state(conn, gates_by_id)
        if incoming and not g.buffer_prev_input:
            g.buffer_pulse = max(g.buffer_pulse, g.buffer_flash_time)
        g.buffer_prev_input = incoming
        g.buffer_pulse = max(0.0, g.buffer_pulse - max(0.0, dt))
        g.output = g.buffer_pulse > 0.0


def update_clocks(dt):
    if dt <= 0:
        return
    for g in gates:
        if g.deleting or g.type != "CLOCK" or not g.clock_running:
            continue
        g.clock_elapsed += dt
        interval = max(0.1, g.clock_interval)
        while g.clock_elapsed >= interval:
            g.clock_elapsed -= interval
            g.input_state = not g.input_state


def update_gate_anim(hover_gate):
    moved = False
    for g in gates:
        prev_x, prev_y = g.draw_x, g.draw_y
        g.draw_x = ease_to(g.draw_x, g.x, 18.0)
        g.draw_y = ease_to(g.draw_y, g.y, 18.0)
        if abs(g.draw_x - prev_x) > 0.01 or abs(g.draw_y - prev_y) > 0.01:
            moved = True
        g.spawn_t = min(1.0, g.spawn_t + 0.08)
        target_hover = 1.0 if hover_gate == g and not g.deleting else 0.0
        target_select = 1.0 if g.id in selected_ids and not g.deleting else 0.0
        g.hover_t = ease_to(g.hover_t, target_hover, max(0.1, ANIM_HOVER * 60.0))
        g.select_t = ease_to(g.select_t, target_select, max(0.1, ANIM_SELECT * 60.0))
        if g.deleting:
            g.delete_t = min(1.0, g.delete_t + ANIM_DELETE)

    to_remove = [g for g in gates if g.deleting and g.delete_t >= 1.0]
    for g in to_remove:
        delete_gate(g)
        moved = True
    if moved:
        bump_layout()


def draw_gates(hover_gate, hover_pin):
    show_text = zoom >= SHOW_TEXT_MIN
    show_pins = show_pins_always or zoom >= SHOW_PINS_MIN
    font = scaled_font(16 * gate_label_scale)

    for g in gates:
        if g.deleting and g.delete_t >= 1.0:
            continue
        ease = g.spawn_t * (2 - g.spawn_t)
        scale = (0.85 + 0.15 * ease) * max(0.0, 1.0 - g.delete_t)

        rx, ry, rw, rh = g.rect_draw(scale)
        srx, sry = world_to_screen((rx, ry))
        rw *= zoom
        rh *= zoom

        color = (70, 70, 80)
        if g.type == "INPUT":
            color = GREEN if g.output else (70, 130, 70)
        if g.type == "BUTTON":
            color = (80, 160, 95) if g.output else (70, 115, 80)
        if g.type == "CLOCK":
            color = (95, 155, 225) if g.output else (70, 95, 130)
        if g.type == "DELAY":
            color = (210, 150, 80) if g.output else (130, 95, 65)
        if g.type == "BUFFER":
            color = (95, 170, 190) if g.output else (70, 105, 120)
        if g.type == "OUTPUT":
            color = g.output_color if g.output else (130, 70, 70)
        if g.type == "CUSTOM":
            any_on = any(bool(v) for v in getattr(g, "custom_outputs_state", []))
            color = (120, 120, 165) if any_on else (88, 88, 125)
        if g.output and g.type not in ("INPUT", "BUTTON", "CLOCK", "DELAY", "BUFFER", "OUTPUT"):
            color = (min(color[0] + 20, 255), min(color[1] + 25, 255), min(color[2] + 20, 255))
        if light_mode:
            mix = 0.32 if g.type != "OUTPUT" else 0.20
            color = lerp_color(color, (255, 246, 212), mix)

        color = lerp_color(color, BG, g.delete_t)
        rect = pygame.Rect(int(srx), int(sry), int(rw), int(rh))
        radius = max(2, int(8 * zoom))
        pygame.draw.rect(screen, color, rect, border_radius=radius)

        outline = (155, 145, 115) if light_mode else (100, 100, 120)
        outline = lerp_color(outline, HOVER, g.hover_t)
        sel_t = clamp(g.select_t * selection_brightness, 0.0, 1.0)
        outline = lerp_color(outline, BLUE, sel_t)
        outline = lerp_color(outline, BG, g.delete_t)
        pygame.draw.rect(screen, outline, rect, max(1, int(2 * zoom)), border_radius=radius)

        if show_text:
            label_color = BG if g.output else WHITE
            label_color = lerp_color(label_color, BG, g.delete_t)
            if g.type == "CLOCK":
                label = font.render("CLOCK", True, label_color)
                tlabel = font.render(f"{g.clock_interval:.2f}s", True, label_color)
                lx = rect.centerx - label.get_width() // 2
                ly = rect.centery - label.get_height()
                screen.blit(label, (lx, ly))
                tx = rect.centerx - tlabel.get_width() // 2
                ty = rect.centery + 2
                screen.blit(tlabel, (tx, ty))
            elif g.type == "DELAY":
                label = font.render("DELAY", True, label_color)
                tlabel = font.render(f"{g.delay_interval:.2f}s", True, label_color)
                lx = rect.centerx - label.get_width() // 2
                ly = rect.centery - label.get_height()
                screen.blit(label, (lx, ly))
                tx = rect.centerx - tlabel.get_width() // 2
                ty = rect.centery + 2
                screen.blit(tlabel, (tx, ty))
            elif g.type == "CUSTOM":
                label = font.render(g.custom_name, True, label_color)
                lx = rect.centerx - label.get_width() // 2
                ly = rect.centery - label.get_height() // 2
                screen.blit(label, (lx, ly))
                tiny = scaled_font(12 * gate_label_scale)
                for lbl in g.custom_labels:
                    txt = tiny.render(lbl.get("text", ""), True, label_color)
                    px = int(rect.centerx + lbl.get("x", 0.0) * zoom - txt.get_width() / 2)
                    py = int(rect.centery + lbl.get("y", 0.0) * zoom - txt.get_height() / 2)
                    screen.blit(txt, (px, py))
            else:
                label = font.render(g.type, True, label_color)
                lx = rect.centerx - label.get_width() // 2
                ly = rect.centery - label.get_height() // 2
                screen.blit(label, (lx, ly))

        if show_pins:
            for i in range(len(g.inputs)):
                ix, iy = g.input_pos_draw(i)
                sx, sy = world_to_screen((ix, iy))
                if g.type == "OUTPUT" and multicolor_outputs and len(g.inputs) >= 3 and i < 3:
                    pin_color = MCOLORS[i]
                else:
                    pin_color = YELLOW
                if hover_pin[0] == g and hover_pin[1] == "in" and hover_pin[2] == i:
                    pin_color = HOVER_PIN
                pin_color = lerp_color(pin_color, BG, g.delete_t)
                pygame.draw.circle(screen, pin_color, (int(sx), int(sy)), max(2, int(PIN_RADIUS * zoom)))
                if g.type == "CUSTOM" and show_text:
                    lbl = g.custom_inputs[i].get("label", "") if i < len(g.custom_inputs) else ""
                    if lbl:
                        txt = scaled_font(12 * gate_label_scale).render(lbl, True, WHITE)
                        screen.blit(txt, (int(sx - txt.get_width() - 6), int(sy - txt.get_height() / 2)))
            out_count = gate_output_count(g)
            for oi in range(out_count):
                ox, oy = g.output_pos_draw_idx(oi)
                sx, sy = world_to_screen((ox, oy))
                pin_color = YELLOW
                if hover_pin[0] == g and hover_pin[1] == "out" and hover_pin[2] == oi:
                    pin_color = HOVER_PIN
                pin_color = lerp_color(pin_color, BG, g.delete_t)
                size = max(3, int(PIN_RADIUS * zoom))
                if g.type == "CUSTOM":
                    pygame.draw.circle(screen, pin_color, (int(sx), int(sy)), size)
                    if show_text and oi < len(g.custom_outputs):
                        lbl = g.custom_outputs[oi].get("label", "")
                        if lbl:
                            txt = scaled_font(12 * gate_label_scale).render(lbl, True, WHITE)
                            screen.blit(txt, (int(sx + 6), int(sy - txt.get_height() / 2)))
                    continue
                if g.pin_orient == 0:
                    pts = [(sx + size, sy), (sx - size, sy - size), (sx - size, sy + size)]
                elif g.pin_orient == 1:
                    pts = [(sx, sy - size), (sx - size, sy + size), (sx + size, sy + size)]
                elif g.pin_orient == 2:
                    pts = [(sx - size, sy), (sx + size, sy - size), (sx + size, sy + size)]
                else:
                    pts = [(sx, sy + size), (sx - size, sy - size), (sx + size, sy - size)]
                pygame.draw.polygon(screen, pin_color, pts)


def draw_gate_preview(gtype, pos_screen, t):
    if gtype is None or t <= 0.01:
        return
    preview_name = gtype
    is_custom = False
    ddef = {}
    if is_custom_gate_token(gtype):
        is_custom = True
        ckey = custom_key_from_token(gtype)
        ddef = get_custom_gate_def(ckey) or {}
        preview_name = ddef.get("name", "CUSTOM")
        gtype = "CUSTOM"
    x, y = pos_screen

    if gtype == "CUSTOM":
        shape = ddef.get("shape", {}) if isinstance(ddef, dict) else {}
        pw = max(40.0, float(shape.get("w", 80.0)))
        ph = max(30.0, float(shape.get("h", 50.0)))
        pin_inputs = shape.get("inputs", []) if isinstance(shape.get("inputs", []), list) else []
        pin_outputs = shape.get("outputs", []) if isinstance(shape.get("outputs", []), list) else []

        sw = max(20, int(pw * zoom))
        sh = max(16, int(ph * zoom))
        surf = pygame.Surface((sw + 16, sh + 16), pygame.SRCALPHA)
        rect = pygame.Rect(8, 8, sw, sh)

        color = (125, 125, 175)
        if light_mode:
            color = lerp_color(color, (255, 244, 210), 0.28)
        alpha = int(150 * t)
        pygame.draw.rect(surf, (*color, alpha), rect, border_radius=max(6, int(8 * zoom)))
        preview_outline = (195, 180, 130) if light_mode else (160, 160, 180)
        pygame.draw.rect(surf, (*preview_outline, alpha), rect, max(1, int(2 * zoom)), border_radius=max(6, int(8 * zoom)))

        shown = preview_name if is_custom else "CUSTOM"
        txt = base_font.render(shown, True, (240, 240, 245))
        txt.set_alpha(int(210 * t))
        surf.blit(txt, (rect.centerx - txt.get_width() // 2, rect.centery - txt.get_height() // 2))

        pin_r = max(3, int(PIN_RADIUS * zoom * 0.45))
        for pin in pin_inputs:
            px = rect.centerx + int(float(pin.get("x", -pw / 2.0)) * zoom)
            py = rect.centery + int(float(pin.get("y", 0.0)) * zoom)
            pygame.draw.circle(surf, (*YELLOW, int(220 * t)), (px, py), pin_r)
        for pin in pin_outputs:
            px = rect.centerx + int(float(pin.get("x", pw / 2.0)) * zoom)
            py = rect.centery + int(float(pin.get("y", 0.0)) * zoom)
            size = pin_r
            dx = px - rect.centerx
            dy = py - rect.centery
            if abs(dx) >= abs(dy):
                if dx >= 0:
                    pts = [(px + size, py), (px - size, py - size), (px - size, py + size)]
                else:
                    pts = [(px - size, py), (px + size, py - size), (px + size, py + size)]
            else:
                if dy >= 0:
                    pts = [(px, py + size), (px - size, py - size), (px + size, py - size)]
                else:
                    pts = [(px, py - size), (px - size, py + size), (px + size, py + size)]
            pygame.draw.polygon(surf, (*YELLOW, int(220 * t)), pts)

        screen.blit(surf, (x - surf.get_width() // 2, y - surf.get_height() // 2))
        return

    surf = pygame.Surface((90, 60), pygame.SRCALPHA)
    color = (120, 120, 140, 90)
    if gtype == "INPUT":
        color = (80, 180, 110, 90)
    if gtype == "BUTTON":
        color = (95, 170, 105, 90)
    if gtype == "CLOCK":
        color = (95, 155, 225, 90)
    if gtype == "DELAY":
        color = (205, 150, 85, 90)
    if gtype == "BUFFER":
        color = (95, 170, 190, 90)
    if gtype == "OUTPUT":
        color = (180, 90, 90, 90)
    if gtype == "CUSTOM":
        color = (125, 125, 175, 90)
    if light_mode:
        c = lerp_color(color[:3], (255, 244, 210), 0.28)
        color = (c[0], c[1], c[2], color[3])
    alpha = int(140 * t)
    color = (*color[:3], alpha)
    pygame.draw.rect(surf, color, (5, 5, 80, 50), border_radius=8)
    preview_outline = (195, 180, 130) if light_mode else (160, 160, 180)
    pygame.draw.rect(surf, (*preview_outline, alpha), (5, 5, 80, 50), 2, border_radius=8)
    shown = preview_name if is_custom else gtype
    txt = base_font.render(shown, True, (240, 240, 245))
    txt.set_alpha(int(200 * t))
    surf.blit(txt, (45 - txt.get_width() // 2, 25 - 8))
    scale = (0.9 + 0.1 * t) * zoom
    sw, sh = int(90 * scale), int(60 * scale)
    surf = pygame.transform.smoothscale(surf, (sw, sh))
    screen.blit(surf, (x - sw // 2, y - sh // 2))


def draw_gate_menu(pos_screen):
    global menu_t
    if not menu_open and menu_t <= 0.01:
        return []

    menu_t = ease_to(menu_t, menu_target, 13.0)
    if menu_t < 0.01:
        menu_t = 0.0
    if menu_t > 0.99:
        menu_t = 1.0

    items = []
    cols = 3
    item_w = 150
    item_h = 80
    pad = 10

    menu_list = ["INPUT_BUTTON", "OUTPUT_BUFFER", "NOT_DELAY", "AND_NAND", "OR_NOR", "XOR_XNOR"]
    rows = math.ceil(len(menu_list) / cols)
    total_w = cols * item_w + (cols - 1) * pad
    total_h = rows * item_h + (rows - 1) * pad

    x0, y0 = pos_screen
    x0 = min(max(20, x0 - total_w // 2), WIDTH - total_w - 20)
    y0 = min(max(20, y0 - total_h // 2), HEIGHT - total_h - 20)

    alpha = int(220 * menu_t)
    panel = pygame.Surface((total_w + 20, total_h + 20), pygame.SRCALPHA)
    pygame.draw.rect(panel, (*PANEL, alpha), (0, 0, total_w + 20, total_h + 20), border_radius=12)
    pygame.draw.rect(panel, (*DIALOG_BORDER_SOFT, alpha), (0, 0, total_w + 20, total_h + 20), 1, border_radius=12)
    screen.blit(panel, (x0 - 10, y0 - 10))

    mx, my = pygame.mouse.get_pos()
    for i, g in enumerate(menu_list):
        row = i // cols
        col = i % cols
        x = x0 + col * (item_w + pad)
        y = y0 + row * (item_h + pad)
        rect = pygame.Rect(x, y, item_w, item_h)

        # Wave-in effect per item, and same-direction wave-out
        delay = i * 0.06
        t = max(0.0, min(1.0, (menu_t - delay) / 0.4))
        ease = t * t * (3 - 2 * t)
        slide = int((1.0 - ease) * 16)
        alpha = int(255 * ease)
        rect = rect.move(0, slide)

        if g in ("AND_NAND", "OR_NOR", "XOR_XNOR", "INPUT_BUTTON", "NOT_DELAY", "OUTPUT_BUFFER"):
            left = pygame.Rect(x, y, item_w // 2, item_h)
            right = pygame.Rect(x + item_w // 2, y, item_w // 2, item_h)
            hover_left = left.collidepoint(mx, my)
            hover_right = right.collidepoint(mx, my)

            tile = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
            pygame.draw.rect(tile, (*MENU_TILE, alpha), tile.get_rect(), border_radius=10)
            pygame.draw.rect(tile, (*MENU_BORDER, alpha), tile.get_rect(), 1, border_radius=10)

            if hover_left:
                pygame.draw.rect(tile, (*MENU_TILE_HOVER, alpha), pygame.Rect(0, 0, rect.w // 2, rect.h), border_radius=10)
            if hover_right:
                pygame.draw.rect(tile, (*MENU_TILE_HOVER, alpha), pygame.Rect(rect.w // 2, 0, rect.w // 2, rect.h), border_radius=10)

            pygame.draw.line(tile, (*MENU_SPLIT, alpha), (rect.w // 2, 8), (rect.w // 2, rect.h - 8), 2)

            if g == "INPUT_BUTTON":
                label1, label2 = "INPUT", "BUTTON"
            elif g == "OUTPUT_BUFFER":
                label1, label2 = "OUTPUT", "BUFFER"
            elif g == "NOT_DELAY":
                label1, label2 = "NOT", "DELAY"
            elif g == "AND_NAND":
                label1, label2 = "AND", "NAND"
            elif g == "OR_NOR":
                label1, label2 = "OR", "NOR"
            else:
                label1, label2 = "XOR", "XNOR"

            l1 = base_small.render(label1, True, WHITE)
            l2 = base_small.render(label2, True, WHITE)
            l1.set_alpha(alpha)
            l2.set_alpha(alpha)
            tile.blit(l1, (rect.w // 4 - l1.get_width() // 2, rect.h // 2 - l1.get_height() // 2))
            tile.blit(l2, (rect.w * 3 // 4 - l2.get_width() // 2, rect.h // 2 - l2.get_height() // 2))

            screen.blit(tile, rect.topleft)
            items.append((label1, left))
            items.append((label2, right))
            continue

        hover = rect.collidepoint(mx, my)
        color = MENU_TILE
        if hover:
            color = MENU_TILE_HOVER
        tile = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        pygame.draw.rect(tile, (*color, alpha), tile.get_rect(), border_radius=10)
        pygame.draw.rect(tile, (*MENU_BORDER, alpha), tile.get_rect(), 1, border_radius=10)

        label = base_small.render(g, True, WHITE)
        label.set_alpha(alpha)
        tile.blit(label, (rect.w // 2 - label.get_width() // 2, rect.h // 2 - label.get_height() // 2))
        screen.blit(tile, rect.topleft)
        items.append((g, rect))

    note_w = (total_w - pad * 2) // 3
    note_h = item_h // 2
    note_x = x0
    note_y = y0 + total_h + pad + 8
    note_rect = pygame.Rect(note_x, note_y, note_w, note_h)
    clock_rect = pygame.Rect(note_x + note_w + pad, note_y, note_w, note_h)
    custom_rect = pygame.Rect(note_x + (note_w + pad) * 2, note_y, note_w, note_h)
    note_alpha = int(255 * menu_t)
    note_hover = note_rect.collidepoint(mx, my)
    note_color = MENU_TILE if not note_hover else MENU_TILE_HOVER
    note_tile = pygame.Surface((note_rect.w, note_rect.h), pygame.SRCALPHA)
    pygame.draw.rect(note_tile, (*note_color, note_alpha), note_tile.get_rect(), border_radius=10)
    pygame.draw.rect(note_tile, (*MENU_BORDER, note_alpha), note_tile.get_rect(), 1, border_radius=10)
    note_label = base_small.render("NOTE", True, WHITE)
    note_label.set_alpha(note_alpha)
    note_tile.blit(
        note_label,
        (note_rect.w // 2 - note_label.get_width() // 2, note_rect.h // 2 - note_label.get_height() // 2),
    )
    screen.blit(note_tile, note_rect.topleft)
    items.append(("NOTE", note_rect))

    clock_hover = clock_rect.collidepoint(mx, my)
    clock_color = MENU_TILE if not clock_hover else MENU_TILE_HOVER
    clock_tile = pygame.Surface((clock_rect.w, clock_rect.h), pygame.SRCALPHA)
    pygame.draw.rect(clock_tile, (*clock_color, note_alpha), clock_tile.get_rect(), border_radius=10)
    pygame.draw.rect(clock_tile, (*MENU_BORDER, note_alpha), clock_tile.get_rect(), 1, border_radius=10)
    clock_label = base_small.render("CLOCK", True, WHITE)
    clock_label.set_alpha(note_alpha)
    clock_tile.blit(
        clock_label,
        (clock_rect.w // 2 - clock_label.get_width() // 2, clock_rect.h // 2 - clock_label.get_height() // 2),
    )
    screen.blit(clock_tile, clock_rect.topleft)
    items.append(("CLOCK", clock_rect))

    custom_hover = custom_rect.collidepoint(mx, my)
    custom_color = MENU_TILE if not custom_hover else MENU_TILE_HOVER
    custom_tile = pygame.Surface((custom_rect.w, custom_rect.h), pygame.SRCALPHA)
    pygame.draw.rect(custom_tile, (*custom_color, note_alpha), custom_tile.get_rect(), border_radius=10)
    pygame.draw.rect(custom_tile, (*MENU_BORDER, note_alpha), custom_tile.get_rect(), 1, border_radius=10)
    custom_label = base_small.render("CUSTOM", True, WHITE)
    custom_label.set_alpha(note_alpha)
    custom_tile.blit(
        custom_label,
        (custom_rect.w // 2 - custom_label.get_width() // 2, custom_rect.h // 2 - custom_label.get_height() // 2),
    )
    screen.blit(custom_tile, custom_rect.topleft)
    items.append(("CUSTOM_MENU", custom_rect))

    return items


def wrap_text_with_ranges(text, font, max_width):
    if text == "":
        return [""], [(0, 0)]
    lines = []
    ranges = []
    line = ""
    line_start = 0
    i = 0
    while i < len(text):
        if text[i] == "\n":
            lines.append(line)
            ranges.append((line_start, i))
            line = ""
            i += 1
            line_start = i
            continue

        if text[i] == " ":
            candidate = line + " "
            if line and font.size(candidate)[0] > max_width:
                lines.append(line)
                ranges.append((line_start, i))
                line = ""
                i += 1
                line_start = i
            else:
                line = candidate
                i += 1
            continue

        word_start = i
        while i < len(text) and text[i] not in (" ", "\n"):
            i += 1
        word = text[word_start:i]

        if line:
            candidate = line + word
            if font.size(candidate)[0] <= max_width:
                line = candidate
                continue
            lines.append(line)
            ranges.append((line_start, word_start))
            line = ""
            line_start = word_start

        if font.size(word)[0] <= max_width:
            line = word
            continue

        for j in range(len(word)):
            candidate = line + word[j]
            if line and font.size(candidate)[0] > max_width:
                lines.append(line)
                ranges.append((line_start, word_start + j))
                line = ""
                line_start = word_start + j
            line = line + word[j]

    lines.append(line)
    ranges.append((line_start, len(text)))
    return lines, ranges


def note_size_for_text(font, text):
    max_w = max(60, int(NOTE_MAX_W * zoom))
    lines, _ = wrap_text_with_ranges(text, font, max_w)
    line_h = font.get_linesize()
    pad = max(4, int(8 * zoom))
    text_w = max(font.size(line)[0] for line in lines) if lines else 0
    w = text_w + pad * 2
    h = line_h * len(lines) + pad * 2
    return w, h, lines, line_h, pad


def note_layout(n, text_override=None):
    font = scaled_font(16 * note_font_scale)
    text = n["text"] if text_override is None else text_override
    w, h, lines, line_h, pad = note_size_for_text(font, text)
    min_w, min_h, _, _, _ = note_size_for_text(font, "note")
    w = max(w, min_w)
    h = max(h, min_h)
    lines, ranges = wrap_text_with_ranges(text, font, max(60, int(NOTE_MAX_W * zoom)))
    sx, sy = world_to_screen((n["draw_x"], n["draw_y"]))
    rect = pygame.Rect(int(sx), int(sy), w, h)
    return rect, lines, ranges, line_h, pad, font


def note_world_rect(n):
    override = note_edit_text if note_edit_id == n["id"] else None
    rect, _, _, _, _, _ = note_layout(n, override)
    p0 = screen_to_world((rect.x, rect.y))
    p1 = screen_to_world((rect.x + rect.w, rect.y + rect.h))
    rx = min(p0[0], p1[0])
    ry = min(p0[1], p1[1])
    rw = abs(p1[0] - p0[0])
    rh = abs(p1[1] - p0[1])
    return pygame.Rect(rx, ry, rw, rh)


def note_at_screen(pos_screen):
    for n in reversed(notes):
        if n.get("deleting"):
            continue
        override = note_edit_text if note_edit_id == n["id"] else None
        rect, _, _, _, _, _ = note_layout(n, override)
        if rect.collidepoint(pos_screen):
            return n
    return None


def start_note_edit(n):
    global note_edit_id, note_edit_text, note_edit_cursor, note_edit_original, note_blink_t, note_edit_anim_t
    global note_edit_anim_index
    note_edit_id = n["id"]
    note_edit_text = n["text"]
    note_edit_original = n["text"]
    note_edit_cursor = len(note_edit_text)
    note_blink_t = 0.0
    note_edit_anim_t = 1.0
    note_edit_anim_index = None


def finish_note_edit(commit=True):
    global note_edit_id, note_edit_text, note_edit_cursor, note_edit_original, note_edit_anim_t
    global note_edit_anim_index
    if note_edit_id is None:
        return
    note = next((n for n in notes if n["id"] == note_edit_id), None)
    if note:
        if commit:
            if note["text"] != note_edit_text:
                push_undo()
            note["text"] = note_edit_text
        else:
            note["text"] = note_edit_original
    note_edit_id = None
    note_edit_text = ""
    note_edit_original = ""
    note_edit_cursor = 0
    note_edit_anim_t = 1.0
    note_edit_anim_index = None


def update_note_anim(hover_note):
    moved = False
    for n in notes:
        prev_x, prev_y = n["draw_x"], n["draw_y"]
        n["draw_x"] = ease_to(n["draw_x"], n["x"], 18.0)
        n["draw_y"] = ease_to(n["draw_y"], n["y"], 18.0)
        if abs(n["draw_x"] - prev_x) > 0.01 or abs(n["draw_y"] - prev_y) > 0.01:
            moved = True
        n["spawn_t"] = min(1.0, n["spawn_t"] + 0.08)
        target_hover = 1.0 if hover_note == n and not n["deleting"] else 0.0
        target_select = 1.0 if n["id"] in selected_note_ids and not n["deleting"] else 0.0
        n["hover_t"] = ease_to(n["hover_t"], target_hover, max(0.1, ANIM_HOVER * 60.0))
        n["select_t"] = ease_to(n["select_t"], target_select, max(0.1, ANIM_SELECT * 60.0))
        if n["deleting"]:
            n["delete_t"] = min(1.0, n["delete_t"] + ANIM_DELETE)

    to_remove = [n for n in notes if n["deleting"] and n["delete_t"] >= 1.0]
    for n in to_remove:
        notes.remove(n)
        moved = True
    if moved:
        bump_layout()


def request_delete_note(n):
    if n["deleting"]:
        return
    if note_edit_id == n["id"]:
        finish_note_edit(commit=True)
    n["deleting"] = True
    n["delete_t"] = 0.0
    if n["id"] in selected_note_ids:
        selected_note_ids.discard(n["id"])
    bump_layout()


def draw_notes():
    if not notes:
        return
    for n in notes:
        if n["deleting"] and n["delete_t"] >= 1.0:
            continue
        override = note_edit_text if note_edit_id == n["id"] else None
        rect, lines, ranges, line_h, pad, font = note_layout(n, override)
        alpha = int(255 * (1.0 - n["delete_t"]))
        if light_mode:
            base = (255, 245, 206)
            outline = (198, 176, 104)
        else:
            base = (55, 55, 70)
            outline = (95, 95, 115)
        outline = lerp_color(outline, HOVER, n["hover_t"])
        sel_t = clamp(n["select_t"] * selection_brightness, 0.0, 1.0)
        outline = lerp_color(outline, BLUE, sel_t)
        fill = lerp_color(base, BG, n["delete_t"])
        radius = max(4, int(8 * zoom))
        border_w = max(1, int(1 * zoom))
        pygame.draw.rect(screen, (*fill, alpha), rect, border_radius=radius)
        pygame.draw.rect(screen, (*outline, alpha), rect, border_w, border_radius=radius)
        ty = rect.y + pad
        for idx, line in enumerate(lines):
            line_start, line_end = ranges[idx]
            if note_edit_id == n["id"] and note_edit_anim_index is not None and line_start <= note_edit_anim_index < line_end:
                local_idx = note_edit_anim_index - line_start
                pre = line[:local_idx]
                ch = line[local_idx:local_idx + 1]
                post = line[local_idx + 1 :]
                x = rect.x + pad
                if pre:
                    txt = font.render(pre, True, WHITE)
                    txt.set_alpha(alpha)
                    screen.blit(txt, (x, ty))
                    x += txt.get_width()
                if ch:
                    ease = note_edit_anim_t * (2 - note_edit_anim_t)
                    ch_alpha = int(alpha * (0.3 + 0.7 * ease))
                    txt = font.render(ch, True, WHITE)
                    txt.set_alpha(ch_alpha)
                    screen.blit(txt, (x, ty))
                    x += txt.get_width()
                if post:
                    txt = font.render(post, True, WHITE)
                    txt.set_alpha(alpha)
                    screen.blit(txt, (x, ty))
            else:
                txt = font.render(line, True, WHITE)
                txt.set_alpha(alpha)
                screen.blit(txt, (rect.x + pad, ty))
            ty += line_h

        if note_edit_id == n["id"]:
            cursor = note_edit_cursor
            caret_x = rect.x + pad
            caret_y = rect.y + pad
            for idx, (start, end) in enumerate(ranges):
                if start <= cursor <= end:
                    caret_x += font.size(lines[idx][: cursor - start])[0]
                    caret_y += idx * line_h
                    break
            if int(note_blink_t * 2) % 2 == 0:
                pygame.draw.line(
                    screen,
                    WHITE,
                    (caret_x, caret_y),
                    (caret_x, caret_y + line_h - 2),
                    2,
                )


def draw_confirm_dialog():
    global confirm_t
    if not confirm_open and confirm_t <= 0.01:
        return {}

    confirm_t = ease_to(confirm_t, confirm_target, 13.0)
    if confirm_t < 0.01:
        confirm_t = 0.0
    if confirm_t > 0.99:
        confirm_t = 1.0

    ease = confirm_t * (2 - confirm_t)
    alpha = int(220 * confirm_t)
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, int(120 * confirm_t)))
    screen.blit(overlay, (0, 0))

    w, h = 420, 210
    x0 = WIDTH // 2 - w // 2
    y0 = HEIGHT // 2 - h // 2
    scale = 0.92 + 0.08 * ease
    panel = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(panel, (*PANEL, alpha), (0, 0, w, h), border_radius=14)
    pygame.draw.rect(panel, (*DIALOG_BORDER, alpha), (0, 0, w, h), 2, border_radius=14)

    title = base_font.render("Start a new file?", True, WHITE)
    title.set_alpha(alpha)
    panel.blit(title, (20, 20))
    sub = base_small.render("Save current work before resetting?", True, GRAY)
    sub.set_alpha(alpha)
    panel.blit(sub, (20, 52))

    btn_w = 110
    btn_h = 40
    gap = 16
    bx = (w - (btn_w * 3 + gap * 2)) // 2
    by = h - 65
    buttons = {}
    labels = [("Save", "save"), ("Don't Save", "nosave"), ("Cancel", "cancel")]
    mx, my = pygame.mouse.get_pos()
    for i, (label, key) in enumerate(labels):
        rx = bx + i * (btn_w + gap)
        rect = pygame.Rect(rx, by, btn_w, btn_h)
        hover = rect.move(x0, y0).collidepoint(mx, my)
        color = BUTTON_ACCENT if key == "save" else BUTTON_NEUTRAL
        if key == "cancel":
            color = BUTTON_DANGER
        if hover:
            color = (min(color[0] + 15, 255), min(color[1] + 15, 255), min(color[2] + 15, 255))
        pygame.draw.rect(panel, (*color, alpha), rect, border_radius=8)
        pygame.draw.rect(panel, (*DIALOG_BORDER_SOFT, alpha), rect, 1, border_radius=8)
        txt = base_small.render(label, True, WHITE)
        txt.set_alpha(alpha)
        panel.blit(txt, (rect.centerx - txt.get_width() // 2, rect.centery - txt.get_height() // 2))
        buttons[key] = rect.move(x0, y0)

    panel = pygame.transform.smoothscale(panel, (int(w * scale), int(h * scale)))
    screen.blit(panel, (x0 + (w - panel.get_width()) // 2, y0 + (h - panel.get_height()) // 2))
    return buttons


def draw_exit_confirm_dialog():
    global exit_confirm_t
    if not exit_confirm_open and exit_confirm_t <= 0.01:
        return {}

    exit_confirm_t = ease_to(exit_confirm_t, exit_confirm_target, 13.0)
    if exit_confirm_t < 0.01:
        exit_confirm_t = 0.0
    if exit_confirm_t > 0.99:
        exit_confirm_t = 1.0

    ease = exit_confirm_t * (2 - exit_confirm_t)
    alpha = int(220 * exit_confirm_t)
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, int(120 * exit_confirm_t)))
    screen.blit(overlay, (0, 0))

    w, h = 420, 210
    x0 = WIDTH // 2 - w // 2
    y0 = HEIGHT // 2 - h // 2
    scale = 0.92 + 0.08 * ease
    panel = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(panel, (*PANEL, alpha), (0, 0, w, h), border_radius=14)
    pygame.draw.rect(panel, (*DIALOG_BORDER, alpha), (0, 0, w, h), 2, border_radius=14)

    title = base_font.render("Exit Logical?", True, WHITE)
    title.set_alpha(alpha)
    panel.blit(title, (20, 20))
    sub = base_small.render("Save current work before leaving?", True, GRAY)
    sub.set_alpha(alpha)
    panel.blit(sub, (20, 52))

    btn_w = 110
    btn_h = 40
    gap = 16
    bx = (w - (btn_w * 3 + gap * 2)) // 2
    by = h - 65
    buttons = {}
    labels = [("Save", "save"), ("Don't Save", "nosave"), ("Cancel", "cancel")]
    mx, my = pygame.mouse.get_pos()
    for i, (label, key) in enumerate(labels):
        rx = bx + i * (btn_w + gap)
        rect = pygame.Rect(rx, by, btn_w, btn_h)
        hover = rect.move(x0, y0).collidepoint(mx, my)
        color = BUTTON_ACCENT if key == "save" else BUTTON_NEUTRAL
        if key == "cancel":
            color = BUTTON_DANGER
        if hover:
            color = (min(color[0] + 15, 255), min(color[1] + 15, 255), min(color[2] + 15, 255))
        pygame.draw.rect(panel, (*color, alpha), rect, border_radius=8)
        pygame.draw.rect(panel, (*DIALOG_BORDER_SOFT, alpha), rect, 1, border_radius=8)
        txt = base_small.render(label, True, WHITE)
        txt.set_alpha(alpha)
        panel.blit(txt, (rect.centerx - txt.get_width() // 2, rect.centery - txt.get_height() // 2))
        buttons[key] = rect.move(x0, y0)

    panel = pygame.transform.smoothscale(panel, (int(w * scale), int(h * scale)))
    screen.blit(panel, (x0 + (w - panel.get_width()) // 2, y0 + (h - panel.get_height()) // 2))
    return buttons


def draw_save_scope_dialog():
    global save_scope_t
    if not save_scope_open and save_scope_t <= 0.01:
        return {}

    save_scope_t = ease_to(save_scope_t, save_scope_target, 13.0)
    if save_scope_t < 0.01:
        save_scope_t = 0.0
    if save_scope_t > 0.99:
        save_scope_t = 1.0

    ease = save_scope_t * (2 - save_scope_t)
    alpha = int(220 * save_scope_t)
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, int(120 * save_scope_t)))
    screen.blit(overlay, (0, 0))

    w, h = 460, 220
    x0 = WIDTH // 2 - w // 2
    y0 = HEIGHT // 2 - h // 2
    scale = 0.92 + 0.08 * ease
    panel = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(panel, (*PANEL, alpha), (0, 0, w, h), border_radius=14)
    pygame.draw.rect(panel, (*DIALOG_BORDER, alpha), (0, 0, w, h), 2, border_radius=14)

    title = base_font.render("Save File", True, WHITE)
    title.set_alpha(alpha)
    panel.blit(title, (20, 20))
    sub = base_small.render("Save selected segment or whole file?", True, GRAY)
    sub.set_alpha(alpha)
    panel.blit(sub, (20, 52))

    btn_w = 126
    btn_h = 42
    gap = 14
    bx = (w - (btn_w * 3 + gap * 2)) // 2
    by = h - 70
    buttons = {}
    labels = [("Segment", "segment"), ("Whole File", "whole"), ("Cancel", "cancel")]
    mx, my = pygame.mouse.get_pos()
    for i, (label, key) in enumerate(labels):
        rx = bx + i * (btn_w + gap)
        rect = pygame.Rect(rx, by, btn_w, btn_h)
        hover = rect.move(x0, y0).collidepoint(mx, my)
        color = BUTTON_ACCENT if key != "cancel" else BUTTON_DANGER
        if hover:
            color = (min(color[0] + 15, 255), min(color[1] + 15, 255), min(color[2] + 15, 255))
        pygame.draw.rect(panel, (*color, alpha), rect, border_radius=8)
        pygame.draw.rect(panel, (*DIALOG_BORDER_SOFT, alpha), rect, 1, border_radius=8)
        txt = base_small.render(label, True, WHITE)
        txt.set_alpha(alpha)
        panel.blit(txt, (rect.centerx - txt.get_width() // 2, rect.centery - txt.get_height() // 2))
        buttons[key] = rect.move(x0, y0)

    panel = pygame.transform.smoothscale(panel, (int(w * scale), int(h * scale)))
    screen.blit(panel, (x0 + (w - panel.get_width()) // 2, y0 + (h - panel.get_height()) // 2))
    return buttons


def draw_clock_dialog():
    global clock_menu_t, clock_menu_open, clock_menu_target, clock_menu_gate_id
    if not clock_menu_open and clock_menu_t <= 0.01:
        return {}

    gate = next((g for g in gates if g.id == clock_menu_gate_id and not g.deleting), None)
    if gate is None:
        clock_menu_open = False
        clock_menu_target = 0.0
        clock_menu_gate_id = None
        return {}

    clock_menu_t = ease_to(clock_menu_t, clock_menu_target, 13.0)
    if clock_menu_t < 0.01:
        clock_menu_t = 0.0
    if clock_menu_t > 0.99:
        clock_menu_t = 1.0

    ease = clock_menu_t * (2 - clock_menu_t)
    alpha = int(220 * clock_menu_t)
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, int(120 * clock_menu_t)))
    screen.blit(overlay, (0, 0))

    w, h = 440, 250
    x0 = WIDTH // 2 - w // 2
    y0 = HEIGHT // 2 - h // 2
    scale = 0.92 + 0.08 * ease
    panel = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(panel, (*PANEL, alpha), (0, 0, w, h), border_radius=14)
    pygame.draw.rect(panel, (*DIALOG_BORDER, alpha), (0, 0, w, h), 2, border_radius=14)

    def item_anim(idx, duration=0.35):
        delay = idx * 0.06
        t = max(0.0, min(1.0, (clock_menu_t - delay) / duration))
        eased = t * t * (3 - 2 * t)
        return eased, int((1.0 - eased) * 14), int(alpha * eased)

    title_ease, title_slide, title_alpha = item_anim(0)
    title = base_font.render("Clock Input", True, WHITE)
    title.set_alpha(title_alpha)
    panel.blit(title, (20, 20 + title_slide))
    state_txt = "Running" if gate.clock_running else "Stopped"
    sub_ease, sub_slide, sub_alpha = item_anim(1)
    sub = base_small.render(f"Interval: {gate.clock_interval:.2f}s  |  {state_txt}", True, GRAY)
    sub.set_alpha(sub_alpha)
    panel.blit(sub, (20, 54 + sub_slide))

    buttons = {}
    mx, my = pygame.mouse.get_pos()
    adjusts = [("-1.0s", "minus_big"), ("-0.1s", "minus_small"), ("+0.1s", "plus_small"), ("+1.0s", "plus_big")]
    bw = 90
    bh = 40
    gap = 10
    row_y = 100
    row_x = (w - (bw * len(adjusts) + gap * (len(adjusts) - 1))) // 2
    for i, (label, key) in enumerate(adjusts):
        ease_i, slide_i, alpha_i = item_anim(2 + i)
        rect = pygame.Rect(row_x + i * (bw + gap), row_y + slide_i, bw, bh)
        hover = rect.move(x0, y0).collidepoint(mx, my)
        color = BUTTON_ACCENT
        if hover:
            color = tuple(min(c + 20, 255) for c in color)
        pygame.draw.rect(panel, (*color, alpha_i), rect, border_radius=8)
        pygame.draw.rect(panel, (*DIALOG_BORDER_SOFT, alpha_i), rect, 1, border_radius=8)
        txt = base_small.render(label, True, WHITE)
        txt.set_alpha(alpha_i)
        panel.blit(txt, (rect.centerx - txt.get_width() // 2, rect.centery - txt.get_height() // 2))
        if ease_i > 0.02:
            buttons[key] = rect.move(x0, y0)

    run_label = "Stop" if gate.clock_running else "Start"
    action_labels = [(run_label, "toggle_run"), ("Close", "close")]
    abw = 140
    aby = h - 64
    abx = (w - (abw * 2 + 16)) // 2
    for i, (label, key) in enumerate(action_labels):
        ease_i, slide_i, alpha_i = item_anim(6 + i)
        rect = pygame.Rect(abx + i * (abw + 16), aby + slide_i, abw, 40)
        hover = rect.move(x0, y0).collidepoint(mx, my)
        color = TOGGLE_ON if key == "toggle_run" else BUTTON_NEUTRAL
        if hover:
            color = tuple(min(c + 15, 255) for c in color)
        pygame.draw.rect(panel, (*color, alpha_i), rect, border_radius=8)
        pygame.draw.rect(panel, (*DIALOG_BORDER_SOFT, alpha_i), rect, 1, border_radius=8)
        txt = base_small.render(label, True, WHITE)
        txt.set_alpha(alpha_i)
        panel.blit(txt, (rect.centerx - txt.get_width() // 2, rect.centery - txt.get_height() // 2))
        if ease_i > 0.02:
            buttons[key] = rect.move(x0, y0)

    panel = pygame.transform.smoothscale(panel, (int(w * scale), int(h * scale)))
    screen.blit(panel, (x0 + (w - panel.get_width()) // 2, y0 + (h - panel.get_height()) // 2))
    return buttons


def draw_delay_dialog():
    global delay_menu_t, delay_menu_open, delay_menu_target, delay_menu_gate_id
    if not delay_menu_open and delay_menu_t <= 0.01:
        return {}

    gate = next((g for g in gates if g.id == delay_menu_gate_id and not g.deleting), None)
    if gate is None:
        delay_menu_open = False
        delay_menu_target = 0.0
        delay_menu_gate_id = None
        return {}

    delay_menu_t = ease_to(delay_menu_t, delay_menu_target, 13.0)
    if delay_menu_t < 0.01:
        delay_menu_t = 0.0
    if delay_menu_t > 0.99:
        delay_menu_t = 1.0

    ease = delay_menu_t * (2 - delay_menu_t)
    alpha = int(220 * delay_menu_t)
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, int(120 * delay_menu_t)))
    screen.blit(overlay, (0, 0))

    w, h = 440, 230
    x0 = WIDTH // 2 - w // 2
    y0 = HEIGHT // 2 - h // 2
    scale = 0.92 + 0.08 * ease
    panel = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(panel, (*PANEL, alpha), (0, 0, w, h), border_radius=14)
    pygame.draw.rect(panel, (*DIALOG_BORDER, alpha), (0, 0, w, h), 2, border_radius=14)

    def item_anim(idx, duration=0.35):
        delay = idx * 0.06
        t = max(0.0, min(1.0, (delay_menu_t - delay) / duration))
        eased = t * t * (3 - 2 * t)
        return eased, int((1.0 - eased) * 14), int(alpha * eased)

    _, title_slide, title_alpha = item_anim(0)
    title = base_font.render("Delay Block", True, WHITE)
    title.set_alpha(title_alpha)
    panel.blit(title, (20, 20 + title_slide))
    _, sub_slide, sub_alpha = item_anim(1)
    sub = base_small.render(f"Delay: {gate.delay_interval:.2f}s", True, GRAY)
    sub.set_alpha(sub_alpha)
    panel.blit(sub, (20, 54 + sub_slide))

    buttons = {}
    mx, my = pygame.mouse.get_pos()
    adjusts = [("-1.0s", "minus_big"), ("-0.1s", "minus_small"), ("+0.1s", "plus_small"), ("+1.0s", "plus_big")]
    bw = 90
    bh = 40
    gap = 10
    row_y = 94
    row_x = (w - (bw * len(adjusts) + gap * (len(adjusts) - 1))) // 2
    for i, (label, key) in enumerate(adjusts):
        ease_i, slide_i, alpha_i = item_anim(2 + i)
        rect = pygame.Rect(row_x + i * (bw + gap), row_y + slide_i, bw, bh)
        hover = rect.move(x0, y0).collidepoint(mx, my)
        color = BUTTON_CLOCK if not hover else BUTTON_CLOCK_HOVER
        pygame.draw.rect(panel, (*color, alpha_i), rect, border_radius=8)
        pygame.draw.rect(panel, (*DIALOG_BORDER_SOFT, alpha_i), rect, 1, border_radius=8)
        txt = base_small.render(label, True, WHITE)
        txt.set_alpha(alpha_i)
        panel.blit(txt, (rect.centerx - txt.get_width() // 2, rect.centery - txt.get_height() // 2))
        if ease_i > 0.02:
            buttons[key] = rect.move(x0, y0)

    ease_c, slide_c, alpha_c = item_anim(6)
    close_rect = pygame.Rect(w // 2 - 70, h - 58 + slide_c, 140, 38)
    hover = close_rect.move(x0, y0).collidepoint(mx, my)
    color = BUTTON_NEUTRAL if not hover else tuple(min(c + 20, 255) for c in BUTTON_NEUTRAL)
    pygame.draw.rect(panel, (*color, alpha_c), close_rect, border_radius=8)
    pygame.draw.rect(panel, (*DIALOG_BORDER_SOFT, alpha_c), close_rect, 1, border_radius=8)
    txt = base_small.render("Close", True, WHITE)
    txt.set_alpha(alpha_c)
    panel.blit(txt, (close_rect.centerx - txt.get_width() // 2, close_rect.centery - txt.get_height() // 2))
    if ease_c > 0.02:
        buttons["close"] = close_rect.move(x0, y0)

    panel = pygame.transform.smoothscale(panel, (int(w * scale), int(h * scale)))
    screen.blit(panel, (x0 + (w - panel.get_width()) // 2, y0 + (h - panel.get_height()) // 2))
    return buttons


def draw_help_dialog():
    global help_t, help_scroll, help_scroll_target, help_scroll_max
    if not help_open and help_t <= 0.01:
        return {}

    help_t = ease_to(help_t, help_target, 13.0)
    if help_t < 0.01:
        help_t = 0.0
    if help_t > 0.99:
        help_t = 1.0

    ease = help_t * (2 - help_t)
    alpha = int(230 * help_t)
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, int(120 * help_t)))
    screen.blit(overlay, (0, 0))

    w, h = 640, 520
    x0 = WIDTH // 2 - w // 2
    y0 = HEIGHT // 2 - h // 2
    scale = 0.92 + 0.08 * ease
    panel = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(panel, (*PANEL, alpha), (0, 0, w, h), border_radius=14)
    pygame.draw.rect(panel, (*DIALOG_BORDER, alpha), (0, 0, w, h), 2, border_radius=14)

    title = base_font.render("Instructions", True, WHITE)
    title.set_alpha(alpha)
    panel.blit(title, (20, 18))

    lines = [
        "Left click empty space: open gate menu",
        "Left click gate pin to start/finish wiring",
        "Right click: delete hovered wire/gate/note or clear selection",
        "Right drag: pan camera",
        "Mouse wheel: zoom (or scroll open dialogs)",
        "Middle double click: center view on all gates",
        "Double click NOTE: edit note text",
        "Double click CLOCK: open clock menu",
        "Double click DELAY: open delay block menu",
        "Hold BUTTON gate: output on while held",
        "OUTPUT and BUFFER can be dragged like other gates",
        "BUFFER pulses output only on input rising edge",
        "R / T: rotate pin orientation clockwise / counter-clockwise",
        "Backspace: delete selected gates/notes",
        "Tab: open settings",
        "Esc: new file (save prompt)",
        "Space: exit app (save prompt)",
        "Ctrl+S: save (choose segment or whole file)",
        "Ctrl+L: load whole file or segment file",
        "Ctrl+C: copy selected gates/notes",
        "Ctrl+V: paste copied selection at cursor",
        "Ctrl+Shift+V: load and paste segment file at cursor",
        "After paste: only pasted blocks stay selected",
        "Settings are saved inside files and restored on load",
        "Settings > Keybinds lets you change shortcuts",
        "Signal delay setting can be toggled globally",
        "DELAY block uses its own delay value (ignores global delay switch)",
        "Multicolor outputs (RGB) optional in settings",
        "When RGB is on, output mixes active input colors",
    ]
    content_rect = pygame.Rect(18, 56, w - 36, h - 126)
    pygame.draw.rect(panel, (*GRID, int(alpha * 0.35)), content_rect, border_radius=10)
    pygame.draw.rect(panel, (*DIALOG_BORDER_SOFT, int(alpha * 0.75)), content_rect, 1, border_radius=10)

    line_h = 24
    content_h = content_rect.h - 14
    total_h = len(lines) * line_h
    help_scroll_max = max(0.0, float(total_h - content_h))
    help_scroll_target = clamp(help_scroll_target, 0.0, help_scroll_max)
    help_scroll = ease_to(help_scroll, help_scroll_target, 14.0)
    if abs(help_scroll - help_scroll_target) < 0.25:
        help_scroll = help_scroll_target

    scroll_y = int(round(help_scroll))
    prev_clip = panel.get_clip()
    panel.set_clip(content_rect.inflate(-10, -8))
    y = content_rect.y + 7 - scroll_y
    for line in lines:
        if y + line_h >= content_rect.y - 8 and y <= content_rect.bottom + 8:
            txt = base_small.render(line, True, GRAY)
            txt.set_alpha(alpha)
            panel.blit(txt, (content_rect.x + 10, y))
        y += line_h
    panel.set_clip(prev_clip)

    if help_scroll_max > 1.0:
        track = pygame.Rect(content_rect.right - 10, content_rect.y + 8, 4, content_rect.h - 16)
        pygame.draw.rect(panel, (*DIALOG_BORDER_SOFT, int(alpha * 0.7)), track, border_radius=2)
        knob_h = max(22, int(track.h * (content_h / max(content_h + help_scroll_max, 1.0))))
        knob_t = 0.0 if help_scroll_max <= 0 else (help_scroll / help_scroll_max)
        knob_y = int(lerp(track.y, track.bottom - knob_h, knob_t))
        knob = pygame.Rect(track.x - 2, knob_y, 8, knob_h)
        pygame.draw.rect(panel, (*ACCENT, int(alpha * 0.95)), knob, border_radius=4)

    btn = pygame.Rect(w // 2 - 60, h - 55, 120, 38)
    mx, my = pygame.mouse.get_pos()
    hover = btn.move(x0, y0).collidepoint(mx, my)
    color = BUTTON_NEUTRAL
    if hover:
        color = tuple(min(c + 15, 255) for c in color)
    pygame.draw.rect(panel, (*color, alpha), btn, border_radius=8)
    pygame.draw.rect(panel, (*DIALOG_BORDER_SOFT, alpha), btn, 1, border_radius=8)
    txt = base_small.render("Close", True, WHITE)
    txt.set_alpha(alpha)
    panel.blit(txt, (btn.centerx - txt.get_width() // 2, btn.centery - txt.get_height() // 2))

    panel = pygame.transform.smoothscale(panel, (int(w * scale), int(h * scale)))
    screen.blit(panel, (x0 + (w - panel.get_width()) // 2, y0 + (h - panel.get_height()) // 2))
    return {"close": btn.move(x0, y0)}


def draw_settings_dialog():
    global settings_t, settings_slider_rects, settings_scroll, settings_scroll_target, settings_scroll_max
    if not settings_open and settings_t <= 0.01:
        return {}

    def anim(key, target):
        v = settings_anim.get(key, target)
        v = ease_to(v, target, 13.0)
        settings_anim[key] = v
        return v

    settings_t = ease_to(settings_t, settings_target, 13.0)
    if settings_t < 0.01:
        settings_t = 0.0
    if settings_t > 0.99:
        settings_t = 1.0

    ease = settings_t * (2 - settings_t)
    alpha = int(230 * settings_t)
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, int(120 * settings_t)))
    screen.blit(overlay, (0, 0))

    w, h = 700, 560
    x0 = WIDTH // 2 - w // 2
    y0 = HEIGHT // 2 - h // 2
    scale = 0.92 + 0.08 * ease
    panel = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(panel, (*PANEL, alpha), (0, 0, w, h), border_radius=14)
    pygame.draw.rect(panel, (*DIALOG_BORDER, alpha), (0, 0, w, h), 2, border_radius=14)

    title = base_font.render("Settings", True, WHITE)
    title.set_alpha(alpha)
    panel.blit(title, (20, 18))

    buttons = {}
    settings_slider_rects = {}
    mx, my = pygame.mouse.get_pos()

    content_rect = pygame.Rect(18, 58, w - 36, h - 126)
    pygame.draw.rect(panel, (*GRID, int(alpha * 0.35)), content_rect, border_radius=10)
    pygame.draw.rect(panel, (*DIALOG_BORDER_SOFT, int(alpha * 0.75)), content_rect, 1, border_radius=10)

    content_left = content_rect.x + 10
    content_right = content_rect.right - 12
    content_w = content_right - content_left
    settings_scroll_target = clamp(settings_scroll_target, 0.0, settings_scroll_max)
    settings_scroll = ease_to(settings_scroll, settings_scroll_target, 14.0)
    if abs(settings_scroll - settings_scroll_target) < 0.25:
        settings_scroll = settings_scroll_target

    row_y = 0
    row_h = 38

    def draw_toggle(label_text, value, key):
        nonlocal row_y
        label = base_small.render(label_text, True, WHITE)
        label.set_alpha(alpha)
        draw_y = content_rect.y + 8 + row_y - int(round(settings_scroll))
        panel.blit(label, (content_left, draw_y))
        toggle = pygame.Rect(content_right - 98, draw_y - 4, 90, 30)
        t = anim(key, 1.0 if value else 0.0)
        tcolor = lerp_color(TOGGLE_OFF, TOGGLE_ON, t)
        pygame.draw.rect(panel, (*tcolor, alpha), toggle, border_radius=16)
        pygame.draw.rect(panel, (*DIALOG_BORDER_SOFT, alpha), toggle, 1, border_radius=16)
        knob_x = int(toggle.x + lerp(8, 56, t))
        knob = pygame.Rect(knob_x, toggle.y + 5, 24, 20)
        pygame.draw.rect(panel, (*TOGGLE_KNOB, alpha), knob, border_radius=10)
        if toggle.colliderect(content_rect.inflate(-4, -2)):
            buttons[key] = toggle.move(x0, y0)
        row_y += row_h

    def draw_slider(label_text, options, current_value, key):
        nonlocal row_y
        label = base_small.render(label_text, True, WHITE)
        label.set_alpha(alpha)
        draw_y = content_rect.y + 8 + row_y - int(round(settings_scroll))
        panel.blit(label, (content_left, draw_y))
        track = pygame.Rect(content_right - 248, draw_y + 10, 180, 6)
        pygame.draw.rect(panel, (*SLIDER_TRACK, alpha), track, border_radius=3)
        values = [v for v, _ in options]
        labels = [lbl for _, lbl in options]
        idx = min(range(len(values)), key=lambda i: abs(values[i] - current_value))
        t = anim(key, idx / (len(values) - 1) if len(values) > 1 else 0.0)
        knob_x = int(lerp(track.x, track.x + track.w, t))
        knob = pygame.Rect(knob_x - 6, track.y - 6, 12, 18)
        pygame.draw.rect(panel, (*SLIDER_KNOB, alpha), knob, border_radius=6)
        value_txt = base_small.render(labels[idx], True, GRAY)
        value_txt.set_alpha(alpha)
        panel.blit(value_txt, (track.x + track.w + 10, draw_y))
        if track.colliderect(content_rect.inflate(-4, -2)):
            settings_slider_rects[key] = (track.move(x0, y0), options)
        row_y += row_h

    prev_clip = panel.get_clip()
    panel.set_clip(content_rect.inflate(-10, -8))
    draw_toggle("Light mode (white + yellow)", light_mode, "toggle_light_mode")
    draw_toggle("Straight wires", straight_wires, "toggle_straight")
    draw_toggle("Snap to grid", snap_to_grid, "toggle_snap")
    draw_toggle("Show pins at any zoom", show_pins_always, "toggle_pins")
    draw_toggle("Auto-center on double middle click", auto_center, "toggle_center")
    draw_toggle("Signal delay", signal_delay_enabled, "toggle_signal_delay")
    draw_toggle("Multicolor outputs (RGB)", multicolor_outputs, "toggle_multicolor")
    row_y += 8
    draw_slider("Grid size", [(15, "15"), (25, "25"), (35, "35")], grid_step, "grid_size")
    draw_slider("Zoom min", [(0.3, "0.3"), (0.4, "0.4"), (0.5, "0.5")], zoom_min, "zoom_min")
    draw_slider("Zoom max", [(2.0, "2.0"), (2.5, "2.5"), (3.0, "3.0")], zoom_max, "zoom_max")
    draw_slider("Gate label size", [(0.85, "Small"), (1.0, "Normal"), (1.2, "Large")], gate_label_scale, "gate_label")
    draw_slider("Note font size", [(0.85, "Small"), (1.0, "Normal"), (1.2, "Large")], note_font_scale, "note_font")
    draw_slider("Selection brightness", [(0.7, "Low"), (1.0, "Med"), (1.3, "High")], selection_brightness, "sel_bright")
    draw_slider("Wire thickness", [(1.0, "1"), (2.0, "2"), (3.0, "3")], wire_thickness, "wire_thick")
    panel.set_clip(prev_clip)

    settings_scroll_max = max(0.0, float(row_y - (content_rect.h - 14)))
    settings_scroll_target = clamp(settings_scroll_target, 0.0, settings_scroll_max)

    if settings_scroll_max > 1.0:
        track = pygame.Rect(content_rect.right - 10, content_rect.y + 8, 4, content_rect.h - 16)
        pygame.draw.rect(panel, (*DIALOG_BORDER_SOFT, int(alpha * 0.7)), track, border_radius=2)
        vis_h = content_rect.h - 14
        knob_h = max(22, int(track.h * (vis_h / max(vis_h + settings_scroll_max, 1.0))))
        knob_t = 0.0 if settings_scroll_max <= 0 else (settings_scroll / settings_scroll_max)
        knob_y = int(lerp(track.y, track.bottom - knob_h, knob_t))
        knob = pygame.Rect(track.x - 2, knob_y, 8, knob_h)
        pygame.draw.rect(panel, (*ACCENT, int(alpha * 0.95)), knob, border_radius=4)

    # Buttons
    btn_w = 150
    btn_h = 38
    gap = 14
    bx = (w - (btn_w * 3 + gap * 2)) // 2
    by = h - 60
    for i, (label, key) in enumerate([("Instructions", "instructions"), ("Keybinds", "keybinds"), ("Close", "close")]):
        rect = pygame.Rect(bx + i * (btn_w + gap), by, btn_w, btn_h)
        hover = rect.move(x0, y0).collidepoint(mx, my)
        color = BUTTON_ACCENT if key in ("instructions", "keybinds") else BUTTON_NEUTRAL
        if hover:
            color = tuple(min(c + 15, 255) for c in color)
        pygame.draw.rect(panel, (*color, alpha), rect, border_radius=8)
        pygame.draw.rect(panel, (*DIALOG_BORDER_SOFT, alpha), rect, 1, border_radius=8)
        txt = base_small.render(label, True, WHITE)
        txt.set_alpha(alpha)
        panel.blit(txt, (rect.centerx - txt.get_width() // 2, rect.centery - txt.get_height() // 2))
        buttons[key] = rect.move(x0, y0)

    panel = pygame.transform.smoothscale(panel, (int(w * scale), int(h * scale)))
    screen.blit(panel, (x0 + (w - panel.get_width()) // 2, y0 + (h - panel.get_height()) // 2))
    return buttons


def draw_keybinds_dialog():
    global keybinds_t, keybinds_scroll, keybinds_scroll_target, keybinds_scroll_max
    if not keybinds_open and keybinds_t <= 0.01:
        return {}

    keybinds_t = ease_to(keybinds_t, keybinds_target, 13.0)
    if keybinds_t < 0.01:
        keybinds_t = 0.0
    if keybinds_t > 0.99:
        keybinds_t = 1.0

    ease = keybinds_t * (2 - keybinds_t)
    alpha = int(232 * keybinds_t)
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, int(130 * keybinds_t)))
    screen.blit(overlay, (0, 0))

    w, h = 760, 560
    x0 = WIDTH // 2 - w // 2
    y0 = HEIGHT // 2 - h // 2
    scale = 0.92 + 0.08 * ease
    panel = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(panel, (*PANEL, alpha), (0, 0, w, h), border_radius=14)
    pygame.draw.rect(panel, (*DIALOG_BORDER, alpha), (0, 0, w, h), 2, border_radius=14)

    title = base_font.render("Keybinds", True, WHITE)
    title.set_alpha(alpha)
    panel.blit(title, (20, 18))
    hint_text = "Click Change, then press a shortcut"
    if keybind_capture_action is not None:
        action_label = next((label for key, label in KEYBIND_ITEMS if key == keybind_capture_action), keybind_capture_action)
        hint_text = f"Listening: {action_label} (Esc cancels)"
    hint = base_small.render(hint_text, True, GRAY)
    hint.set_alpha(alpha)
    panel.blit(hint, (20, 46))

    content_rect = pygame.Rect(18, 76, w - 36, h - 146)
    pygame.draw.rect(panel, (*GRID, int(alpha * 0.35)), content_rect, border_radius=10)
    pygame.draw.rect(panel, (*DIALOG_BORDER_SOFT, int(alpha * 0.75)), content_rect, 1, border_radius=10)

    keybinds_scroll_target = clamp(keybinds_scroll_target, 0.0, keybinds_scroll_max)
    keybinds_scroll = ease_to(keybinds_scroll, keybinds_scroll_target, 14.0)
    if abs(keybinds_scroll - keybinds_scroll_target) < 0.25:
        keybinds_scroll = keybinds_scroll_target

    buttons = {}
    mx, my = pygame.mouse.get_pos()
    row_h = 34
    row_gap = 6
    y = 0
    prev_clip = panel.get_clip()
    panel.set_clip(content_rect.inflate(-8, -8))
    for action, label in KEYBIND_ITEMS:
        draw_y = content_rect.y + 8 + y - int(round(keybinds_scroll))
        row_rect = pygame.Rect(content_rect.x + 8, draw_y, content_rect.w - 16, row_h)
        bg = lerp_color(PANEL, GRID, 0.35)
        pygame.draw.rect(panel, (*bg, int(alpha * 0.95)), row_rect, border_radius=8)
        pygame.draw.rect(panel, (*DIALOG_BORDER_SOFT, int(alpha * 0.65)), row_rect, 1, border_radius=8)

        label_s = base_small.render(label, True, WHITE)
        label_s.set_alpha(alpha)
        panel.blit(label_s, (row_rect.x + 10, row_rect.centery - label_s.get_height() // 2))

        bind_text = keybind_to_text(keybinds.get(action))
        bind_color = ACCENT if keybind_capture_action == action else GRAY
        bind_s = base_small.render(bind_text, True, bind_color)
        bind_s.set_alpha(alpha)
        panel.blit(bind_s, (row_rect.x + 270, row_rect.centery - bind_s.get_height() // 2))

        cap = "Set" if keybind_capture_action != action else "Cancel"
        cap_s = base_small.render(cap, True, WHITE)
        set_w = cap_s.get_width() + 24
        set_rect = pygame.Rect(row_rect.right - (set_w + 10), row_rect.y + 3, set_w, row_h - 6)

        reset_rect = None
        is_custom = not bindings_equal(keybinds.get(action), DEFAULT_KEYBINDS.get(action))
        if is_custom:
            reset_s = base_small.render("Reset", True, WHITE)
            reset_w = reset_s.get_width() + 24
            reset_rect = pygame.Rect(set_rect.x - (reset_w + 8), row_rect.y + 3, reset_w, row_h - 6)
            r_hover = reset_rect.move(x0, y0).collidepoint(mx, my)
            r_color = BUTTON_DANGER
            if r_hover:
                r_color = tuple(min(c + 15, 255) for c in r_color)
            pygame.draw.rect(panel, (*r_color, alpha), reset_rect, border_radius=7)
            pygame.draw.rect(panel, (*DIALOG_BORDER_SOFT, alpha), reset_rect, 1, border_radius=7)
            reset_s.set_alpha(alpha)
            panel.blit(reset_s, (reset_rect.centerx - reset_s.get_width() // 2, reset_rect.centery - reset_s.get_height() // 2))

        change_rect = set_rect
        hover = change_rect.move(x0, y0).collidepoint(mx, my)
        btn_color = BUTTON_ACCENT if keybind_capture_action != action else TOGGLE_ON
        if hover:
            btn_color = tuple(min(c + 15, 255) for c in btn_color)
        pygame.draw.rect(panel, (*btn_color, alpha), change_rect, border_radius=7)
        pygame.draw.rect(panel, (*DIALOG_BORDER_SOFT, alpha), change_rect, 1, border_radius=7)
        cap_s.set_alpha(alpha)
        panel.blit(cap_s, (change_rect.centerx - cap_s.get_width() // 2, change_rect.centery - cap_s.get_height() // 2))
        if row_rect.colliderect(content_rect.inflate(-4, -2)):
            buttons[f"change_{action}"] = change_rect.move(x0, y0)
            if reset_rect is not None:
                buttons[f"reset_{action}"] = reset_rect.move(x0, y0)
        y += row_h + row_gap
    panel.set_clip(prev_clip)

    keybinds_scroll_max = max(0.0, float(y - (content_rect.h - 10)))
    keybinds_scroll_target = clamp(keybinds_scroll_target, 0.0, keybinds_scroll_max)

    if keybinds_scroll_max > 1.0:
        track = pygame.Rect(content_rect.right - 10, content_rect.y + 8, 4, content_rect.h - 16)
        pygame.draw.rect(panel, (*DIALOG_BORDER_SOFT, int(alpha * 0.7)), track, border_radius=2)
        vis_h = content_rect.h - 10
        knob_h = max(24, int(track.h * (vis_h / max(vis_h + keybinds_scroll_max, 1.0))))
        knob_t = 0.0 if keybinds_scroll_max <= 0 else (keybinds_scroll / keybinds_scroll_max)
        knob_y = int(lerp(track.y, track.bottom - knob_h, knob_t))
        knob = pygame.Rect(track.x - 2, knob_y, 8, knob_h)
        pygame.draw.rect(panel, (*ACCENT, int(alpha * 0.95)), knob, border_radius=4)

    btn_w = 160
    btn_h = 40
    gap = 16
    bx = (w - (btn_w * 2 + gap)) // 2
    by = h - 56
    for i, (label, key) in enumerate([("Reset Defaults", "reset_defaults"), ("Close", "close")]):
        rect = pygame.Rect(bx + i * (btn_w + gap), by, btn_w, btn_h)
        hover = rect.move(x0, y0).collidepoint(mx, my)
        color = BUTTON_DANGER if key == "reset_defaults" else BUTTON_NEUTRAL
        if hover:
            color = tuple(min(c + 15, 255) for c in color)
        pygame.draw.rect(panel, (*color, alpha), rect, border_radius=8)
        pygame.draw.rect(panel, (*DIALOG_BORDER_SOFT, alpha), rect, 1, border_radius=8)
        txt = base_small.render(label, True, WHITE)
        txt.set_alpha(alpha)
        panel.blit(txt, (rect.centerx - txt.get_width() // 2, rect.centery - txt.get_height() // 2))
        buttons[key] = rect.move(x0, y0)

    panel = pygame.transform.smoothscale(panel, (int(w * scale), int(h * scale)))
    screen.blit(panel, (x0 + (w - panel.get_width()) // 2, y0 + (h - panel.get_height()) // 2))
    return buttons


def draw_custom_blocks_dialog():
    global custom_menu_t, custom_menu_scroll, custom_menu_scroll_target, custom_menu_scroll_max
    if not custom_menu_open and custom_menu_t <= 0.01:
        return {}

    custom_menu_t = ease_to(custom_menu_t, custom_menu_target, 13.0)
    if custom_menu_t < 0.01:
        custom_menu_t = 0.0
    if custom_menu_t > 0.99:
        custom_menu_t = 1.0

    ease = custom_menu_t * (2 - custom_menu_t)
    alpha = int(235 * custom_menu_t)
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, int(120 * custom_menu_t)))
    screen.blit(overlay, (0, 0))

    w, h = 780, 560
    x0 = WIDTH // 2 - w // 2
    y0 = HEIGHT // 2 - h // 2
    scale = 0.92 + 0.08 * ease
    panel = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(panel, (*PANEL, alpha), (0, 0, w, h), border_radius=14)
    pygame.draw.rect(panel, (*DIALOG_BORDER, alpha), (0, 0, w, h), 2, border_radius=14)

    title = base_font.render("Custom Gates", True, WHITE)
    title.set_alpha(alpha)
    panel.blit(title, (20, 16))

    buttons = {}
    mx, my = pygame.mouse.get_pos()

    new_rect = pygame.Rect(20, 50, 150, 34)
    new_hover = new_rect.move(x0, y0).collidepoint(mx, my)
    new_color = BUTTON_ACCENT if not new_hover else tuple(min(c + 15, 255) for c in BUTTON_ACCENT)
    pygame.draw.rect(panel, (*new_color, alpha), new_rect, border_radius=8)
    pygame.draw.rect(panel, (*DIALOG_BORDER_SOFT, alpha), new_rect, 1, border_radius=8)
    new_txt = base_small.render("New Block", True, WHITE)
    new_txt.set_alpha(alpha)
    panel.blit(new_txt, (new_rect.centerx - new_txt.get_width() // 2, new_rect.centery - new_txt.get_height() // 2))
    buttons["new"] = new_rect.move(x0, y0)

    content_rect = pygame.Rect(18, 92, w - 36, h - 152)
    pygame.draw.rect(panel, (*GRID, int(alpha * 0.35)), content_rect, border_radius=10)
    pygame.draw.rect(panel, (*DIALOG_BORDER_SOFT, int(alpha * 0.75)), content_rect, 1, border_radius=10)

    custom_menu_scroll_target = clamp(custom_menu_scroll_target, 0.0, custom_menu_scroll_max)
    custom_menu_scroll = ease_to(custom_menu_scroll, custom_menu_scroll_target, 14.0)
    if abs(custom_menu_scroll - custom_menu_scroll_target) < 0.25:
        custom_menu_scroll = custom_menu_scroll_target

    rows = []
    user_items = sorted(custom_gate_defs_user.items(), key=lambda kv: kv[1].get("name", kv[0]).lower())
    file_items = sorted(custom_gate_defs_file.items(), key=lambda kv: kv[1].get("name", kv[0]).lower())
    rows.append(("header", "Your Blocks"))
    if user_items:
        for key, data in user_items:
            rows.append(("item", key, data, True))
    else:
        rows.append(("empty", "No user blocks yet"))
    rows.append(("header", "Loaded Save Blocks"))
    if file_items:
        for key, data in file_items:
            rows.append(("item", key, data, False))
    else:
        rows.append(("empty", "No blocks loaded from file"))

    y = 0
    prev_clip = panel.get_clip()
    panel.set_clip(content_rect.inflate(-8, -8))
    for row in rows:
        draw_y = content_rect.y + 8 + y - int(round(custom_menu_scroll))
        if row[0] == "header":
            txt = base_small.render(row[1], True, ACCENT)
            txt.set_alpha(alpha)
            panel.blit(txt, (content_rect.x + 10, draw_y))
            y += 28
            continue
        if row[0] == "empty":
            txt = base_small.render(row[1], True, GRAY)
            txt.set_alpha(alpha)
            panel.blit(txt, (content_rect.x + 16, draw_y))
            y += 30
            continue

        _, key, data, can_delete = row
        row_rect = pygame.Rect(content_rect.x + 8, draw_y, content_rect.w - 16, 42)
        bg = lerp_color(PANEL, GRID, 0.35)
        pygame.draw.rect(panel, (*bg, int(alpha * 0.95)), row_rect, border_radius=8)
        pygame.draw.rect(panel, (*DIALOG_BORDER_SOFT, int(alpha * 0.7)), row_rect, 1, border_radius=8)

        name = str(data.get("name", key))
        in_count = len(data.get("shape", {}).get("inputs", []))
        out_count = len(data.get("shape", {}).get("outputs", []))
        info = f"{name}  ({in_count} in / {out_count} out)"
        txt = base_small.render(info, True, WHITE)
        txt.set_alpha(alpha)
        panel.blit(txt, (row_rect.x + 10, row_rect.centery - txt.get_height() // 2))

        bx = row_rect.right - 10
        if can_delete:
            d_txt = base_small.render("Delete", True, WHITE)
            d_w = d_txt.get_width() + 20
            d_rect = pygame.Rect(bx - d_w, row_rect.y + 6, d_w, row_rect.h - 12)
            d_hover = d_rect.move(x0, y0).collidepoint(mx, my)
            d_color = BUTTON_DANGER if not d_hover else tuple(min(c + 15, 255) for c in BUTTON_DANGER)
            pygame.draw.rect(panel, (*d_color, alpha), d_rect, border_radius=7)
            pygame.draw.rect(panel, (*DIALOG_BORDER_SOFT, alpha), d_rect, 1, border_radius=7)
            d_txt.set_alpha(alpha)
            panel.blit(d_txt, (d_rect.centerx - d_txt.get_width() // 2, d_rect.centery - d_txt.get_height() // 2))
            buttons[f"delete|{key}"] = d_rect.move(x0, y0)
            bx = d_rect.x - 8

        e_txt = base_small.render("Edit", True, WHITE)
        e_w = e_txt.get_width() + 20
        e_rect = pygame.Rect(bx - e_w, row_rect.y + 6, e_w, row_rect.h - 12)
        e_hover = e_rect.move(x0, y0).collidepoint(mx, my)
        e_color = BUTTON_ACCENT if not e_hover else tuple(min(c + 15, 255) for c in BUTTON_ACCENT)
        pygame.draw.rect(panel, (*e_color, alpha), e_rect, border_radius=7)
        pygame.draw.rect(panel, (*DIALOG_BORDER_SOFT, alpha), e_rect, 1, border_radius=7)
        e_txt.set_alpha(alpha)
        panel.blit(e_txt, (e_rect.centerx - e_txt.get_width() // 2, e_rect.centery - e_txt.get_height() // 2))
        buttons[f"edit|{key}"] = e_rect.move(x0, y0)
        bx = e_rect.x - 8

        p_txt = base_small.render("Place", True, WHITE)
        p_w = p_txt.get_width() + 20
        p_rect = pygame.Rect(bx - p_w, row_rect.y + 6, p_w, row_rect.h - 12)
        p_hover = p_rect.move(x0, y0).collidepoint(mx, my)
        p_color = TOGGLE_ON if not p_hover else tuple(min(c + 15, 255) for c in TOGGLE_ON)
        pygame.draw.rect(panel, (*p_color, alpha), p_rect, border_radius=7)
        pygame.draw.rect(panel, (*DIALOG_BORDER_SOFT, alpha), p_rect, 1, border_radius=7)
        p_txt.set_alpha(alpha)
        panel.blit(p_txt, (p_rect.centerx - p_txt.get_width() // 2, p_rect.centery - p_txt.get_height() // 2))
        buttons[f"place|{key}"] = p_rect.move(x0, y0)

        y += 48
    panel.set_clip(prev_clip)

    custom_menu_scroll_max = max(0.0, float(y - (content_rect.h - 10)))
    custom_menu_scroll_target = clamp(custom_menu_scroll_target, 0.0, custom_menu_scroll_max)
    if custom_menu_scroll_max > 1.0:
        track = pygame.Rect(content_rect.right - 10, content_rect.y + 8, 4, content_rect.h - 16)
        pygame.draw.rect(panel, (*DIALOG_BORDER_SOFT, int(alpha * 0.7)), track, border_radius=2)
        vis_h = content_rect.h - 10
        knob_h = max(24, int(track.h * (vis_h / max(vis_h + custom_menu_scroll_max, 1.0))))
        knob_t = 0.0 if custom_menu_scroll_max <= 0 else (custom_menu_scroll / custom_menu_scroll_max)
        knob_y = int(lerp(track.y, track.bottom - knob_h, knob_t))
        knob = pygame.Rect(track.x - 2, knob_y, 8, knob_h)
        pygame.draw.rect(panel, (*ACCENT, int(alpha * 0.95)), knob, border_radius=4)

    close_rect = pygame.Rect(w // 2 - 70, h - 48, 140, 34)
    close_hover = close_rect.move(x0, y0).collidepoint(mx, my)
    close_color = BUTTON_NEUTRAL if not close_hover else tuple(min(c + 15, 255) for c in BUTTON_NEUTRAL)
    pygame.draw.rect(panel, (*close_color, alpha), close_rect, border_radius=8)
    pygame.draw.rect(panel, (*DIALOG_BORDER_SOFT, alpha), close_rect, 1, border_radius=8)
    close_txt = base_small.render("Close", True, WHITE)
    close_txt.set_alpha(alpha)
    panel.blit(close_txt, (close_rect.centerx - close_txt.get_width() // 2, close_rect.centery - close_txt.get_height() // 2))
    buttons["close"] = close_rect.move(x0, y0)

    panel = pygame.transform.smoothscale(panel, (int(w * scale), int(h * scale)))
    screen.blit(panel, (x0 + (w - panel.get_width()) // 2, y0 + (h - panel.get_height()) // 2))
    return buttons


def run_custom_shape_designer(block_name, initial_block=None):
    shape = (initial_block or {}).get("shape", {}) if isinstance(initial_block, dict) else {}
    rw = max(40, int(shape.get("w", 140)))
    rh = max(30, int(shape.get("h", 90)))
    rect = pygame.Rect(-rw // 2, -rh // 2, rw, rh)
    inputs = []
    outputs = []
    labels = []
    for pin in shape.get("inputs", []) if isinstance(shape.get("inputs", []), list) else []:
        inputs.append({
            "x": rect.centerx + float(pin.get("x", -rw / 2)),
            "y": rect.centery + float(pin.get("y", 0)),
            "label": str(pin.get("label", "")),
        })
    for pin in shape.get("outputs", []) if isinstance(shape.get("outputs", []), list) else []:
        outputs.append({
            "x": rect.centerx + float(pin.get("x", rw / 2)),
            "y": rect.centery + float(pin.get("y", 0)),
            "label": str(pin.get("label", "")),
        })
    for lbl in shape.get("labels", []) if isinstance(shape.get("labels", []), list) else []:
        labels.append({
            "x": rect.centerx + float(lbl.get("x", 0)),
            "y": rect.centery + float(lbl.get("y", 0)),
            "text": str(lbl.get("text", "")),
        })

    tool = "select"
    open_t = 0.0
    running = True
    accepted = False
    drawing_rect = False
    rect_start = (0.0, 0.0)
    dragging = False
    resizing = False
    selected = None
    drag_world_prev = (0.0, 0.0)
    drag_snapshot = None
    drag_changed = False
    pan = False
    pan_start = (0, 0)
    cam_start = (0.0, 0.0)
    d_cam_x = 0.0
    d_cam_y = 0.0
    d_zoom = 1.0
    local_undo = []
    local_redo = []

    def w2s(p):
        return ((p[0] - d_cam_x) * d_zoom + WIDTH / 2, (p[1] - d_cam_y) * d_zoom + HEIGHT / 2)

    def s2w(p):
        return ((p[0] - WIDTH / 2) / d_zoom + d_cam_x, (p[1] - HEIGHT / 2) / d_zoom + d_cam_y)

    def project_all_pins():
        if rect is None:
            return
        for pin in inputs:
            pin["x"], pin["y"] = nearest_point_on_rect_outline(rect, (pin["x"], pin["y"]))
        for pin in outputs:
            pin["x"], pin["y"] = nearest_point_on_rect_outline(rect, (pin["x"], pin["y"]))
        for lbl in labels:
            lbl["x"] = clamp(lbl["x"], rect.left, rect.right)
            lbl["y"] = clamp(lbl["y"], rect.top, rect.bottom)

    def label_hit_index(world_pos):
        if not labels:
            return None
        for i in range(len(labels) - 1, -1, -1):
            lbl = labels[i]
            txt = lbl.get("text", "")
            tw, th = base_small.size(txt if txt else "label")
            hw = max(12.0, (tw / max(d_zoom, 0.01)) * 0.5 + 6.0)
            hh = max(10.0, (th / max(d_zoom, 0.01)) * 0.5 + 4.0)
            if abs(lbl["x"] - world_pos[0]) <= hw and abs(lbl["y"] - world_pos[1]) <= hh:
                return i
        return None

    def input_hit_index(world_pos):
        for i in range(len(inputs) - 1, -1, -1):
            pin = inputs[i]
            if (pin["x"] - world_pos[0]) ** 2 + (pin["y"] - world_pos[1]) ** 2 <= (12 / d_zoom) ** 2:
                return i
        return None

    def output_hit_index(world_pos):
        for i in range(len(outputs) - 1, -1, -1):
            pin = outputs[i]
            if (pin["x"] - world_pos[0]) ** 2 + (pin["y"] - world_pos[1]) ** 2 <= (12 / d_zoom) ** 2:
                return i
        return None

    def local_snapshot():
        return {
            "rect": None if rect is None else (rect.x, rect.y, rect.w, rect.h),
            "inputs": [dict(p) for p in inputs],
            "outputs": [dict(p) for p in outputs],
            "labels": [dict(l) for l in labels],
            "tool": tool,
            "selected": selected,
        }

    def local_restore(state):
        nonlocal rect, inputs, outputs, labels, tool, selected
        r = state.get("rect")
        rect = None if r is None else pygame.Rect(int(r[0]), int(r[1]), int(r[2]), int(r[3]))
        inputs = [dict(p) for p in state.get("inputs", [])]
        outputs = [dict(p) for p in state.get("outputs", [])]
        labels = [dict(l) for l in state.get("labels", [])]
        tool = state.get("tool", tool)
        selected = state.get("selected", None)

    def local_push_undo():
        local_undo.append(local_snapshot())
        local_redo.clear()

    def local_undo_action():
        if not local_undo:
            return
        local_redo.append(local_snapshot())
        local_restore(local_undo.pop())

    def local_redo_action():
        if not local_redo:
            return
        local_undo.append(local_snapshot())
        local_restore(local_redo.pop())

    while running:
        open_t = min(1.0, open_t + 0.12)
        mx, my = pygame.mouse.get_pos()
        world_mouse = s2w((mx, my))
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.KEYDOWN:
                mods = event.mod
                if mods & pygame.KMOD_CTRL:
                    if event.key == pygame.K_z and not (mods & pygame.KMOD_SHIFT):
                        local_undo_action()
                        continue
                    if event.key == pygame.K_y or (event.key == pygame.K_z and (mods & pygame.KMOD_SHIFT)):
                        local_redo_action()
                        continue
                if event.key == pygame.K_ESCAPE:
                    return None
                if event.key in (pygame.K_BACKSPACE, pygame.K_DELETE):
                    if selected is not None and selected[0] in ("label", "input", "output"):
                        idx = selected[1]
                        local_push_undo()
                        if selected[0] == "label" and 0 <= idx < len(labels):
                            del labels[idx]
                        elif selected[0] == "input" and 0 <= idx < len(inputs):
                            del inputs[idx]
                        elif selected[0] == "output" and 0 <= idx < len(outputs):
                            del outputs[idx]
                        selected = None
                    continue
            if event.type == pygame.MOUSEWHEEL:
                prev = s2w((mx, my))
                if event.y > 0:
                    d_zoom = min(2.8, d_zoom * 1.08)
                elif event.y < 0:
                    d_zoom = max(0.35, d_zoom * 0.92)
                after = s2w((mx, my))
                d_cam_x += prev[0] - after[0]
                d_cam_y += prev[1] - after[1]
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                ww = 208
                sidebar = pygame.Rect(0, 0, ww, HEIGHT)
                topbar = pygame.Rect(ww, 0, WIDTH - ww, 56)
                if tool == "select" and not sidebar.collidepoint(event.pos) and not topbar.collidepoint(event.pos):
                    hit_label = label_hit_index(world_mouse)
                    hit_in = input_hit_index(world_mouse)
                    hit_out = output_hit_index(world_mouse)
                    if hit_label is not None or hit_in is not None or hit_out is not None:
                        local_push_undo()
                        if hit_label is not None:
                            del labels[hit_label]
                        elif hit_in is not None:
                            del inputs[hit_in]
                        elif hit_out is not None:
                            del outputs[hit_out]
                        selected = None
                        continue
                pan = True
                pan_start = event.pos
                cam_start = (d_cam_x, d_cam_y)
            if event.type == pygame.MOUSEBUTTONUP and event.button == 3:
                pan = False
            if event.type == pygame.MOUSEMOTION and pan:
                dx = event.pos[0] - pan_start[0]
                dy = event.pos[1] - pan_start[1]
                d_cam_x = cam_start[0] - dx / d_zoom
                d_cam_y = cam_start[1] - dy / d_zoom

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                ww = 208
                sidebar = pygame.Rect(0, 0, ww, HEIGHT)
                topbar = pygame.Rect(ww, 0, WIDTH - ww, 56)
                if sidebar.collidepoint(event.pos):
                    tool_buttons = [
                        ("select", "Select"),
                        ("square", "Draw Square"),
                        ("input", "Draw Inputs"),
                        ("output", "Draw Outputs"),
                        ("label", "Add Labels"),
                    ]
                    by = 90
                    for key, _ in tool_buttons:
                        r = pygame.Rect(16, by, ww - 32, 42)
                        if r.collidepoint(event.pos):
                            tool = key
                            selected = None
                        by += 52
                    continue
                if topbar.collidepoint(event.pos):
                    cancel_r = pygame.Rect(WIDTH - 300, 10, 120, 36)
                    next_r = pygame.Rect(WIDTH - 160, 10, 120, 36)
                    if cancel_r.collidepoint(event.pos):
                        return None
                    if next_r.collidepoint(event.pos) and rect is not None and len(inputs) >= 1 and len(outputs) >= 1:
                        accepted = True
                        running = False
                    continue

                if tool == "square":
                    drawing_rect = True
                    rect_start = world_mouse
                    continue

                if rect is not None and tool in ("input", "output"):
                    px, py = nearest_point_on_rect_outline(rect, world_mouse)
                    target = inputs if tool == "input" else outputs
                    local_push_undo()
                    target.append({"x": px, "y": py, "label": f"{'IN' if tool == 'input' else 'OUT'}{len(target) + 1}"})
                    continue

                if rect is not None and tool == "label":
                    handled = False
                    for i, pin in enumerate(inputs):
                        if (pin["x"] - world_mouse[0]) ** 2 + (pin["y"] - world_mouse[1]) ** 2 <= (12 / d_zoom) ** 2:
                            txt = prompt_text_dialog("Input Label", "Label text:", pin.get("label", ""))
                            if txt is not None:
                                local_push_undo()
                                inputs[i]["label"] = txt
                            handled = True
                            break
                    if not handled:
                        for i, pin in enumerate(outputs):
                            if (pin["x"] - world_mouse[0]) ** 2 + (pin["y"] - world_mouse[1]) ** 2 <= (12 / d_zoom) ** 2:
                                txt = prompt_text_dialog("Output Label", "Label text:", pin.get("label", ""))
                                if txt is not None:
                                    local_push_undo()
                                    outputs[i]["label"] = txt
                                handled = True
                                break
                    if not handled and rect.collidepoint(world_mouse):
                        label_text = prompt_text_dialog("Label", "Text to place on block:", "label")
                        if label_text:
                            local_push_undo()
                            labels.append({"x": world_mouse[0], "y": world_mouse[1], "text": label_text})
                    continue

                if tool == "select":
                    selected = None
                    if rect is not None:
                        rx, ry = w2s((rect.right, rect.bottom))
                        if (event.pos[0] - rx) ** 2 + (event.pos[1] - ry) ** 2 <= 14 ** 2:
                            selected = ("rect", None)
                            resizing = True
                            dragging = True
                            continue
                    for i, pin in enumerate(inputs):
                        if (pin["x"] - world_mouse[0]) ** 2 + (pin["y"] - world_mouse[1]) ** 2 <= (12 / d_zoom) ** 2:
                            selected = ("input", i)
                            break
                    if selected is None:
                        for i, pin in enumerate(outputs):
                            if (pin["x"] - world_mouse[0]) ** 2 + (pin["y"] - world_mouse[1]) ** 2 <= (12 / d_zoom) ** 2:
                                selected = ("output", i)
                                break
                    if selected is None:
                        hit_label = label_hit_index(world_mouse)
                        if hit_label is not None:
                            selected = ("label", hit_label)
                    if selected is None and rect is not None and rect.collidepoint(world_mouse):
                        selected = ("rect", None)
                    if selected is not None:
                        dragging = True
                        drag_world_prev = world_mouse
                        drag_snapshot = local_snapshot()
                        drag_changed = False

            if event.type == pygame.MOUSEMOTION:
                if drawing_rect:
                    p0 = rect_start
                    p1 = world_mouse
                    x = min(p0[0], p1[0])
                    y = min(p0[1], p1[1])
                    w = max(40, abs(p1[0] - p0[0]))
                    h = max(30, abs(p1[1] - p0[1]))
                    if rect is None:
                        local_push_undo()
                    rect = pygame.Rect(int(x), int(y), int(w), int(h))
                    project_all_pins()
                if dragging and selected is not None:
                    dx = world_mouse[0] - drag_world_prev[0]
                    dy = world_mouse[1] - drag_world_prev[1]
                    drag_world_prev = world_mouse
                    if selected[0] == "rect" and rect is not None:
                        if resizing:
                            rect.w = max(40, int(world_mouse[0] - rect.x))
                            rect.h = max(30, int(world_mouse[1] - rect.y))
                            project_all_pins()
                        else:
                            rect.x += int(dx)
                            rect.y += int(dy)
                            for pin in inputs:
                                pin["x"] += dx
                                pin["y"] += dy
                            for pin in outputs:
                                pin["x"] += dx
                                pin["y"] += dy
                            for lbl in labels:
                                lbl["x"] += dx
                                lbl["y"] += dy
                    elif selected[0] == "input" and rect is not None:
                        i = selected[1]
                        inputs[i]["x"], inputs[i]["y"] = nearest_point_on_rect_outline(rect, world_mouse)
                    elif selected[0] == "output" and rect is not None:
                        i = selected[1]
                        outputs[i]["x"], outputs[i]["y"] = nearest_point_on_rect_outline(rect, world_mouse)
                    elif selected[0] == "label" and rect is not None:
                        i = selected[1]
                        labels[i]["x"] = clamp(labels[i]["x"] + dx, rect.left, rect.right)
                        labels[i]["y"] = clamp(labels[i]["y"] + dy, rect.top, rect.bottom)
                    if abs(dx) > 0.001 or abs(dy) > 0.001:
                        drag_changed = True
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                drawing_rect = False
                dragging = False
                resizing = False
                if drag_snapshot is not None and drag_changed:
                    local_undo.append(drag_snapshot)
                    local_redo.clear()
                drag_snapshot = None
                drag_changed = False

        screen.fill(BG)
        step = grid_step
        top_left = s2w((0, 0))
        bot_right = s2w((WIDTH, HEIGHT))
        x0 = int(math.floor(top_left[0] / step) * step)
        x1 = int(math.ceil(bot_right[0] / step) * step)
        y0 = int(math.floor(top_left[1] / step) * step)
        y1 = int(math.ceil(bot_right[1] / step) * step)
        for x in range(x0, x1 + step, step):
            sx, sy0 = w2s((x, y0))
            _, sy1 = w2s((x, y1))
            pygame.draw.line(screen, GRID, (sx, sy0), (sx, sy1), 1)
        for y in range(y0, y1 + step, step):
            sx0, sy = w2s((x0, y))
            sx1, _ = w2s((x1, y))
            pygame.draw.line(screen, GRID, (sx0, sy), (sx1, sy), 1)

        if rect is not None:
            tl = w2s((rect.x, rect.y))
            br = w2s((rect.right, rect.bottom))
            draw_rect = pygame.Rect(int(tl[0]), int(tl[1]), int(br[0] - tl[0]), int(br[1] - tl[1]))
            fill = lerp_color(MENU_TILE, PANEL, 0.25)
            pygame.draw.rect(screen, fill, draw_rect, border_radius=10)
            pygame.draw.rect(screen, ACCENT if selected and selected[0] == "rect" else DIALOG_BORDER_SOFT, draw_rect, 2, border_radius=10)
            if block_name:
                name_font = base_font
                shown = str(block_name)
                max_w = max(40, draw_rect.w - 16)
                if name_font.size(shown)[0] > max_w:
                    trimmed = shown
                    while trimmed and name_font.size(trimmed + "...")[0] > max_w:
                        trimmed = trimmed[:-1]
                    shown = (trimmed + "...") if trimmed else "..."
                name_surf = name_font.render(shown, True, WHITE)
                screen.blit(
                    name_surf,
                    (draw_rect.centerx - name_surf.get_width() // 2, draw_rect.centery - name_surf.get_height() // 2),
                )
            hx, hy = w2s((rect.right, rect.bottom))
            pygame.draw.circle(screen, ACCENT, (int(hx), int(hy)), 6)
        for pin in inputs:
            sx, sy = w2s((pin["x"], pin["y"]))
            pygame.draw.circle(screen, GREEN, (int(sx), int(sy)), 6)
            if pin.get("label"):
                txt = base_small.render(pin["label"], True, WHITE)
                screen.blit(txt, (int(sx - txt.get_width() - 8), int(sy - txt.get_height() / 2)))
        for pin in outputs:
            sx, sy = w2s((pin["x"], pin["y"]))
            pygame.draw.circle(screen, RED, (int(sx), int(sy)), 6)
            if pin.get("label"):
                txt = base_small.render(pin["label"], True, WHITE)
                screen.blit(txt, (int(sx + 8), int(sy - txt.get_height() / 2)))
        for lbl in labels:
            sx, sy = w2s((lbl["x"], lbl["y"]))
            txt = base_small.render(lbl["text"], True, WHITE)
            screen.blit(txt, (int(sx - txt.get_width() / 2), int(sy - txt.get_height() / 2)))

        if rect is not None and tool in ("input", "output"):
            px, py = nearest_point_on_rect_outline(rect, world_mouse)
            sx, sy = w2s((px, py))
            color = GREEN if tool == "input" else RED
            pygame.draw.circle(screen, color, (int(sx), int(sy)), 8, 2)

        sidebar = pygame.Rect(0, 0, 208, HEIGHT)
        pygame.draw.rect(screen, PANEL, sidebar)
        pygame.draw.rect(screen, DIALOG_BORDER_SOFT, sidebar, 1)
        st = base_font.render("Block Designer", True, WHITE)
        screen.blit(st, (16, 18))
        sb = base_small.render(block_name, True, GRAY)
        screen.blit(sb, (16, 46))
        tool_buttons = [
            ("select", "Select"),
            ("square", "Draw Square"),
            ("input", "Draw Inputs"),
            ("output", "Draw Outputs"),
            ("label", "Add Labels"),
        ]
        by = 90
        for key, label in tool_buttons:
            r = pygame.Rect(16, by, sidebar.w - 32, 42)
            active = tool == key
            color = BUTTON_ACCENT if active else BUTTON_NEUTRAL
            pygame.draw.rect(screen, color, r, border_radius=8)
            pygame.draw.rect(screen, DIALOG_BORDER_SOFT, r, 1, border_radius=8)
            txt = base_small.render(label, True, WHITE)
            screen.blit(txt, (r.centerx - txt.get_width() // 2, r.centery - txt.get_height() // 2))
            by += 52

        topbar = pygame.Rect(208, 0, WIDTH - 208, 56)
        pygame.draw.rect(screen, PANEL, topbar)
        pygame.draw.line(screen, DIALOG_BORDER_SOFT, (208, 56), (WIDTH, 56), 1)
        ttitle = base_font.render("Shape Setup", True, WHITE)
        screen.blit(ttitle, (224, 16))
        valid = rect is not None and len(inputs) >= 1 and len(outputs) >= 1
        cancel_r = pygame.Rect(WIDTH - 300, 10, 120, 36)
        next_r = pygame.Rect(WIDTH - 160, 10, 120, 36)
        pygame.draw.rect(screen, BUTTON_NEUTRAL, cancel_r, border_radius=8)
        pygame.draw.rect(screen, DIALOG_BORDER_SOFT, cancel_r, 1, border_radius=8)
        next_color = TOGGLE_ON if valid else TOGGLE_OFF
        pygame.draw.rect(screen, next_color, next_r, border_radius=8)
        pygame.draw.rect(screen, DIALOG_BORDER_SOFT, next_r, 1, border_radius=8)
        ctxt = base_small.render("Cancel", True, WHITE)
        ntxt = base_small.render("Next", True, WHITE)
        screen.blit(ctxt, (cancel_r.centerx - ctxt.get_width() // 2, cancel_r.centery - ctxt.get_height() // 2))
        screen.blit(ntxt, (next_r.centerx - ntxt.get_width() // 2, next_r.centery - ntxt.get_height() // 2))

        if open_t < 1.0:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, int((1.0 - open_t) * 170)))
            screen.blit(overlay, (0, 0))

        pygame.display.flip()
        CLOCK.tick(FPS)

    if not accepted or rect is None or len(inputs) < 1 or len(outputs) < 1:
        return None

    cx, cy = rect.centerx, rect.centery
    return {
        "w": float(rect.w),
        "h": float(rect.h),
        "inputs": [{"x": float(p["x"] - cx), "y": float(p["y"] - cy), "label": p.get("label", "")} for p in inputs],
        "outputs": [{"x": float(p["x"] - cx), "y": float(p["y"] - cy), "label": p.get("label", "")} for p in outputs],
        "labels": [{"x": float(l["x"] - cx), "y": float(l["y"] - cy), "text": l.get("text", "")} for l in labels],
    }


def run_custom_logic_editor(block_def):
    definition = copy_custom_block(block_def)
    shape = definition.get("shape", {})
    in_pins = shape.get("inputs", [])
    out_pins = shape.get("outputs", [])

    local_gates = []
    gates_by_id = {}

    def add_gate(g):
        local_gates.append(g)
        gates_by_id[g.id] = g
        return g

    logic = definition.get("logic", {})
    loaded = logic.get("gates", []) if isinstance(logic, dict) else []
    if loaded:
        for n in loaded:
            g = Gate(n.get("type", "NOT"), float(n.get("x", 0.0)), float(n.get("y", 0.0)), custom_key=n.get("custom_key"))
            g.id = int(n.get("id", g.id))
            g.pin_orient = int(n.get("pin_orient", 0)) % 4
            g.inputs = [normalize_conn(c) for c in n.get("inputs", [])]
            g.delay_interval = max(0.1, float(n.get("delay_interval", g.delay_interval)))
            g.buffer_flash_time = max(0.01, float(n.get("buffer_flash_time", g.buffer_flash_time)))
            add_gate(g)
    input_ids = [int(v) for v in logic.get("input_ids", []) if isinstance(v, int)]
    output_ids = [int(v) for v in logic.get("output_ids", []) if isinstance(v, int)]

    if not loaded:
        scale = 3.0
        for i, p in enumerate(in_pins):
            g = Gate("INPUT", float(p.get("x", -40)) * scale, float(p.get("y", 0)) * scale)
            g.inputs = []
            g.locked_io = True
            g.io_kind = "in"
            g.io_index = i
            add_gate(g)
            input_ids.append(g.id)
        for i, p in enumerate(out_pins):
            g = Gate("OUTPUT", float(p.get("x", 40)) * scale, float(p.get("y", 0)) * scale)
            g.inputs = [None]
            g.locked_io = True
            g.io_kind = "out"
            g.io_index = i
            add_gate(g)
            output_ids.append(g.id)
    else:
        for idx, gid in enumerate(input_ids):
            g = gates_by_id.get(gid)
            if not g:
                continue
            g.type = "INPUT"
            g.inputs = []
            g.locked_io = True
            g.io_kind = "in"
            g.io_index = idx
        for idx, gid in enumerate(output_ids):
            g = gates_by_id.get(gid)
            if not g:
                continue
            g.type = "OUTPUT"
            g.inputs = [g.inputs[0] if g.inputs else None]
            g.locked_io = True
            g.io_kind = "out"
            g.io_index = idx
        scale = 3.0
        if len(input_ids) < len(in_pins):
            for i in range(len(input_ids), len(in_pins)):
                p = in_pins[i]
                g = Gate("INPUT", float(p.get("x", -40)) * scale, float(p.get("y", 0)) * scale)
                g.inputs = []
                g.locked_io = True
                g.io_kind = "in"
                g.io_index = i
                add_gate(g)
                input_ids.append(g.id)
        if len(output_ids) < len(out_pins):
            for i in range(len(output_ids), len(out_pins)):
                p = out_pins[i]
                g = Gate("OUTPUT", float(p.get("x", 40)) * scale, float(p.get("y", 0)) * scale)
                g.inputs = [None]
                g.locked_io = True
                g.io_kind = "out"
                g.io_index = i
                add_gate(g)
                output_ids.append(g.id)

    selected_tool = "select"
    place_types = ["NOT", "AND", "NAND", "OR", "NOR", "XOR", "XNOR", "BUFFER", "DELAY"]
    selected_ids_local = set()
    wire_from_local = None
    drag_gate = None
    drag_pending = False
    drag_start = (0, 0)
    drag_world_start = (0.0, 0.0)
    drag_group_start = {}
    pan = False
    pan_start = (0, 0)
    cam_start = (0.0, 0.0)
    d_cam_x = 0.0
    d_cam_y = 0.0
    d_zoom = 1.0
    open_t = 0.0
    running = True
    accepted = False
    local_dt = 1.0 / FPS
    local_delay_pending = {}
    last_click_gate_id_local = None
    last_click_gate_time_local = 0
    local_undo_stack = []
    local_redo_stack = []
    local_drag_snapshot = None
    local_drag_active = False

    def w2s(p):
        return ((p[0] - d_cam_x) * d_zoom + WIDTH / 2, (p[1] - d_cam_y) * d_zoom + HEIGHT / 2)

    def s2w(p):
        return ((p[0] - WIDTH / 2) / d_zoom + d_cam_x, (p[1] - HEIGHT / 2) / d_zoom + d_cam_y)

    def local_gate_at(world_pos):
        for g in reversed(local_gates):
            if g.rect().collidepoint(world_pos):
                return g
        return None

    def local_find_pin_hit(world_pos):
        for g in reversed(local_gates):
            oidx = output_hit(g, world_pos)
            if oidx is not None:
                return (g, "out", oidx)
            iidx = input_hit(g, world_pos)
            if iidx is not None:
                return (g, "in", iidx)
        return (None, None, None)

    def local_delete_gate(g):
        if g.locked_io:
            return
        if g in local_gates:
            local_gates.remove(g)
        gates_by_id.pop(g.id, None)
        for other in local_gates:
            for i, conn in enumerate(other.inputs):
                if conn_source_id(conn) == g.id:
                    other.inputs[i] = None

    def local_serialize_state():
        return {
            "gates": [
                {
                    "id": g.id,
                    "type": g.type,
                    "custom_key": g.custom_key if g.type == "CUSTOM" else None,
                    "x": g.x,
                    "y": g.y,
                    "pin_orient": g.pin_orient,
                    "inputs": [normalize_conn(c) for c in g.inputs],
                    "input_state": g.input_state,
                    "output": g.output,
                    "delay_interval": g.delay_interval,
                    "buffer_prev_input": g.buffer_prev_input,
                    "buffer_pulse": g.buffer_pulse,
                    "buffer_flash_time": g.buffer_flash_time,
                    "locked_io": bool(getattr(g, "locked_io", False)),
                    "io_kind": getattr(g, "io_kind", None),
                    "io_index": getattr(g, "io_index", None),
                }
                for g in local_gates
            ],
            "selected_ids": list(selected_ids_local),
            "wire_from": normalize_conn(wire_from_local),
            "delay_pending": {
                str(gid): [bool(v[0]), float(v[1])]
                for gid, v in local_delay_pending.items()
                if isinstance(v, (list, tuple)) and len(v) == 2
            },
        }

    def local_restore_state(state):
        nonlocal local_gates, gates_by_id, selected_ids_local, wire_from_local
        nonlocal local_delay_pending, drag_pending, drag_gate, drag_group_start
        nonlocal local_drag_snapshot, local_drag_active
        local_gates = []
        gates_by_id = {}
        for n in state.get("gates", []):
            g = Gate(n.get("type", "NOT"), float(n.get("x", 0.0)), float(n.get("y", 0.0)), custom_key=n.get("custom_key"))
            g.id = int(n.get("id", g.id))
            g.pin_orient = int(n.get("pin_orient", 0)) % 4
            g.inputs = [normalize_conn(c) for c in n.get("inputs", [])]
            g.input_state = bool(n.get("input_state", False))
            g.output = bool(n.get("output", False))
            g.delay_interval = max(0.1, float(n.get("delay_interval", g.delay_interval)))
            g.buffer_prev_input = bool(n.get("buffer_prev_input", False))
            g.buffer_pulse = max(0.0, float(n.get("buffer_pulse", 0.0)))
            g.buffer_flash_time = max(0.01, float(n.get("buffer_flash_time", g.buffer_flash_time)))
            g.locked_io = bool(n.get("locked_io", False))
            g.io_kind = n.get("io_kind", None)
            g.io_index = n.get("io_index", None)
            g.draw_x = g.x
            g.draw_y = g.y
            local_gates.append(g)
            gates_by_id[g.id] = g

        selected_ids_local = {gid for gid in state.get("selected_ids", []) if gid in gates_by_id}
        wire_from_local = normalize_conn(state.get("wire_from"))
        if wire_from_local is not None and conn_source_id(wire_from_local) not in gates_by_id:
            wire_from_local = None

        local_delay_pending = {}
        for gid_txt, v in state.get("delay_pending", {}).items():
            try:
                gid = int(gid_txt)
            except Exception:
                continue
            if gid not in gates_by_id or gates_by_id[gid].type != "DELAY":
                continue
            if isinstance(v, (list, tuple)) and len(v) == 2:
                local_delay_pending[gid] = (bool(v[0]), max(0.0, float(v[1])))

        drag_pending = False
        drag_gate = None
        drag_group_start = {}
        local_drag_snapshot = None
        local_drag_active = False

    def local_push_undo():
        local_undo_stack.append(local_serialize_state())
        local_redo_stack.clear()

    def local_undo():
        if not local_undo_stack:
            return
        local_redo_stack.append(local_serialize_state())
        prev = local_undo_stack.pop()
        local_restore_state(prev)

    def local_redo():
        if not local_redo_stack:
            return
        local_undo_stack.append(local_serialize_state())
        nxt = local_redo_stack.pop()
        local_restore_state(nxt)

    def eval_local(dt):
        by = {g.id: g for g in local_gates}
        for g in local_gates:
            g.draw_x = g.x
            g.draw_y = g.y
            if g.type == "INPUT":
                g.output = g.input_state

        def eval_combinational():
            for _ in range(30):
                changed = False
                for g in local_gates:
                    if g.type in ("INPUT", "BUFFER", "DELAY"):
                        continue
                    vals = [conn_output_state(c, by) for c in g.inputs]
                    desired = False
                    if g.type == "OUTPUT":
                        desired = vals[0] if vals else False
                    elif g.type == "NOT":
                        desired = not (vals[0] if vals else False)
                    elif g.type == "AND":
                        desired = all(vals) if vals else False
                    elif g.type == "NAND":
                        desired = not (all(vals) if vals else False)
                    elif g.type == "OR":
                        desired = any(vals) if vals else False
                    elif g.type == "NOR":
                        desired = not (any(vals) if vals else False)
                    elif g.type == "XOR":
                        desired = sum(1 for v in vals if v) == 1
                    elif g.type == "XNOR":
                        desired = sum(1 for v in vals if v) != 1
                    if g.output != desired:
                        g.output = desired
                        changed = True
                if not changed:
                    break

        eval_combinational()

        # BUFFER: short pulse on rising edge.
        for g in local_gates:
            if g.type != "BUFFER":
                continue
            incoming = conn_output_state(g.inputs[0], by) if g.inputs else False
            if incoming and not g.buffer_prev_input:
                g.buffer_pulse = max(g.buffer_pulse, g.buffer_flash_time)
            g.buffer_prev_input = incoming
            g.buffer_pulse = max(0.0, g.buffer_pulse - max(0.0, dt))
            g.output = g.buffer_pulse > 0.0

        # DELAY: output changes after configured interval.
        live_delay_ids = set()
        for g in local_gates:
            if g.type != "DELAY":
                continue
            live_delay_ids.add(g.id)
            desired = conn_output_state(g.inputs[0], by) if g.inputs else False
            pending = local_delay_pending.get(g.id)
            if desired != g.output:
                if pending is None or bool(pending[0]) != bool(desired):
                    local_delay_pending[g.id] = (bool(desired), max(0.1, float(g.delay_interval)))
                    pending = local_delay_pending[g.id]
            else:
                if pending is not None:
                    local_delay_pending.pop(g.id, None)
                    pending = None
            if pending is not None:
                target, remain = pending
                remain -= max(0.0, dt)
                if remain <= 0.0:
                    g.output = bool(target)
                    local_delay_pending.pop(g.id, None)
                else:
                    local_delay_pending[g.id] = (bool(target), remain)
        for gid in list(local_delay_pending.keys()):
            if gid not in live_delay_ids:
                local_delay_pending.pop(gid, None)

        eval_combinational()

    while running:
        open_t = min(1.0, open_t + 0.12)
        mx, my = pygame.mouse.get_pos()
        world_mouse = s2w((mx, my))
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.KEYDOWN:
                mods = event.mod
                if mods & pygame.KMOD_CTRL:
                    if event.key == pygame.K_z and not (mods & pygame.KMOD_SHIFT):
                        local_undo()
                        continue
                    if event.key == pygame.K_y or (event.key == pygame.K_z and (mods & pygame.KMOD_SHIFT)):
                        local_redo()
                        continue
                if event.key == pygame.K_ESCAPE:
                    return None
                if event.key == pygame.K_BACKSPACE:
                    can_delete = any((gid in gates_by_id and not gates_by_id[gid].locked_io) for gid in selected_ids_local)
                    if can_delete:
                        local_push_undo()
                    for gid in list(selected_ids_local):
                        g = gates_by_id.get(gid)
                        if g and not g.locked_io:
                            local_delete_gate(g)
                    selected_ids_local = {gid for gid in selected_ids_local if gid in gates_by_id}
            if event.type == pygame.MOUSEWHEEL:
                prev = s2w((mx, my))
                if event.y > 0:
                    d_zoom = min(2.8, d_zoom * 1.08)
                elif event.y < 0:
                    d_zoom = max(0.35, d_zoom * 0.92)
                after = s2w((mx, my))
                d_cam_x += prev[0] - after[0]
                d_cam_y += prev[1] - after[1]
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                pan = True
                pan_start = event.pos
                cam_start = (d_cam_x, d_cam_y)
            if event.type == pygame.MOUSEBUTTONUP and event.button == 3:
                pan = False
            if event.type == pygame.MOUSEMOTION and pan:
                dx = event.pos[0] - pan_start[0]
                dy = event.pos[1] - pan_start[1]
                d_cam_x = cam_start[0] - dx / d_zoom
                d_cam_y = cam_start[1] - dy / d_zoom

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                ww = 220
                sidebar = pygame.Rect(0, 0, ww, HEIGHT)
                topbar = pygame.Rect(ww, 0, WIDTH - ww, 56)
                if sidebar.collidepoint(event.pos):
                    by = 84
                    select_r = pygame.Rect(16, by, ww - 32, 38)
                    if select_r.collidepoint(event.pos):
                        selected_tool = "select"
                    by += 48
                    for gtype in place_types:
                        r = pygame.Rect(16, by, ww - 32, 34)
                        if r.collidepoint(event.pos):
                            selected_tool = gtype
                        by += 40
                    continue
                if topbar.collidepoint(event.pos):
                    cancel_r = pygame.Rect(WIDTH - 300, 10, 120, 36)
                    save_r = pygame.Rect(WIDTH - 160, 10, 120, 36)
                    if cancel_r.collidepoint(event.pos):
                        return None
                    if save_r.collidepoint(event.pos):
                        accepted = True
                        running = False
                    continue

                hit_gate, hit_kind, hit_idx = local_find_pin_hit(world_mouse)
                if hit_gate is not None:
                    if wire_from_local is None and hit_kind == "out":
                        wire_from_local = make_conn(hit_gate.id, hit_idx if hit_idx is not None else 0)
                    elif wire_from_local is not None and hit_kind == "in":
                        if normalize_conn(hit_gate.inputs[hit_idx]) != normalize_conn(wire_from_local):
                            local_push_undo()
                        hit_gate.inputs[hit_idx] = wire_from_local
                        wire_from_local = None
                    continue

                g = local_gate_at(world_mouse)
                if g is not None:
                    if g.id not in selected_ids_local:
                        selected_ids_local = {g.id}
                    drag_gate = g
                    drag_pending = True
                    local_drag_snapshot = None
                    local_drag_active = False
                    drag_start = event.pos
                    drag_world_start = world_mouse
                    drag_group_start = {gid: (gates_by_id[gid].x, gates_by_id[gid].y) for gid in selected_ids_local if gid in gates_by_id}
                    continue

                if selected_tool != "select":
                    local_push_undo()
                    p = snap_world(world_mouse)
                    ng = Gate(selected_tool, p[0], p[1])
                    add_gate(ng)
                    selected_ids_local = {ng.id}

            if event.type == pygame.MOUSEMOTION and drag_pending and drag_gate is not None:
                dx = event.pos[0] - drag_start[0]
                dy = event.pos[1] - drag_start[1]
                if abs(dx) >= DRAG_THRESHOLD or abs(dy) >= DRAG_THRESHOLD:
                    if local_drag_snapshot is None:
                        local_drag_snapshot = local_serialize_state()
                    world_now = world_mouse
                    dxw = world_now[0] - drag_world_start[0]
                    dyw = world_now[1] - drag_world_start[1]
                    moved_any = False
                    for gid, (sx, sy) in drag_group_start.items():
                        gg = gates_by_id.get(gid)
                        if gg:
                            nx, ny = snap_world((sx + dxw, sy + dyw))
                            if nx != gg.x or ny != gg.y:
                                moved_any = True
                            gg.x = nx
                            gg.y = ny
                    if moved_any:
                        local_drag_active = True

            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if drag_pending and drag_gate is not None:
                    dx = event.pos[0] - drag_start[0]
                    dy = event.pos[1] - drag_start[1]
                    if abs(dx) < DRAG_THRESHOLD and abs(dy) < DRAG_THRESHOLD and drag_gate.locked_io and drag_gate.type == "INPUT":
                        drag_gate.input_state = not drag_gate.input_state
                    elif abs(dx) < DRAG_THRESHOLD and abs(dy) < DRAG_THRESHOLD and not drag_gate.locked_io and drag_gate.type == "DELAY":
                        now = pygame.time.get_ticks()
                        if last_click_gate_id_local == drag_gate.id and now - last_click_gate_time_local <= 350:
                            entered = prompt_text_dialog("Delay Time", "Seconds (min 0.1):", f"{drag_gate.delay_interval:.2f}")
                            if entered is not None:
                                try:
                                    new_delay = max(0.1, float(entered))
                                    if abs(new_delay - drag_gate.delay_interval) > 1e-9:
                                        local_push_undo()
                                        drag_gate.delay_interval = new_delay
                                except Exception:
                                    pass
                            last_click_gate_id_local = None
                            last_click_gate_time_local = 0
                        else:
                            last_click_gate_id_local = drag_gate.id
                            last_click_gate_time_local = now
                    if local_drag_active and local_drag_snapshot is not None:
                        local_undo_stack.append(local_drag_snapshot)
                        local_redo_stack.clear()
                    drag_pending = False
                    drag_gate = None
                    local_drag_snapshot = None
                    local_drag_active = False

            if event.type == pygame.MOUSEBUTTONUP and event.button == 3:
                hit_gate, hit_kind, hit_idx = local_find_pin_hit(world_mouse)
                if hit_gate and hit_kind == "in":
                    if hit_gate.inputs[hit_idx] is not None:
                        local_push_undo()
                    hit_gate.inputs[hit_idx] = None
                else:
                    target = hit_gate if hit_gate is not None else local_gate_at(world_mouse)
                    if target and not target.locked_io:
                        local_push_undo()
                        local_delete_gate(target)

        eval_local(local_dt)

        screen.fill(BG)
        step = grid_step
        top_left = s2w((0, 0))
        bot_right = s2w((WIDTH, HEIGHT))
        x0 = int(math.floor(top_left[0] / step) * step)
        x1 = int(math.ceil(bot_right[0] / step) * step)
        y0 = int(math.floor(top_left[1] / step) * step)
        y1 = int(math.ceil(bot_right[1] / step) * step)
        for x in range(x0, x1 + step, step):
            sx, sy0 = w2s((x, y0))
            _, sy1 = w2s((x, y1))
            pygame.draw.line(screen, GRID, (sx, sy0), (sx, sy1), 1)
        for y in range(y0, y1 + step, step):
            sx0, sy = w2s((x0, y))
            sx1, _ = w2s((x1, y))
            pygame.draw.line(screen, GRID, (sx0, sy), (sx1, sy), 1)

        by_id = {g.id: g for g in local_gates}
        for g in local_gates:
            for idx, conn in enumerate(g.inputs):
                if conn is None:
                    continue
                sid, so = conn_parts(conn)
                src = by_id.get(sid)
                if not src:
                    continue
                sx, sy = src.output_pos_draw_idx(so)
                tx, ty = g.input_pos_draw(idx)
                color = WIRE_ON if gate_output_state(src, so) else WIRE_OFF
                pygame.draw.line(screen, color, w2s((sx, sy)), w2s((tx, ty)), max(1, int(2 * d_zoom * wire_thickness)))

        for g in local_gates:
            g.draw_x = g.x
            g.draw_y = g.y
            rx, ry, rw, rh = g.rect_draw(1.0)
            sx, sy = w2s((rx, ry))
            rect = pygame.Rect(int(sx), int(sy), int(rw * d_zoom), int(rh * d_zoom))
            color = (90, 90, 110)
            if g.type == "INPUT":
                color = GREEN if g.output else (70, 130, 70)
            elif g.type == "OUTPUT":
                color = RED if g.output else (120, 80, 80)
            elif g.type == "BUFFER":
                color = (95, 170, 190) if g.output else (70, 105, 120)
            elif g.type == "DELAY":
                color = (210, 150, 80) if g.output else (130, 95, 65)
            elif g.output:
                color = (100, 155, 210)
            if g.locked_io:
                color = lerp_color(color, ACCENT, 0.25)
            outline = ACCENT if g.id in selected_ids_local else DIALOG_BORDER_SOFT
            pygame.draw.rect(screen, color, rect, border_radius=8)
            pygame.draw.rect(screen, outline, rect, 2, border_radius=8)
            if g.type == "DELAY":
                label = base_small.render("DELAY", True, WHITE)
                tlabel = base_small.render(f"{g.delay_interval:.2f}s", True, WHITE)
                screen.blit(label, (rect.centerx - label.get_width() // 2, rect.centery - label.get_height()))
                screen.blit(tlabel, (rect.centerx - tlabel.get_width() // 2, rect.centery + 2))
            else:
                label = base_small.render(g.type, True, WHITE)
                screen.blit(label, (rect.centerx - label.get_width() // 2, rect.centery - label.get_height() // 2))
            for i in range(len(g.inputs)):
                ix, iy = g.input_pos_draw(i)
                px, py = w2s((ix, iy))
                pygame.draw.circle(screen, YELLOW, (int(px), int(py)), max(3, int(PIN_RADIUS * d_zoom)))
            for oi in range(gate_output_count(g)):
                ox, oy = g.output_pos_draw_idx(oi)
                px, py = w2s((ox, oy))
                pygame.draw.circle(screen, YELLOW, (int(px), int(py)), max(3, int(PIN_RADIUS * d_zoom)))

        if wire_from_local is not None:
            sid, so = conn_parts(wire_from_local)
            src = by_id.get(sid)
            if src:
                sx, sy = src.output_pos_draw_idx(so)
                pygame.draw.line(screen, WIRE_ON if gate_output_state(src, so) else WIRE_OFF, w2s((sx, sy)), (mx, my), 2)

        sidebar = pygame.Rect(0, 0, 220, HEIGHT)
        pygame.draw.rect(screen, PANEL, sidebar)
        pygame.draw.rect(screen, DIALOG_BORDER_SOFT, sidebar, 1)
        tt = base_font.render("Logic Editor", True, WHITE)
        screen.blit(tt, (16, 14))
        st = base_small.render(definition.get("name", "Custom"), True, GRAY)
        screen.blit(st, (16, 42))
        by = 84
        sr = pygame.Rect(16, by, sidebar.w - 32, 38)
        pygame.draw.rect(screen, BUTTON_ACCENT if selected_tool == "select" else BUTTON_NEUTRAL, sr, border_radius=8)
        pygame.draw.rect(screen, DIALOG_BORDER_SOFT, sr, 1, border_radius=8)
        tx = base_small.render("Select / Wire / Move", True, WHITE)
        screen.blit(tx, (sr.centerx - tx.get_width() // 2, sr.centery - tx.get_height() // 2))
        by += 48
        for gtype in place_types:
            r = pygame.Rect(16, by, sidebar.w - 32, 34)
            pygame.draw.rect(screen, BUTTON_ACCENT if selected_tool == gtype else BUTTON_NEUTRAL, r, border_radius=7)
            pygame.draw.rect(screen, DIALOG_BORDER_SOFT, r, 1, border_radius=7)
            tx = base_small.render(gtype, True, WHITE)
            screen.blit(tx, (r.centerx - tx.get_width() // 2, r.centery - tx.get_height() // 2))
            by += 40

        topbar = pygame.Rect(220, 0, WIDTH - 220, 56)
        pygame.draw.rect(screen, PANEL, topbar)
        pygame.draw.line(screen, DIALOG_BORDER_SOFT, (220, 56), (WIDTH, 56), 1)
        ttitle = base_font.render("Custom Logic", True, WHITE)
        screen.blit(ttitle, (236, 16))
        cancel_r = pygame.Rect(WIDTH - 300, 10, 120, 36)
        save_r = pygame.Rect(WIDTH - 160, 10, 120, 36)
        pygame.draw.rect(screen, BUTTON_NEUTRAL, cancel_r, border_radius=8)
        pygame.draw.rect(screen, DIALOG_BORDER_SOFT, cancel_r, 1, border_radius=8)
        pygame.draw.rect(screen, TOGGLE_ON, save_r, border_radius=8)
        pygame.draw.rect(screen, DIALOG_BORDER_SOFT, save_r, 1, border_radius=8)
        ctxt = base_small.render("Cancel", True, WHITE)
        stxt = base_small.render("Save Block", True, WHITE)
        screen.blit(ctxt, (cancel_r.centerx - ctxt.get_width() // 2, cancel_r.centery - ctxt.get_height() // 2))
        screen.blit(stxt, (save_r.centerx - stxt.get_width() // 2, save_r.centery - stxt.get_height() // 2))

        if open_t < 1.0:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, int((1.0 - open_t) * 170)))
            screen.blit(overlay, (0, 0))

        pygame.display.flip()
        local_dt = CLOCK.tick(FPS) / 1000.0

    if not accepted:
        return None

    nodes = []
    for g in local_gates:
        nodes.append({
            "id": g.id,
            "type": g.type,
            "custom_key": g.custom_key if g.type == "CUSTOM" else None,
            "x": g.x,
            "y": g.y,
            "pin_orient": g.pin_orient,
            "inputs": [normalize_conn(c) for c in g.inputs],
            "delay_interval": g.delay_interval,
            "buffer_flash_time": g.buffer_flash_time,
        })
    in_gates = [g for g in local_gates if getattr(g, "locked_io", False) and getattr(g, "io_kind", "") == "in"]
    out_gates = [g for g in local_gates if getattr(g, "locked_io", False) and getattr(g, "io_kind", "") == "out"]
    in_ids = [g.id for g in sorted(in_gates, key=lambda gg: getattr(gg, "io_index", 0))]
    out_ids = [g.id for g in sorted(out_gates, key=lambda gg: getattr(gg, "io_index", 0))]
    definition["logic"] = {
        "gates": nodes,
        "input_ids": in_ids,
        "output_ids": out_ids,
    }
    return definition


def run_custom_block_builder(existing_key=None, logic_only=False):
    existing = None
    source_map = custom_gate_defs_user
    if existing_key is not None:
        existing = get_custom_gate_def(existing_key)
        if existing_key in custom_gate_defs_file:
            source_map = custom_gate_defs_file
        if existing is None:
            return None

    if existing is None:
        name = prompt_text_dialog("New Custom Block", "Block name:", "My Block")
        if not name:
            return None
        working = {"name": name, "shape": {}, "logic": {}, "source": "user"}
        shape = run_custom_shape_designer(name, working)
        if shape is None:
            return None
        working["shape"] = shape
        working = run_custom_logic_editor(working)
        if working is None:
            return None
        key = new_user_block_key(name)
        working["key"] = key
        working["source"] = "user"
        custom_gate_defs_user[key] = normalize_custom_block(working, source="user")
        mark_settings_dirty()
        return key

    working = copy_custom_block(existing)
    if not logic_only:
        shape = run_custom_shape_designer(working.get("name", "Custom"), working)
        if shape is None:
            return None
        working["shape"] = shape
    edited = run_custom_logic_editor(working)
    if edited is None:
        return None
    edited["key"] = existing_key
    edited["source"] = "user" if source_map is custom_gate_defs_user else "file"
    source_map[existing_key] = normalize_custom_block(edited, source=edited["source"])
    refresh_custom_gate_instances(existing_key)
    mark_settings_dirty()
    return existing_key


def draw_wires():
    gates_by_id = {g.id: g for g in gates if not g.deleting}

    def output_dir(g, out_idx=0):
        if g.type == "CUSTOM":
            ox, oy = g.output_pos_draw_idx(out_idx)
            dx = ox - g.draw_x
            dy = oy - g.draw_y
            if abs(dx) >= abs(dy):
                return (1, 0) if dx >= 0 else (-1, 0)
            return (0, 1) if dy >= 0 else (0, -1)
        if g.pin_orient == 0:
            return (1, 0)
        if g.pin_orient == 1:
            return (0, -1)
        if g.pin_orient == 2:
            return (-1, 0)
        return (0, 1)

    def input_dir(g):
        if g.pin_orient == 0:
            return (1, 0)
        if g.pin_orient == 1:
            return (0, -1)
        if g.pin_orient == 2:
            return (-1, 0)
        return (0, 1)

    def snap(v, step):
        return round(v / step) * step

    def build_obstacles(clearance=10):
        rects = []
        for gg in gates:
            if gg.deleting:
                continue
            r = gg.rect()
            r = pygame.Rect(gg.draw_x - r.w / 2, gg.draw_y - r.h / 2, r.w, r.h)
            r.inflate_ip(clearance * 2, clearance * 2)
            rects.append(r)
        return rects

    def point_blocked(p, rects):
        x, y = p
        for r in rects:
            if r.collidepoint(x, y):
                return True
        return False

    def astar_route(start, goal, rects, step=12.5):
        sx, sy = start
        gx, gy = goal
        minx = min(sx, gx)
        maxx = max(sx, gx)
        miny = min(sy, gy)
        maxy = max(sy, gy)
        for r in rects:
            minx = min(minx, r.left)
            maxx = max(maxx, r.right)
            miny = min(miny, r.top)
            maxy = max(maxy, r.bottom)
        margin = 120
        minx -= margin
        maxx += margin
        miny -= margin
        maxy += margin

        sx = snap(sx, step)
        sy = snap(sy, step)
        gx = snap(gx, step)
        gy = snap(gy, step)

        start = (sx, sy)
        goal = (gx, gy)
        if point_blocked(start, rects) or point_blocked(goal, rects):
            return [start, goal]

        def h(p):
            return abs(p[0] - goal[0]) + abs(p[1] - goal[1])

        open_heap = []
        heapq.heappush(open_heap, (h(start), 0, start))
        g_score = {start: 0}
        came = {}
        prev_dir = {}
        closed = set()
        counter = 0

        def neighbors(p):
            x, y = p
            return [(x + step, y), (x - step, y), (x, y + step), (x, y - step)]

        while open_heap:
            _, _, current = heapq.heappop(open_heap)
            if current in closed:
                continue
            if current == goal:
                path = [current]
                while current in came:
                    current = came[current]
                    path.append(current)
                path.reverse()
                return path

            closed.add(current)
            cx, cy = current
            for n in neighbors(current):
                nx, ny = n
                if nx < minx or nx > maxx or ny < miny or ny > maxy:
                    continue
                if point_blocked(n, rects):
                    continue
                if n in closed:
                    continue
                move_dir = (nx - cx, ny - cy)
                turn_cost = 0
                if current in prev_dir and prev_dir[current] != move_dir:
                    turn_cost = 6
                tentative = g_score.get(current, 1e18) + step + turn_cost
                if tentative < g_score.get(n, 1e18):
                    came[n] = current
                    prev_dir[n] = move_dir
                    g_score[n] = tentative
                    counter += 1
                    heapq.heappush(open_heap, (tentative + h(n), counter, n))

        return [start, goal]

    def simplify_path(points):
        if len(points) <= 2:
            return points
        simplified = [points[0]]
        for i in range(1, len(points) - 1):
            x0, y0 = simplified[-1]
            x1, y1 = points[i]
            x2, y2 = points[i + 1]
            if (x1 - x0, y1 - y0) == (x2 - x1, y2 - y1):
                continue
            simplified.append(points[i])
        simplified.append(points[-1])
        return simplified

    obstacles = build_obstacles(clearance=12)
    version = layout_version
    for g in gates:
        if g.deleting:
            continue
        for idx, conn in enumerate(g.inputs):
            if conn is None:
                continue
            src_id, out_idx = conn_parts(conn)
            src = gates_by_id.get(src_id)
            if not src:
                continue
            sx, sy = src.output_pos_draw_idx(out_idx)
            tx, ty = g.input_pos_draw(idx)
            if straight_wires:
                color = WIRE_ON if gate_output_state(src, out_idx) else WIRE_OFF
                thickness = max(1, int(2 * zoom * wire_thickness))
                pygame.draw.line(screen, color, world_to_screen((sx, sy)), world_to_screen((tx, ty)), thickness)
                continue
            dx, dy = output_dir(src, out_idx)
            lead = 18
            sx2 = sx + dx * lead
            sy2 = sy + dy * lead
            ix, iy = input_dir(g)
            in_pre = (tx - ix * lead, ty - iy * lead)

            key = (
                version,
                src.id,
                out_idx,
                g.id,
                idx,
                src.pin_orient,
                g.pin_orient,
                round(sx, 1),
                round(sy, 1),
                round(tx, 1),
                round(ty, 1),
            )
            cached = wire_cache.get(key)
            if cached is None:
                path = astar_route((sx2, sy2), in_pre, obstacles, step=12.5)
                path = simplify_path(path)
                points = [(sx, sy), (sx2, sy2)] + path[1:] + [(tx, ty)]
                wire_cache[key] = points
            else:
                points = cached

            color = WIRE_ON if gate_output_state(src, out_idx) else WIRE_OFF
            thickness = max(1, int(2 * zoom * wire_thickness))
            pygame.draw.lines(screen, color, False, [world_to_screen(p) for p in points], thickness)


def delete_gate(g):
    gates.remove(g)
    for other in gates:
        for i, conn in enumerate(other.inputs):
            if conn_source_id(conn) == g.id:
                other.inputs[i] = None


def request_delete_gate(g):
    if g.deleting:
        return
    g.deleting = True
    g.delete_t = 0.0
    if g.id in selected_ids:
        selected_ids.discard(g.id)
    for other in gates:
        for i, conn in enumerate(other.inputs):
            if conn_source_id(conn) == g.id:
                other.inputs[i] = None
    bump_layout()


def delete_selected():
    to_delete = [g for g in gates if g.id in selected_ids]
    notes_to_delete = [n for n in notes if n["id"] in selected_note_ids]
    if not to_delete and not notes_to_delete:
        return
    push_undo()
    for g in to_delete:
        request_delete_gate(g)
    selected_ids.clear()
    for n in notes_to_delete:
        request_delete_note(n)
    selected_note_ids.clear()


def copy_selected():
    global copy_buffer
    selected = [g for g in gates if g.id in selected_ids]
    if not selected:
        copy_buffer = []
        return

    cx = sum(g.x for g in selected) / len(selected)
    cy = sum(g.y for g in selected) / len(selected)

    id_set = {g.id for g in selected}
    nodes = []
    for g in selected:
        rel_x = g.x - cx
        rel_y = g.y - cy
        nodes.append({
            "id": g.id,
            "type": g.type,
            "custom_key": g.custom_key if g.type == "CUSTOM" else None,
            "rel": (rel_x, rel_y),
            "input_state": g.input_state,
            "pin_orient": g.pin_orient,
            "inputs": [normalize_conn(inp) for inp in g.inputs],
            "clock_interval": g.clock_interval,
            "clock_running": g.clock_running,
            "clock_elapsed": g.clock_elapsed,
            "delay_interval": g.delay_interval,
            "buffer_prev_input": g.buffer_prev_input,
            "buffer_pulse": g.buffer_pulse,
            "buffer_flash_time": g.buffer_flash_time,
        })

    copy_buffer = [nodes, id_set]


def paste_copy(mouse_pos_screen):
    if not copy_buffer:
        return
    push_undo()
    nodes, id_set = copy_buffer
    mx, my = screen_to_world(mouse_pos_screen)
    mx, my = snap_world((mx, my))

    new_map = {}
    new_gates = []
    selected_ids.clear()
    selected_note_ids.clear()
    for n in nodes:
        gx = mx + n["rel"][0]
        gy = my + n["rel"][1]
        ng = Gate(n["type"], gx, gy, custom_key=n.get("custom_key"))
        ng.input_state = n["input_state"]
        ng.pin_orient = n.get("pin_orient", 0)
        ng.clock_interval = n.get("clock_interval", 1.0)
        ng.clock_running = n.get("clock_running", False)
        ng.clock_elapsed = n.get("clock_elapsed", 0.0)
        ng.delay_interval = n.get("delay_interval", 0.5)
        ng.buffer_prev_input = n.get("buffer_prev_input", False)
        ng.buffer_pulse = n.get("buffer_pulse", 0.0)
        ng.buffer_flash_time = n.get("buffer_flash_time", 0.15)
        new_map[n["id"]] = ng
        new_gates.append(ng)

    for n in nodes:
        ng = new_map[n["id"]]
        if ng.inputs:
            new_inputs = []
            for inp in n["inputs"]:
                if inp is None:
                    new_inputs.append(None)
                else:
                    src_id, src_out = conn_parts(inp)
                    if src_id in id_set:
                        new_inputs.append(make_conn(new_map[src_id].id, src_out))
                    else:
                        new_inputs.append(None)
            ng.inputs = new_inputs

    for ng in new_gates:
        gates.append(ng)
        selected_ids.add(ng.id)
    bump_layout()


def draw_selection_rect(rect):
    if not rect:
        return
    x, y, w, h, alpha = rect
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    s.fill((80, 120, 200, alpha))
    screen.blit(s, (x, y))
    pygame.draw.rect(screen, (120, 170, 255), (x, y, w, h), 1)


def serialize_state():
    used_custom_keys = sorted({
        g.custom_key for g in gates if g.type == "CUSTOM" and g.custom_key is not None
    })
    all_defs = all_custom_gate_defs()
    custom_blocks = []
    for key in used_custom_keys:
        d = all_defs.get(key)
        if d is None:
            continue
        copy_d = json.loads(json.dumps(d))
        copy_d["key"] = key
        custom_blocks.append(copy_d)
    return {
        "gates": [
            {
                "id": g.id,
                "type": g.type,
                "custom_key": g.custom_key if g.type == "CUSTOM" else None,
                "x": g.x,
                "y": g.y,
                "input_state": g.input_state,
                "pin_orient": g.pin_orient,
                "inputs": [normalize_conn(inp) for inp in g.inputs],
                "clock_interval": g.clock_interval,
                "clock_running": g.clock_running,
                "clock_elapsed": g.clock_elapsed,
                "delay_interval": g.delay_interval,
                "buffer_prev_input": g.buffer_prev_input,
                "buffer_pulse": g.buffer_pulse,
                "buffer_flash_time": g.buffer_flash_time,
            }
            for g in gates
        ],
        "notes": [{"id": n["id"], "x": n["x"], "y": n["y"], "text": n["text"]} for n in notes],
        "selected_gate": selected_gate,
        "selected_ids": list(selected_ids),
        "selected_notes": list(selected_note_ids),
        "cam": (cam_x, cam_y, zoom),
        "settings": collect_settings(),
        "custom_blocks": custom_blocks,
    }


def restore_state(state):
    global gates, selected_gate, selected_ids, selected_note_ids, next_id, cam_x, cam_y, zoom, notes
    global wire_cache, signal_pending
    global straight_wires, snap_to_grid, zoom_min, zoom_max, gate_label_scale, note_font_scale
    global show_pins_always, selection_brightness, auto_center, wire_thickness, signal_delay_enabled, multicolor_outputs, light_mode
    global custom_gate_defs_file
    gates = []
    notes = []
    loaded_blocks = {}
    custom_key_map = {}
    for block in state.get("custom_blocks", []):
        nb = normalize_custom_block(block, source="file")
        if nb is None:
            continue
        old_key = str(nb.get("key", "")).strip()
        key = old_key
        if not key:
            name = nb.get("name", "custom")
            key = f"file:{slugify_block_name(name)}"
        if key in custom_gate_defs_user:
            key = f"file:{key}"
        nb["key"] = key
        loaded_blocks[key] = nb
        if old_key:
            custom_key_map[old_key] = key
    custom_gate_defs_file = loaded_blocks
    max_id = 0
    for n in state.get("notes", []):
        nid = n.get("id", new_id())
        note = {
            "id": nid,
            "x": n["x"],
            "y": n["y"],
            "draw_x": n["x"],
            "draw_y": n["y"],
            "text": n.get("text", ""),
            "spawn_t": 1.0,
            "hover_t": 0.0,
            "select_t": 0.0,
            "delete_t": 0.0,
            "deleting": False,
        }
        notes.append(note)
        max_id = max(max_id, nid)
    for n in state["gates"]:
        ckey = n.get("custom_key")
        if ckey in custom_key_map:
            ckey = custom_key_map[ckey]
        g = Gate(n["type"], n["x"], n["y"], custom_key=ckey)
        g.id = n["id"]
        g.input_state = n["input_state"]
        g.pin_orient = n.get("pin_orient", 0)
        g.inputs = [normalize_conn(inp) for inp in n["inputs"]]
        g.clock_interval = n.get("clock_interval", 1.0)
        g.clock_running = n.get("clock_running", False)
        g.clock_elapsed = n.get("clock_elapsed", 0.0)
        g.delay_interval = n.get("delay_interval", 0.5)
        g.buffer_prev_input = n.get("buffer_prev_input", False)
        g.buffer_pulse = n.get("buffer_pulse", 0.0)
        g.buffer_flash_time = n.get("buffer_flash_time", 0.15)
        g.draw_x = g.x
        g.draw_y = g.y
        g.spawn_t = 1.0
        gates.append(g)
        max_id = max(max_id, g.id)
    next_id = max_id + 1
    selected_gate = state.get("selected_gate", None)
    selected_ids = set(state.get("selected_ids", []))
    selected_note_ids = set(state.get("selected_notes", []))
    cam_x, cam_y, zoom = state.get("cam", (cam_x, cam_y, zoom))
    settings = state.get("settings", {})
    light_mode = settings.get("light_mode", light_mode)
    apply_theme()
    straight_wires = settings.get("straight_wires", straight_wires)
    snap_to_grid = settings.get("snap_to_grid", snap_to_grid)
    zoom_min = settings.get("zoom_min", zoom_min)
    zoom_max = settings.get("zoom_max", zoom_max)
    gate_label_scale = settings.get("gate_label_scale", gate_label_scale)
    note_font_scale = settings.get("note_font_scale", note_font_scale)
    show_pins_always = settings.get("show_pins_always", show_pins_always)
    selection_brightness = settings.get("selection_brightness", selection_brightness)
    auto_center = settings.get("auto_center", auto_center)
    wire_thickness = settings.get("wire_thickness", wire_thickness)
    signal_delay_enabled = settings.get("signal_delay_enabled", signal_delay_enabled)
    multicolor_outputs = settings.get("multicolor_outputs", multicolor_outputs)
    remap_output_gate_inputs(multicolor_outputs)
    zoom = clamp(zoom, zoom_min, zoom_max)
    signal_pending.clear()
    wire_cache.clear()
    mark_settings_dirty()
    bump_layout()


def push_undo():
    undo_stack.append(serialize_state())
    redo_stack.clear()


def undo():
    if not undo_stack:
        return
    redo_stack.append(serialize_state())
    state = undo_stack.pop()
    restore_state(state)


def redo():
    if not redo_stack:
        return
    undo_stack.append(serialize_state())
    state = redo_stack.pop()
    restore_state(state)


def apply_zoom(amount, mouse_pos):
    global zoom, cam_x, cam_y
    before = screen_to_world(mouse_pos)
    zoom = max(zoom_min, min(zoom_max, zoom * amount))
    after = screen_to_world(mouse_pos)
    cam_x += before[0] - after[0]
    cam_y += before[1] - after[1]


def new_file():
    global gates, selected_gate, wire_from, selected_ids, copy_buffer, notes, selected_note_ids
    global note_edit_id, note_edit_text, note_edit_cursor, note_edit_original
    global exit_confirm_open, exit_confirm_t, exit_confirm_target
    global save_scope_open, save_scope_t, save_scope_target
    global settings_drag_slider
    global undo_stack, redo_stack, cam_x, cam_y, zoom, wire_cache, signal_pending
    global menu_open, menu_t, menu_target, selecting, select_rect
    global help_open, help_t, help_target, confirm_open, confirm_t, confirm_target
    global clock_menu_open, clock_menu_t, clock_menu_target, clock_menu_gate_id
    global delay_menu_open, delay_menu_t, delay_menu_target, delay_menu_gate_id
    global settings_open, settings_t, settings_target, settings_toggle_t
    global settings_scroll, settings_scroll_target, settings_scroll_max
    global help_scroll, help_scroll_target, help_scroll_max
    global keybinds_open, keybinds_t, keybinds_target, keybind_capture_action, keybind_capture_started_ms
    global keybinds_scroll, keybinds_scroll_target, keybinds_scroll_max
    global custom_menu_open, custom_menu_t, custom_menu_target, custom_menu_scroll, custom_menu_scroll_target, custom_menu_scroll_max
    global custom_gate_defs_file
    global is_dragging, _drag_gate, _drag_pending, _drag_snapshot, _drag_group_start, _drag_note_snapshot
    global _drag_note_pending, _drag_note, _drag_note_group_start
    global preview_t, pan_pending, panning, pan_moved, held_button_gate_id
    global last_click_gate_id, last_click_gate_time, last_click_note_id, last_click_time
    gates = []
    notes = []
    selected_gate = None
    wire_from = None
    selected_ids.clear()
    selected_note_ids.clear()
    copy_buffer = []
    custom_gate_defs_file.clear()
    note_edit_id = None
    note_edit_text = ""
    note_edit_original = ""
    note_edit_cursor = 0
    undo_stack.clear()
    redo_stack.clear()
    wire_cache.clear()
    signal_pending.clear()
    cam_x = 0.0
    cam_y = 0.0
    zoom = 1.0
    menu_open = False
    menu_t = 0.0
    menu_target = 0.0
    selecting = False
    select_rect = None
    is_dragging = False
    _drag_gate = None
    _drag_pending = False
    _drag_snapshot = None
    _drag_group_start = None
    _drag_note_snapshot = None
    _drag_note_pending = False
    _drag_note = None
    _drag_note_group_start = None
    preview_t = 0.0
    pan_pending = False
    panning = False
    pan_moved = False
    held_button_gate_id = None
    last_click_gate_id = None
    last_click_gate_time = 0
    last_click_note_id = None
    last_click_time = 0
    help_open = False
    help_t = 0.0
    help_target = 0.0
    help_scroll = 0.0
    help_scroll_target = 0.0
    help_scroll_max = 0.0
    settings_open = False
    settings_t = 0.0
    settings_target = 0.0
    settings_toggle_t = 0.0
    settings_drag_slider = None
    settings_scroll = 0.0
    settings_scroll_target = 0.0
    settings_scroll_max = 0.0
    confirm_open = False
    confirm_t = 0.0
    confirm_target = 0.0
    exit_confirm_open = False
    exit_confirm_t = 0.0
    exit_confirm_target = 0.0
    save_scope_open = False
    save_scope_t = 0.0
    save_scope_target = 0.0
    clock_menu_open = False
    clock_menu_t = 0.0
    clock_menu_target = 0.0
    clock_menu_gate_id = None
    delay_menu_open = False
    delay_menu_t = 0.0
    delay_menu_target = 0.0
    delay_menu_gate_id = None
    keybinds_open = False
    keybinds_t = 0.0
    keybinds_target = 0.0
    keybind_capture_action = None
    keybind_capture_started_ms = 0
    keybinds_scroll = 0.0
    keybinds_scroll_target = 0.0
    keybinds_scroll_max = 0.0
    custom_menu_open = False
    custom_menu_t = 0.0
    custom_menu_target = 0.0
    custom_menu_scroll = 0.0
    custom_menu_scroll_target = 0.0
    custom_menu_scroll_max = 0.0
    bump_layout()


def selected_segment_data():
    selected_gates = [g for g in gates if g.id in selected_ids and not g.deleting]
    selected_notes = [n for n in notes if n["id"] in selected_note_ids and not n["deleting"]]
    if not selected_gates and not selected_notes:
        return None

    ref_points = [(g.x, g.y) for g in selected_gates] + [(n["x"], n["y"]) for n in selected_notes]
    cx = sum(p[0] for p in ref_points) / len(ref_points)
    cy = sum(p[1] for p in ref_points) / len(ref_points)

    id_set = {g.id for g in selected_gates}
    seg_gates = []
    for g in selected_gates:
        seg_gates.append({
            "id": g.id,
            "type": g.type,
            "custom_key": g.custom_key if g.type == "CUSTOM" else None,
            "rel": (g.x - cx, g.y - cy),
            "input_state": g.input_state,
            "pin_orient": g.pin_orient,
            "inputs": [
                (make_conn(conn_source_id(inp), conn_parts(inp)[1]) if conn_source_id(inp) in id_set else None)
                for inp in g.inputs
            ],
            "clock_interval": g.clock_interval,
            "clock_running": g.clock_running,
            "clock_elapsed": g.clock_elapsed,
            "delay_interval": g.delay_interval,
            "buffer_prev_input": g.buffer_prev_input,
            "buffer_pulse": g.buffer_pulse,
            "buffer_flash_time": g.buffer_flash_time,
        })

    seg_notes = []
    for n in selected_notes:
        seg_notes.append({
            "rel": (n["x"] - cx, n["y"] - cy),
            "text": n["text"],
        })

    used_custom_keys = sorted({g.custom_key for g in selected_gates if g.type == "CUSTOM" and g.custom_key})
    custom_blocks = []
    defs = all_custom_gate_defs()
    for key in used_custom_keys:
        d = defs.get(key)
        if d is None:
            continue
        cp = copy_custom_block(d)
        cp["key"] = key
        custom_blocks.append(cp)

    return {
        "kind": "logical_segment",
        "gates": seg_gates,
        "notes": seg_notes,
        "custom_blocks": custom_blocks,
    }


def apply_segment_state(segment_state, mouse_pos_screen):
    custom_key_map = {}
    for block in segment_state.get("custom_blocks", []):
        nb = normalize_custom_block(block, source="file")
        if nb is None:
            continue
        old_key = str(nb.get("key", "")).strip()
        key = old_key
        if not key:
            key = f"file:{slugify_block_name(nb.get('name', 'custom'))}"
        if key in custom_gate_defs_user:
            key = f"file:{key}"
        nb["key"] = key
        custom_gate_defs_file[key] = nb
        if old_key:
            custom_key_map[old_key] = key

    seg_gates = segment_state.get("gates", [])
    seg_notes = segment_state.get("notes", [])
    if not seg_gates and not seg_notes:
        return

    push_undo()
    mx, my = screen_to_world(mouse_pos_screen)
    mx, my = snap_world((mx, my))

    new_map = {}
    added_gate_ids = set()
    for n in seg_gates:
        gx = mx + n["rel"][0]
        gy = my + n["rel"][1]
        ckey = n.get("custom_key")
        if ckey in custom_key_map:
            ckey = custom_key_map[ckey]
        ng = Gate(n["type"], gx, gy, custom_key=ckey)
        ng.input_state = n.get("input_state", False)
        ng.pin_orient = n.get("pin_orient", 0)
        ng.clock_interval = n.get("clock_interval", 1.0)
        ng.clock_running = n.get("clock_running", False)
        ng.clock_elapsed = n.get("clock_elapsed", 0.0)
        ng.delay_interval = n.get("delay_interval", 0.5)
        ng.buffer_prev_input = n.get("buffer_prev_input", False)
        ng.buffer_pulse = n.get("buffer_pulse", 0.0)
        ng.buffer_flash_time = n.get("buffer_flash_time", 0.15)
        new_map[n["id"]] = ng
        gates.append(ng)
        added_gate_ids.add(ng.id)

    for n in seg_gates:
        ng = new_map[n["id"]]
        new_inputs = []
        for inp in n.get("inputs", []):
            if inp is None:
                new_inputs.append(None)
            else:
                src_id, src_out = conn_parts(inp)
                if src_id in new_map:
                    new_inputs.append(make_conn(new_map[src_id].id, src_out))
                else:
                    new_inputs.append(None)
        ng.inputs = new_inputs

    added_note_ids = set()
    for n in seg_notes:
        nx = mx + n["rel"][0]
        ny = my + n["rel"][1]
        nn = {
            "id": new_id(),
            "x": nx,
            "y": ny,
            "draw_x": nx,
            "draw_y": ny,
            "text": n.get("text", "note"),
            "spawn_t": 0.0,
            "hover_t": 0.0,
            "select_t": 0.0,
            "delete_t": 0.0,
            "deleting": False,
        }
        notes.append(nn)
        added_note_ids.add(nn["id"])

    selected_ids.clear()
    selected_ids.update(added_gate_ids)
    selected_note_ids.clear()
    selected_note_ids.update(added_note_ids)
    bump_layout()


def prompt_save_path(segment=False):
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    path = filedialog.asksaveasfilename(
        defaultextension=".json",
        filetypes=[("Logical JSON", "*.json"), ("All Files", "*.*")],
        title="Save Segment File" if segment else "Save Logical File",
        initialfile="logic(seg).json" if segment else "logic.json",
    )
    root.destroy()
    return path


def prompt_load_path():
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    path = filedialog.askopenfilename(
        filetypes=[("Logical JSON", "*.json"), ("All Files", "*.*")],
        title="Load Logical File",
    )
    root.destroy()
    return path


def save_to_file(scope="whole"):
    global dialog_open
    if dialog_open:
        return False
    segment_mode = scope == "segment"
    state = selected_segment_data() if segment_mode else serialize_state()
    if state is None:
        return False
    dialog_open = True
    try:
        path = prompt_save_path(segment=segment_mode)
        if not path:
            return False
        tag = "(sec)" if segment_mode else "(file)"
        root, ext = os.path.splitext(path)
        if ext == "":
            ext = ".json"
        base = os.path.basename(root)
        if tag not in base:
            root = root + tag
        path = root + ext
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
            return True
        except Exception:
            return False
    finally:
        dialog_open = False


def exit_app():
    save_cached_settings()
    pygame.quit()
    sys.exit()


def load_from_file():
    global dialog_open
    if dialog_open:
        return
    dialog_open = True
    try:
        path = prompt_load_path()
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                state = json.load(f)
            if isinstance(state, dict) and state.get("kind") == "logical_segment":
                apply_segment_state(state, pygame.mouse.get_pos())
            else:
                push_undo()
                restore_state(state)
        except Exception:
            pass
    finally:
        dialog_open = False


def paste_segment_from_file(mouse_pos_screen):
    global dialog_open
    if dialog_open:
        return
    dialog_open = True
    try:
        path = prompt_load_path()
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                state = json.load(f)
            if isinstance(state, dict) and state.get("kind") == "logical_segment":
                apply_segment_state(state, mouse_pos_screen)
        except Exception:
            pass
    finally:
        dialog_open = False


# Main loop
load_cached_settings()
frame_dt = 1.0 / FPS
while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            if not confirm_open and not exit_confirm_open and not save_scope_open and not clock_menu_open and not delay_menu_open and not keybinds_open and not custom_menu_open:
                help_open = False
                help_target = 0.0
                settings_open = False
                settings_target = 0.0
                keybinds_open = False
                keybinds_target = 0.0
                custom_menu_open = False
                custom_menu_target = 0.0
                exit_confirm_open = True
                exit_confirm_target = 1.0
            continue
        if event.type == pygame.KEYDOWN:
            if confirm_open:
                if event.key == pygame.K_ESCAPE:
                    confirm_target = 0.0
                    confirm_open = False
                continue
            if exit_confirm_open:
                if event.key == pygame.K_ESCAPE:
                    exit_confirm_target = 0.0
                    exit_confirm_open = False
                continue
            if save_scope_open:
                if event.key == pygame.K_ESCAPE:
                    save_scope_target = 0.0
                    save_scope_open = False
                continue
            if clock_menu_open:
                if event.key == pygame.K_ESCAPE:
                    clock_menu_target = 0.0
                    clock_menu_open = False
                    clock_menu_gate_id = None
                continue
            if delay_menu_open:
                if event.key == pygame.K_ESCAPE:
                    delay_menu_target = 0.0
                    delay_menu_open = False
                    delay_menu_gate_id = None
                continue
            if help_open:
                if event.key == pygame.K_ESCAPE or event.key == pygame.K_TAB:
                    help_target = 0.0
                    help_open = False
                continue
            if custom_menu_open:
                if event.key == pygame.K_ESCAPE or event.key == pygame.K_TAB:
                    custom_menu_target = 0.0
                    custom_menu_open = False
                continue
            if keybinds_open:
                if keybind_capture_action is not None:
                    now_ms = pygame.time.get_ticks()
                    if now_ms - keybind_capture_started_ms < 120:
                        continue
                    if event.key in (pygame.K_LCTRL, pygame.K_RCTRL, pygame.K_LSHIFT, pygame.K_RSHIFT, pygame.K_LALT, pygame.K_RALT):
                        continue
                    if event.key == pygame.K_ESCAPE and not (event.mod & (pygame.KMOD_CTRL | pygame.KMOD_SHIFT | pygame.KMOD_ALT)):
                        keybind_capture_action = None
                    else:
                        keybinds[keybind_capture_action] = binding_from_event(event)
                        keybind_capture_action = None
                        mark_keybinds_dirty()
                    continue
                if event.key == pygame.K_ESCAPE or event.key == pygame.K_TAB:
                    keybinds_target = 0.0
                    keybinds_open = False
                    keybind_capture_action = None
                    keybind_capture_started_ms = 0
                continue
            if settings_open:
                if event.key == pygame.K_ESCAPE or event.key == pygame.K_TAB:
                    settings_target = 0.0
                    settings_open = False
                    settings_drag_slider = None
                continue
            if note_edit_id is not None:
                mods = pygame.key.get_mods()
                if event.key == pygame.K_ESCAPE:
                    finish_note_edit(commit=False)
                    continue
                if event.key == pygame.K_RETURN:
                    if mods & pygame.KMOD_SHIFT:
                        note_edit_text = note_edit_text[:note_edit_cursor] + "\n" + note_edit_text[note_edit_cursor:]
                        note_edit_cursor += 1
                        note_edit_anim_t = 0.0
                        note_edit_anim_index = note_edit_cursor - 1
                    else:
                        finish_note_edit(commit=True)
                    continue
                if event.key == pygame.K_BACKSPACE:
                    if mods & pygame.KMOD_CTRL:
                        if note_edit_cursor > 0:
                            cut = note_edit_text[:note_edit_cursor].rstrip()
                            new_len = cut.rfind(" ")
                            if new_len == -1:
                                note_edit_text = note_edit_text[note_edit_cursor:]
                                note_edit_cursor = 0
                            else:
                                note_edit_text = note_edit_text[: new_len + 1] + note_edit_text[note_edit_cursor:]
                                note_edit_cursor = new_len + 1
                            note_edit_anim_t = 0.0
                            note_edit_anim_index = None
                        continue
                    if note_edit_cursor > 0:
                        note_edit_text = (
                            note_edit_text[: note_edit_cursor - 1] + note_edit_text[note_edit_cursor:]
                        )
                        note_edit_cursor -= 1
                        note_edit_anim_t = 0.0
                        note_edit_anim_index = None
                    continue
                if event.key == pygame.K_DELETE:
                    if note_edit_cursor < len(note_edit_text):
                        note_edit_text = (
                            note_edit_text[:note_edit_cursor] + note_edit_text[note_edit_cursor + 1 :]
                        )
                        note_edit_anim_t = 0.0
                        note_edit_anim_index = None
                    continue
                if event.key == pygame.K_LEFT:
                    note_edit_cursor = max(0, note_edit_cursor - 1)
                    continue
                if event.key == pygame.K_RIGHT:
                    note_edit_cursor = min(len(note_edit_text), note_edit_cursor + 1)
                    continue
                if event.key == pygame.K_HOME:
                    note_edit_cursor = 0
                    continue
                if event.key == pygame.K_END:
                    note_edit_cursor = len(note_edit_text)
                    continue
                if event.unicode and not (mods & (pygame.KMOD_CTRL | pygame.KMOD_ALT)):
                    note_edit_text = (
                        note_edit_text[:note_edit_cursor] + event.unicode + note_edit_text[note_edit_cursor:]
                    )
                    note_edit_cursor += 1
                    note_edit_anim_t = 0.0
                    note_edit_anim_index = note_edit_cursor - 1
                continue
            if action_pressed(event, "exit_prompt"):
                if note_edit_id is None:
                    exit_confirm_open = True
                    exit_confirm_target = 1.0
            if action_pressed(event, "new_file_prompt"):
                confirm_open = True
                confirm_target = 1.0
            if action_pressed(event, "open_settings"):
                settings_open = True
                settings_target = 1.0
                settings_scroll = 0.0
                settings_scroll_target = 0.0
            if action_pressed(event, "save"):
                save_scope_open = True
                save_scope_target = 1.0
            if action_pressed(event, "load"):
                load_from_file()
            if action_pressed(event, "undo"):
                undo()
            if action_pressed(event, "redo"):
                redo()
            if action_pressed(event, "rotate_cw") or action_pressed(event, "rotate_ccw"):
                if selected_ids:
                    candidates = [g for g in gates if g.id in selected_ids and not g.deleting]
                    if candidates:
                        push_undo()
                        for g in candidates:
                            if action_pressed(event, "rotate_cw"):
                                g.pin_orient = (g.pin_orient + 1) % 4
                            else:
                                g.pin_orient = (g.pin_orient - 1) % 4
                        bump_layout()
            if action_pressed(event, "delete"):
                delete_selected()
            if action_pressed(event, "copy"):
                copy_selected()
            if action_pressed(event, "paste_segment"):
                paste_segment_from_file(pygame.mouse.get_pos())
            elif action_pressed(event, "paste"):
                paste_copy(pygame.mouse.get_pos())
            if action_pressed(event, "clear_all"):
                push_undo()
                gates.clear()
                wire_from = None
                selected_ids.clear()

        if event.type == pygame.MOUSEWHEEL:
            if custom_menu_open:
                custom_menu_scroll_target -= event.y * 42
                custom_menu_scroll_target = clamp(custom_menu_scroll_target, 0.0, custom_menu_scroll_max)
                continue
            if keybinds_open:
                keybinds_scroll_target -= event.y * 42
                keybinds_scroll_target = clamp(keybinds_scroll_target, 0.0, keybinds_scroll_max)
                continue
            if help_open:
                help_scroll_target -= event.y * 42
                help_scroll_target = clamp(help_scroll_target, 0.0, help_scroll_max)
                continue
            if settings_open:
                settings_scroll_target -= event.y * 42
                settings_scroll_target = clamp(settings_scroll_target, 0.0, settings_scroll_max)
                continue
            if event.y > 0:
                apply_zoom(1.1, pygame.mouse.get_pos())
            elif event.y < 0:
                apply_zoom(0.9, pygame.mouse.get_pos())

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 2:
            if auto_center and gates:
                now = pygame.time.get_ticks()
                if now - last_mid_click <= 350:
                    xs = [g.x for g in gates]
                    ys = [g.y for g in gates]
                    cam_x = (min(xs) + max(xs)) / 2
                    cam_y = (min(ys) + max(ys)) / 2
                    last_mid_click = 0
                else:
                    last_mid_click = now

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if custom_menu_open:
                buttons = draw_custom_blocks_dialog()
                if buttons:
                    if buttons.get("new") and buttons["new"].collidepoint(event.pos):
                        _new_key = run_custom_block_builder()
                        if _new_key:
                            selected_gate = custom_token_from_key(_new_key)
                    elif buttons.get("close") and buttons["close"].collidepoint(event.pos):
                        custom_menu_target = 0.0
                        custom_menu_open = False
                    else:
                        handled = False
                        for key, rect in buttons.items():
                            if not rect.collidepoint(event.pos):
                                continue
                            if "|" in key:
                                action, payload = key.split("|", 1)
                                if action == "place":
                                    selected_gate = custom_token_from_key(payload)
                                    custom_menu_target = 0.0
                                    custom_menu_open = False
                                elif action == "edit":
                                    run_custom_block_builder(existing_key=payload)
                                elif action == "delete":
                                    if payload in custom_gate_defs_user:
                                        del custom_gate_defs_user[payload]
                                        selected_gate = None if selected_gate == custom_token_from_key(payload) else selected_gate
                                        mark_settings_dirty()
                                        refresh_custom_gate_instances(payload)
                                    elif payload in custom_gate_defs_file:
                                        del custom_gate_defs_file[payload]
                                        selected_gate = None if selected_gate == custom_token_from_key(payload) else selected_gate
                                        refresh_custom_gate_instances(payload)
                                handled = True
                                break
                        if not handled:
                            pass
                continue
            if save_scope_open:
                buttons = draw_save_scope_dialog()
                if buttons:
                    if buttons["segment"].collidepoint(event.pos):
                        save_to_file(scope="segment")
                        save_scope_target = 0.0
                        save_scope_open = False
                    elif buttons["whole"].collidepoint(event.pos):
                        save_to_file(scope="whole")
                        save_scope_target = 0.0
                        save_scope_open = False
                    elif buttons["cancel"].collidepoint(event.pos):
                        save_scope_target = 0.0
                        save_scope_open = False
                continue
            if clock_menu_open:
                buttons = draw_clock_dialog()
                gate = next((g for g in gates if g.id == clock_menu_gate_id and not g.deleting), None)
                if buttons and gate:
                    if buttons["minus_big"].collidepoint(event.pos):
                        gate.clock_interval = clamp(gate.clock_interval - 1.0, 0.1, 30.0)
                    elif buttons["minus_small"].collidepoint(event.pos):
                        gate.clock_interval = clamp(gate.clock_interval - 0.1, 0.1, 30.0)
                    elif buttons["plus_small"].collidepoint(event.pos):
                        gate.clock_interval = clamp(gate.clock_interval + 0.1, 0.1, 30.0)
                    elif buttons["plus_big"].collidepoint(event.pos):
                        gate.clock_interval = clamp(gate.clock_interval + 1.0, 0.1, 30.0)
                    elif buttons["toggle_run"].collidepoint(event.pos):
                        gate.clock_running = not gate.clock_running
                    elif buttons["close"].collidepoint(event.pos):
                        clock_menu_target = 0.0
                        clock_menu_open = False
                        clock_menu_gate_id = None
                continue
            if delay_menu_open:
                buttons = draw_delay_dialog()
                gate = next((g for g in gates if g.id == delay_menu_gate_id and not g.deleting), None)
                if buttons and gate:
                    if buttons["minus_big"].collidepoint(event.pos):
                        gate.delay_interval = clamp(gate.delay_interval - 1.0, 0.1, 30.0)
                    elif buttons["minus_small"].collidepoint(event.pos):
                        gate.delay_interval = clamp(gate.delay_interval - 0.1, 0.1, 30.0)
                    elif buttons["plus_small"].collidepoint(event.pos):
                        gate.delay_interval = clamp(gate.delay_interval + 0.1, 0.1, 30.0)
                    elif buttons["plus_big"].collidepoint(event.pos):
                        gate.delay_interval = clamp(gate.delay_interval + 1.0, 0.1, 30.0)
                    elif buttons["close"].collidepoint(event.pos):
                        delay_menu_target = 0.0
                        delay_menu_open = False
                        delay_menu_gate_id = None
                continue
            if confirm_open:
                buttons = draw_confirm_dialog()
                if buttons:
                    if buttons["save"].collidepoint(event.pos):
                        if save_to_file(scope="whole"):
                            new_file()
                            confirm_target = 0.0
                            confirm_open = False
                    elif buttons["nosave"].collidepoint(event.pos):
                        new_file()
                        confirm_target = 0.0
                        confirm_open = False
                    elif buttons["cancel"].collidepoint(event.pos):
                        confirm_target = 0.0
                        confirm_open = False
                continue
            if exit_confirm_open:
                buttons = draw_exit_confirm_dialog()
                if buttons:
                    if buttons["save"].collidepoint(event.pos):
                        if save_to_file(scope="whole"):
                            exit_app()
                    elif buttons["nosave"].collidepoint(event.pos):
                        exit_app()
                    elif buttons["cancel"].collidepoint(event.pos):
                        exit_confirm_target = 0.0
                        exit_confirm_open = False
                continue
            if help_open:
                buttons = draw_help_dialog()
                if buttons and buttons["close"].collidepoint(event.pos):
                    help_target = 0.0
                    help_open = False
                continue
            if keybinds_open:
                buttons = draw_keybinds_dialog()
                if buttons:
                    if buttons.get("reset_defaults") and buttons["reset_defaults"].collidepoint(event.pos):
                        keybinds = {k: dict(v) for k, v in DEFAULT_KEYBINDS.items()}
                        keybind_capture_action = None
                        keybind_capture_started_ms = 0
                        mark_keybinds_dirty()
                    elif buttons.get("close") and buttons["close"].collidepoint(event.pos):
                        keybinds_target = 0.0
                        keybinds_open = False
                        keybind_capture_action = None
                        keybind_capture_started_ms = 0
                    else:
                        hit_change = False
                        for action, _ in KEYBIND_ITEMS:
                            rkey = f"reset_{action}"
                            if buttons.get(rkey) and buttons[rkey].collidepoint(event.pos):
                                keybinds[action] = dict(DEFAULT_KEYBINDS[action])
                                if keybind_capture_action == action:
                                    keybind_capture_action = None
                                    keybind_capture_started_ms = 0
                                mark_keybinds_dirty()
                                hit_change = True
                                break
                            key = f"change_{action}"
                            if buttons.get(key) and buttons[key].collidepoint(event.pos):
                                if keybind_capture_action == action:
                                    keybind_capture_action = None
                                    keybind_capture_started_ms = 0
                                else:
                                    keybind_capture_action = action
                                    keybind_capture_started_ms = pygame.time.get_ticks()
                                hit_change = True
                                break
                        if not hit_change:
                            keybind_capture_action = None
                            keybind_capture_started_ms = 0
                continue
            if settings_open:
                buttons = draw_settings_dialog()
                if buttons:
                    def set_slider_value(key, mx):
                        global grid_step, zoom_min, zoom_max, gate_label_scale, note_font_scale
                        global selection_brightness, wire_thickness
                        track_info = settings_slider_rects.get(key)
                        if not track_info:
                            return
                        track, options = track_info
                        values = [v for v, _ in options]
                        if track.w <= 0:
                            return
                        t = clamp((mx - track.x) / track.w, 0.0, 1.0)
                        idx = int(round(t * (len(values) - 1)))
                        value = values[idx]
                        if key == "grid_size":
                            grid_step = value
                        elif key == "zoom_min":
                            zoom_min = value
                            if zoom_min >= zoom_max:
                                max_opts = [2.0, 2.5, 3.0]
                                zoom_max = next((v for v in max_opts if v > zoom_min), max_opts[-1])
                        elif key == "zoom_max":
                            zoom_max = value
                            if zoom_max <= zoom_min:
                                min_opts = [0.3, 0.4, 0.5]
                                zoom_min = next((v for v in reversed(min_opts) if v < zoom_max), min_opts[0])
                        elif key == "gate_label":
                            gate_label_scale = value
                        elif key == "note_font":
                            note_font_scale = value
                        elif key == "sel_bright":
                            selection_brightness = value
                        elif key == "wire_thick":
                            wire_thickness = value
                        if key in ("zoom_min", "zoom_max"):
                            global zoom
                            zoom = clamp(zoom, zoom_min, zoom_max)
                        mark_settings_dirty()

                    if buttons.get("toggle_straight") and buttons["toggle_straight"].collidepoint(event.pos):
                        straight_wires = not straight_wires
                        wire_cache.clear()
                        bump_layout()
                        mark_settings_dirty()
                    elif buttons.get("toggle_snap") and buttons["toggle_snap"].collidepoint(event.pos):
                        snap_to_grid = not snap_to_grid
                        if snap_to_grid:
                            push_undo()
                            for g in gates:
                                if g.deleting:
                                    continue
                                g.x, g.y = snap_world((g.x, g.y))
                            for n in notes:
                                if n["deleting"]:
                                    continue
                                n["x"], n["y"] = snap_world((n["x"], n["y"]))
                            bump_layout()
                        mark_settings_dirty()
                    elif buttons.get("toggle_pins") and buttons["toggle_pins"].collidepoint(event.pos):
                        show_pins_always = not show_pins_always
                        mark_settings_dirty()
                    elif buttons.get("toggle_center") and buttons["toggle_center"].collidepoint(event.pos):
                        auto_center = not auto_center
                        mark_settings_dirty()
                    elif buttons.get("toggle_light_mode") and buttons["toggle_light_mode"].collidepoint(event.pos):
                        light_mode = not light_mode
                        apply_theme()
                        mark_settings_dirty()
                    elif buttons.get("toggle_signal_delay") and buttons["toggle_signal_delay"].collidepoint(event.pos):
                        signal_delay_enabled = not signal_delay_enabled
                        if not signal_delay_enabled:
                            signal_pending.clear()
                        mark_settings_dirty()
                    elif buttons.get("toggle_multicolor") and buttons["toggle_multicolor"].collidepoint(event.pos):
                        multicolor_outputs = not multicolor_outputs
                        remap_output_gate_inputs(multicolor_outputs)
                        signal_pending.clear()
                        mark_settings_dirty()
                    elif buttons.get("instructions") and buttons["instructions"].collidepoint(event.pos):
                        settings_target = 0.0
                        settings_open = False
                        settings_drag_slider = None
                        help_open = True
                        help_target = 1.0
                        help_scroll = 0.0
                        help_scroll_target = 0.0
                    elif buttons.get("keybinds") and buttons["keybinds"].collidepoint(event.pos):
                        settings_target = 0.0
                        settings_open = False
                        settings_drag_slider = None
                        keybinds_open = True
                        keybinds_t = 0.0
                        keybinds_target = 1.0
                        keybind_capture_action = None
                        keybind_capture_started_ms = 0
                        keybinds_scroll = 0.0
                        keybinds_scroll_target = 0.0
                    elif buttons.get("close") and buttons["close"].collidepoint(event.pos):
                        settings_target = 0.0
                        settings_open = False
                        settings_drag_slider = None
                    else:
                        for key in ("grid_size", "zoom_min", "zoom_max", "gate_label", "note_font", "sel_bright", "wire_thick"):
                            info = settings_slider_rects.get(key)
                            if info and info[0].inflate(20, 12).collidepoint(event.pos):
                                settings_drag_slider = key
                                set_slider_value(key, event.pos[0])
                                break
                continue
            mx, my = event.pos
            world_pos = screen_to_world((mx, my))

            if menu_open:
                items = draw_gate_menu(menu_pos)
                clicked_item = False
                for gtype, rect in items:
                    if rect.collidepoint(mx, my):
                        if gtype == "CUSTOM_MENU":
                            custom_menu_open = True
                            custom_menu_t = 0.0
                            custom_menu_target = 1.0
                            custom_menu_scroll = 0.0
                            custom_menu_scroll_target = 0.0
                        else:
                            selected_gate = gtype
                        menu_open = False
                        menu_target = 0.0
                        clicked_item = True
                        break
                if not clicked_item:
                    menu_open = False
                    menu_target = 0.0
                continue

            note_hit = note_at_screen((mx, my))
            if note_edit_id is not None and (note_hit is None or note_hit["id"] != note_edit_id):
                finish_note_edit(commit=True)

            if note_hit:
                if note_edit_id == note_hit["id"]:
                    finish_note_edit(commit=True)
                    last_click_time = 0
                    last_click_note_id = None
                if selected_note_ids != {note_hit["id"]}:
                    selected_note_ids = {note_hit["id"]}
                    selected_ids.clear()
                now = pygame.time.get_ticks()
                if note_edit_id is None and last_click_note_id == note_hit["id"] and now - last_click_time <= 350:
                    start_note_edit(note_hit)
                    last_click_time = 0
                    last_click_note_id = None
                    menu_open = False
                    menu_target = 0.0
                    continue
                last_click_time = now
                last_click_note_id = note_hit["id"]
                _drag_note_pending = True
                _drag_note = note_hit
                _drag_start = (mx, my)
                _drag_note_world_start = world_pos
                _drag_note_group_start = None
                menu_open = False
                menu_target = 0.0
                continue

            hit_gate, hit_kind, hit_idx = find_pin_hit(world_pos)
            if hit_gate:
                if wire_from is None:
                    if hit_kind == "out":
                        wire_from = make_conn(hit_gate.id, hit_idx if hit_idx is not None else 0)
                        preview_x, preview_y = world_pos
                else:
                    if hit_kind == "in":
                        push_undo()
                        hit_gate.inputs[hit_idx] = wire_from
                        wire_from = None
                menu_open = False
                menu_target = 0.0
                continue

            g = gate_at(world_pos)
            if g:
                if g.type == "BUTTON":
                    g.input_state = True
                    held_button_gate_id = g.id
                _drag_pending = True
                _drag_gate = g
                _drag_start = (mx, my)
                _drag_world_start = world_pos
                _drag_group_start = None
                if g.id not in selected_ids:
                    selected_ids = {g.id}
                    selected_note_ids.clear()
                menu_open = False
                menu_target = 0.0
                continue

            selecting = True
            select_start = (mx, my)
            select_rect = None

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            if confirm_open or exit_confirm_open or save_scope_open or clock_menu_open or delay_menu_open or help_open or settings_open or keybinds_open or custom_menu_open:
                continue
            mx, my = event.pos
            pan_pending = True
            pan_start = (mx, my)
            cam_start = (cam_x, cam_y)
            pan_moved = False

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if held_button_gate_id is not None:
                held_gate = next((g for g in gates if g.id == held_button_gate_id and not g.deleting), None)
                if held_gate and held_gate.type == "BUTTON":
                    held_gate.input_state = False
                held_button_gate_id = None
            if settings_open and settings_drag_slider is not None:
                settings_drag_slider = None
                continue
            if confirm_open or exit_confirm_open or save_scope_open or clock_menu_open or delay_menu_open or help_open or settings_open or keybinds_open or custom_menu_open:
                continue
            mx, my = event.pos
            if _drag_note_pending and _drag_note:
                _drag_note_pending = False
                _drag_note = None
                _drag_note_group_start = None

            if _drag_note_group_start is not None:
                _drag_note = None
                if _drag_note_snapshot is not None:
                    undo_stack.append(_drag_note_snapshot)
                    redo_stack.clear()
                    _drag_note_snapshot = None
                _drag_note_group_start = None
            if _drag_pending and _drag_gate:
                dx = mx - _drag_start[0]
                dy = my - _drag_start[1]
                if abs(dx) < DRAG_THRESHOLD and abs(dy) < DRAG_THRESHOLD:
                    if _drag_gate.type == "INPUT":
                        push_undo()
                        _drag_gate.input_state = not _drag_gate.input_state
                    elif _drag_gate.type == "CUSTOM":
                        now = pygame.time.get_ticks()
                        if last_click_gate_id == _drag_gate.id and now - last_click_gate_time <= 350:
                            if _drag_gate.custom_key:
                                run_custom_block_builder(existing_key=_drag_gate.custom_key, logic_only=True)
                            last_click_gate_id = None
                            last_click_gate_time = 0
                            menu_open = False
                            menu_target = 0.0
                        else:
                            last_click_gate_id = _drag_gate.id
                            last_click_gate_time = now
                    elif _drag_gate.type in TRADITIONAL_GATES:
                        now = pygame.time.get_ticks()
                        if last_click_gate_id == _drag_gate.id and now - last_click_gate_time <= 350:
                            entered = prompt_text_dialog(
                                "Inputs",
                                "Number of inputs (2-5):",
                                f"{len(_drag_gate.inputs)}",
                            )
                            if entered is not None:
                                try:
                                    count = int(float(entered))
                                except Exception:
                                    count = None
                                if count is not None:
                                    count = max(2, min(5, count))
                                    if len(_drag_gate.inputs) != count:
                                        push_undo()
                                        cur = list(_drag_gate.inputs)
                                        if len(cur) > count:
                                            cur = cur[:count]
                                        else:
                                            cur.extend([None] * (count - len(cur)))
                                        _drag_gate.inputs = cur
                                        bump_layout()
                            last_click_gate_id = None
                            last_click_gate_time = 0
                            menu_open = False
                            menu_target = 0.0
                        else:
                            last_click_gate_id = _drag_gate.id
                            last_click_gate_time = now
                    elif _drag_gate.type in ("CLOCK", "DELAY"):
                        now = pygame.time.get_ticks()
                        if last_click_gate_id == _drag_gate.id and now - last_click_gate_time <= 350:
                            selected_ids = {_drag_gate.id}
                            selected_note_ids.clear()
                            if _drag_gate.type == "CLOCK":
                                clock_menu_gate_id = _drag_gate.id
                                clock_menu_t = 0.0
                                clock_menu_open = True
                                clock_menu_target = 1.0
                            else:
                                delay_menu_gate_id = _drag_gate.id
                                delay_menu_t = 0.0
                                delay_menu_open = True
                                delay_menu_target = 1.0
                            last_click_gate_id = None
                            last_click_gate_time = 0
                            menu_open = False
                            menu_target = 0.0
                        else:
                            last_click_gate_id = _drag_gate.id
                            last_click_gate_time = now
                _drag_pending = False
                _drag_gate = None
                _drag_group_start = None

            if is_dragging and _drag_gate:
                is_dragging = False
                _drag_gate = None
                if _drag_snapshot is not None:
                    undo_stack.append(_drag_snapshot)
                    redo_stack.clear()
                    _drag_snapshot = None
                _drag_group_start = None

            if selecting:
                selecting = False
                if select_rect:
                    x, y, w, h, _ = select_rect
                    p0 = screen_to_world((x, y))
                    p1 = screen_to_world((x + w, y + h))
                    rx = min(p0[0], p1[0])
                    ry = min(p0[1], p1[1])
                    rw = abs(p1[0] - p0[0])
                    rh = abs(p1[1] - p0[1])
                    rect = pygame.Rect(rx, ry, rw, rh)
                    selected_ids = {g.id for g in gates if (not g.deleting) and rect.colliderect(g.rect())}
                    selected_note_ids = {
                        n["id"] for n in notes if (not n["deleting"]) and rect.colliderect(note_world_rect(n))
                    }
                else:
                    if selected_gate is None:
                        menu_open = True
                        menu_pos = (mx, my)
                        menu_target = 1.0
                    else:
                        world_pos = screen_to_world((mx, my))
                        world_pos = snap_world(world_pos)
                        if selected_gate == "NOTE":
                            push_undo()
                            note_font = scaled_font(16 * note_font_scale)
                            note_w, note_h, _, _, _ = note_size_for_text(note_font, "note")
                            spawn_x = world_pos[0] - (note_w / (2 * zoom))
                            spawn_y = world_pos[1] - (note_h / (2 * zoom))
                            new_note = {
                                "id": new_id(),
                                "x": spawn_x,
                                "y": spawn_y,
                                "draw_x": spawn_x,
                                "draw_y": spawn_y,
                                "text": "note",
                                "spawn_t": 0.0,
                                "hover_t": 0.0,
                                "select_t": 0.0,
                                "delete_t": 0.0,
                                "deleting": False,
                            }
                            notes.append(new_note)
                            selected_note_ids = {new_note["id"]}
                            selected_ids.clear()
                            start_note_edit(new_note)
                            bump_layout()
                        elif gate_at(world_pos) is None:
                            push_undo()
                            if is_custom_gate_token(selected_gate):
                                ckey = custom_key_from_token(selected_gate)
                                gates.append(Gate("CUSTOM", world_pos[0], world_pos[1], custom_key=ckey))
                            else:
                                gates.append(Gate(selected_gate, world_pos[0], world_pos[1]))
                            bump_layout()

        if event.type == pygame.MOUSEBUTTONUP and event.button == 3:
            if confirm_open or exit_confirm_open or save_scope_open or clock_menu_open or delay_menu_open or help_open or settings_open or keybinds_open or custom_menu_open:
                continue
            was_panning = panning or pan_moved
            panning = False
            pan_pending = False
            pan_moved = False

            # If it was just a right-click (no pan), use it for delete/deselect
            if not was_panning:
                world_pos = screen_to_world(event.pos)

                if wire_from is not None:
                    wire_from = None
                    continue

                note_hit = note_at_screen(event.pos)
                if note_hit:
                    push_undo()
                    request_delete_note(note_hit)
                    continue

                hit_gate, hit_kind, hit_idx = find_pin_hit(world_pos)
                if hit_gate and hit_kind == "in":
                    push_undo()
                    hit_gate.inputs[hit_idx] = None
                    continue

                g = gate_at(world_pos)
                if g:
                    push_undo()
                    request_delete_gate(g)
                    if g.id in selected_ids:
                        selected_ids.discard(g.id)
                    continue

                selected_gate = None
                menu_open = False
                menu_target = 0.0
                selected_ids.clear()
                selected_note_ids.clear()

        if event.type == pygame.MOUSEMOTION:
            if settings_open and settings_drag_slider is not None:
                info = settings_slider_rects.get(settings_drag_slider)
                if info:
                    track, options = info
                    values = [v for v, _ in options]
                    if track.w > 0:
                        t = clamp((event.pos[0] - track.x) / track.w, 0.0, 1.0)
                        idx = int(round(t * (len(values) - 1)))
                        value = values[idx]
                        if settings_drag_slider == "grid_size":
                            grid_step = value
                        elif settings_drag_slider == "zoom_min":
                            zoom_min = value
                            if zoom_min >= zoom_max:
                                max_opts = [2.0, 2.5, 3.0]
                                zoom_max = next((v for v in max_opts if v > zoom_min), max_opts[-1])
                        elif settings_drag_slider == "zoom_max":
                            zoom_max = value
                            if zoom_max <= zoom_min:
                                min_opts = [0.3, 0.4, 0.5]
                                zoom_min = next((v for v in reversed(min_opts) if v < zoom_max), min_opts[0])
                        elif settings_drag_slider == "gate_label":
                            gate_label_scale = value
                        elif settings_drag_slider == "note_font":
                            note_font_scale = value
                        elif settings_drag_slider == "sel_bright":
                            selection_brightness = value
                        elif settings_drag_slider == "wire_thick":
                            wire_thickness = value
                        if settings_drag_slider in ("zoom_min", "zoom_max"):
                            zoom = clamp(zoom, zoom_min, zoom_max)
                        mark_settings_dirty()
                continue
            if confirm_open or exit_confirm_open or save_scope_open or clock_menu_open or delay_menu_open or help_open or settings_open or keybinds_open or custom_menu_open:
                continue
            mx, my = event.pos
            if _drag_note_pending and _drag_note:
                dx = mx - _drag_start[0]
                dy = my - _drag_start[1]
                if abs(dx) >= DRAG_THRESHOLD or abs(dy) >= DRAG_THRESHOLD:
                    if note_edit_id == _drag_note["id"]:
                        finish_note_edit(commit=True)
                    _drag_note_pending = False
                    if _drag_note_snapshot is None:
                        _drag_note_snapshot = serialize_state()
                    _drag_note_group_start = {n["id"]: (n["x"], n["y"]) for n in notes if n["id"] in selected_note_ids}
            if _drag_note_group_start is not None and _drag_note:
                world_pos = screen_to_world((mx, my))
                dxw = world_pos[0] - _drag_note_world_start[0]
                dyw = world_pos[1] - _drag_note_world_start[1]
                moved = False
                for n in notes:
                    if n["id"] in selected_note_ids:
                        sx, sy = _drag_note_group_start[n["id"]]
                        nx, ny = snap_world((sx + dxw, sy + dyw))
                        if nx != n["x"] or ny != n["y"]:
                            moved = True
                        n["x"] = nx
                        n["y"] = ny
                if moved:
                    bump_layout()
            if _drag_pending and _drag_gate:
                dx = mx - _drag_start[0]
                dy = my - _drag_start[1]
                if abs(dx) >= DRAG_THRESHOLD or abs(dy) >= DRAG_THRESHOLD:
                    if _drag_gate.type == "BUTTON":
                        _drag_gate.input_state = False
                    is_dragging = True
                    _drag_pending = False
                    if _drag_snapshot is None:
                        _drag_snapshot = serialize_state()
                    _drag_group_start = {g.id: (g.x, g.y) for g in gates if g.id in selected_ids}
            if is_dragging and _drag_gate and _drag_group_start is not None:
                world_pos = screen_to_world((mx, my))
                dxw = world_pos[0] - _drag_world_start[0]
                dyw = world_pos[1] - _drag_world_start[1]
                moved = False
                for g in gates:
                    if g.id in selected_ids:
                        sx, sy = _drag_group_start[g.id]
                        nx, ny = snap_world((sx + dxw, sy + dyw))
                        if nx != g.x or ny != g.y:
                            moved = True
                        g.x = nx
                        g.y = ny
                if moved:
                    bump_layout()
            if selecting:
                x0, y0 = select_start
                x1, y1 = mx, my
                if abs(x1 - x0) > 4 or abs(y1 - y0) > 4:
                    x = min(x0, x1)
                    y = min(y0, y1)
                    w = abs(x1 - x0)
                    h = abs(y1 - y0)
                    alpha = int(40 * select_t)
                    select_rect = (x, y, w, h, alpha)
                else:
                    select_rect = None
            if pan_pending or panning:
                dx = mx - pan_start[0]
                dy = my - pan_start[1]
                if pan_pending and (abs(dx) >= DRAG_THRESHOLD or abs(dy) >= DRAG_THRESHOLD):
                    panning = True
                    pan_pending = False
                    pan_moved = True
                if panning:
                    cam_x = cam_start[0] - dx / zoom
                    cam_y = cam_start[1] - dy / zoom

    screen.fill(BG)
    draw_grid()
    draw_label()

    mx, my = pygame.mouse.get_pos()
    world_mouse = screen_to_world((mx, my))
    hover_note = note_at_screen((mx, my))
    hover_pin = (None, None, None) if hover_note else find_pin_hit(world_mouse)
    hover_gate = None if (hover_note or hover_pin[0] is not None) else gate_at(world_mouse)

    update_clocks(frame_dt)
    eval_all(frame_dt)
    update_buffers(frame_dt)
    update_gate_anim(hover_gate)
    update_note_anim(hover_note)
    draw_wires()
    draw_gates(hover_gate, hover_pin)
    draw_notes()

    if menu_open or menu_t > 0.01:
        _ = draw_gate_menu(menu_pos)

    if confirm_open or confirm_t > 0.01:
        _ = draw_confirm_dialog()
    if exit_confirm_open or exit_confirm_t > 0.01:
        _ = draw_exit_confirm_dialog()
    if save_scope_open or save_scope_t > 0.01:
        _ = draw_save_scope_dialog()
    if clock_menu_open or clock_menu_t > 0.01:
        _ = draw_clock_dialog()
    if delay_menu_open or delay_menu_t > 0.01:
        _ = draw_delay_dialog()
    if settings_open or settings_t > 0.01:
        _ = draw_settings_dialog()
    if help_open or help_t > 0.01:
        _ = draw_help_dialog()
    if keybinds_open or keybinds_t > 0.01:
        _ = draw_keybinds_dialog()
    if custom_menu_open or custom_menu_t > 0.01:
        _ = draw_custom_blocks_dialog()

    hide_preview = (
        hover_gate is not None
        or hover_pin[0] is not None
        or hover_note is not None
        or menu_open
        or save_scope_open
        or clock_menu_open
        or delay_menu_open
        or keybinds_open
        or custom_menu_open
        or selected_gate is None
    )
    preview_target = 0.0 if hide_preview else 1.0
    preview_t = ease_to(preview_t, preview_target, max(0.1, ANIM_PREVIEW * 60.0))
    draw_gate_preview(selected_gate, (mx, my), preview_t)

    select_target = 1.0 if selecting else 0.0
    select_t = ease_to(select_t, select_target, max(0.1, ANIM_SELECT_RECT * 60.0))
    if selecting and select_rect:
        draw_selection_rect(select_rect)

    if wire_from is not None:
        preview_x = ease_to(preview_x, world_mouse[0], 22.0)
        preview_y = ease_to(preview_y, world_mouse[1], 22.0)
        src_id, src_out_idx = conn_parts(wire_from)
        src = next((s for s in gates if s.id == src_id), None)
        if src:
            sx, sy = src.output_pos_draw_idx(src_out_idx)
            s1 = world_to_screen((sx, sy))
            s2 = world_to_screen((preview_x, preview_y))
            color = WIRE_ON if gate_output_state(src, src_out_idx) else WIRE_OFF
            thickness = max(1, int(2 * zoom * wire_thickness))
            pygame.draw.line(screen, color, s1, s2, thickness)

    help_text = "Tab: settings"
    screen.blit(base_small.render(help_text, True, GRAY), (12, HEIGHT - 24))

    if note_edit_id is not None:
        note_blink_t += 1.0 / FPS
        note_edit_anim_t = min(1.0, note_edit_anim_t + 0.12)

    flush_cached_settings()
    pygame.display.flip()
    frame_dt = CLOCK.tick(FPS) / 1000.0
