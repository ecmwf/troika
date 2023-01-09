
Defining new sites
==================

The site is responsible for interacting with a job execution framework, like a
queueing system. Additional sites should be advertised as part of the
``troika.sites`` group and selected using the :ref:`type` site configuration
keyword.

Site API reference
------------------

A site is a class inheriting from :py:class:`troika.sites.base.Site`.

.. autoclass:: troika.sites.base.Site
   :members: directive_prefix, directive_translate, submit, monitor, kill, check_connection,
      get_native_parser, get_directive_translation
   :undoc-members:
