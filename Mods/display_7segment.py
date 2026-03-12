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

        
        # Import the global gate map from the main script
        import Logical
        
        # Scale segments based on actual gate size vs base 100x160
        scale_x = (gate.w / 100) * zoom
        scale_y = (gate.h / 160) * zoom
        
        for i in range(min(len(gate.inputs), len(segments))):
            conn = gate.inputs[i]
            is_on = False
            
            # Use the simulator's built-in function to get the output state
            # This correctly handles both integer IDs and (ID, index) tuples
            if conn is not None and hasattr(Logical, 'gates_by_id_map'):
                is_on = Logical.conn_output_state(conn, Logical.gates_by_id_map)
            
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

