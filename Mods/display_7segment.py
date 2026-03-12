import pygame

def setup(manager):
    # Segment definitions: (x_rel, y_rel, w_rel, h_rel)
    # Relative to the gate's top-left in its custom 100x160 size
    segments = [
        (20, 15, 60, 10),  # A (top)
        (75, 25, 10, 50),  # B (upper right)
        (75, 85, 10, 50),  # C (lower right)
        (20, 135, 60, 10), # D (bottom)
        (15, 85, 10, 50),  # E (lower left)
        (15, 25, 10, 50),  # F (upper left)
        (20, 75, 60, 10),  # G (middle)
    ]
    
    def eval_7seg(inputs):
        return False # Displays don't output anything

    # Register the gate with custom size 100x160, 7 inputs and custom spacing
    manager.register_gate("7SEG", eval_7seg, color=(30, 30, 40), inputs=7, w=100, h=160, spacing=20)

    def on_draw(gate, screen, rect, zoom):
        if gate.type != "7SEG":
            return

        # Get the logical values of the 7 inputs
        # gate.inputs contains IDs of connected gates
        # We need their current output state
        # In Logical.py, gate.eval() stores the result in gate.output
        # But we need the value of EACH input.
        # However, the simulator computes these in eval_all.
        # Let's assume we can access the connected gates' output.
        # Wait, I should've passed gates_by_id or the states to on_draw.
        # Actually, let's look at how evaluation is done.
        
        # For simplicity in this example, let's assume we can access global 'gates_by_id' 
        # or if we are in the draw loop, the evaluation for this frame is already done.
        # But wait, the display 'inputs' are IDs.
        
        # Import the global gate map from the main script
        import Logical
        
        # Scale segments based on actual gate size vs base 100x160
        scale_x = (gate.w / 100) * zoom
        scale_y = (gate.h / 160) * zoom
        
        for i in range(min(len(gate.inputs), len(segments))):
            conn_id = gate.inputs[i]
            is_on = False
            if conn_id is not None and conn_id in Logical.gates_by_id_map:
                is_on = Logical.gates_by_id_map[conn_id].output
            
            seg_color = (255, 50, 50) if is_on else (50, 20, 20)
            
            # Draw segment relative to gate rect, scaled
            sx, sy, sw, sh = segments[i]
            seg_rect = pygame.Rect(
                rect.x + sx * scale_x,
                rect.y + sy * scale_y,
                sw * scale_x,
                sh * scale_y
            )
            pygame.draw.rect(screen, seg_color, seg_rect, border_radius=int(2*zoom))

    # Note: I need to make sure 'gates_by_id_map' is accessible.
    manager.add_hook("on_draw", on_draw)

    def on_init():
        print("7SEG Mod Initialized!")
        
    manager.add_hook("on_init", on_init)    
