'''

    blargs command line parser
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Easy argument parsing with powerful dependency support.
    :copyright: (c) 2012 by Karl Gyllstrom
    :license: BSD (see LICENSE.txt)

'''


# XXX need to test multiple for 3+


from blargs import (Parser, Option, UnspecifiedArgumentError, ConflictError, ArgumentError,
                   DependencyError, MissingRequiredArgumentError,
                   FormatError, ConditionError,
                   MultipleSpecifiedArgumentError,
                   ManyAllowedNoneSpecifiedArgumentError,
                   MissingValueError, FailedConditionError,
                   FakeSystemExit)


import sys
import os
from itertools import permutations
import unittest


if sys.version_info[0] == 3:
    import functools
    reduce = functools.reduce
    xrange = range
    import io
    StringIO = io.StringIO
else:
    from StringIO import StringIO


def specify(*names):
    return reduce(list.__add__, (['--%s' % name, '3'] for name in names))


class FileBasedTestCase(unittest.TestCase):
    def setUp(self):
        from tempfile import mkdtemp
        self._dir = mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self._dir)

    def test_config(self):
        def create():
            p = Parser()
            p.config('a')
            return p

        self.assertRaises(IOError, create()._process_command_line, ['--a',
             'doesnotexist.cfg'])

        fname = os.path.join(self._dir, 'config.cfg')

        def write_config(**kw):
            delim = '='
            if 'delim' in kw:
                delim = kw['delim']
                del kw['delim']
            with open(fname, 'w') as w:
                w.write('[myconfig]\n# comment1\n; comment2\n' + '\n'.join(
                    ('%s %s %s' % (k, delim, v) for k, v in kw.items())))

        write_config(b=3, c='hello')

        vals = create()._process_command_line(['--a', fname])
        self.assertEqual(list(vals.keys()), ['help'])

        def create():
            p = Parser({})
            p.config('a')
            p.int('b')
            p.str('c')
            p.int('d')
            return p

        for delim in '=:':
            write_config(b=3, c='hello', d=5, delim=delim)
            try:
                vals = create()._process_command_line(['--a', fname])
            except MultipleSpecifiedArgumentError as e:
                print(e)
            self.assertEqual(vals['b'], 3)
            self.assertEqual(vals['c'], 'hello')
            self.assertEqual(vals['d'], 5)

        write_config(b=3, c='hello', d='what')
        self.assertRaises(FormatError, create()._process_command_line, ['--a', fname])

        # XXX may want subsequent line to eventually be true
#        vals = create()._process_command_line(['--a', fname, '--d', '4'])
        self.assertRaises(MultipleSpecifiedArgumentError,
                create()._process_command_line, (['--a', fname, '--d', '4']))

#         self.assertEqual(vals['b'], 3)
#         self.assertEqual(vals['c'], 'hello')
#         self.assertEqual(vals['d'], 4)

        self.assertRaises(MultipleSpecifiedArgumentError,
                create()._process_command_line, (['--a', fname, '--d', '4', '--c', 'sup',
                '--b', '1']))

