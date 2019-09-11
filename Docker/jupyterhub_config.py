c.JupyterHub.services = [
    {
        # the /services/<name> path for accessing the notebook viewer
        'name': 'nbviewer',
        # the interface and port nbviewer will use
        'url': 'http://127.0.0.1:9000',
        # command to start the nbviewer
        'command': ['python', '-m', 'nbviewer']
    }
]

c.Authenticator.admin_users = set(["krinsman"])

c.JupyterHub.hub_ip = '0.0.0.0'

# following advice here: https://jupyterlab.readthedocs.io/en/stable/user/jupyterhub.html
c.Spawner.default_url = '/lab'
# also advice here: https://github.com/jupyterhub/jupyterlab-hub
c.Spawner.cmd = ['jupyter-labhub']
