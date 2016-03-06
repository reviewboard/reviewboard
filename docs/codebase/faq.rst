.. _faq:

==========================
Frequently Asked Questions
==========================

Contributions
=============

Can I submit pull requests?
---------------------------

No. We require all submissions to be made through our
`Review Board server`_. You have to admit, it would be a bit odd to use
anything else for code review :)

.. _`Review Board server`: https://reviews.reviewboard.org/


Troubleshooting
===============

My SSH-related unit tests always fail on MacOS X 10.11
------------------------------------------------------

On MacOS X 10.11 (El Capitan), :file:`/usr/bin` is no longer writable,
favoring :file:`/usr/local/bin` instead. However, the SSH daemon doesn't
search :file:`/usr/local/bin` for tools like :command:`cvs`, :command:`bzr`,
and so on.

This results in a number of failures, as the unit tests may succeed to SSH
into your local machine, but can't locate the appropriate command.

To work around this, you will need to make a couple changes to your
environment.

1. Construct a :file:`~/.ssh/environment` file, containing::

    PATH=/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin


   (Note that you cannot use ``$PATH`` in this string.)

2. Edit :file:`/etc/ssh/sshd_config` and add::

    PermitUserEnvironment yes

3. Restart sshd::

    $ sudo launchctl stop com.openssh.sshd

You should then be able to run the test suite without problems.
