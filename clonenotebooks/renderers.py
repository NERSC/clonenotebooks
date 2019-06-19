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
#            provider_url, provider_label, provider_icon,
#            executor_url, executor_label, executor_icon,
            json_notebook, #breadcrumbs, title, 
            **namespace):

        return super().render_notebook_template(body, nb, download_url, json_notebook,
                                                clone_notebooks=self.clone_notebooks,
                                                **namespace)

#        return self.render_template(
#            "formats/%s.html" % self.format,
#            body=body,
#            nb=nb,
#            download_url=download_url,
#            format=self.format,
#            default_format=self.default_format,
#            format_prefix=self.format_prefix,
#            formats=dict(self.filter_formats(nb, json_notebook)),
#            format_base=self.request.uri.replace(self.format_prefix, "").replace(self.base_url, '/'),
#            date=datetime.utcnow().strftime(self.date_fmt),
#            clone_notebooks=self.clone_notebooks,
            #**config
#            )

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
                                   request=self.request)

class GitHubBlobRenderingHandler(GitHubBlobHandler):
    """handler for files on github
    If it's a...
    - notebook, render it
    - non-notebook file, serve file unmodified
    - directory, redirect to tree
    """
    def render_notebook_template(self, body, nb, download_url,
#            provider_url, provider_label, provider_icon,
#            executor_url, executor_label, executor_icon,
            json_notebook, #breadcrumbs, title, 
            **namespace):

        return super().render_notebook_template(body, nb, download_url, json_notebook,
#                                                provider_url=namespace['provider_url'],
#                                                provider_label=namespace['provider_label'],
#                                                provider_icon=namespace['provider_icon'],
#                                                executor_url=namespace['executor_url'],
#                                                executor_label=namespace['executor_label'],
#                                                executor_icon=namespace['executor_icon'],
#                                                breadcrumbs=namespace['breadcrumbs'],
                                                clone_notebooks=self.clone_notebooks,
                                                **namespace)

#        return self.render_template(
#            "formats/%s.html" % self.format,
#            body=body,
#            nb=nb,
#            download_url=download_url,
#            provider_url=namespace['provider_url'],
#            provider_label=namespace['provider_label'],
#            provider_icon=namespace['provider_icon'],
#            executor_url=namespace['executor_url'],
#            executor_label=namespace['executor_label'],
#            executor_icon=namespace['executor_icon'],
#            format=self.format,
#            default_format=self.default_format,
#            format_prefix=self.format_prefix,
#            formats=dict(self.filter_formats(nb, json_notebook)),
#            format_base=self.request.uri.replace(self.format_prefix, "").replace(self.base_url, '/'),
#            date=datetime.utcnow().strftime(self.date_fmt),
#            breadcrumbs=namespace['breadcrumbs'],
#            clone_notebooks=self.clone_notebooks,
#            **config
#            )

    def _github_url(self):
        return os.environ.get('GITHUB_URL') if os.environ.get('GITHUB_URL', '') else "https://github.com/"

    @gen.coroutine
    def clone_to_user_server(self, raw_url):
        """Clone a notebook on GitHub to the user's home directory.
        Parameters
        ==========
        user, repo, path, ref: str
          Used to create the URI nbviewer uses to specify the notebook on GitHub.
        """
        app_log.info("\nWe are in clone_to_user_server! yay!\n")
        #fullpath = [user, repo, path, ref]
        #app_log.info("\n value of fullpath before joining is: %s\n" % fullpath)
        #fullpath = url_escape("/".join(fullpath))
        #app_log.info("\n value of fullpath after joining is: %s\n" % fullpath)
        #self.redirect('/user-redirect/github_clone?clone_from=%s' % fullpath)
        self.redirect('/user-redirect/github_clone?clone_from=%s' % raw_url)

    @cached
    @gen.coroutine
    def get(self, user, repo, ref, path):
