from functools import wraps
from itertools import starmap, permutations
import sys

# Todo:
#   replace config
#   * don't overwrite existing namespace (e.g., function name assumed to be value)
#   X fixed? * can't have multiple unspecified_default
#   * dependency language (e.g. a -> b or c)
#   * show relationships in -h
#   * make app (vs. existing) args more obvious
#   * editdist spell suggestions (e.g., ``did you mean X?")
#   * required mismatches with unspecified_default if arg is not made explicit
#   * error is --one-flag not specified even if multiple are allowed
#   * deal with difference between localized/non
#   * enumeration type


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

def options_to_names(f):
    ''' Convert any :class:`Option`s to names. '''

    @wraps(f)
    def inner(*args, **kwargs):
        new_args = []
        for arg in args[1:]:
            if isinstance(arg, Option):
                arg = arg.argname

            new_args.append(arg)

        return f(*[args[0]] + new_args, **kwargs)

    return inner


def verify_args_exist(f):
    @wraps(f)
    def inner(*args, **kwargs):
        def raise_error(name):
            raise ValueError('%s not known' % name)

        self = args[0]
        for arg in args[1:]:
            if isinstance(arg, basestring) and arg not in self.options:
                raise_error(arg)

        return f(*args, **kwargs)

    return inner


def localize_all(f):
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


class Multidict(dict):
    class _MyList(list):
        pass

    def __setitem__(self, key, value):
        v = self.get(key, None)
        if v is None:
            v = Multidict._MyList()
            super(Multidict, self).__setitem__(key, v)

        v.append(value)


# ---------- exceptions ---------- #


class ArgumentError(ValueError):
    ''' Passed to user. '''
    pass


class FormatError(ArgumentError):
    ''' Argument not formatted correctly. '''
    pass


class MissingRequiredArgumentError(ArgumentError):
    ''' Required argument not specified. '''
    pass


class ManyAllowedNoneSpecifiedArgumentError(ArgumentError):
    ''' An argument out of a list of required is missing.
    e.g., one of -a and -b is required and neither is specified. '''

    def __init__(self, allowed):
        super(ManyAllowedNoneSpecifiedArgumentError, self).__init__('[%s] not specified' % ', '.join(allowed))


class UnspecifiedArgumentError(ArgumentError):
    ''' User supplies argument that isn't specified. '''

    pass


class MultipleSpecifiedArgumentError(ArgumentError):
    ''' Multiple of the same argument specified. '''
    pass


class DependencyError(ArgumentError):
    ''' User specified an argument that requires another, unspecified argument. '''
    pass


class ConflictError(ArgumentError):
    ''' User specified an argument that conflicts another specified argument. '''
    pass

# ---------- end exceptions ---------- #


class Option(object):
    def __init__(self, argname, parser):
        ''' Do not construct directly, as it will not be tethered to a
        :class:`Parser` object and thereby will not be handled in argument
        parsing. '''

        self.argname = argname
        self.parser = parser

    def requires(self, *others):
        ''' Specifiy other options which this argument requires.

        :param others: required options
        :type others: sequence of either :class:`Option` or basestring of option names
        '''
        [self.parser._set_requires(self.argname, x) for x in others]
        return self

    def conflicts(self, *others):
        ''' Specifiy other options which this argument conflicts with.

        :param others: conflicting options
        :type others: sequence of either :class:`Option` or basestring of option names
        '''
        [self.parser._set_conflicts(self.argname, x) for x in others]
        return self

    def shorthand(self, alias):
        ''' Set shorthand for this argument. Shorthand arguments are 1
        character in length and are prefixed by a single '-'. For example:

        >>> parser.str('option').shorthand('o')

        would cause '--option' and '-o' to be alias argument labels when invoked on the command line.

        :param alias: alias of argument
        '''

        self.parser._add_shorthand(self.argname, alias)
        return self

    def default(self, value):
        ''' Provide a default value for this argument. '''
        self.parser._set_default(self.argname, value)
        return self

    def cast(self, cast):
        ''' Provide a casting value for this argument. '''
        self.parser._casts[self.argname] = cast
        return self

    def required(self):
        ''' Indicate that this argument is required. '''

        self.parser._set_required(self.argname)
        return self

    def unspecified_default(self):
        ''' Indicate that values passed without argument labels will be
        attributed to this argument. '''

        self.parser._set_unspecified_default(self.argname)
        return self

    def multiple(self):
        ''' Indicate that the argument can be specified multiple times. '''
        self.parser._set_multiple(self.argname)

# ---------- Argument readers ---------- #


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
            raise ValueError('no value passed')
        return self.value


# ---------- Argument readers ---------- #


