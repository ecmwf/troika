
Preprocessing
=============

When submitting a job, Troika will read the script to extract information,
translate the information into a set of directives, and generate a processed
script to send to the site. This behaviour can be extended using
:doc:`controllers </extending/controller>` and
:doc:`translators </extending/translator>`.


Script parsing
--------------

Troika will first feed the script to a series of parsers to extract meaningful information:

* Troika directives, as defined below,
* Native queueing system directives,
* A 'shebang' line.

This information will be made available to the controller, translators and generator.


Troika directives
-----------------

A Troika directive has the form::

   # troika name=value

The ``troika`` is case insensitive and additional whitespace is ignored. A
standard set of directives will be described below. Controllers and translators
may accept other directives.


Translation
-----------

Translators operate on the parsed data to update the set of directives. The following translators are available with Troika. Plugins may define extra translators, see :doc:`/extending/translator`.


``join_output_error``
~~~~~~~~~~~~~~~~~~~~~

When no ``error_file`` is supplied, add the ``join_output_error`` directive. For instance, with PBS this will generate the ``#PBS -j oe`` directive.


``enable_hyperthreading``
~~~~~~~~~~~~~~~~~~~~~~~~~

Add the ``enable_hyperthreading`` directive (if not yet provided), being true when ``threads_per_core`` is supplied and greater than 1, and false otherwise. With Slurm, this will result in a ``#SBATCH --hint=[no]multithread`` directive.


Generation
----------

The generated script will be made of the following fragments:

* The shebang line (a default value can be configured using :ref:`default_shebang`),
* The translated directives, if relevant,
* The native directives from the original script, if any,
* Extra lines that the translators may generate (e.g., environment variables), if any,
* The script body.


Standard directives
-------------------

The following directives form a common set supported by most sites. Some sites
may support additional directives, see the site documentation. This set can be
extended or updated through the :ref:`directive_translate` configuration
mapping.

=========================  ========================  ==============================  =====
Directive                  PBS translation           Slurm translation               Notes
=========================  ========================  ==============================  =====
``billing_account``        ``-A <value>``            ``--account=<value>``
``cpus_per_task``                                    ``--cpus-per-task=<value>``
``enable_hyperthreading``                            ``--hint=[no]multithread``      [1]_
``error_file``             ``-e <value>``            ``--error=<value>``
``export_vars``            ``-v <value>`` or ``-V``  ``--export=<value>``            [1]_
``join_output_error``      ``-j oe``                 Ignored
``licenses``                                         ``--licenses=<value>``
``mail_type``              ``-m <value>``            ``--mail-type=<value>``         [1]_
``mail_user``              ``-M <value>``            ``--mail-user=<value>``
``memory_per_node``                                  ``--mem=<value>``
``memory_per_cpu``                                   ``--mem-per-cpu=<value>``
``name``                   ``-M <value>``            ``--job-name=<value>``
``output_file``            ``-o <value>``            ``--output=<value>``
``partition``                                        ``--partition=<value>``
``priority``               ``-p <value>``            ``--priority=<value>``
``tasks_per_node``                                   ``--ntasks-per-node=<value>``
``threads_per_core``                                 ``--threads-per-core=<value>``
``tmpdir_size``                                      ``--tmp=<value>``
``total_nodes``                                      ``--nodes=<value>``
``total_tasks``                                      ``--ntasks=<value>``
``queue``                  ``-q <value>``            ``--qos=<value>``
``walltime``                                         ``--time=<value>``
``working_dir``            ``-l walltime=<value>``   ``--chdir=<value>``
=========================  ========================  ==============================  =====

.. rubric:: Notes

.. [1] The value will be translated to match the site's requirements.

The following aliases are also defined for convenience:

============  ================
Alias         Target directive
============  ================
``error``     ``error_file``
``job_name``  ``name``
``output``    ``output_file``
``time``      ``walltime``
============  ================