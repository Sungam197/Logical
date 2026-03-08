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

next_id = 1

def new_id():
    global next_id
    nid = next_id
    next_id += 1
    return nid

class Gate:
    def __init__(self, gtype, x, y):
        self.id = new_id()
        self.type = gtype
        self.x = x
        self.y = y
        self.draw_x = x
        self.draw_y = y
        self.spawn_t = 0.0
        if gtype in TWO_INPUT:
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

    def rect(self):
        return pygame.Rect(self.x - 40, self.y - 25, 80, 50)

    def rect_draw(self, scale):
        w = 80 * scale
        h = 50 * scale
        return (self.draw_x - w / 2, self.draw_y - h / 2, w, h)

    def input_pos_draw(self, idx):
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

    def output_pos_draw(self):
        dx_edge = 40
        dy_edge = 25
        if self.pin_orient == 0:
            return (self.draw_x + dx_edge, self.draw_y)
        if self.pin_orient == 1:
            return (self.draw_x, self.draw_y - dy_edge)
        if self.pin_orient == 2:
            return (self.draw_x - dx_edge, self.draw_y)
        return (self.draw_x, self.draw_y + dy_edge)

    def eval(self, gates_by_id):
        if self.type in ("INPUT", "BUTTON", "CLOCK"):
            self.output = self.input_state
            return

        vals = []
        for i in range(len(self.inputs)):
            conn = self.inputs[i]
            if conn is None:
                vals.append(False)
            else:
                vals.append(gates_by_id[conn].output)

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
snap_to_grid = False
zoom_min = 0.4
zoom_max = 2.5
gate_label_scale = 1.0
note_font_scale = 1.0
show_pins_always = False
selection_brightness = 1.0
auto_center = True
wire_thickness = 1.0
signal_delay_enabled = True
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
    ox, oy = g.output_pos_draw()
    return (pos_world[0] - ox) ** 2 + (pos_world[1] - oy) ** 2 <= PIN_HIT ** 2


def input_hit(g, pos_world):
    for i in range(len(g.inputs)):
        ix, iy = g.input_pos_draw(i)
        if (pos_world[0] - ix) ** 2 + (pos_world[1] - iy) ** 2 <= PIN_HIT ** 2:
            return i
    return None


def find_pin_hit(pos_world):
    for g in reversed(gates):
        if g.deleting:
            continue
        if output_hit(g, pos_world):
            return (g, "out", None)
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
    label = base_font.render("Logical v2.5.4", True, ACCENT)
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
        if conn is None or conn not in gates_by_id:
            vals.append(False)
        else:
            vals.append(gates_by_id[conn].output)
    if multicolor_outputs and len(vals) >= 3:
        active = [MCOLORS[idx] for idx in range(3) if vals[idx]]
        if active:
            r = int(sum(c[0] for c in active) / len(active))
            gg = int(sum(c[1] for c in active) / len(active))
            b = int(sum(c[2] for c in active) / len(active))
            return True, (r, gg, b)
        return False, RED
    return (vals[0] if vals else False), RED