#        if path.endswith('.ipynb') and self.clone_notebooks:
#            app_log.info("\nPath ends with ipynb and clone notebooks is true\n")
#            is_clone = self.get_query_arguments('clone')
#            app_log.info("\nValue of 'is_clone' is: %s \n" % is_clone)
#            if is_clone:
#                app_log.info("\nIs_clone is true!\n")
#                self.clone_to_user_server(user, repo, path, ref)
#                return

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

        if path.endswith('.ipynb') and self.clone_notebooks:
            app_log.info("\nPath ends with ipynb and clone notebooks is true\n")
            is_clone = self.get_query_arguments('clone')
            app_log.info("\nValue of 'is_clone' is: %s \n" % is_clone)
            if is_clone:
                app_log.info("\nIs_clone is true!\n")

                app_log.info("raw_url: %s" % raw_url)
                truncated_url = re.match(r'^https?://(?P<truncated_url>.*)', raw_url).group('truncated_url')
                app_log.info("truncated_url: %s" % truncated_url)

                self.clone_to_user_server(truncated_url)
                return

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
                msg="file from Github: %s" % raw_url,
                public=True,
                request=self.request,
                provider_url=blob_url,
                executor_url=executor_url,
                breadcrumbs=breadcrumbs,
#                msg="file from GitHub: %s" % raw_url,
#                public=True,
#                request=self.request,
                **self.PROVIDER_CTX
            )
        else:
            mime, enc = mimetypes.guess_type(path)
            self.set_header("Content-Type", mime or 'text/plain')
            self.cache_and_finish(filedata)

        # if path.endswith('.ipynb') and self.clone_notebooks:
        #     app_log.info("\nPath ends with ipynb and clone notebooks is true\n")
        #     is_clone = self.get_query_arguments('clone')
        #     app_log.info("\nValue of 'is_clone' is: %s \n" % is_clone)
        #     if is_clone:
        #         app_log.info("\nIs_clone is true!\n")
        #         self.clone_to_user_server(raw_url)
        #         return

class LocalRenderingHandler(LocalFileHandler):
    def render_notebook_template(self, body, nb, download_url,
#            provider_url, provider_label, provider_icon,
#            executor_url, executor_label, executor_icon,
            json_notebook, #breadcrumbs, title, 
            **namespace):

        return super().render_notebook_template(body, nb, download_url, json_notebook,
#                                                breadcrumbs=namespace['breadcrumbs'],
#                                                title=namespace['title'],
                                                clone_notebooks=self.clone_notebooks,
                                                **namespace)

#        return self.render_template(
#            "formats/%s.html" % self.format,
#            body=body,
#            nb=nb,
#            download_url=download_url,
#            format=self.format,
#            default_format=self.default_format,
#            format_prefix=self.format_prefix,
#            formats=dict(self.filter_formats(nb, json_notebook)),
#            format_base=self.request.uri.replace(self.format_prefix, "").replace(self.base_url, '/'),
#            date=datetime.utcnow().strftime(self.date_fmt),
#            breadcrumbs=namespace['breadcrumbs'],
#            title=namespace['title'],
#            clone_notebooks=self.clone_notebooks,
            #**config
