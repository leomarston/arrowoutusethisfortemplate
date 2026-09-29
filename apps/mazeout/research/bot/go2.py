#!/usr/bin/env python3
"""go2.py LEVEL NNN [go.py flags] — session 2: go.py with the corner add-on (corners.py) patched into bot before it runs."""
import os, sys, runpy
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here)
import corners  # noqa: F401  (patches bot.read_board / bot.ray)
sys.argv = [os.path.join(here, 'go.py')] + sys.argv[1:]
runpy.run_path(os.path.join(here, 'go.py'), run_name='__main__')
