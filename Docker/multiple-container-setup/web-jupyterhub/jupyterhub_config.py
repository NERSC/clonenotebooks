# Configuration file for jupyterhub.

import os
import requests

ip = requests.get("https://v4.ifconfig.co/json").json()["ip"]

## Allow named single-user servers per user
# c.JupyterHub.allow_named_servers = False
c.JupyterHub.allow_named_servers = True

# Additional config if notebooks should be cloned to a user's named server
#c.JupyterHub.default_server_name = 'test'

## Whether to shutdown single-user servers when the Hub shuts down.
#
#  Disable if you want to be able to teardown the Hub while leaving the single-
#  user servers running.
#
#  If both this and cleanup_proxy are False, sending SIGINT to the Hub will only
#  shutdown the Hub, leaving everything else running.
#
#  The Hub should be able to resume from database state.
# c.JupyterHub.cleanup_servers = True
c.JupyterHub.cleanup_servers = False

## The ip or hostname for proxies and spawners to use for connecting to the Hub.
#
#  Use when the bind address (`hub_ip`) is 0.0.0.0 or otherwise different from
#  the connect address.
#
#  Default: when `hub_ip` is 0.0.0.0, use `socket.gethostname()`, otherwise use
#  `hub_ip`.
#
#  Note: Some spawners or proxy implementations might not support hostnames.
#  Check your spawner or proxy documentation to see if they have extra
#  requirements.
#
#  .. versionadded:: 0.8
# c.JupyterHub.hub_connect_ip = ''
c.JupyterHub.hub_connect_ip = ip

## The ip address for the Hub process to *bind* to.
#
#  By default, the hub listens on localhost only. This address must be accessible
#  from the proxy and user servers. You may need to set this to a public ip or ''
#  for all interfaces if the proxy or user servers are in containers or on a
#  different host.
#
#  See `hub_connect_ip` for cases where the bind and connect address should
#  differ, or `hub_bind_url` for setting the full bind URL.
# c.JupyterHub.hub_ip = '127.0.0.1'
c.JupyterHub.hub_ip = "0.0.0.0"

## List of service specification dictionaries.
#
#  A service
#
#  For instance::
#
#      services = [
#          {
#              'name': 'cull_idle',
#              'command': ['/path/to/cull_idle_servers.py'],
#          },
#          {
#              'name': 'formgrader',
#              'url': 'http://127.0.0.1:1234',
#              'api_token': 'super-secret',
#              'environment':
#          }
#      ]
c.JupyterHub.services = [
    {
        "name": "nbviewer",
        "url": "http://web-nbviewer:5000",
        "api_token": os.environ["NBVIEWER_JUPYTERHUB_API_TOKEN"],
    }
]

## The URL the single-user server should start in.
#
#  `{username}` will be expanded to the user's username
#
#  Example uses:
#
#  - You can set `notebook_dir` to `/` and `default_url` to `/tree/home/{username}` to allow people to
#    navigate the whole filesystem from their notebook server, but still start in their home directory.
#  - Start with `/notebooks` instead of `/tree` if `default_url` points to a notebook instead of a directory.
#  - You can set this to `/lab` to have JupyterLab start by default, rather than Jupyter Notebook.
# c.Spawner.default_url = ''
c.Spawner.default_url = "/lab"

## Whitelist of environment variables for the single-user server to inherit from
#  the JupyterHub process.
#
#  This whitelist is used to ensure that sensitive information in the JupyterHub
#  process's environment (such as `CONFIGPROXY_AUTH_TOKEN`) is not passed to the
#  single-user server's process.
# c.Spawner.env_keep = ['PATH', 'PYTHONPATH', 'CONDA_ROOT', 'CONDA_DEFAULT_ENV', 'VIRTUAL_ENV', 'LANG', 'LC_ALL']
c.Spawner.env_keep = [
    "PATH",
    "CONDA_ROOT",
    "CONDA_DEFAULT_ENV",
    "VIRTUAL_ENV",
    "LANG",
    "LC_ALL",
]

## The IP address (or hostname) the single-user server should listen on.
#
#  The JupyterHub proxy implementation should be able to send packets to this
#  interface.
# c.Spawner.ip = ''
c.Spawner.ip = "0.0.0.0"

## Path to the notebook directory for the single-user server.
#
#  The user sees a file listing of this directory when the notebook interface is
#  started. The current interface does not easily allow browsing beyond the
#  subdirectories in this directory's tree.
#
#  `~` will be expanded to the home directory of the user, and {username} will be
#  replaced with the name of the user.
#
#  Note that this does *not* prevent users from accessing files outside of this
#  path! They can do so with many other means.
c.Spawner.notebook_dir = "/"

# ------------------------------------------------------------------------------
# Additional ConfigurableHTTPProxy configuration
# ------------------------------------------------------------------------------

c.ConfigurableHTTPProxy.should_start = False

c.ConfigurableHTTPProxy.api_url = "http://web-proxy:8001"

### Prometheus

c.JupyterHub.authenticate_prometheus = False
