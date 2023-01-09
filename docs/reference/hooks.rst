
.. _hooks:

Hooks
=====

Hooks allow executing extra actions at various points of the execution of
Troika. This page describes the built-in hooks. Plugins may define additional
hooks, see :doc:`/extending/hook`. To enable hooks, add it to the list
corresponding to its type in the :ref:`site configuration <hook_options>`, e.g.:

.. code-block:: yaml

    at_startup: ['check_connection']

.. _at_startup:

at_startup
----------

Startup hooks are called directly after selecting the site, before executing the
requested action. The following startup hook is defined:

check_connection
~~~~~~~~~~~~~~~~

This hook checks whether the connection to the selected site works before trying
to execute the required action. If not, it will cause Troika to abort
immediately.


.. _pre_submit:

pre_submit
----------

Pre-submit hooks are called between script generation and submission. The
following pre-submit hooks are defined:

.. _hook_create_output_dir:

create_output_dir
~~~~~~~~~~~~~~~~~

This hook ensures the directory containing the output file exists on the remote
platform, creating it if needed. The command issued can be set using the
:ref:`config_pmkdir_commmand` option.

.. _hook_copy_orig_script:

copy_orig_script
~~~~~~~~~~~~~~~~

This hook copies the original script (before preprocessing) to the remote
platform, for instance to enable an ecFlow client to see it. The name of the
target file is ``<script>.orig``.


.. _post_kill:

post_kill
---------

Post-kill hooks are called after a :ref:`kill` command has been executed, for
instance to notify the task manager that a job has been killed. The following
post-kill hook is defined:

abort_on_ecflow
~~~~~~~~~~~~~~~

This hook calls ``ecflow --abort`` when a job is killed, making sure that the
ecFlow server is notified of the script termination. This relies on the presence
of the ``ecflow_name`` and ``ecflow_pass`` directives in the script.


.. _at_exit:

at_exit
-------

Exit hooks are executed at the end of the execution, even in the case of a
failure (the hook itself may perform different actions based on whether the
execution was successful). The following exit hooks are defined:

.. _hook_copy_submit_logfile:

copy_submit_logfile
~~~~~~~~~~~~~~~~~~~

After a :ref:`submit` action, copy the log file to the remote platform.

.. _hook_copy_kill_logfile:

copy_kill_logfile
~~~~~~~~~~~~~~~~~

.. program:: troika

After a :ref:`kill` action, copy the log file to the remote platform. This
requires the presence of the :option:`-o` option on the command line.