#         self.assertEqual(vals['b'], 1)
#         self.assertEqual(vals['c'], 'sup')
#         self.assertEqual(vals['d'], 4)

        def create():
            p = Parser({})
            p.config('a').default(fname)
            p.int('b').requires(p.int('d'))
            p.str('c')
            return p

        write_config(b=3, c='sup')
        self.assertRaises(DependencyError, create()._process_command_line) # should pass because default
        self.assertRaises(DependencyError, create()._process_command_line, ['--a', fname])

        with open(fname, 'w') as w:
            w.write('''[myconfig]
b=9
[part]
b=3
''')

        p = Parser()
        p.config('a')
        p.int('b')
        self.assertRaises(MultipleSpecifiedArgumentError,
                p._process_command_line, ['--a', fname])

        p = Parser()
        p.config('a')
        p.int('b').multiple()
        vals = p._process_command_line(['--a', fname])
        self.assertEqual(sorted(vals['b']), [3, 9])

        write_config(b='hello world')
        p = Parser()
        p.config('a')
        p.multiword('b')
        vals = p._process_command_line(['--a', fname])
        self.assertEqual(vals['b'], 'hello world')

    def test_file(self):
        def create():
            p = Parser()
            p.file('a')
            return p

        self.assertRaises(MissingValueError, create()._process_command_line, ['--a'])
        self.assertRaises(IOError, create()._process_command_line, ['--a', 'aaa'])
        vals = create()._process_command_line(['--a', 'test.py'])
        with open('test.py') as f:
            self.assertEqual(vals['a'].read(), f.read())

        def create():
            p = Parser()
            p.file('a', mode='w')
            return p

        fname = os.path.join(self._dir, 'mytest')
        vals = create()._process_command_line(['--a', fname])
        f = vals['a']
        msg = 'aaaxxx'
        f.write(msg)
        f.close()

        with open(fname) as f:
            self.assertEqual(f.read(), msg)

    def test_directory(self):
        def create():
            p = Parser()
            p.directory('a')
            return p

        dirpath = os.path.join(self._dir, 'ok')
        self.assertRaises(IOError, create()._process_command_line, ['--a', dirpath])
        os.mkdir(dirpath)
        vals = create()._process_command_line(['--a', dirpath])
        self.assertEqual(vals['a'], dirpath)

        # fail when trying to indicate directory that is actually a file
        fname = os.path.join(self._dir, 'testfile')
        with open(fname, 'w') as f:
            f.write('mmm')
        self.assertRaises(IOError, create()._process_command_line, ['--a', fname])

        # create directory
        dirpath = os.path.join(self._dir, 'sub', 'leaf')
        p = create()
        p.directory('b', create=True)
        vals = p._process_command_line(['--b', dirpath])
        self.assertEqual(vals['b'], dirpath)


class MultiDictTestCase(unittest.TestCase):
    def test_multidict(self):
        from blargs import Multidict

        m = Multidict()
        self.assertRaises(KeyError, lambda x: x['x'], m)
        m['x'] = 'y'
        self.assertEqual(m['x'], 'y')
        m['x'] = 'z'
        self.assertEqual(m['x'], ['y', 'z'])


class TestCase(unittest.TestCase):
    def test_env(self):
        import os

        os.environ['PORT'] = 'yes'
        p = Parser()
        p.int('port').environment()

        self.assertRaises(FormatError, p._process_command_line)

        os.environ['PORT'] = '9999'

        for port in ('Port', 'pORt', 'port', 'PORT'):
            p = Parser()
            p.int(port).environment()
            vals = p._process_command_line()
            self.assertEqual(vals[port], 9999)

            vals = p._process_command_line(['--%s' % port, '2222'])
            self.assertEqual(vals[port], 2222)

    def test_error_printing(self):
        def create(strio):
            with Parser(locals()) as p:
                p._out = strio
                p._suppress_sys_exit = True
                p.require_one(
                    p.all_if_any(
                        p.int('a'),
                        p.int('b'),
                    ),
                    p.only_one_if_any(
                        p.int('c'),
                        p.int('d'),
                    )
                )
                p.int('x').required()
                p.str('yi').shorthand('y')
                p.float('z').multiple()
                p.range('e')

        s = StringIO()
        self.assertRaises(FakeSystemExit, create, s)
        self.assertEqual(s.getvalue(), '''Error: [--a, --b, --c, --d] not specified
usage: test.py
[--a <option>] [--yi/-y <option>] [--c <option>] [--b <option>] [--e <option>] [--help/-h <option>] [--x <option>] [--z <option>] [--d <option>]
'''.format(sys.argv[0]))

    def test_url(self):
        p = Parser()
        p.url('url').required()
        self.assertRaises(MissingRequiredArgumentError, p._process_command_line)
        vals = p._process_command_line(['--url', 'http://www.com'])

        p = Parser()
        p.url('url')
        self.assertRaises(FormatError, p._process_command_line, ['--url', '/www.com'])

    def test_non_arg_exception(self):
        def inner():
            with Parser() as p:
                p.flag()

        self.assertRaises(TypeError, inner)

    def test_requires_and_default(self):
        p = Parser()
        p.int('a').default(3)
        p.int('b').requires(p['a'])
        p._process_command_line(['--b', '5'])

    def test_complex1(self):
        def create():
            p = Parser()
            p.require_one(
                p.all_if_any(
                    p.int('a'),
                    p.int('b'),
                    p.int('c'),
                ),
                p.only_one_if_any(
                    p.int('d'),
                    p.int('e'),
                    p.int('f'),
                ),
            )

            return p

        self.assertRaises(ArgumentError, create()._process_command_line)
        create()._process_command_line(['--d', '3'])
        create()._process_command_line(['--e', '3'])
        create()._process_command_line(['--f', '3'])
        self.assertRaises(ConflictError, create()._process_command_line, ['--d', '3', '--e', '4'])

        self.assertRaises(DependencyError, create()._process_command_line, ['--a', '3'])
        self.assertRaises(DependencyError, create()._process_command_line, ['--b', '3'])
        self.assertRaises(DependencyError, create()._process_command_line, ['--c', '3'])

        create()._process_command_line(['--a', '3', '--b', '4', '--c', '5'])
        self.assertRaises(ConflictError, create()._process_command_line, ['--a', '3',
            '--b', '4', '--c', '5', '--d', '3'])

    def test_complex2(self):
        def create():
            p = Parser()
            p.require_one(
                p.all_if_any(
                    p.only_one_if_any(
                        p.int('a'),
                        p.int('b'),
                    ),
                    p.int('c'),
                ),
                p.only_one_if_any(
                    p.all_if_any(
                        p.int('d'),
                        p.int('e'),
                    ),
                    p.int('f'),
                ),
            )
            return p

        self.assertRaises(DependencyError, create()._process_command_line, specify('a'))
        self.assertRaises(DependencyError, create()._process_command_line, specify('b'))
        self.assertRaises(DependencyError, create()._process_command_line, specify('c'))
        self.assertRaises(ConflictError, create()._process_command_line, specify('a', 'b', 'c'))

        self.assertRaises(ArgumentError, create()._process_command_line)
        self.assertRaises(DependencyError, create()._process_command_line, specify('d'))
        create()._process_command_line(specify('d', 'e'))
        self.assertRaises(ConflictError, create()._process_command_line, specify('d', 'e', 'f'))
        create()._process_command_line(specify('f'))

        satisfies1 = (['a', 'c'], ['b', 'c'])
        satisfies2 = (['d', 'e'], ['f'])
        for s1 in satisfies1:
            create()._process_command_line(specify(*s1))
            for s2 in satisfies2:
                self.assertRaises(ConflictError, create()._process_command_line, specify(*s1 + s2))

        for s2 in satisfies2:
            create()._process_command_line(specify(*s1))

    def test_numeric_conditions(self):
        def create():
            p = Parser()
            a = p.float('a')
            p.int('b').unless(a < 20)
            return p

