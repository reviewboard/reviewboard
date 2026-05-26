.. _doc-review-settings:

========================
Document Review Settings
========================

.. versionadded:: 8.0

This page (:guilabel:`Admin UI -> Settings -> Document Review`) is used
to configure Review Board's Document Review feature.

Document Review allows users to review documents, presentations, and more,
whether those documents are files attached to a review request or part of a
diff.


.. admonition:: Document Review requires a Review Board subscription

   It's included in a `Review Board Plus or Enterprise
   <https://www.reviewboard.org/get/>`_ subscription, and with a legacy
   `Power Pack`_ license.


.. _Power Pack: https://www.reviewboard.org/powerpack/


.. _doc-review-broker-settings:

Broker Settings
---------------

The following settings are available:

* :guilabel:`Broker URL`

  The URL to the message broker used for sending new documents to the
  Doc Converter microservice.

  This is in the form of:

  .. code-block:: text

     amqp://username:password@server:port/vhost

  If you use `Review Bot`_, you can use the same message broker.

  See :ref:`powerpack-doc-review` for details on setting up your message
  broker and Doc Converter microservice.


.. _Review Bot: https://www.reviewboard.org/downloads/reviewbot/


.. _doc-review-broker-status:

Doc Converter Message Broker Status
-----------------------------------

Once a broker is configured, you can see the status of any Doc Converter
microservices that are available to handle document processing.

.. image:: doc-converter-status.png
   :width: 368
   :height: 161
   :alt: An example Doc Converter broker status pane, showing that it's
         connected to one broker with one Doc Converter instance. The ID
         of the instance is shown. A status message says, "The document
         conversion service is ready!" There's a Refresh button below it.
   :sources: 2x doc-converter-status@2x.png

Click :guilabel:`Refresh` to initiate a new scan for the broker and workers.
