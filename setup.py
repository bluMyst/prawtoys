import sys
import os
import pathlib
import subprocess

if os.name not in ['nt', 'posix']:
    print("Unrecognized OS type:", os.name)
    exit(1)

# It's either Windows or Linux. Nothing else is supported.
is_windows = os.name == 'nt'

# The prawtoys folder with everything in it.
root = pathlib.Path(sys.path[0])

venv_scripts = root / "virtualenv" / "Scripts"
venv_python = venv_scripts / ("python.exe" if is_windows else "python")

# os.devnull is 'nul' on Windows and '/dev/null' on *nix.
devnull = open(os.devnull, 'w')

def must_return_0(cmd, *args, **kwargs):
    """ run subprocess.call and exit the program if the returncode != 0 """
    returncode = subprocess.call(cmd, *args, **kwargs)

    if returncode != 0:
        print("Uh oh! Failed to run the command:", cmd)
        print("Got nonzero return code:", returncode)
        exit(1)

if (root / 'virtualenv').exists():
    #      |--------------------------------80 characters---------------------------------|
    print("It looks like there's already a folder called virtualenv. If you're having")
    print("trouble with the virtualenv and want to re-generate it, delete that folder and")
    print("run this script again.")
    exit(1)

# Try to figure out what the Python command is called on this system.
print("Searching for Python command name...")

for python_command in ['python3', 'python']:
    try:
        returncode = subprocess.call(python_command + ' --version',
                                     stdout=devnull)
    except FileNotFoundError:
        continue

    if returncode != 0:
        print("Found Python under the name 'python3', but it gave is an error.")
        exit(1)
    else:
        print("Found it! It's '" + python_command + "'")
        break # python_command is now set to the right value
else:
    print("Couldn't figure out where Python was!")
    exit(1)

print()
print("Creating virtual environment...")
must_return_0(python_command + " -m virtualenv virtualenv")

if not venv_python.exists():
    print("Unable to find the python executable in:", str(venv_python))
    exit(1)

print()
print("Installing modules...")
must_return_0(str(venv_python) + " -m pip install -r requirements.txt")

# We need a script to run prawtoys because we need to run it through our
# virtual environment, and asking the user to do that manually is too much
# hassle.
#
# Either write:
# virtualenv\Scripts\python.exe prawtoys.py %*
#
# for Windows, or:
# virtualenv/Scripts/python prawtoys.py "$@"
# For *nix.
#
# Those little things on the end make sure that all arguments are
# passed correctly.
print("Generating prawtoys script...")

if is_windows:
    with (root / "prawtoys.bat").open('w') as script:
        script.write("@echo off\n\n")

        script.write("{python} {prawtoys} %*\n".format(
            python=str(venv_python),
            prawtoys=str(root / "prawtoys.py")))
else:
    with (root / "prawtoys.sh").open('w') as script:
        script.write("#!/bin/bash\n\n")

        script.write("{python} {prawtoys} \"$@\"\n".format(
            python=str(venv_python),
            prawtoys=str(root / "prawtoys.py")))

print()
print("That's it! You should be good to go!")
print("To start PRAWToys, just run:",
      "prawtoys.bat" if is_windows else "prawtoys.sh")
print("Running 'python prawtoys.py' WILL NOT WORK!")
