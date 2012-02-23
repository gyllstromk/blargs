#  Copyright (c) 2011, Karl Gyllstrom
#  All rights reserved.
#
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions are met:
#
#  1. Redistributions of source code must retain the above copyright notice,
#     this list of conditions and the following disclaimer.
#
#  2. Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions and the following disclaimer in the documentation
#     and/or other materials provided with the distribution.
#
#     THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS
#     IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
#     THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
#     PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR
#     CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
#     EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
#     PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
#     PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
#     LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
#     NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
#     SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
#     The views and conclusions contained in the software and documentation are
#     those of the authors and should not be interpreted as representing
#     official policies, either expressed or implied, of the FreeBSD Project.


import operator
from functools import wraps
from itertools import starmap, permutations
import sys


def Config(filename, dictionary=None, overwrite=True):
    if dictionary is None:
        dictionary = {}

    for item in open(filename):
        if item.startswith('#'):
            continue

        toks = item.rstrip().split()
        if len(toks) == 2:
            if dictionary.get(toks[0], None) is not None and not overwrite:
                continue
            dictionary.__setitem__(*toks)

    return dictionary


# ---------- decorators ---------- #

def _names_to_options(f):
    @wraps(f)
    def inner(*args, **kwargs):
        new_args = []
        for arg in args[1:]:
            if isinstance(arg, basestring):
                arg = args[0]._options[arg]

            new_args.append(arg)

        return f(*[args[0]] + new_args, **kwargs)

    return inner


def _options_to_names(f):
    ''' Convert any :class:`Option`s to names. '''

    @wraps(f)
    def inner(*args, **kwargs):
        new_args = []
        for arg in args[1:]:
            if isinstance(arg, Option) and not isinstance(arg, Group):
                arg = arg.argname

            new_args.append(arg)

        return f(*[args[0]] + new_args, **kwargs)

    return inner


def _verify_args_exist(f):
    @wraps(f)
    def inner(*args, **kwargs):
        def raise_error(name):
            raise ValueError('%s not known' % name)

        self = args[0]
        for arg in args[1:]:
            if isinstance(arg, basestring) and arg not in self._readers:
                raise_error(arg)

        return f(*args, **kwargs)

    return inner


def _localize_all(f):
    @wraps(f)
    def inner(*args, **kwargs):
        args = list(args)
        self = args[0]
        new_args = []
        for arg in args[1:]:
            if isinstance(arg, basestring):
                arg = self._localize(arg)
            new_args.append(arg)
        args[1:] = new_args
        return f(*args, **kwargs)

    return inner


def localize(f):
    @wraps(f)
    def inner(*args, **kwargs):
        args = list(args)
        self = args[0]
#        args[1:] = [self._localize(x) for x in args[1]]
        args[1] = self._localize(args[1])

        return f(*args, **kwargs)

    return inner

# ---------- end decorators ---------- #


# ---------- exceptions ---------- #


class ArgumentError(ValueError):
    ''' Root class of all arguments that are thrown due to user input which
    violates a rule set by the parser. In other words, errors of this type
    should be caught and communicated to the user some how. The default
    behavior is to signal the particular error and show the `usage`.'''

    pass


class FormatError(ArgumentError):
    ''' Argument not formatted correctly. '''
    pass


class ConditionError(ArgumentError):
    ''' Condition not met. '''

    def __init__(self, argname, condition):
        self.argname = argname
        self.condition = condition

    def __str__(self):
        return '%s required unless %s' % (self.argname, self.condition)


class MissingRequiredArgumentError(ArgumentError):
    ''' Required argument not specified. '''

    def __init__(self, arg):
        if isinstance(arg, Option):
            arg = arg.argname

        super(MissingRequiredArgumentError, self).__init__(
                'No value passed for %s' % arg)


class ManyAllowedNoneSpecifiedArgumentError(ArgumentError):
    ''' An argument out of a list of required is missing.
    e.g., one of -a and -b is required and neither is specified. '''

    def __init__(self, allowed):
        super(ManyAllowedNoneSpecifiedArgumentError, self).__init__(('[%s] not'
                + ' specified') % ', '.join(map(str, allowed)))


class UnspecifiedArgumentError(ArgumentError):
    ''' User supplies argument that isn't specified. '''

    pass


class MultipleSpecifiedArgumentError(ArgumentError):
    ''' Multiple of the same argument specified. '''
    pass


