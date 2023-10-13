.. _health-checks:

=============
Health Checks
=============

.. versionadded:: 6.0

Monitoring and auto-scaling services can check Review Board to make sure it's
healthy.

A healthy Review Board instance is serving requests and can connect to its
database(s) and cache server(s).

Access to the health check endpoint is restricted by IP address.

We'll walk through how to perform a health check and how to configure access.


Performing Health Checks
------------------------

To check a Review Board server's health, perform a HTTP GET on the
``/health/`` endpoint on your server (for example:
``https://reviews.example.com/health/``).

This will return an HTTP status code and JSON payload representing the health
of the Review Board server.

A healthy server will send a :http:`200` response with the following JSON
payload:

.. code-block:: json

   {
       "checks": {
           "cache.default": "UP",
           "database.default": "UP"
       },
       "errors": {},
       "status": "UP"
   }

A server that's failing will send a :http:`503` response with a JSON payload
looking something like:

.. code-block:: json

   {
       "checks": {
           "cache.default": "DOWN",
           "database.default": "DOWN"
       },
       "errors": {
           "cache.default": "Unable to communicate with the cache server",
           "database.default": "Connection timed out"
       },
       "status": "DOWN"
   }

If any services are down, the main ``status`` field will be ``DOWN``.


.. _health-checks-docker:

Docker
------

Our :ref:`official Docker images <docker>` are pre-configured to perform
health checks.

To enable this in your own image, run:

.. code-block:: dockerfile

   HEALTHCHECK CMD curl -f http://127.0.0.1/health/ || exit 1


If this is being configured on an external server, make sure to use the
correct URL above and :ref:`configure access
<health-checks-configure-access>` to the health check endpoint.

You can configure the interval between health checks, how long until the
first health check, and how many failures until a server is considered
unhealthy. See the `Docker HEALTHCHECK documentation`_ for instructions.

.. _Docker HEALTHCHECK documentation:
   https://docs.docker.com/engine/reference/builder/#healthcheck


.. _health-checks-kubernetes:

Kubernetes
----------

You can configure a HTTP liveness probe in Kubernetes to check Review Board's
health. Note that you may need to :ref:`configure access
<health-checks-configure-access>` to the health check endpoint for your pod.

A liveness probe may look like:

.. code-block:: yaml

   apiVersion: v1
   kind: Pod
   metadata:
     name: reviewboard-liveness-http
     labels:
       test: liveness

   spec:
     containers:
       - name: liveness
         image: k8s.gcr.io/liveness
         args:
           - /server

         livenessProbe:
           httpGet:
             path: /health/
             port: 8080

You can configure the interval between health checks, how long until the
first health check, and how many failures until a server is considered
unhealthy. See the `Kubernetes liveness probe documentation`_ for
instructions.


.. _Kubernetes liveness probe documentation:
   https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/#define-a-liveness-http-request


.. _health-checks-configure-access:

Configuring Access
------------------

By default, health checks can only be accessed by clients on the same server,
using ``http://127.0.0.1/health/`` or ``http://[::1]/health/``.

To allow external servers to check the health of Review Board, you will need
to add its IP address to ``HEALTHCHECK_IPS`` in your site directory's
:file:`conf/settings_local.py` file.

For example:

.. code-block:: python

   HEALTHCHECK_IPS = [
       '10.0.1.20',
   ]
