# SCRIPT LIST
SCRIPT_LIST = [
    "picture.py"
]






# CODE
import os

class Script():
    # Just a container
    pass

def _load():
    global SCRIPTS, _load, Script, os
    
    for i in SCRIPT_LIST:
        # Load module (I couldn't get importlib.load_module to work :/)
        filepath = os.path.join(os.path.dirname(__file__), i)
        
        module = Script()
        with open(filepath, "r", encoding="utf8") as f:
            exec(f.read(), {}, module.__dict__)

        # Save it    
        SCRIPTS[module.NAME] = module
    
    del _load   # Don't clobber the global namespace (in case of "from scripts import *")
    del Script
    del os

SCRIPTS = {}
_load()
