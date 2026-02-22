.. _writing-legacy-auth-backends:

======================================
Writing Legacy Authentication Backends
======================================

.. deprecated:: 1.6
   Legacy authentication backends are deprecated in 1.6.
   See :ref:`writing-auth-backends`.


Overview
========

Authentication in Review Board is handled by classes called Authentication
Backends. They perform the tasks of looking up users from some database or
server, authenticating against it given user credentials, and creating
local representations of the users in Review Board's database.

Review Board provides local database, NIS, LDAP and Active Directory backends
out of the box. New ones can be written to work with other types of
authentication schemes.


Authentication Classes
======================

An Authentication Backend class is a simple class inheriting from
``object``, which provides the following methods:

* :py:meth:`authenticate`
* :py:meth:`get_or_create_user`
* :py:meth:`get_user`


authenticate
------------

.. py:method:: authenticate(username, password)
   :noindex:

   :param username: The user's username.
   :param password: The user's password.
   :rtype: The authenticated user, if authentication succeeds. On failure,
           ``None``.

   Authenticates the user against a database or server.

   This is responsible for making any necessary communication with the
   database or server and determining the validity of the credentials
   passed.

   If the credentials are invalid, the function must return ``None``, which
   will allow it to fall back to the next authentication backend in the chain
   (or fail, if this is the last authentication backend).

   If the credentials are valid, the function must return a valid
   :py:class:`User <django.contrib.auth.models.User>`. Generally, rather than
   constructing one itself, it should call its own
   :py:func:`get_or_create_user` with the username.

   To help with debugging, this function should log any errors in
   communication using Python's :py:mod:`logging` support.

   The function may need to strip whitespace from the username before
   authentication. If the server itself strips whitespace when authenticating,
   but this function does not, it can lead to duplicate users in the database.


get_or_create_user
------------------

.. py:method:: get_or_create_user(username)
   :noindex:

   :param username: The user's username.
   :rtype: The user, if it exists. Otherwise, ``None``.

   Looks up or creates a :py:class:`User <django.contrib.auth.models.User>`
   based on information from the database or server.

   This tends to follow the pattern of:

   .. code-block:: python

      username = username.strip()

      try:
          user = User.objects.get(username=username)
      except User.DoesNotExist:
          # Construct a user from the database...
          return user

   Like :py:func:`authenticate`, this will look up the user from the
   database or server. However, it will not verify anything other than the
   username. It also must make sure to strip the username.

   This function is used both when logging in and when adding a user to
   a review request as a reviewer. In the latter case, Review Board will
   look up the user using the authentication backend in order to see if
   the user exists and can be added.


get_user
--------

.. py:method:: get_user(user_id)
   :noindex:

   :param user_id: The ID of the user in the database.
   :rtype: The user, if it exists. Otherwise, ``None``.

   This is a simple function that just looks up the
   :py:class:`User <django.contrib.auth.models.User>` in the database,
   given the numeric ID. This should always simply contain:

   .. code-block:: python

      return get_object_or_none(User, pk=user_id)

   Note: :py:func:`get_object_or_none` comes from :py:mod:`djblets.util.misc`.


Installing the Authentication Backend
=====================================

The authentication backend should be packaged as a standard Python egg.
This includes creating a :file:`setup.py` and making a proper Python module
that includes your authentication backend.

Once this is Python package is installed on the system running Review Board,
you can change the Authentication type in Review Board to :guilabel:`Custom`
and specify the Python path for your authentication backend class.
