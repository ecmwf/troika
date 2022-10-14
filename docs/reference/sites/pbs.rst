
PBS queueing system
===================

This site submits jobs to the PBS queueing system.  It can be selected by
setting ``type: pbs`` in the site configuration. The options are documented in
the :ref:`configuration reference <pbs_site_options>`.

Submit
------

The job will be passed to the ``qsub`` command. If :ref:`config_copy_script` is
``true``, the script will be copied and passed as a command-line argument.
Otherwise, it will be piped into ``qsub``'s standard input.

Monitor
-------

The ``qstat`` command will be executed and its input written into the ``.stat``
file.

Kill
----

If a :ref:`kill_sequence` is provided, the given signals will be transmitted to
the job using ``qsig``. Otherwise, the job will be interrupted using ``qdel``.
