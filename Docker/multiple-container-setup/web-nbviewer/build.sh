#!/bin/bash

docker build                    \
    "$@"                        \
    --tag clonenotebooks/web-nbviewer:latest .
