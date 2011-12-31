.. blargs documentation master file, created by
   sphinx-quickstart on Sat Dec 31 12:11:21 2011.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to blargs's documentation!
==================================

blargs provides easy command line parsing, as an alternative to argparse and
optparse from Python's standard library. The main distinctions are:

  * Support for arbitrarily complex dependency relationships. For example, argument A might require arguments B and C, while conflicting with D.
  * Cleaner, more minimal syntax.

Use blargs if

Usage
=====

>>> with Parser(locals()) as p:
...    p.add_int('first').requires(
...       p.add_flag('second'),
...       p.add_option('third'),
...    )
...    p.add_int('fourth').conflicts('first')

When the with clause terminates, the arguments are parsed from sys.argv. The following command lines will be rejected:

    python test.py --first 3  # does not supply second or third

    python test.py --first 3 --second --third 'hello' --fourth 3  # fourth conflicts

new addition ## what

The following will be accepted

  python test.py

  python test.py --first 3 --second --third 'hello'

Contents:

.. toctree::
   :maxdepth: 2
   main

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

