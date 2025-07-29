from setuptools import setup
import sys

APP = ["main.py"]
DATA_FILES = ["icon.icns"]

OPTIONS = {
    "iconfile": "icon.icns",
    "no_strip": True,
    # include Tk and Tcl so the GUI can run inside the bundled application
    # removing the exclude list allows py2app to detect and bundle the
    # required frameworks automatically
    "force_system_tk": False,

    "plist": {
        "CFBundleName": "Magic Schedule Builder",
        "CFBundleIdentifier": "com.owen.magic-schedule-builder",
        "CFBundleShortVersionString": "1.0",

        # Path used by the py2app stub to locate the embedded Python runtime
        "PyRuntimeLocations": [
            "@executable_path/../Frameworks/Python.framework/Versions/%s/Python"
            % (f"{sys.version_info[0]}.{sys.version_info[1]}")
        ],
        "PythonInfoDict": {
            "PythonExecutable": "@executable_path/../Frameworks/Python.framework/Versions/%s/Python"
            % (f"{sys.version_info[0]}.{sys.version_info[1]}") ,
            "PythonShortVersion": f"{sys.version_info[0]}.{sys.version_info[1]}",
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