#        self.assertRaises(MissingRequiredArgumentError, create()._process_command_line, ['--a', '20'])
        create()._process_command_line(['--a', '19'])
        create()._process_command_line(['--a', '9'])
        create()._process_command_line(['--b', '3', '--a', '29'])

        def create2():
            p = create()
            p.int('c').unless(10 < p['a'])
            return p

        self.assertRaises(MissingRequiredArgumentError, create2()._process_command_line, ['--a', '20'])
        self.assertRaises(MissingRequiredArgumentError, create2()._process_command_line, ['--a', '9'])
        create2()._process_command_line(['--a', '19'])

        def create3():
            p = create2()
            p.int('d').unless(p['a'] == 19)
            return p

        self.assertRaises(MissingRequiredArgumentError, create3()._process_command_line, ['--a', '20'])
        self.assertRaises(MissingRequiredArgumentError, create3()._process_command_line, ['--a', '9'])
        create3()._process_command_line(['--a', '19'])

        def create4():
            p = create3()
            p.int('e').unless(p['a'] == p['d'])
            return p

        self.assertRaises(MissingRequiredArgumentError, create4()._process_command_line, ['--a', '19'])
        self.assertRaises(MissingRequiredArgumentError, create4()._process_command_line, ['--a', '19', '--d', '18'])
        create4()._process_command_line(['--a', '19', '--d', '19'])

        def create5():
            p = create4()
            p.int('f').unless(p['e'] != p['d'])
            return p

        self.assertRaises(MissingRequiredArgumentError,
                create5()._process_command_line, ['--a', '19'])

        self.assertRaises(MissingRequiredArgumentError,
                create5()._process_command_line, ['--a', '19', '--d', '18'])

        self.assertRaises(MissingRequiredArgumentError,
                create5()._process_command_line, ['--a', '19', '--d', '19', '--e',
                    '19'])

        create5()._process_command_line(['--a', '19', '--d', '19', '--e', '18'])

        p = Parser()
        a = p.float('a')
        b = p.float('b').requires(a < 10)
        self.assertRaises(ConditionError, p._process_command_line, ['--b',
            '3.9', '--a', '11'])

        def create():
            p = Parser()
            a = p.float('a')
            b = p.float('b').if_(a < 10)
            return p

        self.assertRaises(MissingRequiredArgumentError,
                create()._process_command_line, ['--a', '8'])

        create()._process_command_line(['--a', '11'])

    def test_conditions(self):
        p = Parser()
        a = p.float('a')
        b = p.float('b')
        c = p.float('c').requires(a.or_(b))
        self.assertRaises(DependencyError, p._process_command_line, ['--c', '9.2'])
        p._process_command_line(['--a', '11', '--c', '9.2'])
        p._process_command_line(['--b', '11', '--c', '9.2'])

        def create():
            p = Parser()
            a = p.float('a')
            b = p.float('b')
            c = p.float('c').if_(a.or_(b))
            return p

        create()._process_command_line(['--c', '9.2'])

        self.assertRaises(MissingRequiredArgumentError,
                create()._process_command_line, ['--a', '11'])

        create()._process_command_line(['--a', '11', '--c', '9.2'])
        self.assertRaises(MissingRequiredArgumentError,
                create()._process_command_line, ['--b', '11'])

        create()._process_command_line(['--b', '11', '--c', '9.2'])

    def test_compound(self):
        def create():
            p = Parser()
            a = p.float('a')
            b = p.float('b').unless((a > 0).and_(a < 10))
            return p

        self.assertRaises(MissingRequiredArgumentError,
                create()._process_command_line, ['--a', '0'])

        self.assertRaises(MissingRequiredArgumentError,
                create()._process_command_line, ['--a', '10'])

        create()._process_command_line(['--a', '5'])

        def create():
            p = Parser()
            a = p.float('a')
            c = p.float('b').unless((a < 0).or_(a > 10))
            return p

        create()._process_command_line(['--a', '11'])
        create()._process_command_line(['--a', '-1'])
        self.assertRaises(MissingRequiredArgumentError,
                create()._process_command_line, ['--a', '0'])

        self.assertRaises(MissingRequiredArgumentError,
                create()._process_command_line, ['--a', '10'])

        def create():
            p = Parser()
            a = p.float('a')
            c = p.float('b').if_(a > 0).unless((a > 10).and_(a < 20))
            return p

        create()._process_command_line(['--a', '11'])
        self.assertRaises(MissingRequiredArgumentError,
                create()._process_command_line, ['--a', '1'])

        self.assertRaises(MissingRequiredArgumentError,
                create()._process_command_line, ['--a', '5'])

        self.assertRaises(MissingRequiredArgumentError,
                create()._process_command_line, ['--a', '20'])

        def create():
            p = Parser()
            a = p.int('a')
            b = p.int('b')
            p.int('c').requires(a.or_(b))
            p.int('d').requires(a.and_(b))
            return p

        self.assertRaises(DependencyError, create()._process_command_line, specify('c'))
        create()._process_command_line(specify('c', 'a'))
        create()._process_command_line(specify('c', 'b'))
        create()._process_command_line(specify('c', 'a', 'b'))
        self.assertRaises(DependencyError, create()._process_command_line, specify('d'))
        self.assertRaises(DependencyError, create()._process_command_line, specify('d', 'a'))
        self.assertRaises(DependencyError, create()._process_command_line, specify('d', 'b'))
        create()._process_command_line(specify('d', 'a', 'b'))

        # self conditions
        def create():
            p = Parser()
            p.str('a').requires(p['a'] != 'c')
            return p

        create()._process_command_line(['--a', '1'])
        self.assertRaises(ConditionError, create()._process_command_line, ['--a', 'c'])

    def test_redundant(self):
        try:
            with Parser() as p:
                p.float('a')
                p.int('a')
            self.fail()
        except ValueError:
            pass

    def test_groups(self):
        def create():
            p = Parser()
            p.require_one(
                p.only_one_if_any(
                    p.int('a'),
                    p.int('b')
                ),
                p.only_one_if_any(
                    p.int('c'),
                    p.int('d')
                )
            )
            return p

        self.assertRaises(ManyAllowedNoneSpecifiedArgumentError, create()._process_command_line, [])
        create()._process_command_line(specify('a'))
        create()._process_command_line(specify('b'))
        for char in 'abcd':
            for other in set('abcd') - set([char]):
                self.assertRaises(ConflictError, create()._process_command_line, specify(char, other))

        def create():
            p = Parser()
            p.only_one_if_any(
                p.int('a'),
                p.int('b')
            ).requires(
                p.only_one_if_any(
                    p.int('c'),
                    p.int('d')
                )
            )
            return p

        self.assertRaises(DependencyError, create()._process_command_line, specify('a'))
        self.assertRaises(DependencyError, create()._process_command_line, specify('b'))
        create()._process_command_line(specify('c'))
        create()._process_command_line(specify('d'))

        create()._process_command_line(specify('a', 'c'))
        create()._process_command_line(specify('b', 'c'))
        create()._process_command_line(specify('a', 'd'))
        create()._process_command_line(specify('b', 'd'))

    def test_float(self):
        def create():
            p = Parser()
            p.float('a')
            p.float('c')
            return p

        self.assertRaises(FormatError, create()._process_command_line, ['--a', 'b'])
        self.assertRaises(FormatError, create()._process_command_line, ['--a', '1.2.3'])
        self.assertRaises(MissingValueError, create()._process_command_line, ['--a'])
