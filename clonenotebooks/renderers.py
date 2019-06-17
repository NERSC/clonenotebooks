import os
import mimetypes
import json

from nbviewer.providers.base import cached
from nbviewer.utils import response_text, quote, base64_decode
from nbviewer.providers.url.handlers import URLHandler
from nbviewer.providers.github.handlers import GitHubBlobHandler

from urllib.parse import urlparse
from urllib import robotparser

from tornado import gen, httpclient, web
from tornado.log import app_log
from tornado.escape import url_unescape, url_escape

class URLRenderingHandler(URLHandler):
    """Renderer for /url or /urls"""

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

        proto = 'http' + secure
        netloc = url_unescape(netloc)

        if '/?' in url:
            url, query = url.rsplit('/?', 1)
        else:
            query = None

        remote_url = u"{}://{}/{}".format(proto, netloc, quote(url))

        if query:
            remote_url = remote_url + '?' + query
        if not url.endswith('.ipynb'):
            # this is how we handle relative links (files/ URLs) in notebooks
            # if it's not a .ipynb URL and it is a link from a notebook,
            # redirect to the original URL rather than trying to render it as a notebook
            refer_url = self.request.headers.get('Referer', '').split('://')[-1]
            if refer_url.startswith(self.request.host + '/url'):
                self.redirect(remote_url)
                return

        parse_result = urlparse(remote_url)

        robots_url = parse_result.scheme + "://" + parse_result.netloc + "/robots.txt"

        public = False # Assume non-public

        try:
            robots_response = yield self.fetch(robots_url)
            robotstxt = response_text(robots_response)
            rfp = robotparser.RobotFileParser()
            rfp.set_url(robots_url)
            rfp.parse(robotstxt.splitlines())
            public = rfp.can_fetch('*', remote_url)
        except httpclient.HTTPError as e:
            app_log.debug("Robots.txt not available for {}".format(remote_url),
                    exc_info=True)
            public = True
        except Exception as e:
            app_log.error(e)

        if self.clone_notebooks:
            is_clone = self.get_query_arguments('clone')
            app_log.info("\n Value of is_clone is: %s\n", is_clone)
            if is_clone:
                app_log.info("made it through the is_clone test!")
                destination = netloc + '/' + url
                app_log.info("\n destination is: %s\n", destination)
                self.clone_to_user_server(url=destination, protocol=proto)
                return

        response = yield self.fetch(remote_url)

        try:
            nbjson = response_text(response, encoding='utf-8')
        except UnicodeDecodeError:
            app_log.error("Notebook is not utf8: %s", remote_url, exc_info=True)
            raise web.HTTPError(400)

        yield self.finish_notebook(nbjson, download_url=remote_url,
                                   msg="file from url: %s" % remote_url,
                                   public=public,
                                   request=self.request,
                                   format=self.format) 

class GitHubBlobRenderingHandler(GitHubBlobHandler):
    """handler for files on github
    If it's a...
    - notebook, render it
    - non-notebook file, serve file unmodified
    - directory, redirect to tree
    """
    PROVIDER_CTX = {
        'provider_label': 'GitHub',
        'provider_icon': 'github',
        'executor_label': 'Binder',
        'executor_icon': 'icon-binder',
    }

    
    BINDER_TMPL = '{binder_base_url}/gh/{org}/{repo}/{ref}'
    BINDER_PATH_TMPL = BINDER_TMPL+'?filepath={path}'


    def _github_url(self):
        return os.environ.get('GITHUB_URL') if os.environ.get('GITHUB_URL', '') else "https://github.com/"

    @gen.coroutine
    def clone_to_user_server(self, user, repo, path, ref):
        """Clone a notebook on GitHub to the user's home directory.
        Parameters
        ==========
        user, repo, path, ref: str
          Used to create the URI nbviewer uses to specify the notebook on GitHub.
        """
        app_log.info("\nWe are in clone_to_user_server! yay!\n")
        fullpath = [user, repo, path, ref]
        app_log.info("\n value of fullpath before joining is: %s\n" % fullpath)
        fullpath = url_escape("/".join(fullpath))
        app_log.info("\n value of fullpath after joining is: %s\n" % fullpath)
        self.redirect('/user-redirect/github_clone?clone_from=%s' % fullpath)

    @cached
    @gen.coroutine
    def get(self, user, repo, ref, path):
        if path.endswith('.ipynb') and self.clone_notebooks:
            app_log.info("\nPath ends with ipynb and clone notebooks is true\n")
            is_clone = self.get_query_arguments('clone')
            app_log.info("\nValue of 'is_clone' is: %s \n" % is_clone)
            if is_clone:
                app_log.info("\nIs_clone is true!\n")
                self.clone_to_user_server(user, repo, path, ref)
                return

        raw_url = u"https://raw.githubusercontent.com/{user}/{repo}/{ref}/{path}".format(
            user=user, repo=repo, ref=ref, path=quote(path)
        )
        blob_url = u"{github_url}{user}/{repo}/blob/{ref}/{path}".format(
            user=user, repo=repo, ref=ref, path=quote(path), github_url=self._github_url()
        )
        with self.catch_client_error():
            tree_entry = yield self.github_client.get_tree_entry(
                user, repo, path=url_unescape(path), ref=ref
            )

        if tree_entry['type'] == 'tree':
            tree_url = "/github/{user}/{repo}/tree/{ref}/{path}/".format(
                user=user, repo=repo, ref=ref, path=quote(path),
            )
            app_log.info("%s is a directory, redirecting to %s", self.request.path, tree_url)
            self.redirect(tree_url)
            return

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

        if path.endswith('.ipynb'):
            dir_path = path.rsplit('/', 1)[0]
            base_url = "/github/{user}/{repo}/tree/{ref}".format(
                user=user, repo=repo, ref=ref,
            )
            breadcrumbs = [{
                'url' : base_url,
                'name' : repo,
            }]
            breadcrumbs.extend(self.breadcrumbs(dir_path, base_url))

            # Enable a binder navbar icon if a binder base URL is configured
            executor_url = self.BINDER_PATH_TMPL.format(
                binder_base_url=self.binder_base_url,
                org=user,
                repo=repo,
                ref=ref,
                path=quote(path)
            ) if self.binder_base_url else None

            try:
                # filedata may be bytes, but we need text
                if isinstance(filedata, bytes):
                    nbjson = filedata.decode('utf-8')
                else:
                    nbjson = filedata
            except Exception as e:
                app_log.error("Failed to decode notebook: %s", raw_url, exc_info=True)
                raise web.HTTPError(400)

            yield self.finish_notebook(nbjson, raw_url,
                provider_url=blob_url,
                executor_url=executor_url,
                breadcrumbs=breadcrumbs,
                msg="file from GitHub: %s" % raw_url,
                public=True,
                format=self.format,
                request=self.request,
                **self.PROVIDER_CTX
            )
        else:
            mime, enc = mimetypes.guess_type(path)
            self.set_header("Content-Type", mime or 'text/plain')
            self.cache_and_finish(filedata)
