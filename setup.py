from setuptools import setup
import sys

PY_SHORT_VERSION = f"{sys.version_info[0]}.{sys.version_info[1]}"

APP = ["main.py"]
DATA_FILES = ["icon.icns"]

OPTIONS = {
    "iconfile": "icon.icns",
    "no_strip": True,
    # ensure Tk loads correctly inside the bundled application
    # by explicitly including Tkinter and Tcl/Tk frameworks
    "includes": ["tkinter"],
    "force_system_tk": False,

    "plist": {
        "CFBundleName": "Magic Schedule Builder",
        "CFBundleIdentifier": "com.owen.magic-schedule-builder",
        "CFBundleShortVersionString": "1.0",

        # Path used by the py2app stub to locate the embedded Python runtime
        "PyRuntimeLocations": [
            f"@executable_path/../Frameworks/Python.framework/Versions/{PY_SHORT_VERSION}/Python"
        ],
        "PythonInfoDict": {
            "PythonExecutable": f"@executable_path/../Frameworks/Python.framework/Versions/{PY_SHORT_VERSION}/Python",
            "PythonShortVersion": PY_SHORT_VERSION,
        },
    },
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
    name="Magic Schedule Builder",
)
