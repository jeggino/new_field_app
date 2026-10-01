import os
os.environ["APP_NAME"] = "Luigi"

import runpy
runpy.run_path("home.py",run_name="__main__")
