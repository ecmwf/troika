
Connections
===========

Connections allow Troika to execute remote commands and interact with queueing
systems on remote sites. This page documents the built-in connections. See
:doc:`/extending/connection` for documentation on how to provide new connections
using plug-ins.


.. _local_connection:

Local connection
----------------

The local connection issues commands on the system where Troika is executed.


.. _ssh_connection:

SSH connection
--------------

The SSH connections allows running commands and sending files through SSH. This
relies on the ``ssh`` and ``scp`` commands. The options are documented in the
:ref:`configuration reference <ssh_connection_options>`.
