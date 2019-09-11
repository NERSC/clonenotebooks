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
# nbviewer dependencies
    libmemcached-dev					\
    libcurl4-openssl-dev				\
    libgnutls28-dev					\
    libzmq3-dev						\
    libevent-dev				        &&  \
    apt-get clean --yes					&&  \
#    
# Install Miniconda
#
    curl -s -o miniconda3.sh https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh    &&  \
    bash miniconda3.sh -f -b -p /opt/conda							      &&  \
    echo "python 3.7.*" >> /opt/conda/conda-meta/pinned					      	      &&  \
    conda config --add channels conda-forge							      &&  \
    conda install   elasticsearch							    	      \
    invoke											      \
    jupyterhub											      \
    jupyterlab											      \
    markdown											      \
    newrelic											      \
    nodejs											      \
    pandoc											      \
    psycopg2											      \
    pycurl											      \
    pylibmc											      \
    setuptools											      \
    statsd											      &&  \
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
    git clone --single-branch --branch step7 https://github.com/krinsman/nbviewer.git /repos/nbviewer	    &&  \
    cd /repos/nbviewer								    			    &&  \
    pip install -e . --no-cache-dir					    				    &&  \
    npm install   							    				    &&  \
    invoke bower							    				    &&  \
    invoke less												    &&  \							    
# Install notebook cloning extension
    git clone https://github.com/krinsman/clonenotebooks.git /repos/clonenotebooks			    &&  \
    cd /repos/clonenotebooks									            &&  \
    pip install -e . --no-cache-dir									    &&  \
    jupyter serverextension enable clonenotebooks.cloners --sys-prefix				            &&  \
# Clean up after ourselves
    rm -rf /tmp/*

# Add necessary config files
WORKDIR  /srv
ADD jupyterhub_config.py .
ADD nbviewer_config.py   .

