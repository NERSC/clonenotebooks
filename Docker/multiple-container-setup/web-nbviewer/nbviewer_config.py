# 'clone_to_directory' is a string, possibly including {username} as a stand-in, which will automatically be replaced by
# the JupyterHub user's user name, analogous to the c.Spawner.notebook_dir and c.Spawner.default_url config settings in JupyterHub.
# Note: all directories are relative to the notebook server's root directory, usually equal to c.Spawner.notebook_dir
c.NBViewer.handler_settings = {
    "clone_notebooks": True,
    "clone_to_directory": "/home/{username}",
}

c.NBViewer.local_handler = "clonenotebooks.renderers.LocalRenderingHandler"
c.NBViewer.url_handler = "clonenotebooks.renderers.URLRenderingHandler"
c.NBViewer.github_blob_handler = "clonenotebooks.renderers.GitHubBlobRenderingHandler"
c.NBViewer.github_tree_handler = "clonenotebooks.renderers.GitHubTreeRenderingHandler"
c.NBViewer.gist_handler = "clonenotebooks.renderers.GistRenderingHandler"
c.NBViewer.user_gists_handler = "clonenotebooks.renderers.UserGistsRenderingHandler"

c.NBViewer.localfiles = "/home/william"
c.NBViewer.template_path = "/repos/clonenotebooks/templates"

# c.NBViewer.frontpage = "/repos/clonenotebooks/templates/frontpage.json"

c.NBViewer.static_path = "/repos/clonenotebooks/static"
c.NBViewer.index_handler = "clonenotebooks.renderers.IndexRenderingHandler"