#        p._process_command_line(['--a', '--b'])  # XXX what shoudl correct behavior be?

    def test_errors(self):
        p = Parser()
        p.int('a')
        try:
            p._process_command_line([])
        except TypeError:
            self.fail()

    def test_localize(self):
        p = Parser.with_locals()
        p.str('multi-word').requires(p.str('another-multi-word'))
        vals = p._process_command_line(['--multi-word', 'a', '--another-multi-word', 'b'])
        self.assertTrue('multi_word' in vals)
        self.assertFalse('multi-word' in vals)
        self.assertTrue('multi_word' in locals())

    def test_multiword(self):
        def create():
            p = Parser()
            p.multiword('aa')
            p.str('ab')
            return p

        self.assertRaises(MissingValueError, create()._process_command_line, ['--aa'])
        vals = create()._process_command_line(['--aa', 'a', '--ab', 'b'])
        self.assertEqual(vals['aa'], 'a')
        self.assertEqual(vals['ab'], 'b')

        vals = create()._process_command_line(['--aa', 'a c d', '--ab', 'b'])
        self.assertEqual(vals['aa'], 'a c d')

        vals = create()._process_command_line(['--aa', 'a', 'c', 'd', '--ab', 'b'])
        self.assertEqual(vals['aa'], 'a c d')

        p = Parser().set_single_prefix('+').set_double_prefix('M')
        p.multiword('aa')
        p.str('ab').shorthand('a')
        vals = p._process_command_line(['Maa', 'a', 'c', 'd', 'Mab', 'b'])
        self.assertEqual(vals['aa'], 'a c d')

        p = Parser().set_single_prefix('+').set_double_prefix('M')
        p.multiword('aa')
        p.str('ab').shorthand('a')
        vals = p._process_command_line(['Maa', 'a', 'c', 'd', '+a', 'b'])
        self.assertEqual(vals['aa'], 'a c d')

        self.assertRaises(ValueError, Parser().set_single_prefix('++').set_double_prefix, '+')

    def test_shorthand(self):
        p = Parser()
        aa = p.int('aa').shorthand('a')
        self.assertRaises(ValueError, lambda x: p.int('ab').shorthand(x), 'a')
        self.assertRaises(ValueError, p.int('bb').shorthand, 'a')
        self.assertRaises(ValueError, aa.shorthand, 'a')
