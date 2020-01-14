c.NBViewer.handler_settings = {"clone_notebooks": True}

c.NBViewer.local_handler = "clonenotebooks.renderers.LocalRenderingHandler"
c.NBViewer.url_handler = "clonenotebooks.renderers.URLRenderingHandler"
c.NBViewer.github_blob_handler = "clonenotebooks.renderers.GitHubBlobRenderingHandler"
c.NBViewer.github_tree_handler = "clonenotebooks.renderers.GitHubTreeRenderingHandler"
c.NBViewer.gist_handler = "clonenotebooks.renderers.GistRenderingHandler"
c.NBViewer.user_gists_handler = "clonenotebooks.renderers.UserGistsRenderingHandler"

c.NBViewer.static_path = "/repos/clonenotebooks/static"

c.NBViewer.github_user_handler = "clonenotebooks.renderers.GitHubUserRenderingHandler"
c.NBViewer.index_handler = "clonenotebooks.renderers.IndexRenderingHandler"

c.NBViewer.localfiles = "/repos/nbviewer/notebook-5.7.8/tools/tests"
c.NBViewer.template_path = "/repos/clonenotebooks/templates"
c.NBViewer.frontpage = "/repos/clonenotebooks/templates/frontpage.json"