class Parser(object):
    ''' Command line parser. '''

    def __init__(self, store=None, default_help=True):
        self.options = {}
        self.option_labels = {}
        self._required = {}
        self.multiple = set()
        self._casts = {}
        self.defaults = {}
        self.extras = []
        self._unspecified_default = None
        self.requires = Multidict()
        self.require_n = {}
        self.conflicts = Multidict()
        self.alias = {}

        self._to_underscore = False
        self._single_flag = '-'
        self._double_flag = '--'

        # set by user
        self._init_user_set(store)

        if default_help:
            self.flag('help').shorthand('h')

    def underscore(self):
        self._to_underscore = True
        return self

    def single_flag(self, flag):
        ''' Set the single flag prefix. This appears before short arguments
        (e.g., -a). '''

        self._single_flag = flag
        return self

    def double_flag(self, flag):
        ''' Set the double flag prefix. This appears before long arguments
        (e.g., --arg). '''

        self._double_flag = flag
        return self

    def _init_user_set(self, store=None):
        self.user_values = Multidict()
        self.specified = {}
        if store is None:
            store = {}
        self.store = store
        self._namemaps = {}
        self._rnamemaps = {}

    @classmethod
    def with_locals(cls):
        ''' Create :class:`Parser` using locals() dict. '''

        import inspect
        vals = inspect.currentframe().f_back.f_locals
        return Parser(vals).underscore()

    def _to_flag(self, name):
        name = self._unlocalize(name)

        if len(name) == 1:
            return self._single_flag + name
        else:
            return self._double_flag + name

    @options_to_names
    def require_all_if_any(self, *names):
        ''' All arguments require each other; i.e., if any is specified, then
        all must be specified. '''

        s = set(names)
        for v in s:
            for vi in s:
                if v == vi:
                    continue

                self._set_requires(v, vi)

    @options_to_names
    def require_at_least_one(self, *names):
        ''' At least one of the arguments is required. '''

        s = set(names)
        for v in s:
            self._set_required(v, s - set([v]))

    @localize
    def _set_unspecified_default(self, name):
        if self._unspecified_default is not None:
            raise ValueError('Trying to specify multiple unspecified defaults')

        self._unspecified_default = name

    @localize
    @options_to_names
    def _set_required(self, name, replacements=None):
        if replacements is None:
            replacements = []
        self._required[name] = replacements

    def config(self, name):
        return self._add_option(name).cast(Config)

    def int(self, name):
        ''' Add integer argument. '''
        return self._add_option(name).cast(int)

    def float(self, name):
        ''' Add float argument. '''
        return self._add_option(name).cast(float)

    def str(self, name):
        ''' Add :py:class:`str` argument. '''
        return self._add_option(name)

    def range(self, name):
        def caster(x):
            def raise_error():
                raise FormatError('%s is not range format: N:N+i, N-N+i, or N N+i' % x)

            for char in (' :-'):
                if char in x:
                    splitter = char
                    break
            else:
                raise_error()

            toks = x.split(splitter)
            if not (2 <= len(toks) <= 3):
                raise_error()
            try:
                return xrange(*(int(y) for y in toks))
            except ValueError:
                raise_error()

        self._add_option(name).cast(caster)
        self._set_option(name, _MultiWordArgumentReader)

    def __getitem__(self, name):
        return Option(name, self)

    @localize
    def _set_option(self, name, option):
        self.options[name] = option

    def multiword(self, name):
        ''' Accepts multiple terms as an argument. For example:
              python test.py --multi path to something

        '''

        result = self._add_option(name)
        self._set_option(name, _MultiWordArgumentReader)
        return result

    def bool(self, name):
        ''' Alias of :func:`flag`. '''

        return self.flag(name)

    def flag(self, name):
        ''' Boolean value. The presence of this flag indicates a true value,
        while an absence indicates false. No arguments. '''

        result = self._add_option(name)
        self._set_option(name, _FlagArgumentReader)
        return result

    def _add_shorthand(self, source, alias):
        if source not in self.options:
            raise ValueError('%s not an option' % source)
        if alias in self.alias:
            raise ValueError('{0} already shorthand for {1}'.format(alias, self.alias[alias]))
        self.alias[alias] = source

    def _add_option(self, name, argument_label=None):

        name = self._localize(name)

        if name in self.options:
            raise ValueError('multiple types specified for %s' % name)

        self.options[name] = _SingleWordReader

        if argument_label is not None:
            self.option_labels[name] = argument_label

        return Option(name, self)

    def _getoption(self, option):
        o = self.options.get(option, None)
        if o is not None:
            return option, o

        source = self.alias.get(option, None)
        if source is None:
            return option, None

        return source, self.options.get(source, None)

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
        return (arg.startswith(self._single_flag) or
                arg.startswith(self._double_flag))

    def _read(self, args):
        argument_value = None

        for arg in args:
            if argument_value is not None:
                if argument_value.consume_or_skip(arg):
                    continue
                argument_value = None

            argument_name = None

            if self._is_argument_label(arg):
                if arg.startswith(self._double_flag):
                    prefix = self._double_flag
                else:
                    prefix = self._single_flag

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
                self.user_values[argument_name] = argument_value
            else:
                self.extras.append(arg)

    def _help_if_necessary(self):
        if 'help' in self.user_values:
            self.print_help()
            sys.exit(0)

    def _find_duplicates(self):
        for key, values in self.user_values.iteritems():
            if len(values) > 1 and key not in self.multiple:
                raise MultipleSpecifiedArgumentError('%s specified multiple times' %
                        self._to_flag(key))

    def _find_requirements(self):
        for key, values in self.user_values.iteritems():
            for r in self.requires.get(key, []):
                if self._localize(r) not in self.user_values:
                    raise DependencyError('%s requires %s' %
                            (self._to_flag(key), self._to_flag(r)))

            reqs = self.require_n.get(key)
            if reqs is None:
                continue

            need_to_satisfy = reqs[0]

            for r in reqs[1]:
                if self._localize(r) in self.user_values:
                    need_to_satisfy -= 1

            if need_to_satisfy > 0:
                raise DependencyError('%s requires one of (%s)' %
                    (self._to_flag(r), ', '.join((self._to_flag(x) for x in
                        reqs[1]))))

    def _find_conflicts(self):
        for key, values in self.user_values.iteritems():
            for r in self.conflicts.get(key, []):
                if r in self.user_values:
                    raise ConflictError('%s conflicts with %s' %
                            (self._to_flag(key),
                             self._to_flag(r)))


    def _validate_entries(self):
        self._find_duplicates()
        self._find_requirements()
        self._find_conflicts()

    def _assign(self):
        for key, values in self.user_values.iteritems():
            try:
                if key not in self.multiple:
                    self._set_specified(key, values[0].get())
                else:
                    self._set_specified(key, [v.get() for v in values])
            except ValueError:
                raise MissingRequiredArgumentError('No value passed for %s' %
                        self._unlocalize(key))

        for key, value in self.options.iteritems():
            if key not in self.specified:
                res = self._required.get(key, None)
                if res is not None:
                    if len(res) == 0:
                        raise MissingRequiredArgumentError('No value passed for'
                                + ' %s' % self._unlocalize(key))

                    for result in res:
                        if result in self.specified:
                            break
                    else:
                        raise ManyAllowedNoneSpecifiedArgumentError(
                                [self._to_flag(x) for x in [key] + list(res)])

