import sys
import os
import re
import types
import pygame

# 1. Resolve paths relative to this script
script_dir = os.path.dirname(os.path.abspath(__file__))
original_file = os.path.join(script_dir, "Logical.py")

if not os.path.exists(original_file):
    print(f"Error: {original_file} not found!")
    sys.exit(1)

with open(original_file, "r", encoding="utf-8") as f:
    code = f.read()

# 2. Patching Logic (Highly specific replacements to avoid definition matches)
def patch_code(c):
    # A. Imports
    c = c.replace("import heapq", "import heapq\nfrom mod_loader import mod_manager")
    
    # B. GATE_TYPES
    c = c.replace('    "XNOR",\n]', '    "XNOR",\n]\nfor custom_gate in mod_manager.gate_registry: GATE_TYPES.append(custom_gate)')
    
    # C. gates_by_id_map and eval_all
    c = c.replace("\ngates = []", "\ngates = []\ngates_by_id_map = {}")
    # Specific anchor for the definition to avoid accidental matches
    c = c.replace("def eval_all(dt=0.0):\n    global signal_pending", 
                  "def eval_all(dt=0.0):\n    global signal_pending, gates_by_id_map")
    c = c.replace("    gates_by_id = {g.id: g for g in gates if not g.deleting}", 
                  "    gates_by_id_map = {g.id: g for g in gates if not g.deleting}\n    gates_by_id = gates_by_id_map")
    
    # D. Gate.__init__
    init_defaults = "        self.spawn_t = 0.0\n        self.w = 80\n        self.h = 50\n        self.spacing = 12"
    c = c.replace("        self.spawn_t = 0.0", init_defaults)

    init_target = """        elif gtype in ONE_INPUT:
            self.inputs = [None]
        else:
            self.inputs = []"""
    init_replacement = """        elif gtype in ONE_INPUT:
            self.inputs = [None]
        elif gtype in mod_manager.gate_registry:
            reg = mod_manager.gate_registry[gtype]
            self.inputs = [None] * reg.get('inputs', 2)
            self.w = reg.get('w', 80)
            self.h = reg.get('h', 50)
            self.spacing = reg.get('spacing', 12)
            print(f"Created {gtype} with w={self.w}, h={self.h}, spacing={self.spacing}")
        else:
            self.inputs = []"""
    c = c.replace(init_target, init_replacement)
    
    # E. Rects
    c = c.replace("return pygame.Rect(self.x - 40, self.y - 25, 80, 50)", 
                  "return pygame.Rect(self.x - self.w / 2, self.y - self.h / 2, self.w, self.h)")
    c = c.replace("w = 80 * scale\n            h = 50 * scale", 
                  "w = self.w * scale\n            h = self.h * scale")
    
    # F. Obstacles
    c = c.replace("r = pygame.Rect(gg.draw_x - r.w / 2, gg.draw_y - r.h / 2, r.w, r.h)",
                  "r = pygame.Rect(gg.draw_x - gg.w / 2, gg.draw_y - gg.h / 2, gg.w, gg.h)")
    
    # K. Pin Positions
    input_pos_patch = """    def input_pos_draw(self, idx):
        dx_edge = self.w / 2
        dy_edge = self.h / 2
        spread = self.spacing

        if len(self.inputs) == 2:
            if self.pin_orient == 0:  # inputs left
                return (self.draw_x - dx_edge, self.draw_y - spread if idx == 0 else self.draw_y + spread)
            if self.pin_orient == 1:  # inputs bottom
                return (self.draw_x - spread if idx == 0 else self.draw_x + spread, self.draw_y + dy_edge)
            if self.pin_orient == 2:  # inputs right
                return (self.draw_x + dx_edge, self.draw_y - spread if idx == 0 else self.draw_y + spread)
            return (self.draw_x - spread if idx == 0 else self.draw_x + spread, self.draw_y - dy_edge)

        if len(self.inputs) > 2:
            offset = (idx - (len(self.inputs) - 1) / 2.0) * spread
            if self.pin_orient == 0:
                return (self.draw_x - dx_edge, self.draw_y + offset)
            if self.pin_orient == 1:
                return (self.draw_x + offset, self.draw_y + dy_edge)
            if self.pin_orient == 2:
                return (self.draw_x + dx_edge, self.draw_y + offset)
            return (self.draw_x + offset, self.draw_y - dy_edge)

        if self.pin_orient == 0:
            return (self.draw_x - dx_edge, self.draw_y)
        if self.pin_orient == 1:
            return (self.draw_x, self.draw_y + dy_edge)
        if self.pin_orient == 2:
            return (self.draw_x + dx_edge, self.draw_y)
        return (self.draw_x, self.draw_y - dy_edge)

    def _old_input_pos_draw(self, idx):"""

    output_pos_patch = """    def output_pos_draw(self):
        dx_edge = self.w / 2
        dy_edge = self.h / 2
        if self.pin_orient == 0:
            return (self.draw_x + dx_edge, self.draw_y)
        if self.pin_orient == 1:
            return (self.draw_x, self.draw_y - dy_edge)
        if self.pin_orient == 2:
            return (self.draw_x - dx_edge, self.draw_y)
        return (self.draw_x, self.draw_y + dy_edge)

    def _old_output_pos_draw(self):"""
    
    c = c.replace("    def input_pos_draw(self, idx):", input_pos_patch)
    c = c.replace("    def output_pos_draw(self):", output_pos_patch)
    
    # F. Gate.eval
    c = c.replace('        if self.type in ("INPUT", "BUTTON", "CLOCK"):', 
                  '        if self.type in mod_manager.gate_registry:\n            vals = []\n            for i in range(len(self.inputs)):\n                conn = self.inputs[i]\n                vals.append(gates_by_id[conn].output if (conn is not None and conn in gates_by_id) else False)\n            self.output = mod_manager.gate_registry[self.type]["eval"](vals)\n            return\n        if self.type in ("INPUT", "BUTTON", "CLOCK"):')
    
    # F2. compute_gate_output patch for eval_all loop
    compute_target = '    if g.type == "XNOR":\n        return sum(1 for v in vals if v) != 1\n    return g.output'
    compute_replace = '    if g.type == "XNOR":\n        return sum(1 for v in vals if v) != 1\n    if g.type in mod_manager.gate_registry:\n        return mod_manager.gate_registry[g.type]["eval"](vals)\n    return g.output'
    c = c.replace(compute_target, compute_replace)
    
    # G. Draw hooks
    c = c.replace('if g.type == "OUTPUT":\n            color = g.output_color if g.output else (130, 70, 70)', 
                  'if g.type == "OUTPUT":\n            color = g.output_color if g.output else (130, 70, 70)\n        if g.type in mod_manager.gate_registry: color = mod_manager.gate_registry[g.type].get("color", color)')
    c = c.replace('pygame.draw.rect(screen, color, rect, border_radius=radius)', 
                  'pygame.draw.rect(screen, color, rect, border_radius=radius)\n        mod_manager.dispatch("on_draw", g, screen, rect, zoom)')
    
    # H. Mod Menu Logic Injection
    mod_menu_logic = r'''
mod_menu_open = False
mod_menu_t = 0.0
mod_menu_pos = (0, 0)
mod_menu_target = 0.0

def draw_mod_menu(pos_screen):
    global mod_menu_t, mod_menu_open
    if not mod_menu_open and mod_menu_t <= 0.01: return []
    mod_menu_t += (mod_menu_target - mod_menu_t) * 0.2
    if mod_menu_t < 0.01: mod_menu_t = 0.0
    if mod_menu_t > 0.99: mod_menu_t = 1.0
    gate_names = list(mod_manager.gate_registry.keys())
    if not gate_names: mod_menu_open = False; return []
    items, cols, item_w, item_h, pad = [], 3, 150, 80, 10
    rows = math.ceil(len(gate_names) / cols)
    total_w, total_h = cols * item_w + (cols - 1) * pad, rows * item_h + (rows - 1) * pad
    x0, y0 = pos_screen; x0, y0 = min(max(20, x0 - total_w // 2), WIDTH - total_w - 20), min(max(20, y0 - total_h // 2), HEIGHT - total_h - 20)
    alpha = int(220 * mod_menu_t); panel = pygame.Surface((total_w + 20, total_h + 20), pygame.SRCALPHA)
    pygame.draw.rect(panel, (*PANEL, alpha), (0, 0, total_w + 20, total_h + 20), border_radius=12)
    pygame.draw.rect(panel, (*DIALOG_BORDER_SOFT, alpha), (0, 0, total_w + 20, total_h + 20), 1, border_radius=12)
    screen.blit(panel, (x0 - 10, y0 - 10)); mx, my = pygame.mouse.get_pos()
    for i, gname in enumerate(gate_names):
        r, c = i // cols, i % cols; rect = pygame.Rect(x0 + c*(item_w+pad), y0 + r*(item_h+pad), item_w, item_h)
        t = max(0.0, min(1.0, (mod_menu_t - (i * 0.06)) / 0.4)); ease = t * t * (3 - 2 * t); alpha_item = int(255 * ease)
        draw_rect = rect.move(0, int((1.0 - ease) * 16)); hover = draw_rect.collidepoint(mx, my)
        tile = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        pygame.draw.rect(tile, (*(MENU_TILE_HOVER if hover else MENU_TILE), alpha_item), tile.get_rect(), border_radius=10)
        pygame.draw.rect(tile, (*MENU_BORDER, alpha_item), tile.get_rect(), 1, border_radius=10)
        lbl = base_small.render(gname, True, WHITE); lbl.set_alpha(alpha_item)
        tile.blit(lbl, (rect.w//2 - lbl.get_width()//2, rect.h//2 - lbl.get_height()//2))
        screen.blit(tile, draw_rect.topleft); items.append((gname, draw_rect))
    return items
'''
    c = c.replace('def draw_gate_menu(pos_screen):', mod_menu_logic + 'def draw_gate_menu(pos_screen):')

    # H2. Inject 'MODS' button above the vanilla gates menu
    target_custom = '    items.append(("CUSTOM_MENU", custom_rect))\n\n    return items'
    replace_custom = '''    items.append(("CUSTOM_MENU", custom_rect))

    # MODS Button
    mods_w = 120
    mods_h = 36
    mods_rect = pygame.Rect(x0 + total_w // 2 - mods_w // 2, y0 - mods_h - pad - 8, mods_w, mods_h)
    mods_hover = mods_rect.collidepoint(mx, my)
    mods_color = MENU_TILE if not mods_hover else MENU_TILE_HOVER
    mods_tile = pygame.Surface((mods_rect.w, mods_rect.h), pygame.SRCALPHA)
    pygame.draw.rect(mods_tile, (*mods_color, note_alpha), mods_tile.get_rect(), border_radius=10)
    pygame.draw.rect(mods_tile, (*MENU_BORDER, note_alpha), mods_tile.get_rect(), 1, border_radius=10)
    mods_label = base_small.render("MODS", True, WHITE)
    mods_label.set_alpha(note_alpha)
    mods_tile.blit(mods_label, (mods_rect.w // 2 - mods_label.get_width() // 2, mods_rect.h // 2 - mods_label.get_height() // 2))
    screen.blit(mods_tile, mods_rect.topleft)
    items.append(("MODS", mods_rect))

    return items'''
    c = c.replace(target_custom, replace_custom)

    # I. Hooks & Event Handling
    event_replace = r'''            if menu_open:
                items = draw_gate_menu(menu_pos)
                clicked_item = False
                for gtype, rect in items:
                    if rect.collidepoint(mx, my):
                        if gtype == "MODS":
                            mod_menu_open, mod_menu_target, mod_menu_pos = True, 1.0, (mx, my)
                            menu_open, menu_target = False, 0.0
                        else:
                            selected_gate = gtype
                            menu_open, menu_target = False, 0.0
                        clicked_item = True; break
                if clicked_item: continue
            if mod_menu_open:
                items = draw_mod_menu(mod_menu_pos)
                clicked_item = False
                for gname, rect in items:
                    if rect.collidepoint(mx, my):
                        selected_gate = gname
                        mod_menu_open, mod_menu_target = False, 0.0
                        clicked_item = True; break
                if clicked_item: continue'''
    c = c.replace('            if menu_open:', event_replace)
    c = c.replace('menu_open = False\n                menu_target = 0.0', 'menu_open = False; menu_target = 0.0; mod_menu_open = False; mod_menu_target = 0.0')
    c = c.replace('selected_gate = None\n                menu_open = False\n                menu_target = 0.0', 'selected_gate = None; menu_open = False; menu_target = 0.0; mod_menu_open = False; mod_menu_target = 0.0')

    draw_calls = '''    if menu_open or menu_t > 0.01:
        _ = draw_gate_menu(menu_pos)
    if mod_menu_open or mod_menu_t > 0.01:
        _ = draw_mod_menu(mod_menu_pos)'''
    c = c.replace('    if menu_open or menu_t > 0.01:\n        _ = draw_gate_menu(menu_pos)', draw_calls)
    
    # I. Hooks
    c = c.replace('        for event in pygame.event.get():', '        for event in pygame.event.get():\n            mod_manager.dispatch("on_event", event)')
    c = c.replace('        eval_all(frame_dt)', '        eval_all(frame_dt)\n        mod_manager.dispatch("on_update", frame_dt)')
    
    # J. Init call - Use a very specific anchor to avoid definition match
    # Definition is 'def apply_window_branding():'
    # Call is 'apply_window_branding()' at top level
    c = c.replace('\napply_window_branding()\n', 
                  '\napply_window_branding()\n# Mod Loader Injection\nfrom mod_loader import mod_manager\nmod_manager.load_mods()\nmod_manager.dispatch("on_init")\n')
                  
    # K. Settings Restart Button
    settings_btn_target = '''    # Buttons
    btn_w = 140
    btn_h = 38
    gap = 16
    bx = (w - (btn_w * 2 + gap)) // 2
    by = h - 60
    for i, (label, key) in enumerate([("Instructions", "instructions"), ("Close", "close")]):
        rect = pygame.Rect(bx + i * (btn_w + gap), by, btn_w, btn_h)
        hover = rect.move(x0, y0).collidepoint(mx, my)
        color = BUTTON_ACCENT if key == "instructions" else BUTTON_NEUTRAL'''
        
    settings_btn_replace = '''    # Buttons
    btn_w = 140
    btn_h = 38
    gap = 16
    bx = (w - (btn_w * 3 + gap * 2)) // 2
    by = h - 60
    for i, (label, key) in enumerate([("Instructions", "instructions"), ("Restart", "restart"), ("Close", "close")]):
        rect = pygame.Rect(bx + i * (btn_w + gap), by, btn_w, btn_h)
        hover = rect.move(x0, y0).collidepoint(mx, my)
        color = BUTTON_ACCENT if key == "instructions" else (BUTTON_DANGER if key == "restart" else BUTTON_NEUTRAL)'''
    c = c.replace(settings_btn_target, settings_btn_replace)

    settings_event_target = '''                    elif buttons.get("close") and buttons["close"].collidepoint(event.pos):
                        settings_target = 0.0
                        settings_open = False
                        settings_drag_slider = None'''
                        
    settings_event_replace = '''                    elif buttons.get("restart") and buttons["restart"].collidepoint(event.pos):
                        import subprocess, sys
                        subprocess.Popen([sys.executable, sys.argv[0]] + sys.argv[1:])
                        sys.exit(0)
                    elif buttons.get("close") and buttons["close"].collidepoint(event.pos):
                        settings_target = 0.0
                        settings_open = False
                        settings_drag_slider = None'''
    c = c.replace(settings_event_target, settings_event_replace)
    
    return c

# 3. Execution
patched_code = patch_code(code)

# Change CWD to the simulator directory for asset loading
os.chdir(script_dir)

# Mock the "Logical" module so mods can import variables from it
logical_mod = types.ModuleType("Logical")
logical_mod.__dict__.update({
    '__name__': '__main__',
    '__file__': os.path.join(script_dir, "Logical.py"),
})
sys.modules["Logical"] = logical_mod

# Run the patched code
try:
    exec(patched_code, logical_mod.__dict__)
except Exception as e:
    import traceback
    print("Error during execution of patched code:")
    traceback.print_exc()
    # Save debug file if it fails
    with open("patched_logical_debug.py", "w", encoding="utf-8") as f:
        f.write(patched_code)
    sys.exit(1)
