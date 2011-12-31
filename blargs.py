from itertools import starmap, permutations
import sys

# Todo:
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


def get_arguments_from_proxy(f):
    def inner(*args, **kwargs):
        self = args[0]
        new_args = []
        for arg in args[1:]:
            if isinstance(arg, ProxySetter):
                arg = arg.argname

            new_args.append(arg)

        return f(*[args[0]] + new_args, **kwargs)

    return inner


def verify_args_exist(f):
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
    def inner(*args, **kwargs):
        args = list(args)
        self = args[0]
#        args[1:] = [self._localize(x) for x in args[1]]
        args[1] = self._localize(args[1])

        return f(*args, **kwargs)

    return inner


def user_print(fmt, args):
    print fmt % args


class Multidict(dict):
    class _MyList(list):
        pass

    def __setitem__(self, key, value):
        v = self.get(key, None)
        if v is None:
            v = Multidict._MyList()
            super(Multidict, self).__setitem__(key, v)

        v.append(value)


class ArgumentError(ValueError):
    """ Passed to user. """
    pass


class FormatError(ArgumentError):
    pass


class MissingRequiredArgumentError(ArgumentError):
    pass


class ManyAllowedNoneSpecifiedArgumentError(ArgumentError):
    """ An argument out of a list of required is missing.
    e.g., one of -a and -b is required and neither is specified. """

    def __init__(self, allowed):
        super(ManyAllowedNoneSpecifiedArgumentError, self).__init__('[%s] not specified' % ', '.join(allowed))


class UnspecifiedArgumentError(ArgumentError):
    """ User supplies argument that isn't specified. """

    pass


class MultipleSpecifiedArgumentError(ArgumentError):
    pass


class DependencyError(ArgumentError):
    pass


class ConflictError(ArgumentError):
    pass


class ProxySetter(object):
    def __init__(self, argname, parser):
        self.argname = argname
        self.parser = parser

    def requires(self, *others):
        [self.parser.set_requires(self.argname, x) for x in others]
        return self

    def conflicts(self, *others):
        [self.parser.set_conflicts(self.argname, x) for x in others]
        return self


class Argument(object):
    def __init__(self):
        self.value = None
        self._init()

    def consume_or_skip(self, arg):
        raise NotImplementedError()

    def _init(self):
        raise NotImplementedError()

    @classmethod
    def default(cls):
        return None


class MultiWordArgument(Argument):
    def _init(self):
        self.value = []

    def consume_or_skip(self, arg):
        if arg.startswith('-'):
            return False
        self.value.append(arg)
        return True

    def get(self):
        return ' '.join(self.value)


class FlagArgument(Argument):
    def _init(self):
        self.value = True

    def consume_or_skip(self, arg):
        return False

    def get(self):
        return self.value

    @classmethod
    def default(cls):
        return False


class SingleWord(Argument):
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


class Parser(object):
    def __init__(self, store=None, to_underscore=False, default_help=True):
        # set by developer
        self.options = {}
        self.option_labels = {}
        self.required = {}
        self.multiple = set()
        self.casts = {}
        self.defaults = {}
        self.extras = []
        self._unspecified_default = None
        self.requires = Multidict()
        self.require_n = {}
        self.conflicts = Multidict()
        self.alias = {}
        self._to_underscore = to_underscore

        # set by user
        self._init_user_set(store)

        if default_help:
            self.add_flag('help', alias='h')

    def _init_user_set(self, store=None):
        self.user_values = Multidict()
        self.specified = {}
        if store is None:
            store = {}
        self.store = store
        self._namemaps = {}
        self._rnamemaps = {}

    @classmethod
    def _get_locals_dict(cls):
        # XXX need to get start frame, not just previous
        pass

    @classmethod
    def with_locals(cls):
        import inspect
        vals = inspect.currentframe().f_back.f_locals
