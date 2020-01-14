import os
import re

from jupyterhub.services.auth import HubAuthenticated

from nbviewer.handlers import IndexHandler
from nbviewer.providers.base import cached
from nbviewer.providers.url.handlers import URLHandler
from nbviewer.providers.github.handlers import (
    GitHubBlobHandler,
    GitHubTreeHandler,
    GitHubUserHandler,
)
from nbviewer.providers.local.handlers import LocalFileHandler
from nbviewer.providers.gist.handlers import GistHandler, UserGistsHandler

from nbviewer.utils import url_path_join

from ..utils import cached_property


class CloneRendererMixin(HubAuthenticated):
    @cached_property
    def username(self):
        current_user = self.get_current_user()
        return current_user["name"]

    @cached_property
    def clone_to(self):
        # A string determined by user's config settings, possibly including {username} as a standin
        # Analogous to c.Spawner.notebook_dir and c.Spawner.default_url config in JupyterHub
        clone_to_directory = getattr(self, "clone_to_directory", "")
        clone_to = clone_to_directory.format(username=self.username)
        self.log.info("clone_to: %s", clone_to)
        return clone_to

    def clone_to_user_server(
        self,
        url,
        provider_type,
        protocol="https",
        kernel_name=None,
        kernelspec_source=None,
    ):
        redirect_endpoint = "/user-redirect/{}_clone?clone_from={}&clone_to={}&protocol={}".format(
            provider_type, url, self.clone_to, protocol
        )
        if kernel_name:
            redirect_endpoint += "&kernel_name={}".format(kernel_name)
        if kernelspec_source:
            redirect_endpoint += "&kernelspec_source={}".format(kernelspec_source)
        self.redirect(redirect_endpoint)

    # Here `self` will come from BaseHandler in nbviewer.providers.base (from which the other NBViewer handlers inherit)
    # Contains values to be unpacked into Jinja2 namespace for renderers to render the custom templates in this package
    @cached_property
    def CLONENOTEBOOKS_NAMESPACE(self):
        return {
            "clone_notebooks": getattr(self, "clone_notebooks", False),
            "hub_base_url": self.hub_base_url,
            "url_path_join": url_path_join,
            "username": self.username,
        }


class IndexRenderingHandler(CloneRendererMixin, IndexHandler):
    """Renders front page a.k.a. index"""

    def render_index_template(self, **namespace):
        return super().render_index_template(**self.CLONENOTEBOOKS_NAMESPACE)


class URLRenderingHandler(CloneRendererMixin, URLHandler):
    """Renderer for /url or /urls"""

    def render_notebook_template(
        self, body, nb, download_url, json_notebook, **namespace
    ):

        return super().render_notebook_template(
            body,
            nb,
            download_url,
            json_notebook,
            **self.CLONENOTEBOOKS_NAMESPACE,
            **namespace
        )

    @cached
    async def get(self, secure, netloc, url):

        remote_url, public = await super().get_notebook_data(secure, netloc, url)

        if getattr(self, "clone_notebooks", False):
            is_clone = self.get_query_arguments("clone")
            if is_clone:
                destination = netloc + "/" + url
                self.clone_to_user_server(
                    url=destination, protocol="http" + secure, provider_type="url"
                )
                return

        await super().deliver_notebook(remote_url, public)


class GitHubBlobRenderingHandler(CloneRendererMixin, GitHubBlobHandler):
    """handler for files on github
    If it's a...
    - notebook, render it
    - non-notebook file, serve file unmodified
    - directory, redirect to tree
    """

    def render_notebook_template(
        self, body, nb, download_url, json_notebook, **namespace
    ):

        return super().render_notebook_template(
            body,
            nb,
            download_url,
            json_notebook,
            **self.CLONENOTEBOOKS_NAMESPACE,
            **namespace
        )

    @cached
    async def get(self, user, repo, ref, path):
        raw_url, blob_url, tree_entry = await super().get_notebook_data(
            user, repo, ref, path
        )

        if path.endswith(".ipynb") and getattr(self, "clone_notebooks", False):
            is_clone = self.get_query_arguments("clone")
            if is_clone:
                truncated_url = re.match(
                    r"^https?://(?P<truncated_url>.*)", raw_url
                ).group("truncated_url")

                if (
                    os.environ.get("GITHUB_API_URL", "") == ""
                ):  # Default is no GitHub Enterprise
                    repo_root_url = re.match(
                        r"^https?://(?P<repo_root_url>[^\/]+/[^\/]+/[^\/]+/[^\/]+)/.*",
                        raw_url,
                    ).group("repo_root_url")
                else:  # GitHub Enterprise raw urls formatted differently
                    repo_root_url = re.match(
                        r"^https?://(?P<repo_root_url>[^\/]+/[^\/]+/[^\/]+/raw/[^\/]+)/.*",
                        raw_url,
                    ).group("repo_root_url")

                kernel_name = "{}-{}".format(repo, ref)
                self.clone_to_user_server(
                    url=truncated_url,
                    provider_type="url",
                    protocol="https",
                    kernel_name=kernel_name,
                    kernelspec_source=repo_root_url,
                )
                return

        await super().deliver_notebook(
            user, repo, ref, path, raw_url, blob_url, tree_entry
        )


