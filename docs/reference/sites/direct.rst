
Direct execution
================

This site directly executes job scripts on the target platform. It can be
selected by setting ``type: direct`` in the site configuration. The options are
documented in the :ref:`configuration reference <direct_site_options>`. The job
ID for jobs submitted using this connection corresponds to the process ID on the
target platform.

Submit
------

The submission behaviour is controlled by the connection (whether local or
remote) and the values of the :ref:`config_copy_script` and
:ref:`config_use_shell` options.

If ``use_shell`` is true, then a shell interpreter will be executed on the
target platform, and the job script will either be passed as a command-line
argument (if ``copy_script`` is true) or piped into the shell (if
``copy_script`` is false).


Monitor
-------

The ``ps`` command will be executed on the target platform, and its input
written into the ``.stat`` file.


Kill
----

The ``kill`` command will be executed on the target platform. If no
:ref:`kill_sequence` is given, a single ``SIGTERM`` will be sent.