class DependencyError(ArgumentError):
    ''' User specified an argument that requires another, unspecified argument.
    '''

    pass


class ConflictError(ArgumentError):
    ''' User specified an argument that conflicts another specified argument.
    '''

    def __init__(self, offender1, offender2):
        super(ConflictError, self).__init__('%s conflicts with %s' %
                (offender1, offender2))


class FailedConditionError(ArgumentError):
    ''' Condition failed. '''
    pass


class MissingValueError(ArgumentError):
    ''' Argument flag specified without value. '''
    pass


class InvalidEnumValueError(ArgumentError):
    ''' Enum value provided not allowed. '''
    pass

# ---------- end exceptions ---------- #


class Condition(object):
    def __init__(self):
        self._other_conditions = []
        self._and = True
        self._neg = False

    def __neg__(self):
        self._neg = True
        return self

    def _inner_satisfied(self, parsed):
        raise NotImplementedError

    def and_(self, condition):
        if not self._and:
            raise ValueError('and/or both specified')

        self._other_conditions.append(condition)
        return self

    def or_(self, condition):
        self._other_conditions.append(condition)
        self._and = False
        return self

    def _is_satisfied(self, parsed):
        def _inner():
            for n in self._other_conditions:
                if not n._is_satisfied(parsed):
                    if self._and:
                        return False
                elif not self._and:
                    return True

            return self._inner_satisfied(parsed)

        result = _inner()
        if self._neg:
            result = not result
        return result


class CallableCondition(Condition):
    def __init__(self, call, main, other):
        super(CallableCondition, self).__init__()
        self._call = call
        self._main = main
        self._other = other

    def _inner_satisfied(self, parsed):
        newargs = []
        for arg in (self._main, self._other):
            if isinstance(arg, Option):
                newargs.append(parsed.get(arg.argname))
            else:
                newargs.append(arg)

        return self._call(*newargs)

    def __repr__(self):
        x = self._main.argname

        names = {operator.le: '<=',
                 operator.lt: '<',
                 operator.gt: '>',
                 operator.ge: '>=',
                 operator.eq: '==',
                 operator.ne: '!='}

        x += ' ' + names[self._call] + ' ' + str(self._other)
        return x


class Option(Condition):
    def __init__(self, argname, parser):
        ''' Do not construct directly, as it will not be tethered to a
        :class:`Parser` object and thereby will not be handled in argument
        parsing. '''

        super(Option, self).__init__()

        self.argname = argname
        self._parser = parser
        self._conditions = []

    def requires(self, *others):
        ''' Specifiy other options which this argument requires.

        :param others: required options
        :type others: sequence of either :class:`Option` or basestring of \
                    option names
        '''
        [self._parser._set_requires(self.argname, x) for x in others]
        return self

    def condition(self, func):
        self._conditions.append(func)
        return self

    def conflicts(self, *others):
        ''' Specifiy other options which this argument conflicts with.

        :param others: conflicting options
        :type others: sequence of either :class:`Option` or basestring of \
            option names
        '''
        [self._parser._set_conflicts(self.argname, x) for x in others]
        return self

    def shorthand(self, alias):
        ''' Set shorthand for this argument. Shorthand arguments are 1
        character in length and are prefixed by a single '-'. For example:

        >>> parser.str('option').shorthand('o')

        would cause '--option' and '-o' to be alias argument labels when
        invoked on the command line.

        :param alias: alias of argument
        '''

        self._parser._add_shorthand(self.argname, alias)
        return self

    def default(self, value):
        ''' Provide a default value for this argument. '''
        self._parser._set_default(self.argname, value)
        return self

    def cast(self, cast):
        ''' Provide a casting value for this argument. '''
        self._parser._casts[self.argname] = cast
        return self

    def required(self):
        ''' Indicate that this argument is required. '''

        self._parser._set_required(self.argname)
        return self

    def if_(self, *replacements):
        self._parser._set_required(self.argname, [-x for x in replacements])
        return self

    def unless(self, *replacements):
        ''' Argument is required unless replacements specified. '''

        self._parser._set_required(self.argname, replacements)
        return self

    def unspecified_default(self):
        ''' Indicate that values passed without argument labels will be
        attributed to this argument. '''

        self._parser._set_unspecified_default(self.argname)
        return self

    def multiple(self):
        ''' Indicate that the argument can be specified multiple times. '''
        self._parser._set_multiple(self.argname)
        return self

    def _inner_satisfied(self, parsed):
        return self.argname in parsed

    def _make_condition(self, func, other):
        return CallableCondition(func, self, other)

    def __le__(self, other):
        return self._make_condition(operator.__le__, other)

    def __lt__(self, other):
        return self._make_condition(operator.__lt__, other)

    def __gt__(self, other):
        return self._make_condition(operator.__gt__, other)

    def __ge__(self, other):
        return self._make_condition(operator.__ge__, other)

    def __eq__(self, other):
        return self._make_condition(operator.__eq__, other)

    def __ne__(self, other):
        return self._make_condition(operator.__ne__, other)