class GitHubTreeRenderingHandler(CloneRendererMixin, GitHubTreeHandler):
    def render_treelist_template(
        self,
        entries,
        breadcrumbs,
        provider_url,
        user,
        repo,
        ref,
        path,
        branches,
        tags,
        executor_url,
        **namespace
    ):
        return super().render_treelist_template(
            entries,
            breadcrumbs,
            provider_url,
            user,
            repo,
            ref,
            path,
            branches,
            tags,
            executor_url,
            **self.CLONENOTEBOOKS_NAMESPACE,
            **namespace
        )


class GitHubUserRenderingHandler(CloneRendererMixin, GitHubUserHandler):
    def render_github_user_template(
        self, entries, provider_url, next_url, prev_url, **namespace
    ):
        return super().render_github_user_template(
            entries,
            provider_url,
            next_url,
            prev_url,
            **self.CLONENOTEBOOKS_NAMESPACE,
            **namespace
        )


class LocalRenderingHandler(CloneRendererMixin, LocalFileHandler):
    def render_notebook_template(
        self, body, nb, download_url, json_notebook, **namespace
    ):

        return super().render_notebook_template(
            body,
            nb,
            download_url,
            json_notebook,
            base_url=self.base_url,
            **self.CLONENOTEBOOKS_NAMESPACE,
            **namespace
        )

    def render_dirview_template(self, entries, breadcrumbs, title, **namespace):

        return super().render_dirview_template(
            entries, breadcrumbs, title, **self.CLONENOTEBOOKS_NAMESPACE, **namespace
        )

    @cached
    async def get(self, path):
        fullpath = await super().get_notebook_data(path)

        if getattr(self, "clone_notebooks", False):
            is_clone = self.get_query_arguments("clone")
            if is_clone:
                self.clone_to_user_server(
                    url=fullpath, provider_type="local", protocol=""
                )
                return

        # get_notebook_data returns None if a directory is to be shown or a notebook is to be downloaded,
        # i.e. if no notebook is supposed to be rendered, making deliver_notebook inappropriate
        if fullpath:
            await super().deliver_notebook(fullpath, path)


class GistRenderingHandler(CloneRendererMixin, GistHandler):
    def render_notebook_template(
        self, body, nb, download_url, json_notebook, **namespace
    ):

        return super().render_notebook_template(
            body,
            nb,
            download_url,
            json_notebook,
            **self.CLONENOTEBOOKS_NAMESPACE,
            **namespace
        )

    async def file_get(self, user, gist_id, filename, gist, many_files_gist, file):
        content = await super().get_notebook_data(
            gist_id, filename, many_files_gist, file
        )

        if not content:
            return

        if getattr(self, "clone_notebooks", False):
            is_clone = self.get_query_arguments("clone")
            if is_clone:
                raw_url = file["raw_url"]
                truncated_url = re.match(
                    r"^https?://(?P<truncated_url>.*)", raw_url
                ).group("truncated_url")
                self.clone_to_user_server(
                    url=truncated_url, provider_type="url", protocol="https"
                )
                return

        await super().deliver_notebook(user, gist_id, filename, gist, file, content)


class UserGistsRenderingHandler(CloneRendererMixin, UserGistsHandler):
    def render_usergists_template(
        self, entries, user, provider_url, prev_url, next_url, **namespace
    ):

        return super().render_usergists_template(
            entries,
            user,
            provider_url,
            prev_url,
            next_url,
            **self.CLONENOTEBOOKS_NAMESPACE,
            **namespace
        )