#        self.assertRaises(ValueError, aa.shorthand, 'b')

    def test_range(self):
        def create():
            p = Parser()
            x = p.range('arg').shorthand('a')
            self.assertTrue(x is not None)
            return p

        def xrange_equals(x1, x2):
            return list(x1) == list(x2)

        self.assertRaises(MissingValueError, create()._process_command_line, ['--arg'])
        vals = create()._process_command_line(['--arg', '1:2'])
        self.assertTrue(xrange_equals(vals['arg'], xrange(1, 2)))

        self.assertRaises(FormatError, create()._process_command_line, ['--arg', '1:s2'])

        v = create()._process_command_line(['--arg', '1:-1'])
        self.assertTrue(xrange_equals(v['arg'], xrange(1, 1)))

        v = create()._process_command_line(['--arg', '0 9'])
        self.assertTrue(xrange_equals(v['arg'], xrange(0, 9)))

        v = create()._process_command_line(['--arg', '9'])
        self.assertTrue(xrange_equals(v['arg'], xrange(9)))

        v = create()._process_command_line(['--arg', '0 9 3'])
        self.assertTrue(xrange_equals(v['arg'], xrange(0, 9, 3)))

        v = create().set_single_prefix('+')._process_command_line(['+a', '0', '-1', '3'])
        self.assertTrue(xrange_equals(v['arg'], xrange(0, -1, 3)))

    def test_multiple(self):
        p = Parser()
        p.str('x')

        self.assertRaises(MultipleSpecifiedArgumentError,
                p._process_command_line, ['--x', '1', '--x', '2'])

        def create():
            p = Parser()
            x = p.int('x').multiple()
            self.assertTrue(x != None)
            return p

        vals = create()._process_command_line(['--x', '1', '--x', '2'])
        self.assertEqual(sorted(vals['x']), [1, 2])
        vals = create()._process_command_line(['--x', '1'])
        self.assertEqual(vals['x'], [1])
        vals = create()._process_command_line([])
        self.assertEqual(vals['x'], [None])
        self.assertRaises(FormatError, create()._process_command_line, ['--x', '1', '--x', 'hello'])

    def test_unspecified_default(self):
        p = Parser({})
        p.str('x').unspecified_default()
        self.assertRaises(ValueError, Option.unspecified_default, p.str('y'))

        vals = {}
        p = Parser(vals)
        p.str('x').unspecified_default().required()
        p._process_command_line(['ok'])
        self.assertEqual(vals['x'], 'ok')

        p = Parser({})
        p.str('x').unspecified_default().conflicts(p.str('y'))
        self.assertRaises(ConflictError, p._process_command_line,
            ['--y', 'a', 'unspecified_default'])

        p = Parser({})
        p.str('x').unspecified_default().conflicts(p.str('y'))
        self.assertRaises(ConflictError, p._process_command_line,
            ['unspecified_default', '--y', 'a'])

        # multiple
        p = Parser()
        p.str('x').unspecified_default()
        self.assertRaises(ValueError, p.str('y').unspecified_default)
    
    def test_with(self):
        import sys
        sys.argv[1:] = ['--x', 'yes']
        d = {'test_x': None}

        p = Parser(d)
        with p:
            p.str('x').shorthand('test-x')

    def test_bad_format(self):
        p = Parser()
        p.str('f')
        p.str('m')

        # This no longer fails because (I think) -m is a value for -m, and x
        # being extra is now ok
        # self.assertRaises(ArgumentError, p._process_command_line, '-f -m x'.split())

    def test_basic(self):
        p = Parser()
        p.str('x')
        p.flag('y')
        vals = p._process_command_line([])
        self.assertTrue(vals['x'] is None)
