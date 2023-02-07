
.. _configuration:

Configuration
=============

The Troika configuration file is written in YAML. See
:doc:`/getting_started/configure` for an example, and :ref:`Command-line
interface <cli_config>` for instructions regarding its location. Note that
plugins may extend the configuration beyond what is described here. Please refer
to the plugin-specific documentation for details.

Top-level options
-----------------

The top-level configuration mapping may contain some global options.


.. _config_controller:

controller
~~~~~~~~~~

Use this specific controller. Plugins can define new controllers, see
:doc:`/extending/controller`.


Site configuration
------------------

The site configuration is contained in the ``sites`` mapping. Each key describes
the name of a site, and the values are mapping containing the configuration for
this specific site. The common site configuration options are described here.
Plugins (including connections, sites and hooks) may extend this configuration.
For additional documentation about sites, see :doc:`/reference/sites/index`.

.. _type:

type
~~~~

The site type. Troika supports the :doc:`direct </reference/sites/direct>`,
:doc:`pbs </reference/sites/pbs>` and :doc:`slurm </reference/sites/slurm>`
sites. Plugins may define additional sites, see :doc:`/extending/site`.


.. _connection:

connection
~~~~~~~~~~

The connection type. A site can be reached in different ways. Troika defines the
:ref:`local <local_connection>` and :ref:`ssh <ssh_connection>` connections.
Plugins may define additional connections, see :doc:`/extending/connection`.


.. _default_shebang:

default_shebang
~~~~~~~~~~~~~~~

If set, Troika will add this line to the beginning of the script if it does not
have a shebang.


.. _translators:

translators
~~~~~~~~~~~

List of translators to apply when preprocessing the script. See
:doc:`/reference/preprocessing` for a detailed description and a list of
built-in translators.


unknown_directive
~~~~~~~~~~~~~~~~~

Behaviour if an unknown directive is encountered (see
:doc:`/reference/preprocessing`). Possible values are:

``fail``
   Troika will report an error and abort,
``warn``
   Troika will report a warning and continue,
``ignore``
   Troika will continue silently.

The default value is ``warn``.


directive_prefix
~~~~~~~~~~~~~~~~

Override the directive prefix set by the site, e.g. ``"#SBATCH "``.


.. _directive_translate:

directive_translate
~~~~~~~~~~~~~~~~~~~

Add or replace directives offered by the site. Mapping keys are the directive
names (see :doc:`/reference/preprocessing`), values can be either a
``%``-formatting string, or ``null`` to ignore this directive. The resulting
directive will be computed using ``directive_prefix + (directive_translate[name]
% argument)``.


.. _config_extra_directives:

extra_directives
~~~~~~~~~~~~~~~~

When the :ref:`translator_extra_directives` translator is enabled, these
directives will be added, unless already set. This is a mapping whose keys are
the directive names (see :doc:`/reference/preprocessing`) and values are the
values for these directives.


.. _config_copy_script:

copy_script
~~~~~~~~~~~

If ``true``, when a job is submitted, copy the script to the remote system
before calling the submission system. Otherwise, pipe the script through the
connection to the submission system. Default is ``false``.

.. _kill_sequence:

kill_sequence
~~~~~~~~~~~~~

The kill sequence describes the sequence of events when :ref:`kill` is called.
The default will issue a site-specific "cancel" command (e.g. ``kill -15``,
``scancel``, ``qdel``) immediately. The value of this option is a list of
``[duration, signal]`` pairs, where durations are in seconds and signals can be
numeric or textual. For example, with the following configuration:

.. code-block:: yaml

   kill_sequence: [[0, "SIGINT"], [5, 15], [4, "KILL"]]

Troika will send a ``SIGINT`` immediately, wait for 5 seconds, issue a
``SIGTERM`` (signal 15), wait 4 more seconds and finally issue a ``SIGKILL``.


.. _hook_options:

Hooks
~~~~~

Hooks can be enabled by adding their names to the list corresponding to the hook
type, e.g.:

.. code-block:: yaml

   at_exit: ['copy_submit_logfile', 'copy_kill_logfile']

The following hook types are defined: :ref:`at_startup`, :ref:`pre_submit`,
:ref:`post_kill`, and :ref:`at_exit`. See :doc:`/reference/hooks` for a list of
built-in hooks. Plugins may define new hooks, see :doc:`/extending/hook`. The
options supported by the built-in hooks are listed below.

.. _config_pmkdir_command:

pmkdir_command
^^^^^^^^^^^^^^

Command to issue when creating a directory on the remote platform. Default:
``["mkdir", "-p"]``. Used by the :ref:`hook_create_output_dir`,
:ref:`hook_copy_orig_script`, :ref:`hook_copy_submit_logfile`, and
:ref:`hook_copy_kill_logfile` hooks.


.. _ssh_connection_options:

SSH connection options
~~~~~~~~~~~~~~~~~~~~~~

These options control the behaviour of the SSH connection.

host
^^^^

SSH host to connect to.

user
^^^^

User to log in as.

ssh_command
^^^^^^^^^^^

Path to the ``ssh`` executable. The default is to look for ``ssh`` in the
``PATH``.

scp_command
^^^^^^^^^^^

Path to the ``scp`` executable. The default is to look for ``scp`` in the
``PATH``.

ssh_options
^^^^^^^^^^^

Additional options to pass to ``ssh``. Must be a list.

ssh_verbose
^^^^^^^^^^^

If ``true``, ``ssh`` will be called with the ``-v`` option to include extra
information in the output. Default is ``false``.

ssh_strict_host_key_checking
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If ``true``, perform strict host key checking. Default is ``false``.

ssh_connect_timeout
^^^^^^^^^^^^^^^^^^^

Abandon the SSH connection after this delay (in seconds). If not set, the
behaviour is the one of the ``ssh`` command.


.. _direct_site_options:

Direct site options
~~~~~~~~~~~~~~~~~~~

shell
^^^^^

Command to issue to spawn the shell interpreter, as a list. If not set, the
shell is supposed to be ``bash`` in the ``PATH``, and ``bash -s`` will be used
when :ref:`config_copy_script` is ``false``.


.. _config_use_shell:

use_shell
^^^^^^^^^

If ``true``, the job script will be executed using the shell interpreter.
Otherwise, it will be executed directly. Note that :ref:`config_use_shell` and
:ref:`config_copy_script` cannot be both ``false`` for remote sites. Default is
``false`` when the connection is local, and ``true`` if it is remote.


.. _pbs_site_options:

PBS site options
~~~~~~~~~~~~~~~~

qsub_command
^^^^^^^^^^^^

Path to the ``qsub`` executable.

qdel_command
^^^^^^^^^^^^

Path to the ``qdel`` executable.

qsig_command
^^^^^^^^^^^^

Path to the ``qsig`` executable.

qstat_command
^^^^^^^^^^^^^

Path to the ``qstat`` executable.


.. _slurm_site_options:

Slurm site options
~~~~~~~~~~~~~~~~~~

sbatch_command
^^^^^^^^^^^^^^

Path to the ``sbatch`` executable.

scancel_command
^^^^^^^^^^^^^^^

Path to the ``scancel`` executable.

squeue_command
^^^^^^^^^^^^^^

Path to the ``squeue`` executable.


Other options
~~~~~~~~~~~~~

Some components may define additional options, please refer to their
documentation. Also, :doc:`hooks </reference/hooks>` are selected at this level.