import Logical
def setup(manager):
    def eval_and3(inputs):
        # AND behavior: Return True only if ALL 3 inputs are True
        return inputs[0] and inputs[1]
    
    manager.register_gate("AND3", eval_and3, color=(90, 160, 255), inputs=2, spacing=15)
    
    def on_init():
        print("AND3 Mod Initialized!")
        
    manager.add_hook("on_init", on_init)
