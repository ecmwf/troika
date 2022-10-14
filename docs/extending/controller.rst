
Defining new controllers
========================

The controller is responsible for executing all the Troika actions. Overriding
it can enable additional behaviour to be added. Additional controllers should be
advertised as part of the ``troika.controllers`` group and selected using the
:ref:`config_controller` configuration keyword.

Controller API reference
------------------------

A controller is a class inheriting from
:py:class:`troika.controllers.base.Controller`.

.. autoclass:: troika.controllers.base.Controller
   :members: __repr__, submit, monitor, kill, check_connection,
      list_sites, action_context, setup, teardown, parse_script, run_parser,
      generate_script, run_generator, _get_site
   :undoc-members:
