from setuptools import Extension, setup

cmodule = Extension(
    "mymod.base",
    sources=["mymod/base.c"],
)
setup(
    name="mymod",
    ext_modules=[cmodule],
    packages=["mymod"],
)
