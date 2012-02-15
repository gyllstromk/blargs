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

Installation
------------

Pip is your friend here:

    pip install blargs

.. currentmodule:: blargs

Parser
------

The preferred use of :class:`Parser` is via the `with` idiom, as follows:

>>> with Parser(locals()) as p:
...    p.int('arg1')
...    p.str('arg2')
...    p.bool('arg3')

When the with clause loses scope, the sys.argv is parsed. In the case above,
two arguments are specified: 'arg1', which accepts an int; 'arg2', which
accepts a str, and 'arg3', which is a flag argument (i.e., it is specified or
ommitted).

The following command lines will be rejected:

  python test.py --arg1 a  # 'a' does not parse to int
  python test.py --arg3 a  # 'arg3' is a flag and does not accept a value


Examples
========


>>> with Parser(locals()) as p:
...    arg1 = p.int('arg1')                  # declares int argument named
...                                          # 'arg1'
...
...    p.float('arg2').requires(args1 < 20)  # float argument 'arg2'; if
...                                          # specified, args1 value must be <
...                                          # 20
...
...    p.float('arg3').unless(args1 > 10)    # float argument 'arg2'; if
...                                          # specified, args1 value must be >
...                                          # 10
...
...    p.float('arg4').requires(args1, p['arg2'])  # float argument 'arg2'; if
...                                     specified, args1 value must be < 20


Attributes
==========

A number of attributes can be added to arguments:

  * Whether or not they are required
  * Alias/shorthands (e.g., for --arg1 we might wish to allow -a)
  * The ability to allow the argument to be specified multiple times
  * Casting to a type
  * Default values for when arguments are not specified
  * Dependencies and conflicts among arguments
  * Enabling values passed without argument labels to count as a particular argument.

These attributes are specified via the :class:`Option` class, which is
constructed via :class:`Parser`. In the above example, the invocations of int,
str, and bool all return :class:`Option` objects. We can set attributes via
method calls on this object, which can be chained. For example:

>>> with Parser(locals()) as p:
...   p.int('arg1').shorthand('a').default(0)
...   p.str('arg2').required()
...   p.str('arg3').unspecified_default().shorthand('b')
...   p.int('arg4').multiple()

which indicates:

  * 'arg1' has a shorthand of 'a' and a default value of 0
  * 'arg2' is required
  * 'arg3' has a shorthand of 'b' and, if no -- label is provided, free values will be assigned to arg3
  * 'arg4' can be specified multiple times

The following command lines will be rejected:

  python test.py --arg1 3  # arg2 is not specified

Here's some command lines and how they'll be parsed.

  python test.py --arg2='hello' a --arg4 1 --arg4 5

'a' will be saved as arg3's value, as it is the unspecified default. arg4 will
be a list containing values [1, 5].

# XXX note = and space

..	autoclass:: Parser
  :members:

..	autoclass:: Option
  :members:

..	autoclass:: IOParser
  :members:

Exceptions
----------
.. autoclass::  ArgumentError
.. autoclass::  FormatError
.. autoclass::  MissingRequiredArgumentError
.. autoclass::  ManyAllowedNoneSpecifiedArgumentError
.. autoclass::  MultipleSpecifiedArgumentError
.. autoclass::  DependencyError
.. autoclass::  ConflictError
.. autoclass::  UnspecifiedArgumentError

.. #>>> with Parser(locals()) as p:
.. #...    p.add_int('first').requires(
.. #...       p.add_flag('second'),
.. #...       p.add_option('third'),
.. #...    )
.. #...    p.add_int('fourth').conflicts('first')
.. #
.. #When the with clause terminates, the arguments are parsed from sys.argv. The following command lines will be rejected:
.. #
.. #    python test.py --first 3  # does not supply second or third
.. #
.. #    python test.py --first 3 --second --third 'hello' --fourth 3  # fourth conflicts
.. #
.. #The following will be accepted
.. #
.. #  python test.py
.. #
.. #  python test.py --first 3 --second --third 'hello'
