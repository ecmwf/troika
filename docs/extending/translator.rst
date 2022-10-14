
Defining new translators
========================

Translators can modify the data read from the job script to update the generated
script, for instance by changing the set of scheduler directives. Additional
translators should be advertised as part of the ``troika.translators`` group and
selected using the :ref:`translators` site configuration keyword.


Translator API reference
------------------------

A translator is a function with the following signature:

.. autofunction:: troika.translators.base.translators
