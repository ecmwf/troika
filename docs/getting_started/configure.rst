
Basic configuration
===================

Troika holds a list of *sites* onto which jobs can be submitted. A site is
defined by two main parameters: a *connection type* (`local` or `ssh`), and a
*site type* (e.g. `direct` or `slurm`). Every site is identified by a name
given in the configuration file.

Example configuration file
--------------------------

Troika uses a YAML configuration file. The default location is
``etc/troika.yml`` within Troika's install prefix.

.. code-block:: yaml

   ---
   sites:
       localhost:
           type: direct         # jobs are run directly on the target
           connection: local    # the target is the current host
       remote:
           type: direct         # jobs are run directly on the target
           connection: ssh      # connect to the target via ssh
           host: remotebox      # ssh host
           copy_script: true    # if false, the script will be piped through ssh
           at_startup: ["check_connection"]
       slurm_cluster:
           type: slurm          # jobs are submitted to Slurm
           connection: ssh      # connect to the target via ssh
           host: remotecluster  # ssh host
           copy_script: true    # if false, the script will be piped through ssh
           at_startup: ["check_connection"]
           pre_submit: ["create_output_dir"]
           at_exit: ["copy_submit_logfile"]
       pbs_cluster:
           type: pbs            # jobs are submitted to PBS
           connection: ssh      # connect to the target via ssh
           host: othercluster   # ssh host
           copy_script: true    # if false, the script will be piped through ssh
           at_startup: ["check_connection"]
           pre_submit: ["create_output_dir"]
           at_exit: ["copy_submit_logfile"]

The configuration can be checked using the :ref:`list-sites` command:

.. code-block:: shell-session

   $ troika -c config.yml list-sites
   Available sites:
   Name                         Type            Connection
   ------------------------------------------------------------
   localhost                    direct          local
   remote                       direct          ssh
   slurm_cluster                slurm           ssh
   pbs_cluster                  pbs             ssh

The :ref:`at_startup`, :ref:`pre_submit`, and :ref:`at_exit` keys correspond to
:ref:`hooks <hooks>` that can be activated.