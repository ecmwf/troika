
Slurm queueing system
=====================

This site submits jobs to the Slurm queueing system. It can be selected by
setting ``type: slurm`` in the site configuration. The options are documented in
the :ref:`configuration reference <slurm_site_options>`.

Submit
------

The job will be passed to the ``sbatch`` command. If :ref:`config_copy_script`
is ``true``, the script will be copied and passed as a command-line argument.
Otherwise, it will be piped into ``sbatch``'s standard input.

Monitor
-------

The ``squeue`` command will be executed and its input written into the ``.stat``
file.

Kill
----

The ``squeue`` command will be executed first to query the job status. If it is
pending or if no :ref:`kill_sequence` is set, ``scancel`` will be called without
any signal. Otherwise, the kill sequence will be executed using ``scancel -s
SIGNAL``.
