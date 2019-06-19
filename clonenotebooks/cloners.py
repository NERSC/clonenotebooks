from datetime import datetime
import json
import os.path
import socket
from io import StringIO
import re
from urllib.parse import urlparse
from urllib import robotparser

from notebook.utils import url_path_join
from notebook.base.handlers import IPythonHandler
from notebook.services.contents.manager import copy_pat
import nbformat
from tornado import web
from tornado.escape import url_unescape, url_escape
from tornado import gen
from tornado import httpclient

from contextlib import contextmanager
from nbviewer.utils import response_text
from nbviewer.utils import base64_decode
from nbviewer.providers.github.client import AsyncGitHubClient

def load_jupyter_server_extension(nb_server_app):
    """
    Called when the extension is loaded.

    Args:
        nb_server_app (NotebookWebApplication): handle to the Notebook webserver instance.
    """
    web_app = nb_server_app.web_app
    contents_manager = nb_server_app.contents_manager

    # This class is defined in line so it can close over contents_manager.
    class URLCloneHandler(IPythonHandler):
        client = httpclient.AsyncHTTPClient()

        @gen.coroutine
        def get(self):
            # This is similar to notebook.contents.manager.ContentsManager.copy
            # but it (1) assumes the clone_from is on the filesystem not some
            # non-file-based ContentManager implementation and (2) is able to
            # clone files from outside of ("above") the notebook server's root
            # directory.
            clone_from = url_unescape(self.get_query_argument('clone_from'))
            try:
                protocol = self.get_query_argument('protocol')
            # Assume HTTPS and not HTTP by default:
            except web.MissingArgumentError:
                protocol = 'https'
            clone_to = "/" # root directory of notebook server
            self.log.info("Cloning notebook from URL: %s", clone_from)

            clone_from = re.match(r'(?P<netloc>[^/]+)/(?P<url>.*)', clone_from)
            netloc, url = clone_from.group('netloc', 'url')

            url = url_escape(url, plus=False)

            remote_url = u"{}://{}/{}".format(protocol, netloc, url)

            if not url.endswith('.ipynb'):
                # this is how we handle relative links (files/ URLs) in notebooks
                # if it's not a .ipynb URL and it is a link from a notebook,
                # redirect to the original URL rather than trying to render it as a notebook
                self.log.info("No ipynb file found at address %s at %s", url, netloc)
                refer_url = self.request.headers.get('Referer', '').split('://')[-1]
                if refer_url.startswith(self.request.host + '/url'):
                    self.redirect(remote_url)
                    return

            parse_result = urlparse(remote_url)

            response = yield self.client.fetch(remote_url)
            self.log.info("\nrespose is: %s\n", response)

            try:
                nbjson = response_text(response, encoding='utf-8')
            except UnicodeDecodeError:
                self.log.error("Notebook is not utf8: %s", remote_url, exc_info=True)
                raise web.HTTPError(400)
            
            # Convert possibly old notebooks, like the Gaussian process tutorial in the nbviewer gallery, to the latest nbformat so that they get loaded
            nbnode = nbformat.reads(nbjson, as_version=4)
            nbjson = nbformat.writes(nbnode)
            nbjson = json.loads(nbjson)

            # Need to unescape the URL so we get the right file name when redirecting, e.g. for the Julia notebook in the nbviewer gallery 
            url = url_unescape(url)

            now = datetime.now()
            model = {
                'content': nbjson,
                'created': now,
                'format': 'json',
                'last_modified': now,
                'mimetype': None,
                'type': 'notebook',
                'writable': True}
            name = copy_pat.sub(u'.', os.path.basename(url))
            to_name = contents_manager.increment_filename(name, clone_to, insert='-Copy')
            full_clone_to = u'{0}/{1}'.format(clone_to, to_name)
            contents_manager.save(model, full_clone_to)
            # Redirect to the cloned notebook
            # in JupyterLab's single-document mode.
            self.redirect(url_path_join('lab', 'tree', full_clone_to))

    class GitHubCloneHandler(IPythonHandler):
        client = httpclient.AsyncHTTPClient()

        @property 
        def github_client(self):
            """Create an upgraded GitHub API client from the HTTP client"""
            if getattr(self, "_github_client", None) is None:
                self._github_client = AsyncGitHubClient(self.client)
            return self._github_client
        # def catch_client_error(self):
        #     """context manager for catching httpclient errors
        #     they are transformed into appropriate web.HTTPErrors
        #     """
        #     try:
        #         yield
        #     except httpclient.HTTPError as e:
        #         self.reraise_client_error(e)
        #     except socket.error as e:
        #         raise web.HTTPError(404, str(e))
        # 
        # @gen.coroutine
        # def get(self):
        #     # This is similar to notebook.contents.manager.ContentsManager.copy
        #     # but it (1) assumes the clone_from is on the filesystem not some
        #     # non-file-based ContentManager implementation and (2) is able to
        #     # clone files from outside of ("above") the notebook server's root
        #     # directory.
        #     clone_from = url_unescape(self.get_query_argument('clone_from'))
        #     clone_to = "/"  # root directory of notebook server
        #     self.log.info("Cloning notebook on GitHub found at %s to %s", clone_from, clone_to)

        #     clone_from = clone_from.split('/', 2)
        #     user = clone_from[0]
        #     repo = clone_from[1]
        #     path_ref = clone_from[2]
        #     path_ref = path_ref.rsplit('/', 1)
        #     path = path_ref[0]
        #     ref =  path_ref[1]
 
        #     with self.catch_client_error():
        #         tree_entry = yield self.github_client.get_tree_entry(
        #             user, repo, path=url_unescape(path), ref=ref
        #             )
        #     
        #     # fetch file data from the blobs API
        #     with self.catch_client_error():
        #         response = yield self.github_client.fetch(tree_entry['url'])

        #         data = json.loads(response_text(response))
        #         contents = data['content']
        #         if data['encoding'] == 'base64':
        #             # filedata will be bytes
        #             filedata = base64_decode(contents)
        #         else:
        #             # filedata will be unicode
        #             filedata = contents

        #     try:
        #         # filedata may be bytes, but we need text
        #         if isinstance(filedata, bytes):
        #             nbjson = filedata.decode('utf-8')
        #         else:
        #             nbjson = filedata
        #     except Exception as e:
        #         app_log.error("Failed to decode notebook: %s", path, exc_info=True)
        #         raise web.HTTPError(400)

        #     nbjson = json.load(StringIO(nbjson))
        #     now = datetime.now()
        #     model = {
        #         'content': nbjson,
        #         'created': now,
        #         'format': 'json',
        #         'last_modified': now,
        #         'mimetype': None,
        #         'type': 'notebook',
        #         'writable': True}
        #     name = copy_pat.sub(u'.', os.path.basename(path))
        #     to_name = contents_manager.increment_filename(name, clone_to, insert='-Copy')
        #     full_clone_to = u'{0}/{1}'.format(clone_to, to_name)
        #     contents_manager.save(model, full_clone_to)
        #     # Redirect to the cloned notebook
        #     # in JupyterLab's single-document mode.
        #     self.redirect(url_path_join('lab', 'tree', full_clone_to))

        @gen.coroutine
        def get(self):
            clone_from = self.get_query_argument('clone_from')
            self.redirect('/user-redirect/url_clone?clone_from={}&protocol={}'.format(clone_from, 'https'))

    class LocalCloneHandler(IPythonHandler):
        def get(self):
            # This is similar to notebook.contents.manager.ContentsManager.copy
            # but it (1) assumes the clone_from is on the filesystem not some
            # non-file-based ContentManager implementation and (2) is able to
            # clone files from outside of ("above") the notebook server's root
            # directory.
            clone_from = self.get_query_argument('clone_from')
            clone_to = "/"  # root directory of notebook server
            self.log.info("Cloning %s to %s", clone_from, clone_to)
            if not os.path.isfile(clone_from):
                raise web.HTTPError(400, "No such file: %s" % clone_from)
            with open(clone_from, 'r') as f:
                nbjson = json.load(f)

            # Turn JSON object into a string
            nbjson = json.dumps(nbjson)

            # Convert possibly old notebooks, like the Gaussian process tutorial in the nbviewer gallery, to the latest nbformat so that they get loaded
            nbnode = nbformat.reads(nbjson, as_version=4)
            nbjson = nbformat.writes(nbnode)
            nbjson = json.loads(nbjson)

            now = datetime.now()
            model = {
                'content': nbjson,
                'created': now,
                'format': 'json',
                'last_modified': now,
                'mimetype': None,
                'type': 'notebook',
                'writable': True}
            name = copy_pat.sub(u'.', os.path.basename(clone_from))
            to_name = contents_manager.increment_filename(name, clone_to, insert='-Copy')
            full_clone_to = u'{0}/{1}'.format(clone_to, to_name)
            contents_manager.save(model, full_clone_to)
            # Redirect to the cloned notebook
            # in JupyterLab's single-document mode.
            self.redirect(url_path_join('lab', 'tree', full_clone_to))

    class GistCloneHandler(IPythonHandler):
        @gen.coroutine
        def get(self):
            clone_from = self.get_query_argument('clone_from')
            self.redirect('/user-redirect/url_clone?clone_from={}&protocol={}'.format(clone_from, 'https'))

    host_pattern = '.*$'
    base_url = web_app.settings['base_url']
    url_route_pattern    = url_path_join(base_url, '/url_clone')
    github_route_pattern = url_path_join(base_url, '/github_clone')
    local_route_pattern  = url_path_join(base_url, '/local_clone')
    gist_route_pattern   = url_path_join(base_url, '/gist_clone')

    web_app.add_handlers(host_pattern, [(url_route_pattern, URLCloneHandler),
                                        (github_route_pattern, GitHubCloneHandler),
                                        (local_route_pattern, LocalCloneHandler),
                                        (gist_route_pattern, GistCloneHandler)])
