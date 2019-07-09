This extension can clone notebooks served from:

* URL
[![url_clone](docs/images/url_clone_thumbnail.png)](https://gfycat.com/warmcreepyanemoneshrimp)
* GitHub tree view
[![github_tree_clone](docs/images/github_tree_clone_thumbnail.png)](https://gfycat.com/accomplishedwebbedharlequinbug)
* GitHub individual file view
[![github_blob_clone](docs/images/github_blob_clone_thumbnail.png)](https://gfycat.com/periodiccheeryarrowcrab)
* individual GitHub Gists
[![gist_clone](docs/images/gist_clone_thumbnail.png)](https://gfycat.com/hugesafehornedviper)
* Gist's from a user's page
[![user_gists_clone](docs/images/user_gists_clone_thumbnail.png)](https://gfycat.com/yearlycleanafricanjacana)
* local files from a directory
[![local_dirview_clone](docs/images/local_dirview_clone_thumbnail.png)](https://gfycat.com/ficklescentedasianpiedstarling)
* individual local files
[![local_clone](docs/images/local_clone_thumbnail.png)](https://gfycat.com/fakedeephawaiianmonkseal)

Built starting from
[Daniel Allan's notebook clone extension](https://github.com/danielballan/notebook-clone-extension). Currently
requires [my fork of NBViewer](https://github.com/krinsman/nbviewer)
to run.

## Installation Instructions

The easiest and quickest way to get a version of this up and running
to test out would be to use the Docker image and setup instructions
found
[here](https://github.com/krinsman/jupyterhub-deploy/tree/master/nbviewer/cloneviewer).

Otherwise install [my fork of NBViewer](https://github.com/krinsman/nbviewer) using the same installation
instructions as for the master version, in particular the setup
instructions for using NBViewer as a JupyterHub service. Then download this repository,
and in the folder run (the dot is important, it means "present working
directory"):

    pip install .

if you don't want to make changes to the source code, otherwise

    pip install -e .

This installs the corresponding Python package, but we still need to
tell Jupyter to use the appropriate sub-module as a notebook server
extension. To do this, run:

    jupyter serverextension enable clonenotebooks.cloners --sys-prefix

Make sure you have `nbviewer` installed as a Python package, via Pip
or Conda or whatever else, on order for this to work.

Then copy the `templates` folder to your preferred location, and add
to the command for NBViewer in your `jupyterhub_config.py` file

    --template-path=/your/preferred/location

Then make sure to include an `nbviewer_config.py` file (this is a major why
for now using
[my fork of NBViewer](https://github.com/krinsman/nbviewer) is
necessary) with the lines:

    c.NBViewer.handler_settings    = {'clone_notebooks' : True}
    
    c.NBViewer.local_handler       = "clonenotebooks.renderers.LocalRenderingHandler"
    c.NBViewer.url_handler         = "clonenotebooks.renderers.URLRenderingHandler"
    c.NBViewer.github_blob_handler = "clonenotebooks.renderers.GitHubBlobRenderingHandler"
    c.NBViewer.github_tree_handler = "clonenotebooks.renderers.GitHubTreeRenderingHandler"
    c.NBViewer.gist_handler        = "clonenotebooks.renderers.GistRenderingHandler"
    c.NBViewer.user_gists_handler  = "clonenotebooks.renderers.UserGistsRenderingHandler"

A copy of this file is also included in this repository. Ideally this
should have everything configured, but these setup instructions are more
vague than they could be. I recommend comparing with the Dockerfiles in my
[example setup](https://github.com/krinsman/jupyterhub-deploy/tree/master/nbviewer/cloneviewer)
if any difficulties arise, and giving me feedback about any ways in
which the documentation could be improved, since it will be much
appreciated. [Here is a link to the issues page](https://github.com/krinsman/clonenotebooks/issues)
for requests for improved documentation and/or general feedback.
