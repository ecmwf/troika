
Defining new hooks
==================

Hooks can add extra behaviour at various points during the execution. Additional
hooks should be advertised as part of the ``troika.hooks.<type>`` group, where
``<type>`` is the hook type, as described in :doc:`/reference/hooks`. Hooks can
be selected in the :ref:`site configuration <hook_options>`.


Hooks API reference
-------------------

A hook is a function which signature depends on its type:

.. autofunction:: troika.hooks.base.at_startup

.. autofunction:: troika.hooks.base.pre_submit

.. autofunction:: troika.hooks.base.post_kill

.. autofunction:: troika.hooks.base.at_exit
