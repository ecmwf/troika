
Invoking Troika
===============

An overview of the available options can be seen with the ``--help`` option:

.. code-block:: shell-session

   $ troika --help
   usage: troika [-h] [-V] [-v] [-q] [-l LOGFILE] [-c CONFIG] [-n] action ...

   Submit, monitor and kill jobs on remote systems

   positional arguments:
     action                perform this action, see `troika <action> --help` for details
       submit              submit a new job
       monitor             monitor a submitted job
       kill                kill a submitted job
       check-connection    check whether the connection works
       list-sites          list available sites

   optional arguments:
     -h, --help            show this help message and exit
     -V, --version         show program's version number and exit
     -v, --verbose         increase verbosity level (can be repeated)
     -q, --quiet           decrease verbosity level (can be repeated)
     -l LOGFILE, --logfile LOGFILE
                             save log output to this file
     -c CONFIG, --config CONFIG
                             path to the configuration file
     -n, --dryrun          if true, do not execute, just report

   environment variables:
     TROIKA_CONFIG_FILE    path to the default configuration file

Submit
------

The :ref:`submit` command requires a few parameters:

* A :ref:`site <site>` to submit to,
* A job script to submit,
* A path to the output file on the remote system,
* (Optional) A user to impersonate for the submission.

Troika can be invoked as follows::

   troika submit -u <user> -o <output> <site> <script>

Monitor
-------

The :ref:`monitor` command polls the chosen site to get status information for a
given job::

   troika monitor -u <user> -j <jobid> <site> <script>

The arguments are:

* The user, site and script, just like for the submit command,
* (Optional) The site-specific job ID, to override the one stored by Troika.

The output is written to ``<script>.stat``.

Kill
----

The :ref:`kill` command cancels or aborts the execution of the given job::

   troika kill -u <user> -j <jobid> -o <output> <site> <script>

The arguments have the same meaning as above. Usually, this command relies on
signals sent to the job, which can be configured by setting a
:ref:`kill_sequence`.