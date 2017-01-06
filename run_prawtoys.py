import sys
import os
import pathlib
import subprocess

# TODO: Don't repeat yourself. Most of this code is also in setup.py
if os.name not in ['nt', 'posix']:
    print("Unrecognized OS type:", os.name)
    exit(1)

# It's either Windows or Linux. Nothing else is supported.
is_windows = os.name == 'nt'

# The prawtoys folder with everything in it.
root = pathlib.Path(sys.path[0])

venv_python = (root / "virtualenv" / "Scripts"
    / ("python.exe" if is_windows else "python"))

if not venv_python.exists():
    print("Couldn't find:", str(venv_python))
    print("Have you run setup.py yet?")
    exit(1)

exit(subprocess.call("{python} {prawtoys}".format(
    python=str(venv_python),
    prawtoys=str(root / "prawtoys.py"))))
