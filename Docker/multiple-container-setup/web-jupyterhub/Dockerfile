FROM clonenotebooks/jupyter-base:latest
LABEL maintainer="William Krinsman <krinsman@berkeley.edu>"
WORKDIR /srv
#
RUN apt-get install -y libcurl4-openssl-dev libssl-dev gcc
#
RUN conda install jupyterlab --yes
#
RUN \
    mkdir /repos &&  \
#
    git clone https://github.com/krinsman/clonenotebooks.git /repos/clonenotebooks    &&  \
    cd /repos/clonenotebooks               &&  \
    pip install -e . --no-cache-dir &&  \
    jupyter serverextension enable clonenotebooks.cloners --sys-prefix
#
RUN \
    adduser -q --gecos "" --disabled-password william && \
    echo william:hi | chpasswd
#
ENV PYTHONPATH=/srv
#
# Volume for user cert/key files
#
VOLUME /certs
#
# Entrypoint and command
#
ADD docker-entrypoint.sh jupyterhub_config.py /srv/
RUN chmod +x docker-entrypoint.sh
ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["jupyterhub", "--debug"]
