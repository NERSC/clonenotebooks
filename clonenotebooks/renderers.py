import os
import mimetypes
import io
import json
import errno
import re
from datetime import datetime

from nbviewer.providers.base import cached
from nbviewer.utils import response_text, quote, base64_decode, url_path_join
from nbviewer.providers.url.handlers import URLHandler
from nbviewer.providers.github.handlers import GitHubBlobHandler
from nbviewer.providers.local.handlers import LocalFileHandler
from nbviewer.providers.gist.handlers import GistHandler

from urllib.parse import urlparse
from urllib import robotparser

from tornado import gen, httpclient, web
from tornado.log import app_log
from tornado.escape import url_unescape, url_escape

class URLRenderingHandler(URLHandler):
    """Renderer for /url or /urls"""

    def render_notebook_template(self, body, nb, download_url,
            json_notebook, **namespace):

        return super().render_notebook_template(body, nb, download_url, json_notebook,
                                                clone_notebooks=self.clone_notebooks,
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

        remote_url, public = yield super().format_notebook_request(secure, netloc, url)

        if self.clone_notebooks:
            is_clone = self.get_query_arguments('clone')
            if is_clone:
                destination = netloc + '/' + url
                self.clone_to_user_server(url=destination, protocol='http'+secure)
                return

        yield super().load_notebook(remote_url, public)

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
                                                clone_notebooks=self.clone_notebooks,
                                                **namespace)

    @gen.coroutine
    def clone_to_user_server(self, raw_url):
        """Clone a notebook on GitHub to the user's home directory.
        Parameters
        ==========
        user, repo, path, ref: str
          Used to create the URI nbviewer uses to specify the notebook on GitHub.
        """
        app_log.info("\nWe are in clone_to_user_server! yay!\n")
        self.redirect('/user-redirect/github_clone?clone_from=%s' % raw_url)

    @cached
    @gen.coroutine
    def get(self, user, repo, ref, path):
        raw_url, blob_url, tree_entry = yield super().format_notebook_request(user, repo, ref, path)

        if path.endswith('.ipynb') and self.clone_notebooks:
            is_clone = self.get_query_arguments('clone')
            if is_clone:
                truncated_url = re.match(r'^https?://(?P<truncated_url>.*)', raw_url).group('truncated_url')
                self.clone_to_user_server(truncated_url)
                return

        yield super().load_notebook(user, repo, ref, path, raw_url, blob_url, tree_entry)

