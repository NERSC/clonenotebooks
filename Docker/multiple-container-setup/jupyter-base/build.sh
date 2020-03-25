#!/bin/bash

docker build    \
    --no-cache  \
    --tag clonenotebooks/jupyter-base . \
    --force-rm