#            )

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
        """Get a directory listing, rendered notebook, or raw file
        at the given path based on the type and URL query parameters.
        If the path points to an accessible directory, render its contents.
        If the path points to an accessible notebook file, render it.
        If the path points to an accessible file and the URL contains a
        'download' query parameter, respond with the file as a download.
        If the path points to an accessible file and the URL contains a
        'copy' query parameter, redirect to the current user's notebook
        server.
        Parameters
        ==========
        path: str
            Local filesystem path
        """
        fullpath = os.path.join(self.localfile_path, path)

        if not self.can_show(fullpath):
            raise web.HTTPError(404)

        if os.path.isdir(fullpath):
            html = self.show_dir(fullpath, path)
            raise gen.Return(self.cache_and_finish(html))

        is_download = self.get_query_arguments('download')
        if is_download:
            self.download(fullpath)
            return

        if self.clone_notebooks:
            is_clone = self.get_query_arguments('clone')
            app_log.info("\nValue of is_clone is: %s\n" % is_clone)
            if is_clone:
                app_log.info("\nMade it through the if is_clone test!\n")
                self.clone_to_user_server(fullpath)
                return

        try:
            with io.open(fullpath, encoding='utf-8') as f:
                nbdata = f.read()
        except IOError as ex:
            if ex.errno == errno.EACCES:
                # py2/3: can't read the file, so don't give away it exists
                raise web.HTTPError(404)
            raise ex

        yield self.finish_notebook(nbdata,
                                   download_url='?download',
                                   msg="file from localfile: %s" % path,
                                   public=False,
                                   request=self.request,
                                   breadcrumbs=self.breadcrumbs(path),
                                   title=os.path.basename(path))

    def show_dir(self, fullpath, path):
        """Render the directory view template for a given filesystem path.
        Parameters
        ==========
        fullpath: string
            Absolute path on disk to show
        path: string
            URL path equating to the path on disk
        Returns
        =======
        str
            Rendered HTML
        """
        entries = []
        dirs = []
        ipynbs = []

        try:
            contents = os.listdir(fullpath)
        except IOError as ex:
            if ex.errno == errno.EACCES:
                # py2/3: can't access the dir, so don't give away its presence
                raise web.HTTPError(404)

        for f in contents:
            absf = os.path.join(fullpath, f)

            if not self.can_show(absf):
                continue

            entry = {}
            entry['name'] = f

            # We need to make UTC timestamps conform to true ISO-8601 by
            # appending Z(ulu). Without a timezone, the spec says it should be
            # treated as local time which is not what we want and causes
            # moment.js on the frontend to show times in the past or future
            # depending on the user's timezone.
            # https://en.wikipedia.org/wiki/ISO_8601#Time_zone_designators
            if os.path.isdir(absf):
                st = os.stat(absf)
                dt = datetime.utcfromtimestamp(st.st_mtime)
                entry['modtime'] = dt.isoformat() + 'Z'
                entry['url'] = url_path_join(self._localfile_path, path, f)
                entry['class'] = 'fa fa-folder-open'
                dirs.append(entry)
            elif f.endswith('.ipynb'):
                st = os.stat(absf)
                dt = datetime.utcfromtimestamp(st.st_mtime)
                entry['modtime'] = dt.isoformat() + 'Z'
                entry['url'] = url_path_join(self._localfile_path, path, f)
                entry['class'] = 'fa fa-book'
                ipynbs.append(entry)

        dirs.sort(key=lambda e: e['name'])
        ipynbs.sort(key=lambda e: e['name'])

        entries.extend(dirs)
        entries.extend(ipynbs)

        html = self.render_template('dirview.html',
                                    entries=entries,
                                    breadcrumbs=self.breadcrumbs(path),
                                    title=url_path_join(path, '/'),
                                    clone_notebooks=self.clone_notebooks) 
        return html

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

        if not many_files_gist and not filename:
            filename = list(files.keys())[0]

        if filename and filename in files:
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

                if self.clone_notebooks:
                    is_clone = self.get_query_arguments('clone')
                    if is_clone:
                        raw_url = file['raw_url']
                        app_log.info("raw_url: %s" % raw_url)
                        truncated_url = re.match(r'^https?://(?P<truncated_url>.*)', raw_url).group('truncated_url')
                        app_log.info("truncated_url: %s" % truncated_url)

                        self.clone_to_user_server(truncated_url)
                        return

                yield self.finish_notebook(
                    content,
                    file['raw_url'],
                    msg="gist: %s" % gist_id,
                    public=gist['public'],
                    request=self.request,
                    provider_url=gist['html_url'],
                    executor_url=executor_url,
#                    msg="gist: %s" % gist_id,
#                    public=gist['public'],
#                    format=self.format,
#                    request=self.request,
                    **self.PROVIDER_CTX
                )
            else:
                self.set_header('Content-Type', file.get('type') or 'text/plain')
                # cannot redirect because of X-Frame-Content
                self.finish(content)
                return

        elif filename:
            raise web.HTTPError(404, "No such file in gist: %s (%s)", filename, list(files.keys()))
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

