import os
os.enviton["APP_NAME"] = "Marco"

import rumpy
runpy.run_path("app.py",run_name="__luigi__")