# ---------- Argument readers ---------- #

# Argument readers help parse the command line. The flow is as follows:
#
# 1) We create a reader for each argument based on the type specified by the
#    programmer (e.g., a bool will get a _FlagArgumentReader
#
# 2) The reader is used when we hit the argument label


class _ArgumentReader(object):
    def __init__(self, parent):
        self.value = None
        self.parent = parent
        self._init()

    def consume_or_skip(self, arg):
        raise NotImplementedError()

    def _init(self):
        raise NotImplementedError()

    @classmethod
    def default(cls):
        return None


class _MultiWordArgumentReader(_ArgumentReader):
    def _init(self):
        self.value = []

    def consume_or_skip(self, arg):
        if self.parent._is_argument_label(arg):
            return False

        self.value.append(arg)
        return True

    def get(self):
        return ' '.join(self.value)


class _FlagArgumentReader(_ArgumentReader):
    def _init(self):
        self.value = True

    def consume_or_skip(self, arg):
        return False

    def get(self):
        return self.value

    @classmethod
    def default(cls):
        return False


class _SingleWordReader(_ArgumentReader):
    def _init(self):
        self.value = None

    def consume_or_skip(self, arg):
        if self.value is not None:
            return False

        self.value = arg
        return True

    def get(self):
        if self.value is None:
            raise MissingValueError
        return self.value


# ---------- Argument readers ---------- #


class Group(Option):
    def __init__(self, parser, *names):
        self._parser = parser
#        super(Group, self).__init__('group', parser)
        self._names = names
        self.argname = self

    def default(self, name):
        if name not in self._names:
            raise ValueError('%s not in group' % name)

        self._default = name
        return self

    def _is_satisfied(self, parsed):
        for item in self._names:
            if item._is_satisfied(parsed):
                return True
        return False


class Parser(object):
    ''' Command line parser. '''

    def __init__(self, store=None, default_help=True):
        self._options = {}
        self._readers = {}
        self._option_labels = {}
        self._multiple = set()
        self._casts = {}
        self._defaults = {}
        self._extras = []
        self._unspecified_default = None
        self.require_n = {}

        # dict of A (required) -> args that could replace A if A is not
        # specified
        self._required = {}

        # dict of A -> args that A depends on
        self._requires = {}

        # dict of A -> args that A conflicts with
        self._conflicts = {}
        self._alias = {}

        # convert arg labels to understore in value dict
        self._to_underscore = False

        # prefix to shorthand args
        self._single_prefix = '-'

        # prefix to fullname args
        self._double_prefix = '--'

        # help message
        self._help_prefix = None

        # set by user
        self._init_user_set(store)

        if default_help:
            self.flag('help').shorthand('h')

    def _init_user_set(self, store=None):
        self._preparsed = {}
        if store is None:
            store = {}
        self._store = store
        self._namemaps = {}
        self._rnamemaps = {}

    def set_help_prefix(self, message):
        ''' Indicate text to appear before argument list when the ``help``
        function is triggered. '''

        self._help_prefix = message
        return self

    def underscore(self):
        ''' Convert '-' to '_' in argument names. This is enabled if
        ``with_locals`` is used, as variable naming rules are applied. '''

        self._to_underscore = True
        return self

    def set_single_prefix(self, flag):
        ''' Set the single flag prefix. This appears before short arguments
        (e.g., -a). '''

        if self._double_prefix in flag:
            raise ValueError('single_flag cannot be superset of double_flag')
        self._single_prefix = flag
        return self

    def set_double_prefix(self, flag):
        ''' Set the double flag prefix. This appears before long arguments
        (e.g., --arg). '''

        if flag in self._single_prefix:
            raise ValueError('single_flag cannot be superset of double_flag')

        self._double_prefix = flag
        return self

    def use_aliases(self):
        raise NotImplementedError

    @classmethod
    def with_locals(cls):
        ''' Create :class:`Parser` using locals() dict. '''

        import inspect
        vals = inspect.currentframe().f_back.f_locals
        return Parser(vals).underscore()

    def _to_flag(self, name):
        name = self._unlocalize(name)

        if len(name) == 1:
            return self._single_prefix + name
        else:
            return self._double_prefix + name

