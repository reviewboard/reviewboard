.. _2.0-authenticating:

==============
Authenticating
==============

Logging In
==========

Review Board makes use of Basic HTTP Authentication for logging in. This is
new in Review Board 1.5 and makes authentication much easier to implement.

If not logged in, any request that requires authentication will fail with
an HTTP 403 Unauthorized status.

This response will contain a ``WWW-Authenticate`` header to set
``Basic realm="Web API"``.

The client must respond with an ``Authorization`` header in the next
request to the URL. The contents of this will be :samp:`Basic {base64-auth}`.
The ``base64-auth`` part is a base64-encoded representation of the string
:samp:`{username}:{password}`.

For example, for a username and password of ``joe`` and ``mypass``, you
will base64-encode the string ``joe:mypass`` to get the resulting string
``am9lOm15cGFzcw==``, which you would then send as ``Basic am9lOm15cGFzcw==``.

After a successful login, you'll receive a ``rbsessionid`` cookie that the
client should use for all further requests. The cookie will be valid for a
year.


Logging Out
===========

Basic HTTP Authentication doesn't really provide a way to log clients out,
so it's up to the client to simply stop storing the ``rbsessionid`` cookie
and stop sending a populated ``Authorization`` header. Nothing needs to be
done on the server to tell Review Board you're no longer logged in.


.. comment: vim: ft=rst et ts=3
