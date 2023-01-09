
Installing Troika
=================

Prerequisites
-------------

Troika works on UNIX-based systems. The prerequisites below are for the *base*
system (where Troika will be run). Any *remote* system Troika will connect to
only need standard shell commands (e.g., ``mkdir``) and commands to interact
with jobs (e.g., ``bash`` / ``ps`` / ``kill``, ``sbatch`` / ``squeue`` /
``scancel``).

* Python 3.8 or higher
* ``pyyaml`` (https://pypi.org/project/PyYAML/)
* For testing: ``pytest`` (https://pypi.org/project/pytest/)
* For building the documentation: ``sphinx`` (https://www.sphinx-doc.org)


Installation
------------

Troika can be installed from its source repository. It is recommended to use a virtual environment, e.g.:

.. code-block:: shell

   python3 -m venv troika
   source troika/bin/activate
   python3 -m pip install troika
