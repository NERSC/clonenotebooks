from datetime import datetime
import json
import os.path

from notebook.utils import url_path_join
from notebook.base.handlers import IPythonHandler
from notebook.services.contents.manager import copy_pat
from tornado import web

from contextlib import contextmanager
from nbviewer.providers.github import AsyncGitHubClient
from nbviewer.utils import response_text

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

    class GithubCloneHandler(IPythonHandler):
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
        
        def get(self):
            # This is similar to notebook.contents.manager.ContentsManager.copy
            # but it (1) assumes the clone_from is on the filesystem not some
            # non-file-based ContentManager implementation and (2) is able to
            # clone files from outside of ("above") the notebook server's root
            # directory.
            clone_from = self.get_argument('clone_from')
            clone_to = "/"  # root directory of notebook server
            self.log.info("Cloning notebook on GitHub found at %s to %s", clone_from, clone_to)

            split_clone_from = clone_from.split('/', 2)
            user = split_clone_from[0]
            repo = split_clone_from[1]
            path = split_clone_from[2]
            
            with self.catch_client_error():
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


    host_pattern = '.*$'
    route_pattern = url_path_join(web_app.settings['base_url'], '/github_clone')

    web_app.add_handlers(host_pattern, [(route_pattern, LocalCloneHandler)])