# --- types --- #

    def config(self, name):
        return self._add_option(name).cast(Config)

    def int(self, name):
        ''' Add integer argument. '''
        return self._add_option(name).cast(int)

    def float(self, name):
        ''' Add float argument. '''

        return self._add_option(name).cast(float)

#    def enum(self, name, values):
#        ''' Add enum type. '''
#
#        def inner(value):
#            if not value in values:
#                raise InvalidEnumValueError()
#            return value
#
#        return self._add_option(name).cast(inner)

    def str(self, name):
        ''' Add :py:class:`str` argument. '''
        return self._add_option(name)

    def range(self, name):
        ''' Range type. Accepts similar values to that of python's py:`range`
            and py:`xrange`. Accepted delimiters are space, -, and :.

            >>> with Parser() as p:
            ...   p.range('values')

            Now accepts:

            ::

              python test.py --values 10  # -> xrange(10)
              python test.py --values 0-1  # -> xrange(0, 1)
              python test.py --values 0:10:2  # -> xrange(0, 10, 2)
              python test.py --values 0 10 3  # -> xrange(0, 10, 3)
        '''

        def caster(x):
            def raise_error():
                raise FormatError(('%s is not range format: N:N+i, N-N+i, or N'
                        + ' N+i') % x)

            splitter = None
            for char in (' :-'):
                if char in x:
                    splitter = char
                    break

            if splitter:
                toks = x.split(splitter)
            else:
                toks = [x]

            if not (1 <= len(toks) <= 3):
                raise_error()
            try:
                return xrange(*[int(y) for y in toks])
            except ValueError:
                raise_error()

        result = self._add_option(name).cast(caster)
        self._set_reader(name, _MultiWordArgumentReader)
        return result

    def multiword(self, name):
        ''' Accepts multiple terms as an argument. For example:

            >>> with Parser() as p:
            ...   p.multiword('multi')

            Now accepts:

            ::

               python test.py --multi path to something

        '''

        result = self._add_option(name)
        self._set_reader(name, _MultiWordArgumentReader)
        return result

    def bool(self, name):
        ''' Alias of :func:`flag`. '''

        return self.flag(name)

    def flag(self, name):
        ''' Boolean value. The presence of this flag indicates a true value,
        while an absence indicates false. No arguments. '''

        result = self._add_option(name)
        self._set_reader(name, _FlagArgumentReader)
        return result

# --- aggregate calls --- #

    def at_least_one(self, *args):
        ''' Require at least one of ``args``. '''

        return self._require_at_least_one(*args)

    def require_one(self, *args):
        ''' Require only and only one of ``args``. '''

        self._set_one_required(*args)
        return Group(self, *args)

    def all_if_any(self, *args):
        ''' If *any* of ``args`` is specified, then all of ``args`` must be
        specified. '''

        list(starmap(self._set_requires, permutations(args, 2)))
        return Group(self, *args)

    def only_one_if_any(self, *args):
        ''' If *any* of ``args`` is specified, then none of the remaining
        ``args`` may be specified.'''

        list(starmap(self._set_conflicts, permutations(args, 2)))
        return Group(self, *args)

    def __getitem__(self, name):
        return Option(name, self)