class LocalRenderingHandler(LocalFileHandler):
    def render_notebook_template(self, body, nb, download_url,
            json_notebook, **namespace):

        return super().render_notebook_template(body, nb, download_url, json_notebook,
                                                clone_notebooks=self.clone_notebooks,
                                                **namespace)

    def render_dirview_template(self, entries, breadcrumbs, title, **namespace):

        return super().render_dirview_template(entries, breadcrumbs, title,
                                               clone_notebooks=self.clone_notebooks,
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
        fullpath = super().format_notebook_request(path)

        if self.clone_notebooks:
            is_clone = self.get_query_arguments('clone')
            if is_clone:
                self.clone_to_user_server(fullpath)
                return

        yield super().load_notebook(fullpath, path)

class GistRenderingHandler(GistHandler):
    def render_notebook_template(self, body, nb, download_url, json_notebook, **namespace):

        return super().render_notebook_template(body, nb, download_url, json_notebook,
                                                clone_notebooks=self.clone_notebooks,
                                                **namespace)

    @gen.coroutine
    def clone_to_user_server(self, url):
        self.redirect('/user-redirect/gist_clone?clone_from=%s' % url)

    @cached
    @gen.coroutine
    def get(self, user, gist_id, filename=''):

### BEGIN PREP GIST

        with self.catch_client_error():
            response = yield self.github_client.get_gist(gist_id)

        gist = json.loads(response_text(response))

        gist_id=gist['id']

        if user is None:
            # redirect to /gist/user/gist_id if no user given
            owner_dict = gist.get('owner', {})
            if owner_dict:
                user = owner_dict['login']
            else:
                user = 'anonymous'
            new_url = u"{format}/gist/{user}/{gist_id}".format(
                format=self.format_prefix, user=user, gist_id=gist_id)
            if filename:
                new_url = new_url + "/" + filename
            self.redirect(self.from_base(new_url))
            return

        files = gist['files']

        many_files_gist = (len(files) > 1)

### END PREP GIST

        if not many_files_gist and not filename:
            filename = list(files.keys())[0]

        if filename and filename in files:

### BEGIN SINGLE FILE FORMAT_NOTEBOOK_REQUEST

            file = files[filename]
            if (file['type'] or '').startswith('image/'):
                app_log.debug("Fetching raw image (%s) %s/%s: %s", file['type'], gist_id, filename, file['raw_url'])
                response = yield self.fetch(file['raw_url'])
                # use raw bytes for images:
                content = response.body
            elif file['truncated']:
                app_log.debug("Gist %s/%s truncated, fetching %s", gist_id, filename, file['raw_url'])
                response = yield self.fetch(file['raw_url'])
                content = response_text(response, encoding='utf-8')
            else:
                content = file['content']

            # Enable a binder navbar icon if a binder base URL is configured
            executor_url = self.BINDER_PATH_TMPL.format(
                binder_base_url=self.binder_base_url,
                user=user.rstrip('/'),
                gist_id=gist_id,
                path=quote(filename)
            ) if self.binder_base_url else None

            if not many_files_gist or filename.endswith('.ipynb'):

                app_log.info(file['raw_url'])

### END SINGLE FILE FORMAT_NOTEBOOK_REQUEST

### BEGIN CLONE NOTEBOOKS PART

                if self.clone_notebooks:
                    is_clone = self.get_query_arguments('clone')
                    if is_clone:
                        raw_url = file['raw_url']
                        app_log.info("raw_url: %s" % raw_url)
                        truncated_url = re.match(r'^https?://(?P<truncated_url>.*)', raw_url).group('truncated_url')
                        app_log.info("truncated_url: %s" % truncated_url)

                        self.clone_to_user_server(truncated_url)
                        return

### END CLONE NOTEBOOKS PART

### BEGIN SINGLE FILE LOAD_NOTEBOOK

                yield self.finish_notebook(
                    content,
                    file['raw_url'],
                    msg="gist: %s" % gist_id,
                    public=gist['public'],
                    request=self.request,
                    provider_url=gist['html_url'],
                    executor_url=executor_url,
                    **self.PROVIDER_CTX
                )
            else:
                self.set_header('Content-Type', file.get('type') or 'text/plain')
                # cannot redirect because of X-Frame-Content
                self.finish(content)
                return

        elif filename:
            raise web.HTTPError(404, "No such file in gist: %s (%s)", filename, list(files.keys()))

### END SINGLE FILE LOAD_NOTEBOOK

### BEGIN GistTreeHandler

        else:
            entries = []
            ipynbs = []
            others = []

            for file in files.values():
                e = {}
                e['name'] = file['filename']
                if file['filename'].endswith('.ipynb'):
                    e['url'] = quote('/%s/%s' % (gist_id, file['filename']))
                    e['class'] = 'fa-book'
                    ipynbs.append(e)
                else:
                    provider_url = u"https://gist.github.com/{user}/{gist_id}#file-{clean_name}".format(
                        user=user,
                        gist_id=gist_id,
                        clean_name=clean_filename(file['filename']),
                    )
                    e['url'] = provider_url
                    e['class'] = 'fa-share'
                    others.append(e)

            entries.extend(ipynbs)
            entries.extend(others)

            # Enable a binder navbar icon if a binder base URL is configured
            executor_url = self.BINDER_TMPL.format(
                binder_base_url=self.binder_base_url,
                user=user.rstrip('/'),
                gist_id=gist_id
            ) if self.binder_base_url else None

            html = self.render_template(
                'treelist.html',
                entries=entries,
                tree_type='gist',
                tree_label='gists',
                user=user.rstrip('/'),
                provider_url=gist['html_url'],
                executor_url=executor_url,
                **self.PROVIDER_CTX
            )
            yield self.cache_and_finish(html)

### END GistTreeHandler