#        p = Parser(cls._get_locals_dict())
        p = Parser(vals)
        p._to_underscore = True
        return p


    def _to_flag(self, name):
        name = self._unlocalize(name)

        if len(name) == 1:
            return '-' + name
        else:
            return '--' + name

    @get_arguments_from_proxy
    def set_mutually_required(self, *names):
        s = set(names)
        for v in s:
            for vi in s:
                if v == vi:
                    continue

                self.set_requires(v, vi)

    @get_arguments_from_proxy
    def set_at_least_one_required(self, *names):
        s = set(names)
        for v in s:
            self.set_required(v, s - set([v]))

    @localize
    def set_unspecified_default(self, name):
        if self._unspecified_default is not None:
            raise ValueError('Trying to specify multiple unspecified defaults')

        self._unspecified_default = name

    @localize
    @get_arguments_from_proxy
    def set_required(self, name, replacements=None):
        if replacements is None:
            replacements = []
        self.required[name] = replacements

    def add_config(self, name, **kwargs):
        return self.add_option(name, cast=Config, **kwargs)

    def add_float(self, name, **kwargs):
        return self.add_option(name, cast=float, **kwargs)

    def add_int(self, name, **kwargs):
        return self.add_option(name, cast=int, **kwargs)

    def add_range(self, name, **kwargs):
        def caster(x):
            def raise_error():
                raise FormatError('%s is not range format: N:N+i ' % x)

            toks = x.split(':')
            if len(toks) != 2:
                raise_error()
            try:
                return xrange(*(int(y) for y in toks))
            except ValueError:
                raise_error()

        return self.add_option(name, cast=caster, **kwargs)

    def add_directory(self, name, **kwargs):
        """ Adds a directory option, as :class:`io.Directory` object.  Requires
        directory to exist or raises exception. """

        from plyny.plio.files import Directory
        return self.add_option(name, cast=Directory, **kwargs)

    def add_input_file(self, name, **kwargs):
        """ Adds an input file option, as :class:`io.File` object.  Requires
        file to exist or raises exception. """

        from plyny.plio.files import open_path

        def opener(x):
            f = open_path(x, True)
            f.set_locked(True)
            return f

        result = self.add_option(name, cast=opener, **kwargs)
        self._set_option(name, MultiWordArgument)
        return result

    def add_output_file(self, name, disable_overwrite=True, **kwargs):
        """ Adds an output file option, as :class:`io.FileWriter` object.
        Prevents the overwriting of the file.  """

        from plyny.plio.files import stdio, FileWriter

        name = self._localize(name)

        def opener(x):
            if x == '-':
                return stdio()
            else:
                return FileWriter(x, not disable_overwrite)

        return self.add_option(name, cast=opener, **kwargs)

    def __getitem__(self, name):
        return ProxySetter(name, self)

    @localize
    def _set_option(self, name, option):
        self.options[name] = option

    def add_file(self, name, **kwargs):
        """ Adds a :class:`io.File` option. """
        from plyny.plio.files import open_path
        return self.add_option(name, cast=open_path, **kwargs)

    def add_multiword(self, name, **kwargs):
        result = self.add_option(name, **kwargs)
        self._set_option(name, MultiWordArgument)
        return result

    def add_flag(self, name, **kwargs):
        result = self.add_option(name, **kwargs)
        self._set_option(name, FlagArgument)
        return result

    def add_alias(self, source, alias):
        if source not in self.options:
            raise ValueError('%s not an option' % source)
        self.alias[alias] = source

    def add_option(self, name, alias=None, cast=None, default=None,
            argument_label=None, required=False, multiple=False,
            unspecified_default=False):

        name = self._localize(name)

        if name in self.options:
            raise ValueError('multiple types specified for %s' % name)

        self.options[name] = SingleWord

        if alias is not None:
            self.add_alias(name, alias)

        if cast is not None:
            self.casts[name] = cast

        if default is not None:
            self.set_default(name, default)

        if argument_label is not None:
            self.option_labels[name] = argument_label

        if required:
            self.set_required(name)

        if multiple:
            self.set_multiple(name)

        if unspecified_default:
            self.set_unspecified_default(name)

        return ProxySetter(name, self)

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

    def _read(self, args):
        argument_value = None

        for arg in args:
            if argument_value is not None:
                if argument_value.consume_or_skip(arg):
                    continue
                argument_value = None

            argument_name = None
            has_label = arg.startswith('-')

            if has_label:
                short_cut = len(arg) == 2

                if short_cut:
                    arg = arg[1:]
                else:
                    if not arg.startswith('--'):
                        raise UnspecifiedArgumentError(arg)
                    arg = arg[2:]

                argument_name = self._localize(arg)

                argument_name, argument_value = self._getoption(argument_name)
                if argument_value is None:
                    raise UnspecifiedArgumentError(argument_name)
                argument_value = argument_value()
            elif self._unspecified_default is not None:
                argument_name = self._unspecified_default

                # push value onto SingleWord
                argument_value = SingleWord()
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

    def _verify_requirements(self):
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
        self._verify_requirements()
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
                res = self.required.get(key, None)
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

    @get_arguments_from_proxy
    def set_one_required(self, *names):
        self.set_mutually_exclusive(*names)
        self.set_at_least_one_required(*names)

    @get_arguments_from_proxy
    def set_mutually_dependent(self, *names):
        list(starmap(self.set_requires, permutations(names, 2)))

    @get_arguments_from_proxy
    def set_mutually_exclusive(self, *names):
        list(starmap(self.set_conflicts, permutations(names, 2)))

    def _process_command_line(self, args=None):
        try:
            if args is None:
                args = sys.argv[1:]
            if not isinstance(args, list):
                raise TypeError('%s not list' % args)
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
            cast = self.casts.get(key, None)
            if cast and value is not None:
                if cast == Config:
                    Config(value, self.store, overwrite=False)
                else:
                    try:
                        value = cast(value)
                    except ValueError:
                        raise FormatError('Cannot cast %s to %s', value, cast)

            self.store[key] = value

    @localize
    @get_arguments_from_proxy
    def set_multiple(self, name):
        self.multiple.add(name)

    @localize
    @get_arguments_from_proxy
    def set_default(self, name, value):
        self.defaults[name] = value

    @localize_all
    @verify_args_exist
    @get_arguments_from_proxy
    def set_requires(self, a, b):
        self.requires[a] = b

    @localize_all
    @verify_args_exist
    @get_arguments_from_proxy
    def set_requires_n_of(self, a, n, *others):
        self.require_n[a] = (n, others)

    @localize_all
    @verify_args_exist
    @get_arguments_from_proxy
    def set_conflicts(self, a, b):
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
        if value != FlagArgument:
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


if __name__ == '__main__':
    d = {}

    sys.argv[1:] = ['-f']

    with Parser.with_locals() as p:
        p.add_option('a', 'alias', 'value')
        p.add_multiword('b')
        p.add_flag('c')
        p.add_flag('cubs-cub')
        p.add_option('d')
        p.set_requires('a', 'b')
        p.set_requires('a', 'c')
        p.set_conflicts('a', 'd')
        p.add_float('f')
        p.add_int('i')
        p.add_alias('f', 'float')
        p.set_required('f', ['a'])
#       p.print_help()
        p.set_mutually_exclusive('a', 'd')
        p.set_at_least_one_required('a', 'd')

#    print d
#    print a
