#!/bin/bash

docker build                    \
    "$@"                        \
    --tag clonenotebooks:web-jupyterhub . \
    --force-rm --no-cache
