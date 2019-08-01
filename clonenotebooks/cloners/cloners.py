from datetime import datetime
import json
import os.path
import re

from notebook.utils import url_path_join
from notebook.base.handlers import IPythonHandler
from notebook.services.contents.manager import copy_pat
import nbformat
from tornado import web, httpclient
from tornado.escape import url_unescape, url_escape
from nbviewer.utils import response_text

from tempfile import TemporaryDirectory
from jupyter_client.kernelspec import install_kernel_spec
import sys

def load_jupyter_server_extension(nb_server_app):
    """
    Called when the extension is loaded.

    Args:
        nb_server_app (NotebookWebApplication): handle to the Notebook webserver instance.
    """
    web_app = nb_server_app.web_app
    contents_manager = nb_server_app.contents_manager

    # This class is defined in line so it can close over contents_manager.
    class CloneHandler(IPythonHandler):
        def clone_to_directory(self, nb, clone_from, clone_to):
            # convert notebook to current format
            nbnode = nbformat.reads(nb, as_version=4)
            nb = nbformat.writes(nbnode)
            # change string to JSON object
            nbjson = json.loads(nb)

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
            self.redirect(url_path_join('lab', 'tree', full_clone_to))

        def clone_kernelspec(self, kernelspec, name):
            with TemporaryDirectory() as tmpdir, open(os.path.join(tmpdir, "kernel.json"), "w+") as tmpfile:
                tmpfile.write(kernelspec)
                install_kernel_spec(source_dir=tmpdir, kernel_name=name, prefix=sys.prefix)

    class LocalCloneHandler(CloneHandler):
        def get(self):
            path = self.get_query_argument('clone_from')
            clone_to = "/"  # root directory of notebook server
            self.log.info("Cloning file at %s to %s", path, clone_to)
            if not os.path.isfile(path):
                raise web.HTTPError(400, "No such file: %s" % path)
            with open(path, 'r') as f:
                nbjson = json.load(f)

            # Turn JSON object into a string
            nb = json.dumps(nbjson)
            self.clone_to_directory(nb, path, clone_to)

    class URLCloneHandler(CloneHandler):
        client = httpclient.AsyncHTTPClient()

        async def get(self):
            url = url_unescape(self.get_query_argument('clone_from'))
            if not url.endswith('.ipynb'):
                raise web.HTTPError(415)

            try:
                dirname = os.path.dirname(url)
                kernelspec = await self.fetch_utf8_file(os.path.join(dirname, "kernel.json"))
                name = os.path.basename(dirname)
                self.clone_kernelspec(kernelspec, name)
            except Exception as e:
                self.log.warning("Failed to load kernel.json or to install kernelspec.")
                self.log.error(e)

            clone_to = "/" # root directory of notebook server
            self.log.info("Cloning notebook from URL: %s", url)
            nb = await self.fetch_utf8_file(url)
            
            self.clone_to_directory(nb, url, clone_to)

        async def fetch_utf8_file(self, url):
            try:
                protocol = self.get_query_argument('protocol')
            # Assume HTTPS and not HTTP by default:
            except web.MissingArgumentError:
                protocol = 'https'

            remote_url = u"{}://{}".format(protocol, url_escape(url, plus=False))

            response = await self.client.fetch(remote_url)

            try:
                utf8_file = response_text(response, encoding='utf-8')
            except UnicodeDecodeError:
                self.log.error("File is not utf8: %s", remote_url, exc_info=True)
                raise web.HTTPError(400)
            return utf8_file

    class GitHubCloneHandler(IPythonHandler):
        def get(self):
            raw_url = self.get_query_argument('clone_from')
            self.redirect('/user-redirect/url_clone?clone_from={}&protocol={}'.format(raw_url, 'https'))

    class GistCloneHandler(IPythonHandler):
        def get(self):
            raw_url = self.get_query_argument('clone_from')
            self.redirect('/user-redirect/url_clone?clone_from={}&protocol={}'.format(raw_url, 'https'))

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