#        self.assertEqual(vals['x'], x)
#        self.assertEqual(vals['y'], y)
        self.assertFalse(vals['y'])

    def test_add(self):
        p = Parser()
        p.str('x')
        vals = p._process_command_line(['--x', 'hi'])
        self.assertEqual(vals['x'], 'hi')

        p = Parser(locals())
        p.str('x')
        p._process_command_line(['--x', 'hi'])
        self.assertTrue('x' in locals())

        p = Parser()
        p.str('x')
        vals = p._process_command_line(['--x=5'])
        self.assertEqual(vals['x'], '5')

    def test_default(self):
        p = Parser()
        p.int('x').default(5)
        vals = p._process_command_line([])
        self.assertEqual(vals['x'], 5)

        p = Parser()
        p.int('x').default(5)
        vals = p._process_command_line(['--x', '6'])
        self.assertEqual(vals['x'], 6)
    
    def test_cast(self):
        p = Parser()
        p.str('x').cast(int)
        vals = p._process_command_line(['--x', '1'])
        self.assertEqual(vals['x'], 1)

        p = Parser()
        p.str('x').cast(int)
        self.assertRaises(ArgumentError, p._process_command_line, ['--x', 'a'])

        p = Parser()
        p.int('x')
        vals = p._process_command_line(['--x', '1'])

        p = Parser()
        p.multiword('x').cast(lambda x: [float(y) for y in x.split()])
        vals = p._process_command_line(['--x', '1.2 9.8 4.6'])
        self.assertEqual(vals['x'], [1.2, 9.8000000000000007,
            4.5999999999999996])

        p = Parser()
        p.int('x').default('yes')
        self.assertRaises(FormatError, p._process_command_line)

    def test_required(self):
        p = Parser()
        p.str('x').required()
        self.assertRaises(MissingRequiredArgumentError, p._process_command_line, [])

        p = Parser()
        p.str('x').required()
        self.assertRaises(MissingRequiredArgumentError,
                p._process_command_line, [])

        p = Parser()
        y = p.str('y')
        z = p.str('z')
        x = p.str('x').unless(y.or_(z))
        self.assertTrue(x != None)
        self.assertRaises(ArgumentError,
                p._process_command_line, [])
        p._process_command_line(['--y', 'a'])
        p._process_command_line(['--x', 'a'])
        p._process_command_line(['--x', 'a', '--y', 'b'])
        p._process_command_line(['--z', 'a'])

    def test_requires(self):
        p = Parser()
        r = p.str('x')
        self.assertRaises(ValueError, r.requires, 'y')
        try:
            r.requires(p.str('y'))
        except ValueError:
            self.fail()

        p = Parser()
        y = p.int('y')
        p.int('x').requires(y)

        self.assertRaises(DependencyError, p._process_command_line, ['--x', '5'])

    def test_depends(self):
        def create():
            p = Parser()
            p.str('x').requires(p.str('y'))

            return p

        self.assertRaises(DependencyError, create()._process_command_line, ['--x', 'hi'])
        try:
            create()._process_command_line(['--y', 'sup'])
        except:
            self.assertTrue(False)

        try:
            create()._process_command_line(['--x', 'hi', '--y', 'sup'])
        except:
            self.assertTrue(False)

    def test_unspecified(self):
        p = Parser()
        self.assertRaises(UnspecifiedArgumentError, p._process_command_line, ['--b'])

    def test_enum(self):
        def create():
            p = Parser()
            p.enum('x', ('a', 'b', 'c'))
            return p

        create()._process_command_line()
        self.assertRaises(ConditionError, create()._process_command_line, ['--x', '3'])
        self.assertRaises(ConditionError, create()._process_command_line, ['--x', 'ab'])
        self.assertRaises(ConditionError, create()._process_command_line, ['--x', '9'])
        create()._process_command_line(['--x', 'a'])
        create()._process_command_line(['--x', 'b'])
        create()._process_command_line(['--x', 'c'])

        def create():
            p = Parser()
            p.enum('x', ('a', 'b', 'c')).multiple()
            return p

