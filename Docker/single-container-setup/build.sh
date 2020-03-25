#!/bin/bash

docker build    \
    --no-cache  \
    --tag clonenotebooks/single-container-setup . \
    --force-rm
