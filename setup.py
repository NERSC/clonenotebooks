import pathlib
from setuptools import setup

# The directory containing this file
HERE = pathlib.Path(__file__).parent

# The text of the README file
README = (HERE / "README.md").read_text()

setup(
    name="clonenotebooks",
    version="1.0.3",
    description="NBViewer extension and Jupyter notebook extension for cloning notebooks viewed in NBViewer to user's home directory.",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/krinsman/clonenotebooks",
    author="William Krinsman",
    author_email="krinsman@berkeley.edu",
    license="BSD",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: BSD License",
    ],
    packages=["clonenotebooks", "clonenotebooks.cloners", "clonenotebooks.renderers"],
    install_requires=[
        "nbviewer",
        "notebook",
        "jupyterhub",
        "nbformat",
        "tornado",
        "jupyter_client",
    ],
    include_package_data=True,
    data_files=[
        ("etc/jupyter/jupyter_notebook_config.d", [
            "clonenotebooks/cloners/jupyter-config/jupyter_notebook_config.d/cloners.json"
        ])
    ],
)