#        XXX create()._process_command_line(['--x', 'a', '--x', 'b'])
        create()._process_command_line(['--x', 'b'])
        create()._process_command_line(['--x', 'c'])
        self.assertRaises(ConditionError, create()._process_command_line, ['--x', 'c', '--x', '3'])
        self.assertRaises(ConditionError, create()._process_command_line, ['--x', '3', '--x', 'c'])

    def test_int(self):
        def create():
            p = Parser()
            p.int('x')
            return p

        vals = create()._process_command_line()
        self.assertTrue('x' in vals)
        self.assertEqual(vals['x'], None)
        vals = create()._process_command_line(['--x', '5'])
        self.assertEqual(vals['x'], 5)

        vals = create()._process_command_line(['--x', '-1'])
        self.assertEqual(vals['x'], -1)

    def test_flag(self):
        p = Parser()
        p.flag('x')
        vals = p._process_command_line()
        self.assertTrue('x' in vals)
        self.assertFalse(vals['x'])

        p = Parser()
        p.flag('x')
        vals = p._process_command_line(['--x'])
        self.assertTrue(vals['x'])

    def test_flag2(self):
        p = Parser()
        p.flag('x').requires(p.int('y'))

        p._process_command_line()
        self.assertRaises(DependencyError, p._process_command_line, ['--x'])

    def test_missing(self):
        p = Parser()
        p.int('x')
        self.assertRaises(MissingValueError, p._process_command_line, ['--x'])

    def test_depends_group(self):
        def create():
            p = Parser()
            p.str('x').requires(
                p.str('y'),
                p.str('z'),
                p.str('w')
            )

            return p

