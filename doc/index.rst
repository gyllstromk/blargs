.. blargs documentation master file, created by
   sphinx-quickstart on Sat Dec 31 12:11:21 2011.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to blargs's documentation!
==================================

blargs provides easy command line parsing, as an alternative to argparse and
optparse from Python's standard library. The main distinctions are:

  * Support for arbitrarily complex dependency relationships. For example, argument A might require arguments B and C, while conflicting with D.
  * Cleaner, more minimal, and possibly more `pythonic` syntax.

Installation
------------

Pip is your friend here:

::

    pip install blargs

.. currentmodule:: blargs

Parser
------

The preferred use of :class:`Parser` is via the ``with`` idiom, as follows:

>>> with Parser(locals()) as p:
...    p.int('arg1')
...    p.str('arg2')
...    p.flag('arg3')

The user can now specify the following command lines:

::

    python test.py --arg1=3          # either '=' or
    python test.py --arg1 3          #   space is allowed
    python test.py --arg2 'hello'    #
    python test.py --arg3            # no value is specified; implied true

When the with clause loses scope, the ``sys.argv`` is parsed. In the case above,
two arguments are specified: ``arg1``, which accepts an int; ``arg2``, which
accepts a str, and ``arg3``, which is a flag argument (i.e., it is specified or
ommitted).

The following command lines will be rejected:

::

  python test.py --arg1 a  # 'a' does not parse to int
  python test.py --arg3 a  # 'arg3' is a flag and does not accept a value

Types
=====

>>> with Parser(locals()) as p:
...    # basic types
...    p.str('string_arg')      # --string_arg='hello'
...    p.int('int_arg')         # --int_arg 3
...    p.float('float_arg')     # --float_arg 9.6
...    p.flag('flag_arg')       # --flag_arg  (no argument passed)
...    # complex types
...    p.range('range_arg')     # --range_arg 1:2
...    p.multiword('multi_arg') # --multi_arg hello world
...    p.enum('enum_arg')       # 

Examples
========

Require an argument
-------------------

>>> with Parser(locals()) as p:
...    p.str('required_arg').required()

If we try to not pass it:

::

  python test.py 

We get the following:

::

  No value passed for required_arg
  usage: t.py [--required_arg <option>] [--help,-h]

Shorthand/alias
---------------

>>> with Parser(locals()) as p:
...    p.str('arg1').shorthand('a')

Either is acceptable:

::

  python test.py --arg1 my_string
  python test.py -a my_string

Note that we can specify any number of attributes by daisy-chaining calls. For example:

>>> with Parser(locals()) as p:                 # 'arg1' has 'a' as alias and
...    p.str('arg1').shorthand('a').required()  # is also required

Dependencies/Conflicts
----------------------

Dependencies indicate that some argument is required if another one is
specified, while conflicts indicate that two or more arguments may not be
mutually specified.

>>> with Parser(locals()) as p:                 # if 'arg2' is specified,
...    arg1 = p.str('arg1')                     # so too must be 'arg3' 
...    p.str('arg2').requires(                  # and 'arg1'. Note: if 'arg1'
...      p.str('arg3'),                         # is specified, this does not
...      arg1,                                  # mean 'arg2' must be
...    )
...    p.str('arg4').conflicts(                 # if 'arg4' is specified, then
...      arg1                                   # 'arg1' may not be.
...    )

A slightly more complex example:

>>> with Parser(locals()) as p:
...    p.float('arg1').requires(  # if 'arg1' is specified
...      p.int('arg2'),           # then both 'arg2'
...      p.flag('arg3'),          # and 'arg3' must be too, however,
...    ).conflicts(               # if it is specified,
...      p.str('arg4'),           # then neither 'arg4'
...      p.range('arg5')          # nor 'arg5' may be specified
...    )

Allowing Duplicates
-------------------

Normally an argument may only be specified once by the user. This can be changed:

>>> with Parser(locals()) as p:
...    p.str('arg1').multiple()

To use:

::

  python test.py --arg1 hello --arg1 world

Indicating default values
-------------------------

A default value means the argument will receive the value if not specified.

>>> with Parser(locals()) as p:
...    p.str('arg1').default('hello')

Both executions are equivalent:

::

  python test.py --arg1 hello
  python test.py

Allowing no argument label
--------------------------

If we want an argument to be parsed even without a label:

>>> with Parser(locals()) as p:
...    p.str('arg1').unspecified_default()
...    p.str('arg2')

Now, an argument without a label will be saved to ``arg1'':

::

  python test.py hello  # arg1 = 'hello'
  python test.py --arg2 world hello   # arg1 = 'hello', arg2 = 'world'

By indicating ``multiple``, the variable is stored as a ``list`` *even* if only
one instance is specified by the user.

Conditions
----------

>>> with Parser(locals()) as p:
...    arg1 = p.int('arg1')
...    p.float('arg2').requires(args1 < 20)  # float argument 'arg2'; if
...                                          # specified, arg1 value must be <
...                                          # 20
...
...    p.float('arg3').unless(args1 > 10)    # float argument 'arg2'; if
...                                          # specified, arg1 value must be
...                                          # <= 10

Complex Dependencies
--------------------

>>> with Parser(locals()) as p:
...    p.at_least_one(            # at least one of
...      p.mutually_exclude(      # 'arg1', 'arg2', and/or 'arg3'
...        p.int('arg1'),         # must be specified, but
...        p.flag('arg2'),        # 'arg1' and 'arg2' may not
...      ),                       # both be specified
...      p.str('arg3'),
...    )

.. A number of attributes can be added to arguments:
.. 
..   * Whether or not they are required
..   * Alias/shorthands (e.g., for --arg1 we might wish to allow -a)
..   * The ability to allow the argument to be specified multiple times
..   * Casting to a type
..   * Default values for when arguments are not specified
..   * Dependencies and conflicts among arguments
..   * Enabling values passed without argument labels to count as a particular argument.
.. 
.. These attributes are specified via the :class:`Option` class, which is
.. constructed via :class:`Parser`. In the above example, the invocations of int,
.. str, and bool all return :class:`Option` objects. We can set attributes via
.. method calls on this object, which can be chained. For example:
.. 
.. >>> with Parser(locals()) as p:
.. ...   p.int('arg1').shorthand('a').default(0)
.. ...   p.str('arg2').required()
.. ...   p.str('arg3').unspecified_default().shorthand('b')
.. ...   p.int('arg4').multiple()
.. 
.. which indicates:
.. 
..   * 'arg1' has a shorthand of 'a' and a default value of 0
..   * 'arg2' is required
..   * 'arg3' has a shorthand of 'b' and, if no -- label is provided, free values will be assigned to arg3
..   * 'arg4' can be specified multiple times
.. 
.. The following command lines will be rejected:
.. 
.. ::
.. 
..   python test.py --arg1 3  # arg2 is not specified
.. 
.. Here's some command lines and how they'll be parsed.
.. 
.. ::
.. 
..   python test.py --arg2='hello' a --arg4 1 --arg4 5
.. 
.. ``a`` will be saved as arg3's value, as it is the unspecified default. arg4 will
.. be a list containing values [1, 5].

Code
====

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
