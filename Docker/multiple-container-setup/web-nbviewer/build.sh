#!/bin/bash

docker build                    \
    "$@"                        \
    --tag clonenotebooks/web-nbviewer . \
    --force-rm --no-cache 
