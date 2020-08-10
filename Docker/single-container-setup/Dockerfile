# most recent LTS at time this Dockerfile was written
FROM ubuntu:bionic
LABEL maintainer="William Krinsman <krinsman@berkeley.edu>"

ENV PATH=/opt/conda/bin:$PATH  \
    DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8
WORKDIR /tmp

RUN \
#
# Clone repos to non-temp folder so we can edit them later
#
    mkdir /repos					&&  \
#
# Install basic dependencies
    apt-get update					&&  \
    apt-get --yes upgrade				&&  \
    apt-get --yes install --no-install-recommends	\
    bzip2	 					\
    curl						\
    ca-certificates					\
    libffi-dev						\
    lsb-release						\
    tzdata						\
    wget					        \
    vim                                                 \
    git						        \
    gcc						        \
# nbviewer dependencies
    libcurl4-openssl-dev				\
    libgnutls28-dev					\
    libzmq3-dev						\
    libmemcached-dev						\
    libevent-dev				        &&  \
    apt-get clean --yes					&&  \
#
# Install Miniconda
#
    wget https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh    &&  \
    bash Miniconda3-latest-Linux-x86_64.sh -f -b -p /opt/conda							      &&  \
    echo "python 3.7.*" >> /opt/conda/conda-meta/pinned					      	      &&  \
    conda config --add channels conda-forge							      &&  \
    conda install   									    	      \
    invoke											      \
    jupyterhub											      \
    jupyterlab											      \
    markdown											      \
### newrelic should probably be made an optional dependency for nbviewer, which can probably happen in a new PR
    newrelic											      \
    nodejs											      \
### likewise statsd is the same situation as newrelic; it's installed to prevent code from breaking
    statsd											      \
    pandoc											      \
    psycopg2											      \
    pycurl											      \
    setuptools											      &&  \
    conda clean --all --yes							      		      &&  \
    rm -rf /opt/conda/pkgs/*   	 							      	      &&  \
#
# add dummy users
#
    adduser -q --gecos "" --disabled-password william		  &&  \
    echo william:hi   | chpasswd	      			  &&  \
    adduser -q --gecos "" --disabled-password krinsman		  &&  \
    echo krinsman:bye | chpasswd	      			  &&  \
#
# Install nbviewer
#
    git clone --single-branch --branch master https://github.com/jupyter/nbviewer.git /repos/nbviewer	    &&  \
    cd /repos/nbviewer								    			    &&  \
# --no-dependencies flag because we don't actually need pylibmc or elasticsearch to run this (without
# elasticsearch or memcached) and everything else in requirements.txt is already installed
    pip install -e . --no-cache-dir --no-dependencies			    				    &&  \
    npm install   							    				    &&  \
    invoke bower							    				    &&  \
    invoke less												    &&  \
# Install notebook cloning extension
    git clone https://github.com/NERSC/clonenotebooks.git /repos/clonenotebooks			    &&  \
    cd /repos/clonenotebooks									            &&  \
    pip install -e . --no-cache-dir									    &&  \
    jupyter serverextension enable clonenotebooks.cloners --sys-prefix				            &&  \
# Clean up after ourselves
    rm -rf /tmp/*

# Add necessary config files
WORKDIR  /srv
ADD jupyterhub_config.py .
ADD nbviewer_config.py   .

