from setuptools import setup

APP = ["main.py"]

OPTIONS = {
    "iconfile": "icon.icns",
    "no_strip": True,
    "packages": ["tkinter"],          # include _tkinter.so if you need it
    "force_system_tk": False,         # don’t fall back to the old 8.5 stuff
    "frameworks": [
        "/Library/Frameworks/Tcl.framework",
        "/Library/Frameworks/Tk.framework",
    ],
    "plist": {
        # tell the stub exactly where the embedded python lives
        "PyRuntimeLocations": [
            "@executable_path/../Frameworks/Python.framework/Versions/3.11/Python"
        ],
        "CFBundleName": "Magic Schedule Builder",
        "CFBundleIdentifier": "com.owen.magic-schedule-builder",
        "CFBundleShortVersionString": "1.0",
    },
}

setup(
    app=APP,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
    name="Magic Schedule Builder",
)
