import re

from nbviewer.providers.base import cached
from nbviewer.providers.url.handlers import URLHandler
from nbviewer.providers.github.handlers import GitHubBlobHandler
from nbviewer.providers.github.handlers import GitHubTreeHandler
from nbviewer.providers.local.handlers import LocalFileHandler
from nbviewer.providers.gist.handlers import GistHandler
from nbviewer.providers.gist.handlers import UserGistsHandler

from tornado import gen



class URLRenderingHandler(URLHandler):
    """Renderer for /url or /urls"""

    def render_notebook_template(self, body, nb, download_url,
            json_notebook, **namespace):

        return super().render_notebook_template(body, nb, download_url, json_notebook,
                                                clone_notebooks=getattr(self, 'clone_notebooks', False),
                                                **namespace)

    @gen.coroutine
    def clone_to_user_server(self, url, protocol='https'):
        """Clone the file at the given absolute URL to the user's home directory.
        Parameters
        ==========
        url: str
            Absolute URL to the file
        """
        self.redirect('/user-redirect/url_clone?clone_from={}&protocol={}'.format(url, protocol))

    @cached
    @gen.coroutine
    def get(self, secure, netloc, url):

        remote_url, public = yield super().get_notebook_data(secure, netloc, url)

        if getattr(self, 'clone_notebooks', False):
            is_clone = self.get_query_arguments('clone')
            if is_clone:
                destination = netloc + '/' + url
                self.clone_to_user_server(url=destination, protocol='http'+secure)
                return

        yield super().deliver_notebook(remote_url, public)



class GitHubBlobRenderingHandler(GitHubBlobHandler):
    """handler for files on github
    If it's a...
    - notebook, render it
    - non-notebook file, serve file unmodified
    - directory, redirect to tree
    """
    def render_notebook_template(self, body, nb, download_url, json_notebook, 
                                       **namespace):

        return super().render_notebook_template(body, nb, download_url, json_notebook,
                                                clone_notebooks=getattr(self, 'clone_notebooks', False),
                                                **namespace)

    @gen.coroutine
    def clone_to_user_server(self, raw_url):
        """Clone a notebook on GitHub to the user's home directory.
        Parameters
        ==========
        user, repo, path, ref: str
          Used to create the URI nbviewer uses to specify the notebook on GitHub.
        """
        self.redirect('/user-redirect/github_clone?clone_from=%s' % raw_url)

    @cached
    @gen.coroutine
    def get(self, user, repo, ref, path):
        raw_url, blob_url, tree_entry = yield super().get_notebook_data(user, repo, ref, path)

        if path.endswith('.ipynb') and getattr(self, 'clone_notebooks', False):
            is_clone = self.get_query_arguments('clone')
            if is_clone:
                truncated_url = re.match(r'^https?://(?P<truncated_url>.*)', raw_url).group('truncated_url')
                self.clone_to_user_server(truncated_url)
                return

        yield super().deliver_notebook(user, repo, ref, path, raw_url, blob_url, tree_entry)

class GitHubTreeRenderingHandler(GitHubTreeHandler):
    def render_treelist_template(self, entries, breadcrumbs, provider_url, user, repo, ref, path,
                                 branches, tags, executor_url, **namespace):
        return super().render_treelist_template(entries, breadcrumbs, provider_url, user, repo, ref,
                       path, branches, tags, executor_url, clone_notebooks=getattr(self, 'clone_notebooks', False), **namespace)

class LocalRenderingHandler(LocalFileHandler):
    def render_notebook_template(self, body, nb, download_url,
            json_notebook, **namespace):

        return super().render_notebook_template(body, nb, download_url, json_notebook,
                                                clone_notebooks=getattr(self, 'clone_notebooks', False),
                                                **namespace)

    def render_dirview_template(self, entries, breadcrumbs, title, **namespace):

        return super().render_dirview_template(entries, breadcrumbs, title,
                                               clone_notebooks=getattr(self, 'clone_notebooks', False),
                                               **namespace)

    @gen.coroutine
    def clone_to_user_server(self, fullpath):
        """Clone the file at the given absolute path to the user's home directory.
        Parameters
        ==========
        fullpath: str
            Absolute path to the file
        """
        self.redirect('/user-redirect/local_clone?clone_from=%s' % fullpath)

    @cached
    @gen.coroutine
    def get(self, path):
        fullpath = super().get_notebook_data(path)

        if getattr(self, 'clone_notebooks', False):
            is_clone = self.get_query_arguments('clone')
            if is_clone:
                self.clone_to_user_server(fullpath)
                return

        yield super().deliver_notebook(fullpath, path)



class GistRenderingHandler(GistHandler):
    def render_notebook_template(self, body, nb, download_url, json_notebook, **namespace):

        return super().render_notebook_template(body, nb, download_url, json_notebook,
                                                clone_notebooks=getattr(self, 'clone_notebooks', False),
                                                **namespace)

    @gen.coroutine
    def clone_to_user_server(self, url):
        self.redirect('/user-redirect/gist_clone?clone_from=%s' % url)

    @gen.coroutine
    def file_get(self, user, gist_id, filename, gist, many_files_gist, file):
        content = yield super().get_notebook_data(gist_id, filename, many_files_gist, file)

        if not content:
            return

        if getattr(self, 'clone_notebooks', False):
            is_clone = self.get_query_arguments('clone')
            if is_clone:
                raw_url = file['raw_url']
                truncated_url = re.match(r'^https?://(?P<truncated_url>.*)', raw_url).group('truncated_url')
                self.clone_to_user_server(truncated_url)
                return

        yield super().deliver_notebook(user, gist_id, filename, gist, file, content)

class UserGistsRenderingHandler(UserGistsHandler):
    def render_usergists_template(self, entries, user, provider_url, prev_url, next_url, **namespace):

        return super().render_usergists_template(entries, user, provider_url, prev_url, next_url, 
                                                 clone_notebooks=getattr(self, 'clone_notebooks', False),
                                                 **namespace)
