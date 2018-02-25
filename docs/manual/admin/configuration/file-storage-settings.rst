.. _file-storage-settings:

=====================
File Storage Settings
=====================

The File Storage Settings allows you to customize where uploaded file
attachments will be stored. By default, uploaded files are stored on
the Review Board server, but it can be changed to store on `Amazon S3`_, a
scalable file storage service provided by Amazon.

.. _`Amazon S3`: https://aws.amazon.com/s3/
.. _`OpenStack Swift`: https://docs.openstack.org/swift/latest/


General Settings
================

* **File storage method:**
    Allows you to choose how you want uploaded files. There are two options:

    * :guilabel:`Host file system` - Review Board will use the local file
       system's :file:`media/uploaded` directory to store the files.

    * :guilabel:`Amazon S3` - Review Board will use `Amazon S3`_ to store
      the files. You must have a working, paid account to use this.

      This requires that you install the :mod:`django-storages` Python
      module. See the installation documentation for more information.

    * :guilabel:`OpenStack Swift` - Review Board will use `OpenStack Swift`_
      to store the files.

      This requires that you install the :mod:`django-storage-swift` Python
      module. See the installation documentation for more information.


Amazon S3 Settings
==================

* **Amazon AWS access key:**
    The Amazon AWS access key ID provided in your AWS account. This can be
    found in the :guilabel:`Security Credentials` section of the AWS site.

* **Amazon AWS secret access key:**
    The Amazon AWS secret access key ID provided in your AWS account. This
    too can be found in the :guilabel:`Security Credentials` section of the
    AWS site.

* **S3 bucket name:**
    The name of your Amazon S3 Bucket where your files will be stored and
    made available.

* **Amazon AWS calling format:**
    The method of access for retrieving files on your Amazon S3 account.
    This is one of the following:

    * :guilabel:`Path` - Files will be accessed by a path on
      ``s3.amazonaws.com`` in the format of
      ``http://s3.amazonaws.com/{bucket}/{key}``.

    * :guilabel:`Subdomain` - Files will be accessed by a subdomain of
      ``s3.amazonaws.com`` in the format of
      ``http://{bucket}.s3.amazonaws.com/{key}``. The subdomain is configured
      in your Amazon S3 account.

    * :guilabel:`Vanity` - Files will be accessed by a path on a custom
      vanity domain in the format of
      ``http://{vanity_domain}}/key``. The vanity domain is configured in
      your Amazon S3 account.


OpenStack Swift Settings
========================

* **Swift auth URL:**
    The URL for the auth server, e.g. ``http://127.0.0.1:5000/v2.0``

* **Swift username:**
    The username to use to authenticate, e.g. system:root

* **Swift key:**
    The key (password) to use to authenticate.

* **Swift auth version:**
    The version of the authentication protocol to use.

* **Swift container name:**
    The container in which to store the files. This container must be publicly readable.
