"""Build the Cython TRF match kernel."""
from setuptools import setup
from Cython.Build import cythonize

setup(
    ext_modules=cythonize(
        "trf_match_cython.pyx",
        compiler_directives={"language_level": "3"},
    )
)
