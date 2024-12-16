#!/usr/bin/python

import subprocess
import os
import sys

def main():
    cwd = os.path.dirname(os.path.realpath(__file__))
    os.chdir(cwd)
    if subprocess.call([sys.executable, "-m", "venv", cwd]):
        print("Could not create a virtual environment")
        exit(-1)
    environ = os.environ.copy()
    environ["PATH"] = f"{cwd}/bin:{os.getenv('PATH')}"
    environ["VIRTUAL_ENV"] = cwd
    if 'PYTHONPATH' in environ:
        del environ['PYTHONPATH']
    if 'PYTHONHOME' in environ:
        del environ['PYTHONHOME']
    print(environ)
    if subprocess.call([f"{cwd}/bin/pip", "install", "zc.buildout"], env=environ):
        print("Could not install buildout")
        exit(-1)

if __name__ == "__main__":
    main()