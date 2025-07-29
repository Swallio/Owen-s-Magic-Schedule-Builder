from setuptools import setup

APP = ['Magic Schedule Builder.py']
DATA_FILES = ['icon.icns']
OPTIONS = {
    'argv_emulation': True,
    'iconfile': 'icon.icns',
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
