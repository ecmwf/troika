
Defining new connections
========================

The connection is responsible for reaching a remote site, sending files and
executing commands. Additional connections should be advertised as part of the
``troika.connections`` group and selected using the :ref:`connection` site
configuration keyword.

Connection API reference
------------------------

A connection is a class inheriting from
:py:class:`troika.connections.base.Connection`.

.. autoclass:: troika.connections.base.Connection
   :members: is_local, execute, sendfile, checkstatus
   :undoc-members:
