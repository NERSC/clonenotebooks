import re

from jupyterhub.services.auth import HubAuthenticated

from nbviewer.providers.base import cached
from nbviewer.providers.url.handlers import URLHandler
from nbviewer.providers.github.handlers import GitHubBlobHandler
from nbviewer.providers.github.handlers import GitHubTreeHandler
from nbviewer.providers.local.handlers import LocalFileHandler
from nbviewer.providers.gist.handlers import GistHandler
from nbviewer.providers.gist.handlers import UserGistsHandler

try: # Python 3.8
    from functools import cached_property
except ImportError:
    try: # When my nbviewer fork gets merged into master
        from nbviewer.utils import cached_property
    except ImportError:
        from functools import lru_cache
        def cached_property(method):
            return property(lru_cache(1)(method))

class CloneRendererMixin(HubAuthenticated):
    @cached_property
    def user_name(self):
        current_user = self.get_current_user()
        return current_user["name"]

    def clone_to_user_server(self, url, provider_type, protocol=''):
        self.redirect('/user-redirect/{}_clone?clone_from={}&protocol={}'.format(provider_type, url, protocol))

class URLRenderingHandler(CloneRendererMixin, URLHandler):
    """Renderer for /url or /urls"""

    def render_notebook_template(self, body, nb, download_url,
            json_notebook, **namespace):

        return super().render_notebook_template(body, nb, download_url, json_notebook,
                                                clone_notebooks=getattr(self, 'clone_notebooks', False),
                                                **namespace)

    @cached
    async def get(self, secure, netloc, url):

        remote_url, public = await super().get_notebook_data(secure, netloc, url)

        if getattr(self, 'clone_notebooks', False):
            is_clone = self.get_query_arguments('clone')
            if is_clone:
                destination = netloc + '/' + url
                self.clone_to_user_server(url=destination, protocol='http'+secure, provider_type='url')
                return

        await super().deliver_notebook(remote_url, public)



class GitHubBlobRenderingHandler(CloneRendererMixin, GitHubBlobHandler):
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

    @cached
    async def get(self, user, repo, ref, path):
        raw_url, blob_url, tree_entry = await super().get_notebook_data(user, repo, ref, path)

        if path.endswith('.ipynb') and getattr(self, 'clone_notebooks', False):
            is_clone = self.get_query_arguments('clone')
            if is_clone:
                truncated_url = re.match(r'^https?://(?P<truncated_url>.*)', raw_url).group('truncated_url')
                self.clone_to_user_server(url=truncated_url, provider_type='github')
                return

        await super().deliver_notebook(user, repo, ref, path, raw_url, blob_url, tree_entry)

class GitHubTreeRenderingHandler(GitHubTreeHandler):
    def render_treelist_template(self, entries, breadcrumbs, provider_url, user, repo, ref, path,
                                 branches, tags, executor_url, **namespace):
        return super().render_treelist_template(entries, breadcrumbs, provider_url, user, repo, ref,
                       path, branches, tags, executor_url, clone_notebooks=getattr(self, 'clone_notebooks', False), **namespace)

class LocalRenderingHandler(CloneRendererMixin, LocalFileHandler):
    def render_notebook_template(self, body, nb, download_url,
            json_notebook, **namespace):

        return super().render_notebook_template(body, nb, download_url, json_notebook,
                                                clone_notebooks=getattr(self, 'clone_notebooks', False),
                                                base_url=self.base_url, hub_base_url=self.hub_base_url,
                                                **namespace)

    def render_dirview_template(self, entries, breadcrumbs, title, **namespace):

        return super().render_dirview_template(entries, breadcrumbs, title,
                                               clone_notebooks=getattr(self, 'clone_notebooks', False),
                                               **namespace)

    @cached
    async def get(self, path):
        fullpath = await super().get_notebook_data(path)

        if getattr(self, 'clone_notebooks', False):
            is_clone = self.get_query_arguments('clone')
            if is_clone:
                self.clone_to_user_server(url=fullpath, provider_type='local')
                return

        # get_notebook_data returns None if a directory is to be shown or a notebook is to be downloaded,
        # i.e. if no notebook is supposed to be rendered, making deliver_notebook inappropriate
        if fullpath:
            await super().deliver_notebook(fullpath, path)


class GistRenderingHandler(CloneRendererMixin, GistHandler):
    def render_notebook_template(self, body, nb, download_url, json_notebook, **namespace):

        return super().render_notebook_template(body, nb, download_url, json_notebook,
                                                clone_notebooks=getattr(self, 'clone_notebooks', False),
                                                **namespace)

    async def file_get(self, user, gist_id, filename, gist, many_files_gist, file):
        content = await super().get_notebook_data(gist_id, filename, many_files_gist, file)

        if not content:
            return

        if getattr(self, 'clone_notebooks', False):
            is_clone = self.get_query_arguments('clone')
            if is_clone:
                raw_url = file['raw_url']
                truncated_url = re.match(r'^https?://(?P<truncated_url>.*)', raw_url).group('truncated_url')
                self.clone_to_user_server(url=truncated_url, provider_type='gist')
                return

        await super().deliver_notebook(user, gist_id, filename, gist, file, content)

class UserGistsRenderingHandler(UserGistsHandler):
    def render_usergists_template(self, entries, user, provider_url, prev_url, next_url, **namespace):

        return super().render_usergists_template(entries, user, provider_url, prev_url, next_url, 
                                                 clone_notebooks=getattr(self, 'clone_notebooks', False),
                                                 **namespace)