def compute_gate_output(g, gates_by_id):
    vals = []
    for i in range(len(g.inputs)):
        conn = g.inputs[i]
        if conn is None or conn not in gates_by_id:
            vals.append(False)
        else:
            vals.append(gates_by_id[conn].output)

    if g.type == "OUTPUT":
        out_val, _ = output_logic_info(g, gates_by_id)
        return out_val
    if g.type == "DELAY":
        return vals[0] if vals else False
    if g.type == "NOT":
        return not vals[0]
    if g.type == "AND":
        return vals[0] and vals[1]
    if g.type == "NAND":
        return not (vals[0] and vals[1])
    if g.type == "OR":
        return vals[0] or vals[1]
    if g.type == "NOR":
        return not (vals[0] or vals[1])
    if g.type == "XOR":
        return vals[0] != vals[1]
    if g.type == "XNOR":
        return vals[0] == vals[1]
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
            if conn is not None and conn in gates_by_id:
                incoming = gates_by_id[conn].output
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
        g.draw_x += (g.x - g.draw_x) * 0.25
        g.draw_y += (g.y - g.draw_y) * 0.25
        if abs(g.draw_x - prev_x) > 0.01 or abs(g.draw_y - prev_y) > 0.01:
            moved = True
        g.spawn_t = min(1.0, g.spawn_t + 0.08)
        target_hover = 1.0 if hover_gate == g and not g.deleting else 0.0
        target_select = 1.0 if g.id in selected_ids and not g.deleting else 0.0
        g.hover_t += (target_hover - g.hover_t) * ANIM_HOVER
        g.select_t += (target_select - g.select_t) * ANIM_SELECT
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
            ox, oy = g.output_pos_draw()
            sx, sy = world_to_screen((ox, oy))
            pin_color = YELLOW
            if hover_pin[0] == g and hover_pin[1] == "out":
                pin_color = HOVER_PIN
            pin_color = lerp_color(pin_color, BG, g.delete_t)
            size = max(3, int(PIN_RADIUS * zoom))
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
    x, y = pos_screen
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
    if light_mode:
        c = lerp_color(color[:3], (255, 244, 210), 0.28)
        color = (c[0], c[1], c[2], color[3])
    alpha = int(140 * t)
    color = (*color[:3], alpha)
    pygame.draw.rect(surf, color, (5, 5, 80, 50), border_radius=8)
    preview_outline = (195, 180, 130) if light_mode else (160, 160, 180)
    pygame.draw.rect(surf, (*preview_outline, alpha), (5, 5, 80, 50), 2, border_radius=8)
    txt = base_font.render(gtype, True, (240, 240, 245))
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

    menu_t += (menu_target - menu_t) * 0.2
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

    note_w = item_w
    note_h = item_h // 2
    note_x = x0 + (total_w - (note_w * 2 + pad)) // 2
    note_y = y0 + total_h + pad + 8
    note_rect = pygame.Rect(note_x, note_y, note_w, note_h)
    clock_rect = pygame.Rect(note_x + note_w + pad, note_y, note_w, note_h)
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
        n["draw_x"] += (n["x"] - n["draw_x"]) * 0.25
        n["draw_y"] += (n["y"] - n["draw_y"]) * 0.25
        if abs(n["draw_x"] - prev_x) > 0.01 or abs(n["draw_y"] - prev_y) > 0.01:
            moved = True
        n["spawn_t"] = min(1.0, n["spawn_t"] + 0.08)
        target_hover = 1.0 if hover_note == n and not n["deleting"] else 0.0
        target_select = 1.0 if n["id"] in selected_note_ids and not n["deleting"] else 0.0
        n["hover_t"] += (target_hover - n["hover_t"]) * ANIM_HOVER
        n["select_t"] += (target_select - n["select_t"]) * ANIM_SELECT
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

    confirm_t += (confirm_target - confirm_t) * 0.2
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

    exit_confirm_t += (exit_confirm_target - exit_confirm_t) * 0.2
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

    save_scope_t += (save_scope_target - save_scope_t) * 0.2
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

    clock_menu_t += (clock_menu_target - clock_menu_t) * 0.2
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

    delay_menu_t += (delay_menu_target - delay_menu_t) * 0.2
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

    help_t += (help_target - help_t) * 0.2
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
    help_scroll += (help_scroll_target - help_scroll) * 0.22
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
        v += (target - v) * 0.2
        settings_anim[key] = v
        return v

    settings_t += (settings_target - settings_t) * 0.2
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
    settings_scroll += (settings_scroll_target - settings_scroll) * 0.22
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
    btn_w = 140
    btn_h = 38
    gap = 16
    bx = (w - (btn_w * 2 + gap)) // 2
    by = h - 60
    for i, (label, key) in enumerate([("Instructions", "instructions"), ("Close", "close")]):
        rect = pygame.Rect(bx + i * (btn_w + gap), by, btn_w, btn_h)
        hover = rect.move(x0, y0).collidepoint(mx, my)
        color = BUTTON_ACCENT if key == "instructions" else BUTTON_NEUTRAL
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


