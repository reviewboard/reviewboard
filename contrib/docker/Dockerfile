# Dockerfile for Review Board.
#
# Copyright (C) 2020 Beanbag, Inc.
#
# Documentation on this Docker image is available at
# http://localhost:8081/docs/manual/latest/admin/installation/docker/


##############################################################################
# Stage 1 of the build.
#
# We'll set up development support and compile any modules we need in a
# virtualenv. That will be copied in stage 2 to the destination image, without
# carrying all the development bloat.
#
# We're using Ubuntu (LTS release) rather than Alpine, due to better
# compatibility with compiled Python modules and a long support life.
#
# Alpine doesn't use glibc, and cannot benefit from pre-compiled wheels.
# See https://pythonspeed.com/articles/alpine-docker-python/
##############################################################################
FROM ubuntu:20.04 AS builder
MAINTAINER Beanbag, Inc. <support@beanbaginc.com>

# The version of Review Board this will install.
ARG REVIEWBOARD_VERSION

# Power Pack version to install.
#
# This can be in X.Y or X.Y.Z form.
ARG POWERPACK_VERSION=3.0

# Review Bot extension version to install.
#
# This can be in X.Y or X.Y.Z form.
ARG REVIEWBOT_VERSION=2.0

# Extra extension packages needed by the server.
#
# This is used only when building from *this* Dockerfile. Consumers should
# create a new Dockerfile that inherits from this one and installs packages
# themselves.
ARG EXTRA_PACKAGES=

# Install all the base system-level packages needed by Review Board.
#
# We will be installing some packages (including most Python packages) via
# pip instead of apt-get.
RUN    set -ex \
    && apt-get update -y \
    && apt-get install -y --no-install-recommends \
           build-essential \
           ca-certificates \
           curl \
           gnupg \
           libapr1-dev \
           libaprutil1-dev \
           libffi-dev \
           libssl-dev \
           libjpeg-dev \
           libmysqlclient-dev \
           libsasl2-dev \
           libsvn-dev \
           mysql-client \
           openssl \
           postgresql-client \
           python3.8-dev \
           subversion \
           virtualenv \
    && rm -rf /var/lib/apt/lists/*

# Add the Perforce apt repository.
#
# NOTE: Update the "deb" line when modifying the base Ubuntu version!
RUN    { curl https://package.perforce.com/perforce.pubkey | apt-key add -; } \
    && echo "deb http://package.perforce.com/apt/ubuntu bionic release" \
       > /etc/apt/sources.list.d/perforce.list

# Set up the environment for Python and scripts.
ENV LANG=C.UTF-8
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Set up a virtualenv for Review Board.
ENV VIRTUAL_ENV=/venv
RUN virtualenv -p python3.8 $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install Review Board and its Python dependencies.
#
# If any packages are provided in ./packages/ when building this, we'll
# prioritize those.
COPY ./packages /tmp/packages
RUN    set -ex \
    && pip3 install -U pip \
    && pip3 install \
           --no-cache-dir \
           gunicorn \
           gunicorn[gevent] \
           gunicorn[gthread] \
    && pip3 install \
           --no-cache-dir \
           --pre \
           --find-links /tmp/packages \
           ReviewBoard~=${REVIEWBOARD_VERSION} \
           ReviewBoardPowerPack~=${POWERPACK_VERSION} \
           reviewbot_extension~=${REVIEWBOT_VERSION} \
           ${EXTRA_PACKAGES} \
	&& pip3 install \
           --no-cache-dir \
           'ReviewBoard[ldap]' \
           'ReviewBoard[mercurial]' \
           'ReviewBoard[mysql]' \
           'ReviewBoard[p4]' \
           'ReviewBoard[postgres]' \
           'ReviewBoard[s3]' \
           'ReviewBoard[swift]' \
    && { curl https://pysvn.reviewboard.org | python3.8 -; } \
    && rm -rf /tmp/packages


##############################################################################
# Stage 2 of the build.
#
# We'll create a new, final image that contains the virtualenv and only the
# runtime dependencies necessary to run Review Board.
##############################################################################
FROM ubuntu:20.04

# Review Board user ID
#
# The web server will run as this user, and writable directories (such as
# htdocs/media/uploaded/ and data/) will be owned by this user.
ARG REVIEWBOARD_USER_ID=1001

# Review Board group ID
#
# Writable directories (such as htdocs/media/uploaded/ and data/) will be owned
# by this group.
ARG REVIEWBOARD_GROUP_ID=1001

# Whether to install Power Pack by default.
#
# Set to "no" to disable.
ENV ENABLE_POWERPACK=yes

# Public-facing domain name for the server.
ENV DOMAIN=

# Name of your company, for support purposes.
ENV COMPANY=

# Memcached hostname:port.
ENV MEMCACHED_SERVER=memcached:11211

# Database type.
#
# One of "mysql" or "postgresql"
ENV DATABASE_TYPE=postgresql

# Existing name of the database on the server.
ENV DATABASE_NAME=reviewboard

# Database server.
ENV DATABASE_SERVER=db

# Username for accessing the database.
#
# This should be a user specific to Review Board, and not an administrator.
ENV DATABASE_USERNAME=reviewboard

# Password for accessing the database.
ENV DATABASE_PASSWORD=

# Whether to wait for the database to be up before starting services.
ENV WAIT_FOR_DB=yes

# The number of Gunicorn workers.
#
# This, along with NUM_THREADS, should be tuned for the server it's run on.
# It should be at least 2.
ENV NUM_WORKERS=4

# The number of Gunicorn threads.
#
# This, along with NUM_THREADS, should be tuned for the server it's run on.
ENV NUM_THREADS=20

# The number of seconds before a connection is dropped due to inactivity.
#
# This can be set higher if communication with internal servers or
# repositories regularly takes longer than 2 minutes.
ENV REQUEST_TIMEOUT=120

ENV GUNICORN_FLAGS=

# Public port that gunicorn will listen to.
EXPOSE 8080

# Location of the site directory.
#
# Mount this somewhere to persist the site directory across containers.
VOLUME /site

# Set up the environment for Python and scripts.
#
# These are used by the processes being run, and are not intended to be
# customized.
ENV LANG=C.UTF-8
ENV VIRTUAL_ENV=/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
ENV REVIEWBOARD_SITEDIR /site
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create a user for the web server.
RUN    groupadd -r reviewboard -g $REVIEWBOARD_GROUP_ID \
    && adduser --system --uid $REVIEWBOARD_USER_ID \
               --disabled-password --disabled-login \
               --ingroup reviewboard reviewboard

COPY --from=builder /etc/apt /etc/apt

RUN    apt-get update -y \
    && apt-get install -y --no-install-recommends \
           ca-certificates \
           curl \
           cvs \
           git \
           gosu \
           helix-cli \
           libmysqlclient21 \
           patch \
           mysql-client \
           postgresql-client \
           python3.8 \
           python3.8-distutils \
           stunnel \
           subversion \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3.8 /usr/bin/python3

COPY scripts/* /
COPY --from=builder $VIRTUAL_ENV $VIRTUAL_ENV

# Periodically check that we can hit our API endpoint, to ensure Review Board
# is running.
HEALTHCHECK CMD curl -f http://127.0.0.1:8080/api/info/ || exit 1

# Run the site install/upgrade operation and the web server.
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["/serve.sh"]
