import os
import importlib.util
import sys

class ModManager:
    def __init__(self, mod_dir=None):
        if mod_dir is None:
            # Default to 'mods' folder next to this script
            base_dir = os.path.dirname(os.path.abspath(__file__))
            self.mod_dir = os.path.join(base_dir, "mods")
        else:
            self.mod_dir = mod_dir
        self.mods = {}
        self.gate_registry = {}
        self.hooks = {
            'on_init': [],
            'on_update': [],
            'on_draw': [],
            'on_event': []
        }

    def load_mods(self):
        if not os.path.exists(self.mod_dir):
            os.makedirs(self.mod_dir)

        for filename in os.listdir(self.mod_dir):
            if filename.endswith(".py") and not filename.startswith("__"):
                mod_name = filename[:-3]
                file_path = os.path.join(self.mod_dir, filename)
                
                spec = importlib.util.spec_from_file_location(mod_name, file_path)
                mod = importlib.util.module_from_spec(spec)
                sys.modules[mod_name] = mod
                try:
                    spec.loader.exec_module(mod)
                    self.mods[mod_name] = mod
                    print(f"Loaded mod: {mod_name}")
                    
                    # Call mod's setup if it exists
                    if hasattr(mod, "setup"):
                        mod.setup(self)
                except Exception as e:
                    print(f"Failed to load mod {mod_name}: {e}")

    def register_gate(self, name, eval_fn, color=(70, 70, 80), inputs=2, spacing=12, **kwargs):
        self.gate_registry[name] = {
            'eval': eval_fn,
            'color': color,
            'inputs': inputs,
            'spacing': spacing
        }
        self.gate_registry[name].update(kwargs)
        print(f"Registered custom gate: {name} (w={self.gate_registry[name].get('w')}, h={self.gate_registry[name].get('h')}, spacing={self.gate_registry[name].get('spacing')})")

    def add_hook(self, event, fn):
        if event in self.hooks:
            self.hooks[event].append(fn)

    def dispatch(self, event, *args, **kwargs):
        if event in self.hooks:
            for fn in self.hooks[event]:
                try:
                    fn(*args, **kwargs)
                except Exception as e:
                    print(f"Error in hook {event}: {e}")

# Global instance
mod_manager = ModManager()
