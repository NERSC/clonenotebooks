# Experimental Notebook-sharing extension

Install and enable the extension.

```
pip install -e .
jupyter serverextension enable notebook_clone_extension
```

Now `GET /user/USERNAME/clone?copy_from=/path/to/notebook` will copy the
notebook into `USERNAME`'s notebook server's root directory and redirect the user
to JupyterLab's "single-document mode" view of the new copy of the notebook.

If used in a Hub, `GET /hub/user-redirect/clone?copy_from=/path/to/notebook`
will do the same for the currently-logged-in user.

## Links use in development

* https://jupyterhub.readthedocs.io/en/stable/reference/urls.html?highlight=user-redirect#user-redirect
* https://jupyter-notebook.readthedocs.io/en/stable/extending/handlers.html
* https://jupyter-notebook.readthedocs.io/en/stable/extending/contents.html
* https://jupyterlab.readthedocs.io/en/stable/user/urls.html