# --- private --- #

    def _require_at_least_one(self, *names):
        ''' At least one of the arguments is required. '''

        s = set(names)
        for v in s:
            self._set_required(v, s - set([v]))

        return Group(self, *names)

    @localize
    def _set_unspecified_default(self, name):
        if self._unspecified_default is not None:
            raise ValueError('Trying to specify multiple unspecified defaults')

        self._unspecified_default = name

    @localize
    @_verify_args_exist
    @_names_to_options
    def _set_required(self, arg, replacements=None):
        newreplacements = []
        for item in replacements or []:
            if not isinstance(item, (Option, Condition)):
                item = self._options[item]
            newreplacements.append(item)

        self._required.setdefault(arg, []).extend(newreplacements)

    @localize
    def _set_reader(self, name, option):
        self._readers[name] = option

    def _add_shorthand(self, source, alias):
        if source not in self._readers:
            raise ValueError('%s not an option' % source)
        if alias in self._alias:
            raise ValueError('{0} already shorthand for {1}'.format(alias,
                self._alias[alias]))

        self._alias[alias] = source

    def _add_option(self, name, argument_label=None):
        name = self._localize(name)

        if name in self._readers:
            raise ValueError('multiple types specified for %s' % name)

        self._readers[name] = _SingleWordReader

        if argument_label is not None:
            self._option_labels[name] = argument_label

        o = Option(name, self)
        self._options[name] = o
        return o

    def _getoption(self, option):
        o = self._readers.get(option, None)
        if o is not None:
            return option, o

        source = self._alias.get(option, None)
        if source is None:
            return option, None

        return source, self._readers.get(source, None)

    def _localize(self, key):
        if self._to_underscore:
            modified = key.replace('-', '_')
            self._rnamemaps.setdefault(modified, key)
            return self._namemaps.setdefault(key, modified)
        return key

    def _unlocalize(self, key):
        v = self._rnamemaps.get(key, None)
        if v is None:
            # already unlocalized(?)
            return key
        return v

    def _parse(self, args):
        new_args = []
        for arg in args:
            if '=' in arg:
                new_args += arg.split('=')
            else:
                new_args.append(arg)

        return new_args

    def _is_argument_label(self, arg):
        return (arg.startswith(self._single_prefix) or
                arg.startswith(self._double_prefix))

    def _read(self, args):
        argument_value = None

        for arg in args:
            if argument_value is not None:
                if argument_value.consume_or_skip(arg):
                    continue
                argument_value = None

            argument_name = None

            if self._is_argument_label(arg):
                if arg.startswith(self._double_prefix):
                    prefix = self._double_prefix
                else:
                    prefix = self._single_prefix

                arg = arg[len(prefix):]

                argument_name = self._localize(arg)

                argument_name, argument_value = self._getoption(argument_name)
                if argument_value is None:
                    raise UnspecifiedArgumentError(argument_name)
                argument_value = argument_value(self)
            elif self._unspecified_default is not None:
                argument_name = self._unspecified_default

                # push value onto _SingleWordReader
                argument_value = _SingleWordReader(self)
                argument_value.consume_or_skip(arg)

            if argument_name:
                self._preparsed.setdefault(argument_name,
                        []).append(argument_value)
            else:
                self._extras.append(arg)

    def _help_if_necessary(self):
        if 'help' in self._preparsed:
            self.print_help()
            sys.exit(0)

    def _assign(self):
        parsed = {}
        for key, values in self._preparsed.iteritems():
            try:
                if key not in self._multiple:
                    value = values[0].get()
                else:
                    value = [v.get() for v in values]

                cast = self._casts.get(key)
                if cast:
                    try:
                        value = cast(value)
                    except FormatError:
                        raise
                    except ValueError:
                        raise FormatError('Cannot cast %s to %s', value, cast)

                parsed[key] = value
            except MissingValueError:
                raise MissingValueError('%s specified but missing given value'
                        % key)

        # check multiple

        for key, values in self._preparsed.iteritems():
            if len(values) > 1 and key not in self._multiple:
                raise MultipleSpecifiedArgumentError(('%s specified multiple'
                        + ' times') % self._to_flag(key))

        # check conditions
        for arg in parsed.iterkeys():
            for cond in self._options[arg]._conditions:
                if not cond(parsed):
                    raise FailedConditionError()

        for arg, replacements in self._required.iteritems():
            missing = []
            if not arg._is_satisfied(parsed):
                for v in replacements:
                    if isinstance(v, Group):
                        missing += v._names
                    elif not isinstance(v, Condition):
                        missing.append(v)

                    if v._is_satisfied(parsed):
                        break
                else:
                    if missing:
                        raise ManyAllowedNoneSpecifiedArgumentError([arg] +
                                missing)
                    else:
                        raise MissingRequiredArgumentError(arg)

        for arg, deps in self._requires.iteritems():
            if arg._is_satisfied(parsed):
                for v in deps:
                    if not v._is_satisfied(parsed):
                        if isinstance(v, CallableCondition):
                            raise ConditionError(arg.argname, v)
                        raise DependencyError(v)

        for arg, conflicts in self._conflicts.iteritems():
            if arg._is_satisfied(parsed):
                for conflict in conflicts:
                    if conflict._is_satisfied(parsed):
                        raise ConflictError(arg.argname, conflict.argname)

        for key, value in parsed.iteritems():
            self._set_final(key, value)

        for key, value in self._readers.iteritems():
            if key in self._defaults:
                self._set_final(key, self._defaults[key])
            else:
                self._set_final(key, value.default())

    @_options_to_names
    def _set_one_required(self, *names):
        self.only_one_if_any(*names)
        self._require_at_least_one(*names)

    def _get_args(self, args):
        if args is None:
            args = sys.argv[1:]

        if not isinstance(args, list):
            raise TypeError('%s not list' % args)

        return args

    def _process_command_line(self, args=None):
        try:
            args = self._get_args(args)
            args = self._parse(args)
            self._read(args)
            self._help_if_necessary()

            self._assign()
            store = self._store
        except ArgumentError as e:
            raise e
        finally:
            self._init_user_set()  # reset

        return store

    def process_command_line(self, args=None):
        try:
            return self._process_command_line(args)
        except ArgumentError as e:
            self.bail(e)

    def bail(self, e):
        msg = []
        if isinstance(e, UnspecifiedArgumentError):
            msg.append('illegal option --%s' % e)
        else:
            msg.append(str(e))
        msg.append('usage: %s' % sys.argv[0])
        msg.append(' '.join('[%s]' % self._label(key) for key in self._readers))
        print('\n'.join(msg))
        sys.exit(1)

    def _set_final(self, key, value):
        if key not in self._store:
            self._store[key] = value

    @localize
    @_options_to_names
    def _set_multiple(self, name):
        self._multiple.add(name)

    @localize
    @_options_to_names
    def _set_default(self, name, value):
        self._defaults[name] = value

    @_localize_all
    @_verify_args_exist
    @_names_to_options
    def _set_requires(self, a, b):
        self._requires.setdefault(a, []).append(b)

    @_localize_all
    @_verify_args_exist
    @_options_to_names
    def set_requires_n_of(self, a, n, *others):
        self.require_n[a] = (n, others)

    @_localize_all
    @_verify_args_exist
    @_names_to_options
    def _set_conflicts(self, a, b):
        self._conflicts.setdefault(a, []).append(b)

    def __enter__(self):
        return self

    def __exit__(self, a, b, c):
        self.process_command_line()

    def _option_label(self, name):
        return self._option_labels.get(name, 'option')

    def _label(self, name):
        pkey = self._to_flag(name)
        for k, v in self._alias.iteritems():
            if name in v:
                pkey += ',' + self._to_flag(k)

        value = self._readers[name]
        if value != _FlagArgumentReader:
            pkey = '%s <%s>' % (pkey, self._option_label(name))

        return pkey

    def print_help(self):
        if self._help_prefix:
            print(self._help_prefix)

        print('Arguments:')
        column_width = -1
        for key in self._readers:
            column_width = max(column_width, len(self._label(key)))

        fmt = '   %-' + str(column_width) + 's'

        for key in self._readers:
            print(fmt % self._label(key))


class IOParser(Parser):
    def directory(self, name):
        ''' Adds a directory option, as :class:`io.Directory` object. Requires
        directory to exist or raises exception. '''

        from plyny.plio.files import Directory
        return self._add_option(name).cast(Directory)

    def file(self, name):
        ''' Adds a :class:`io.File` option. '''
        from plyny.plio.files import open_path
        return self._add_option(name).cast(open_path)

    def input_file(self, name):
        ''' Adds an input file option, as :class:`io.File` object. Requires
        file to exist or raises exception. '''

        from plyny.plio.files import open_path

        def opener(x):
            try:
                f = open_path(x, True)
#            f.set_locked(True)
            except Exception as e:
                print(e)
            return f

        result = self._add_option(name).cast(opener)
        self._set_reader(name, _MultiWordArgumentReader)
        return result

    def output_file(self, name, disable_overwrite=True):
        ''' Adds an output file option, as :class:`io.FileWriter` object.
        Prevents the overwriting of the file.  '''

        from plyny.plio.files import stdio, FileWriter

        name = self._localize(name)

        def opener(x):
            if x == '-':
                return stdio()
            else:
                return FileWriter(x, not disable_overwrite)

        return self._add_option(name).cast(opener)


__version__ = '0.2.12a'
