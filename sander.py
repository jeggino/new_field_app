import os
os.environ["APP_NAME"] = "sander"

import runpy
runpy.run_path("home.py",run_name="__main__")
