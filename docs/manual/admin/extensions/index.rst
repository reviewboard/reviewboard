.. _extensions:

==========
Extensions
==========

Review Board provides an extension API that can be used to extend the
available features across the product.

The extension API is still new and bleeding edge, and will be improved over
time. If you're interested in developing an extension, please read our
:ref:`writing-extensions` guide to get started.


Installing Extensions
=====================

Extensions are distributed as Python packages. These may have to be downloaded
on a website, or may be distributed through the standard Python package
distribution system.

In general, extensions can be installed with :command:`easy_install`.
Please prefer to the particular extension's documentation for installation
instructions.


Managing Extensions
===================

The Extensions page in the :ref:`Administration UI <administration-ui>` lists
all extensions currently installed on the system. From here, you can enable,
disable, configure, or edit database entries for an extension.

Depending on the capabilities of the extension, you'll see one or more
buttons:

* **Enable** - Enables the extension.
* **Disable** - Disables the extension.
* **Configure** - Opens a configuration page for customizing the behavior of
  the extension.
* **Database** - Opens a page for editing the extension's internal database.
  (This is an advanced feature and should only be used if you know what you're
  doing.)
