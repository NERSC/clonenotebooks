from datetime import datetime
import json
import os.path
from io import StringIO

from notebook.utils import url_path_join
from notebook.base.handlers import IPythonHandler
from notebook.services.contents.manager import copy_pat
from tornado import web
from tornado.escape import url_unescape
from tornado import gen
from tornado import httpclient

from contextlib import contextmanager
from nbviewer.providers.github.client import AsyncGitHubClient
from nbviewer.utils import response_text
from nbviewer.utils import base64_decode

def load_jupyter_server_extension(nb_server_app):
    """
    Called when the extension is loaded.

    Args:
        nb_server_app (NotebookWebApplication): handle to the Notebook webserver instance.
    """
    web_app = nb_server_app.web_app
    contents_manager = nb_server_app.contents_manager

    # This class is defined in line so it can close over contents_manager.

    class LocalCloneHandler(IPythonHandler):
        def get(self):
            # This is similar to notebook.contents.manager.ContentsManager.copy
            # but it (1) assumes the clone_from is on the filesystem not some
            # non-file-based ContentManager implementation and (2) is able to
            # clone files from outside of ("above") the notebook server's root
            # directory.
            clone_from = self.get_argument('clone_from')
            clone_to = "/"  # root directory of notebook server
            self.log.info("Cloning %s to %s", clone_from, clone_to)
            if not os.path.isfile(clone_from):
                raise web.HTTPError(400, "No such file: %s" % clone_from)
            with open(clone_from, 'r') as f:
                nbjson = json.load(f)
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

    class GitHubCloneHandler(IPythonHandler):
        client = httpclient.AsyncHTTPClient()

        @property 
        def github_client(self):
            """Create an upgraded GitHub API client from the HTTP client"""
            if getattr(self, "_github_client", None) is None:
                self._github_client = AsyncGitHubClient(self.client)
            return self._github_client

        @contextmanager
        def catch_client_error(self):
            """context manager for catching httpclient errors

            they are transformed into appropriate web.HTTPErrors
            """
            try:
                yield
            except httpclient.HTTPError as e:
                self.reraise_client_error(e)
            except socket.error as e:
                raise web.HTTPError(404, str(e))
        
        @gen.coroutine
        def get(self):
            # This is similar to notebook.contents.manager.ContentsManager.copy
            # but it (1) assumes the clone_from is on the filesystem not some
            # non-file-based ContentManager implementation and (2) is able to
            # clone files from outside of ("above") the notebook server's root
            # directory.
            clone_from = url_unescape(self.get_argument('clone_from'))
            clone_to = "/"  # root directory of notebook server
            self.log.info("Cloning notebook on GitHub found at %s to %s", clone_from, clone_to)

            clone_from = clone_from.split('/', 3)
            user = clone_from[0]
            self.log.info("\nValue of user is: %s\n" % user)
            repo = clone_from[1]
            self.log.info("\nValue of repo is: %s\n" % repo)
            path = clone_from[2]
            self.log.info("\nValue of path is: %s\n" % path)
            ref  = clone_from[3]
            self.log.info("\nValue of ref is: %s\n"  % ref)
            
            with self.catch_client_error():
                self.log.info("\nGot to with self.catch_client error -- does it fail here?\n")
                tree_entry = yield self.github_client.get_tree_entry(
                    user, repo, path=url_unescape(path), ref=ref
                    )
            
            # fetch file data from the blobs API
            with self.catch_client_error():
                response = yield self.github_client.fetch(tree_entry['url'])

                data = json.loads(response_text(response))
                contents = data['content']
                if data['encoding'] == 'base64':
                    # filedata will be bytes
                    filedata = base64_decode(contents)
                else:
                    # filedata will be unicode
                    filedata = contents

            try:
                # filedata may be bytes, but we need text
                if isinstance(filedata, bytes):
                    nbjson = filedata.decode('utf-8')
                else:
                    nbjson = filedata
            except Exception as e:
                app_log.error("Failed to decode notebook: %s", path, exc_info=True)
                raise web.HTTPError(400)

            nbjson = json.load(StringIO(nbjson))
            now = datetime.now()
            model = {
                'content': nbjson,
                'created': now,
                'format': 'json',
                'last_modified': now,
                'mimetype': None,
                'type': 'notebook',
                'writable': True}
            name = copy_pat.sub(u'.', os.path.basename(path))
            to_name = contents_manager.increment_filename(name, clone_to, insert='-Copy')
            full_clone_to = u'{0}/{1}'.format(clone_to, to_name)
            contents_manager.save(model, full_clone_to)
            # Redirect to the cloned notebook
            # in JupyterLab's single-document mode.
            self.redirect(url_path_join('lab', 'tree', full_clone_to))


    host_pattern = '.*$'
    local_route_pattern  = url_path_join(web_app.settings['base_url'], '/local_clone')
    github_route_pattern = url_path_join(web_app.settings['base_url'], '/github_clone')

    web_app.add_handlers(host_pattern, [(local_route_pattern, LocalCloneHandler),
                                        (github_route_pattern, GitHubCloneHandler)])
