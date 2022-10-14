
Plug-in interface
=================

All Troika plug-ins rely on the same interface based on
:py:mod:`importlib.metadata`. They should advertise the relevant objects using
the appropriate group, e.g.: ``troika.controllers``. The given name will be used
to look up the plug-in based on the configuration file. Here is an example of a
``setup.cfg`` file advertising Troika plug-ins:

.. code-block:: cfg

   [options.entry_points]
   troika.connections =
       quantum_link = troika_quantum.connections:QuantumLinkConnection
   troika.hooks.at_startup =
       prepare_qubits = troika_quantum.hooks:prepare_qubits
       check_cooling = troika_quantum.hooks:check_cooling
   troika.sites =
       quantum = troika_quantum.sites:QuantumCloudSite
