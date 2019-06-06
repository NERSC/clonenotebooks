from datetime import datetime
import json
import os.path

from notebook.utils import url_path_join
from notebook.base.handlers import IPythonHandler
from notebook.services.contents.manager import copy_pat
from tornado import web


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
                content = json.load(f)
            now = datetime.now()
            model = {
                'content': content,
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
    route_pattern = url_path_join(web_app.settings['base_url'], '/local_clone')

    web_app.add_handlers(host_pattern, [(route_pattern, LocalCloneHandler)])