#                else: raise MissingRequiredArgumentError('No value passed for
#                %s' % key)

        for key, value in self.specified.iteritems():
            self._set_final(key, value)

        for key, value in self.options.iteritems():
            if key in self.defaults:
                self._set_final(key, self.defaults[key])
            else:
                self._set_final(key, value.default())

    @options_to_names
    def set_one_required(self, *names):
        self.mutually_exclude(*names)
        self.require_at_least_one(*names)

    def require_one(self, *names):
        self.set_one_required(*names)

    @options_to_names
    def all_require(self, required, *names):
        [self._set_requires(name, required) for name in names]

    @options_to_names
    def mutually_require(self, *names):
        list(starmap(self._set_requires, permutations(names, 2)))

    @options_to_names
    def mutually_exclude(self, *names):
        list(starmap(self._set_conflicts, permutations(names, 2)))

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
            self._validate_entries()
            self._assign()
            store = self.store
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
        if isinstance(e, UnspecifiedArgumentError):
            print 'illegal option --', e
        else:
            print e
        print 'usage: %s' % sys.argv[0],
        for key in self.options:
            print '[%s]' % self._label(key),

        print
        sys.exit(1)

    def _set_specified(self, key, value):
        self.specified[key] = value

    def _set_final(self, key, value):
        if key not in self.store:
            cast = self._casts.get(key, None)
            if cast and value is not None:
                if cast == Config:
                    Config(value, self.store, overwrite=False)
                else:
                    try:
                        value = cast(value)
                    except FormatError:
                        raise
                    except ValueError:
                        raise FormatError('Cannot cast %s to %s', value, cast)

            self.store[key] = value

    @localize
    @options_to_names
    def _set_multiple(self, name):
        self.multiple.add(name)

    @localize
    @options_to_names
    def _set_default(self, name, value):
        self.defaults[name] = value

    @localize_all
    @verify_args_exist
    @options_to_names
    def _set_requires(self, a, b):
        self.requires[a] = b

    @localize_all
    @verify_args_exist
    @options_to_names
    def set_requires_n_of(self, a, n, *others):
        self.require_n[a] = (n, others)

    @localize_all
    @verify_args_exist
    @options_to_names
    def _set_conflicts(self, a, b):
        self.conflicts[a] = b

    def __enter__(self):
        return self

    def __exit__(self, a, b, c):
        self.process_command_line()

    def _option_label(self, name):
        return self.option_labels.get(name, 'option')

    def _label(self, name):
        pkey = self._to_flag(name)
        for k, v in self.alias.iteritems():
            if name in v:
                pkey += ',' + self._to_flag(k)

        value = self.options[name]
        if value != _FlagArgumentReader:
            pkey = '%s <%s>' % (pkey, self._option_label(name))

        return pkey

    def print_help(self):
        print 'Arguments:'
        column_width = -1
        for key in self.options:
            column_width = max(column_width, len(self._label(key)))

        fmt = '   %-' + str(column_width) + 's'

        for key in self.options:
            print fmt % self._label(key)


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
            f = open_path(x, True)
            f.set_locked(True)
            return f

        result = self._add_option(name).cast(opener)
        self._set_option(name, _MultiWordArgumentReader)
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
