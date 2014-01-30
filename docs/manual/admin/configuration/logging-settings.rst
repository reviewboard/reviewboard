================
Logging Settings
================

These settings control how Review Board logs data. Logging is often useful for
debugging purposes and for spotting some server problems.

Review Board's built-in logging is different from the web server's logging,
and will not log page visits.

If logging is enabled, the log file can be viewed in the
:ref:`server-log`, linked to on the :ref:`administrator-dashboard`.


General
=======

* **Enable logging:**
	Enables logging of Review Board operations. This will log data to the
	file specified in `Log directory`.

	This defaults to being disabled.

.. _`Log Directory`:

* **Log directory:**
	The directory where log files will be stored. This must be writable by
	the web server.

	This defaults to the :file:`logs` directory under the Review Board site
	directory.


Advanced
========

* **Allow code profiling:**
	Logs the time spent on certain operations. This is primarily useful
	for debugging during Review Board development, and will greatly
	increase the size of log files.

	This defaults to being disabled.
