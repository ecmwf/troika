
Command-line interface
======================

.. program:: troika

General behaviour and common options
------------------------------------

The Troika CLI is based on a few actions described below. The global behaviour
can be set using options that are common to all actions. Every action, as well
as the main ``troika`` command, has a :option:`-h` option that prints a help
message. The version of Troika can be retrieved using :option:`-V`.

.. option:: -h, --help

   Print a help message and exit. Can be used as ``troika --help`` as well as
   for actions, e.g. ``troika submit --help``.

.. option:: -V, --version

   Print the version of Troika and exit.

.. important::

   Common options must appear **before** the action on the command line.

Logging
~~~~~~~

The main actions (:ref:`submit`, :ref:`monitor`, :ref:`kill`) will create a log
file called ``<script>.<action>log``, e.g., ``testjob.submitlog`` by default,
this can be overridden by the :option:`-l` option. If the file exists, it will
be overwritten, unless the :option:`-A` flag is present. The log verbosity on the
command line (standard error) can be controlled using the :option:`-v` and
:option:`-q` options. The default verbosity level only prints warnings and
errors.

.. option:: -l <path>, --logfile <path>

   Save log output to this file, instead of deducing a name from the script name
   (main actions) or no file at all.

.. option:: -A, --append-log

   Do not overwrite an existing log file, append to it instead.

.. option:: -q, --quiet

   Decrease the command-line verbosity level, can be repeated. Use ``-qq`` to
   disable all log output.

.. option:: -v, --verbose

   Increase the command-line verbosity level, can be repeated. Use ``-vv`` to
   enable all log output, including debug messages.


.. _cli_config:

Configuration
~~~~~~~~~~~~~

The execution is guided by a configuration file (see :doc:`/reference/config`), that
can be either specified on the command line using :option:`-c`, set as the
:envvar:`TROIKA_CONFIG_FILE`, or put into ``etc/troika.yml`` in Troika's
installation prefix.

.. option:: -c <path>, --config <path>

   Path to the configuration file. Takes precedence over the
   :envvar:`TROIKA_CONFIG_FILE` environment variable.

.. envvar:: TROIKA_CONFIG_FILE

   Path to the configuration file. Overridden by the :option:`-c` option.

Dry run
~~~~~~~

A dry run mode (:option:`-n` flag) is available to test the functionalities
without actually performing submission. All command execution will be disabled,
but some changes like script preprocessing may still happen.

.. option:: -n, --dryrun

    Enable dry-run mode. Commands will be logged as information messages (use
    :option:`-v` to see them) instead of executing them.


Site actions
------------

The main actions provided by Troika act on a given :ref:`site <site>` that may
be remote. A job is expected to be provided as a shell script, and Troika will
write additional local files in the directory containing the script. An output
path must be specified for :ref:`submit` and :ref:`kill` (:option:`-o` option).
It is assumed to be valid on the remote site. :ref:`Hooks <hooks>` may try
creating files and directories using that path.

.. option:: -o <path>, --output <path>

    (:ref:`submit` and :ref:`kill` only) Path to the output file, interpreted on
    the remote site.

A user name may be specified to interact with the site using the :option:`-u`
option. If none is given, it is assumed to be the current user name on the local
side.

.. option:: -u <user>, --user <user>

    User to impersonate when interacting with the site.

For actions that operate on a submitted job, a job identifier can be provided
using the :option:`-j` option. Otherwise, it will be taken from the
``<script>.jid`` file.

.. option:: -j <jobid>, --jobid <jobid>

    (:ref:`monitor` and :ref:`kill` only) Use this job identifier instead of the
    ``<script>.jid`` file.

Extra directives (see :doc:`/reference/preprocessing`) can be specified and will
override the values defined in the script, if any.

.. option:: -D <name>=<value>, --define <name>=<value>

   (:ref:`submit` only) Define additional directives. Can be used multiple
   times.


.. _submit:

submit
~~~~~~

The first main action provided by Troika is to submit a job to a :ref:`site
<site>`. The script is pre-processed and the path to the output (:option:`-o`
option) is added to the scheduler directives, if needed. The site-specific job
identifier is written to a ``<script>.jid`` file alongside the job script.


.. _monitor:

monitor
~~~~~~~

The ``monitor`` action polls the remote site to retrieve status information for
the specified job. The output is written to the ``<script>.stat`` file alongside
the job script.


.. _kill:

kill
~~~~

The ``kill`` action cancels the submission or aborts the execution of the
specified job. The precise behaviour may differ from site to site, but it is
usually following a :ref:`kill sequence <kill_sequence>` defined in the
configuration, sending signals after certain amounts of time.


.. _check-connection:

check-connection
~~~~~~~~~~~~~~~~

The ``check-connection`` action tests whether it is possible to contact a remote
site. A timeout can be set using the :option:`-t` option, otherwise Troika will
wait until a response is given.

.. option:: -t <seconds>, --timeout <seconds>

   Abort if no response is given within that duration.


Additional actions
------------------

.. _list-sites:

list-sites
~~~~~~~~~~

This prints a list of known sites with their type and connection.