#        o1.add_dependency_group((o2, o3, o4))

        self.assertRaises(DependencyError, create()._process_command_line, ['--x', 'hi'])
        try:
            create()._process_command_line(['--y', 'sup'])
        except:
            self.fail()

        for v in permutations([('--y', 'sup'), ('--z', 'zup'), ('--w', 'wup')], 2):
            self.assertRaises(DependencyError, create()._process_command_line,
                    ['--x', 'hi'] + reduce(list.__add__, map(list, v)))

    def test_conflicts(self):
        def create():
            p = Parser()
            p.int('x').conflicts(p.int('y'))
            return p

        self.assertRaises(ConflictError, create()._process_command_line, specify('x', 'y'))
        create()._process_command_line(specify('y'))

        try:
            create()._process_command_line(specify('x'))
        except:
            self.assertTrue(False)

    def test_mutually_exclusive(self):
        def create():
            p = Parser()
            p.int('x')
            p.int('y')
            p.int('z')

            p.only_one_if_any(*'xyz')
            return p

        self.assertRaises(ConflictError, create()._process_command_line, specify('x', 'y'))
        self.assertRaises(ConflictError, create()._process_command_line, specify('x', 'z'))
        self.assertRaises(ConflictError, create()._process_command_line, specify('y', 'z'))
        self.assertRaises(ConflictError, create()._process_command_line, specify('x', 'y', 'z'))

        create()._process_command_line(specify('x'))
        create()._process_command_line(specify('y'))
        create()._process_command_line(specify('z'))
    
    def test_mutually_dependent(self):
        def create():
            p = Parser()
            p.all_if_any(
                p.int('x'),
                p.int('y'),
                p.int('z')
            )

            return p

        self.assertRaises(DependencyError, create()._process_command_line, ['--x', '3'])
        self.assertRaises(DependencyError, create()._process_command_line, ['--y', '3'])
        self.assertRaises(DependencyError, create()._process_command_line, ['--z', '3'])
        self.assertRaises(DependencyError, create()._process_command_line, ['--x', '3', '--y', '3'])
        self.assertRaises(DependencyError, create()._process_command_line, ['--x', '3', '--z', '3'])
        self.assertRaises(DependencyError, create()._process_command_line, ['--y', '3', '--z', '3'])

        create()._process_command_line(['--x', '3', '--y', '3', '--z', '3'])

    def test_oo(self):
        p = Parser()
        p.int('x')
        y = p.int('y')
        z = p.int('z').requires('y')
        x = p['x']
        x.requires(y, z)
        self.assertRaises(DependencyError, p._process_command_line, ['--x', '3'])
        self.assertRaises(DependencyError, p._process_command_line, ['--z', '3'])
        p._process_command_line(['--y', '3'])

        p = Parser()
        p.flag('x')
        p.flag('y').conflicts('x')
        self.assertRaises(ConflictError, p._process_command_line, ['--y', '--x'])

#    def test_index(self):
#        p = Parser()
#        p.str('x')
#        self.assertEqual(p['y'], None)
    
    def test_set_at_least_one_required(self):
        def create():
            p = Parser()
            p.at_least_one(
                p.str('x'),
                p.str('y'),
                p.str('z')
            )

            return p

        create()._process_command_line(['--x', '1'])
        create()._process_command_line(['--y', '1'])
        create()._process_command_line(['--z', '1'])
        create()._process_command_line(['--x', '1', '--y', '1'])
        create()._process_command_line(['--x', '1', '--y', '1', '--z', '1'])
        create()._process_command_line(['--x', '1', '--z', '1'])
        create()._process_command_line(['--y', '1', '--z', '1'])
        self.assertRaises(ArgumentError, create()._process_command_line, [])

    def test_one_required(self):
        def create():
            p = Parser()
            p.require_one(
                p.str('x'),
                p.str('y'),
                p.str('z')
            )

            return p

        create()._process_command_line(['--x', '1'])
        create()._process_command_line(['--y', '1'])
        create()._process_command_line(['--z', '1'])

        self.assertRaises(ConflictError, create()._process_command_line, ['--x', '1', '--y', '1'])
        self.assertRaises(ArgumentError, create()._process_command_line, [])

        p = Parser()
        p.int('a')
        p.int('b')
        p.require_one('a', 'b')
        p._process_command_line(['--b', '3'])


if __name__ == '__main__':
    unittest.main()
