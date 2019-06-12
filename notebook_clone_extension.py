from datetime import datetime
import json
import os.path
from io import StringIO
import re
from urllib.parse import urlparse
from urllib import robotparser

from notebook.utils import url_path_join
from notebook.base.handlers import IPythonHandler
from notebook.services.contents.manager import copy_pat
from tornado import web
from tornado.escape import url_unescape, url_escape
from tornado import gen
from tornado import httpclient

from contextlib import contextmanager
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
            robots_url = parse_result.scheme + "://" + parse_result.netloc + "/robots.txt"
 
            public = False # Assume non-public

            try:
                robots_response = yield self.client.fetch(robots_url)
                robotstxt = response_text(robots_response)
                rfp = robotparser.RobotFileParser()
                rfp.set_url(robots_url)
                rfp.parse(robotstxt.splitlines())
                public = rfp.can_fetch('*', remote_url)
            except httpclient.HTTPError as e:
                self.log.debug("Robots.txt not available for {}".format(remote_url),
                        exc_info=True)
                public = True
            except Exception as e:
                self.log.error(e)

            response = yield self.client.fetch(remote_url)
            self.log.info("\nrespose is: %s\n", response)

            try:
                nbjson = response_text(response, encoding='utf-8')
            except UnicodeDecodeError:
                self.log.error("Notebook is not utf8: %s", remote_url, exc_info=True)
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
            name = copy_pat.sub(u'.', os.path.basename(url))
            to_name = contents_manager.increment_filename(name, clone_to, insert='-Copy')
            full_clone_to = u'{0}/{1}'.format(clone_to, to_name)
            contents_manager.save(model, full_clone_to)
            # Redirect to the cloned notebook
            # in JupyterLab's single-document mode.
            self.redirect(url_path_join('lab', 'tree', full_clone_to))

    host_pattern = '.*$'
    base_url = web_app.settings['base_url']
    url_route_pattern    = url_path_join(base_url, '/url_clone')

    web_app.add_handlers(host_pattern, [(url_route_pattern, URLCloneHandler)])
