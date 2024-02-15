from distutils.core import setup, Extension
setup(name="pymesh", version="1.0",
      ext_modules=[Extension("pymesh", ["pymesh.c"], include_dirs =
          ['/home/oscarpilote/Ortho4XP/src/C/'])])
