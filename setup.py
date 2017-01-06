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

returncode = subprocess.call(python_command + " -m virtualenv virtualenv")
if returncode != 0:
    print()
    print("Virtual environment creation failed!")
    print("Is virtualenv installed? Try running the following as an admin/root:")
    print(python_command, "-m pip install virtualenv")
    exit(1)

if not venv_python.exists():
    print("Unable to find the python executable in:", str(venv_python))
    exit(1)

print()
print("Installing modules...")
must_return_0(str(venv_python) + " -m pip install -r requirements.txt")

print()
print("That's it! You should be good to go!")
print("To start PRAWToys, just run: python run_prawtoys.py")
print("Running 'python prawtoys.py' WILL NOT WORK!")
