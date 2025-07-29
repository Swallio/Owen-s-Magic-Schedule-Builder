from setuptools import setup

APP = ["main.py"]
DATA_FILES = ["icon.icns"]

OPTIONS = {
    "iconfile": "icon.icns",
    "no_strip": True,
    # we already proved you don’t need Tk
    "excludes": ["tkinter", "_tkinter", "tcl", "tk"],
    "force_system_tk": False,

    "plist": {
        "CFBundleName": "Magic Schedule Builder",
        "CFBundleIdentifier": "com.owen.magic-schedule-builder",
        "CFBundleShortVersionString": "1.0",

        # ←--- THIS is what the stub looks for
        "PyRuntimeLocations": [
            "@executable_path/../Frameworks/Python.framework/Versions/3.11/Python"
        ],
    },
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
    name="Magic Schedule Builder",
)
