#!/bin/bash

docker build                    \
    "$@"                        \
    --tag clonenotebooks/web-jupyterhub:latest .