def draw_wires():
    gates_by_id = {g.id: g for g in gates if not g.deleting}

    def output_dir(g):
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
            r = pygame.Rect(gg.draw_x - 40, gg.draw_y - 25, 80, 50)
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
            src = gates_by_id.get(conn)
            if not src:
                continue
            sx, sy = src.output_pos_draw()
            tx, ty = g.input_pos_draw(idx)
            if straight_wires:
                color = WIRE_ON if src.output else WIRE_OFF
                thickness = max(1, int(2 * zoom * wire_thickness))
                pygame.draw.line(screen, color, world_to_screen((sx, sy)), world_to_screen((tx, ty)), thickness)
                continue
            dx, dy = output_dir(src)
            lead = 18
            sx2 = sx + dx * lead
            sy2 = sy + dy * lead
            ix, iy = input_dir(g)
            in_pre = (tx - ix * lead, ty - iy * lead)

            key = (
                version,
                src.id,
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

            color = WIRE_ON if src.output else WIRE_OFF
            thickness = max(1, int(2 * zoom * wire_thickness))
            pygame.draw.lines(screen, color, False, [world_to_screen(p) for p in points], thickness)


def delete_gate(g):
    gates.remove(g)
    for other in gates:
        for i, conn in enumerate(other.inputs):
            if conn == g.id:
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
            if conn == g.id:
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
            "rel": (rel_x, rel_y),
            "input_state": g.input_state,
            "pin_orient": g.pin_orient,
            "inputs": [inp for inp in g.inputs],
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
        ng = Gate(n["type"], gx, gy)
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
                elif inp in id_set:
                    new_inputs.append(new_map[inp].id)
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
    return {
        "gates": [
            {
                "id": g.id,
                "type": g.type,
                "x": g.x,
                "y": g.y,
                "input_state": g.input_state,
                "pin_orient": g.pin_orient,
                "inputs": list(g.inputs),
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
        "settings": {
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
        },
    }


def restore_state(state):
    global gates, selected_gate, selected_ids, selected_note_ids, next_id, cam_x, cam_y, zoom, notes
    global wire_cache, signal_pending
    global straight_wires, snap_to_grid, zoom_min, zoom_max, gate_label_scale, note_font_scale
    global show_pins_always, selection_brightness, auto_center, wire_thickness, signal_delay_enabled, multicolor_outputs, light_mode
    gates = []
    notes = []
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
        g = Gate(n["type"], n["x"], n["y"])
        g.id = n["id"]
        g.input_state = n["input_state"]
        g.pin_orient = n.get("pin_orient", 0)
        g.inputs = list(n["inputs"])
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
            "rel": (g.x - cx, g.y - cy),
            "input_state": g.input_state,
            "pin_orient": g.pin_orient,
            "inputs": [inp if inp in id_set else None for inp in g.inputs],
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

    return {
        "kind": "logical_segment",
        "gates": seg_gates,
        "notes": seg_notes,
    }


def apply_segment_state(segment_state, mouse_pos_screen):
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
        ng = Gate(n["type"], gx, gy)
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
            elif inp in new_map:
                new_inputs.append(new_map[inp].id)
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
    segment_mode = scope == "segment"
    state = selected_segment_data() if segment_mode else serialize_state()
    if state is None:
        return False
    path = prompt_save_path(segment=segment_mode)
    if not path:
        return False
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
        return True
    except Exception:
        return False


def exit_app():
    pygame.quit()
    sys.exit()


def load_from_file():
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


def paste_segment_from_file(mouse_pos_screen):
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


# Main loop
frame_dt = 1.0 / FPS
while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            if not confirm_open and not exit_confirm_open and not save_scope_open and not clock_menu_open and not delay_menu_open:
                help_open = False
                help_target = 0.0
                settings_open = False
                settings_target = 0.0
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
            if event.key == pygame.K_SPACE:
                if note_edit_id is None:
                    exit_confirm_open = True
                    exit_confirm_target = 1.0
            if event.key == pygame.K_ESCAPE:
                confirm_open = True
                confirm_target = 1.0
            if event.key == pygame.K_TAB:
                settings_open = True
                settings_target = 1.0
                settings_scroll = 0.0
                settings_scroll_target = 0.0
            if event.key == pygame.K_s and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                save_scope_open = True
                save_scope_target = 1.0
            if event.key == pygame.K_l and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                load_from_file()
            if event.key == pygame.K_z and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                undo()
            if event.key == pygame.K_y and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                redo()
            if event.key in (pygame.K_r, pygame.K_t):
                if selected_ids:
                    candidates = [g for g in gates if g.id in selected_ids and not g.deleting]
                    if candidates:
                        push_undo()
                        for g in candidates:
                            if event.key == pygame.K_r:
                                g.pin_orient = (g.pin_orient + 1) % 4
                            else:
                                g.pin_orient = (g.pin_orient - 1) % 4
                        bump_layout()
            if event.key == pygame.K_BACKSPACE:
                delete_selected()
            if event.key == pygame.K_c and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                copy_selected()
            if event.key == pygame.K_v and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                if pygame.key.get_mods() & pygame.KMOD_SHIFT:
                    paste_segment_from_file(pygame.mouse.get_pos())
                else:
                    paste_copy(pygame.mouse.get_pos())
            if event.key == pygame.K_c and not (pygame.key.get_mods() & pygame.KMOD_CTRL):
                push_undo()
                gates.clear()
                wire_from = None
                selected_ids.clear()

        if event.type == pygame.MOUSEWHEEL:
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

                    if buttons.get("toggle_straight") and buttons["toggle_straight"].collidepoint(event.pos):
                        straight_wires = not straight_wires
                        wire_cache.clear()
                        bump_layout()
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
                    elif buttons.get("toggle_pins") and buttons["toggle_pins"].collidepoint(event.pos):
                        show_pins_always = not show_pins_always
                    elif buttons.get("toggle_center") and buttons["toggle_center"].collidepoint(event.pos):
                        auto_center = not auto_center
                    elif buttons.get("toggle_light_mode") and buttons["toggle_light_mode"].collidepoint(event.pos):
                        light_mode = not light_mode
                        apply_theme()
                    elif buttons.get("toggle_signal_delay") and buttons["toggle_signal_delay"].collidepoint(event.pos):
                        signal_delay_enabled = not signal_delay_enabled
                        if not signal_delay_enabled:
                            signal_pending.clear()
                    elif buttons.get("toggle_multicolor") and buttons["toggle_multicolor"].collidepoint(event.pos):
                        multicolor_outputs = not multicolor_outputs
                        remap_output_gate_inputs(multicolor_outputs)
                        signal_pending.clear()
                    elif buttons.get("instructions") and buttons["instructions"].collidepoint(event.pos):
                        settings_target = 0.0
                        settings_open = False
                        settings_drag_slider = None
                        help_open = True
                        help_target = 1.0
                        help_scroll = 0.0
                        help_scroll_target = 0.0
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

            note_hit = note_at_screen((mx, my))
            if note_edit_id is not None and (note_hit is None or note_hit["id"] != note_edit_id):
                finish_note_edit(commit=True)

            if note_hit:
                if selected_note_ids != {note_hit["id"]}:
                    selected_note_ids = {note_hit["id"]}
                    selected_ids.clear()
                now = pygame.time.get_ticks()
                if last_click_note_id == note_hit["id"] and now - last_click_time <= 350:
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
                        wire_from = hit_gate.id
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

            if menu_open:
                items = draw_gate_menu(menu_pos)
                clicked_item = False
                for gtype, rect in items:
                    if rect.collidepoint(mx, my):
                        selected_gate = gtype
                        menu_open = False
                        menu_target = 0.0
                        clicked_item = True
                        break
                if clicked_item:
                    continue

            selecting = True
            select_start = (mx, my)
            select_rect = None

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            if confirm_open or exit_confirm_open or save_scope_open or clock_menu_open or delay_menu_open or help_open or settings_open:
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
            if confirm_open or exit_confirm_open or save_scope_open or clock_menu_open or delay_menu_open or help_open or settings_open:
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
                            gates.append(Gate(selected_gate, world_pos[0], world_pos[1]))
                            bump_layout()

        if event.type == pygame.MOUSEBUTTONUP and event.button == 3:
            if confirm_open or exit_confirm_open or save_scope_open or clock_menu_open or delay_menu_open or help_open or settings_open:
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
                continue
            if confirm_open or exit_confirm_open or save_scope_open or clock_menu_open or delay_menu_open or help_open or settings_open:
                continue
            mx, my = event.pos
            if _drag_note_pending and _drag_note:
                dx = mx - _drag_start[0]
                dy = my - _drag_start[1]
                if abs(dx) >= DRAG_THRESHOLD or abs(dy) >= DRAG_THRESHOLD:
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

    hide_preview = (
        hover_gate is not None
        or hover_pin[0] is not None
        or hover_note is not None
        or menu_open
        or save_scope_open
        or clock_menu_open
        or delay_menu_open
        or selected_gate is None
    )
    preview_target = 0.0 if hide_preview else 1.0
    preview_t += (preview_target - preview_t) * ANIM_PREVIEW
    draw_gate_preview(selected_gate, (mx, my), preview_t)

    select_target = 1.0 if selecting else 0.0
    select_t += (select_target - select_t) * ANIM_SELECT_RECT
    if selecting and select_rect:
        draw_selection_rect(select_rect)

    if wire_from is not None:
        preview_x += (world_mouse[0] - preview_x) * 0.35
        preview_y += (world_mouse[1] - preview_y) * 0.35
        src = next((s for s in gates if s.id == wire_from), None)
        if src:
            sx, sy = src.output_pos_draw()
            s1 = world_to_screen((sx, sy))
            s2 = world_to_screen((preview_x, preview_y))
            color = WIRE_ON if src.output else WIRE_OFF
            thickness = max(1, int(2 * zoom * wire_thickness))
            pygame.draw.line(screen, color, s1, s2, thickness)

    help_text = "Tab: settings"
    screen.blit(base_small.render(help_text, True, GRAY), (12, HEIGHT - 24))

    if note_edit_id is not None:
        note_blink_t += 1.0 / FPS
        note_edit_anim_t = min(1.0, note_edit_anim_t + 0.12)

    pygame.display.flip()
    frame_dt = CLOCK.tick(FPS) / 1000.0
