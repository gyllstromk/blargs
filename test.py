#  Copyright (c) 2011, Karl Gyllstrom
#  All rights reserved.
#
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions are met: 
#
#  1. Redistributions of source code must retain the above copyright notice, this
#     list of conditions and the following disclaimer. 
#  2. Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions and the following disclaimer in the documentation
#     and/or other materials provided with the distribution. 
#  
#     THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
#     ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
#     WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
#     DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
#     ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
#     (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
#     LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
#     ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#     (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
#     SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#  
#     The views and conclusions contained in the software and documentation are those
#     of the authors and should not be interpreted as representing official policies, 
#     either expressed or implied, of the FreeBSD Project.

from blargs import *

from itertools import permutations
import unittest


class TestCase(unittest.TestCase):
    def test_numeric_conditions(self):
        p = Parser()
        a = p.float('a')
        p.int('b').unless(a < 20)
        self.assertRaises(MissingRequiredArgumentError, p._process_command_line, ['--a', '20'])
        p._process_command_line(['--a', '19'])
        p._process_command_line(['--a', '9'])
        p._process_command_line(['--b', '3', '--a', '29'])

        p.int('c').unless(10 < a)
        self.assertRaises(MissingRequiredArgumentError, p._process_command_line, ['--a', '20'])
        self.assertRaises(MissingRequiredArgumentError, p._process_command_line, ['--a', '9'])
        p._process_command_line(['--a', '19'])

        d = p.int('d').unless(a == 19)
        self.assertRaises(MissingRequiredArgumentError, p._process_command_line, ['--a', '20'])
        self.assertRaises(MissingRequiredArgumentError, p._process_command_line, ['--a', '9'])
        p._process_command_line(['--a', '19'])

        e = p.int('e').unless(a == d)
        self.assertRaises(MissingRequiredArgumentError, p._process_command_line, ['--a', '19'])
        self.assertRaises(MissingRequiredArgumentError, p._process_command_line, ['--a', '19', '--d', '18'])
        p._process_command_line(['--a', '19', '--d', '19'])

        p.int('f').unless(e != d)
        self.assertRaises(MissingRequiredArgumentError,
                p._process_command_line, ['--a', '19'])

        self.assertRaises(MissingRequiredArgumentError,
                p._process_command_line, ['--a', '19', '--d', '18'])

        self.assertRaises(MissingRequiredArgumentError,
                p._process_command_line, ['--a', '19', '--d', '19', '--e',
                    '19'])

        p._process_command_line(['--a', '19', '--d', '19', '--e', '18'])

        p = Parser()
        a = p.float('a')
        b = p.float('b').requires(a < 10)
        self.assertRaises(ConditionError, p._process_command_line, ['--b',
            '3.9', '--a', '11'])

        p = Parser()
        a = p.float('a')
        b = p.float('b').if_(a < 10)
        self.assertRaises(MissingRequiredArgumentError,
                p._process_command_line, ['--a', '8'])

        p._process_command_line(['--a', '11'])

    def test_conditions(self):
        p = Parser()
        a = p.float('a')
        b = p.float('b')
        c = p.float('c').requires(a.or_(b))
        self.assertRaises(DependencyError, p._process_command_line, ['--c', '9.2'])
        p._process_command_line(['--a', '11', '--c', '9.2'])
        p._process_command_line(['--b', '11', '--c', '9.2'])

        p = Parser()
        a = p.float('a')
        b = p.float('b')
        c = p.float('c').if_(a.or_(b))
        p._process_command_line(['--c', '9.2'])
        self.assertRaises(MissingRequiredArgumentError,
                p._process_command_line, ['--a', '11'])

        p._process_command_line(['--a', '11', '--c', '9.2'])
        self.assertRaises(MissingRequiredArgumentError,
                p._process_command_line, ['--b', '11'])

        p._process_command_line(['--b', '11', '--c', '9.2'])

    def test_compound(self):
        p = Parser()
        a = p.float('a')
        b = p.float('b').unless((a > 0).and_(a < 10))
        self.assertRaises(MissingRequiredArgumentError,
                p._process_command_line, ['--a', '0'])

        self.assertRaises(MissingRequiredArgumentError,
                p._process_command_line, ['--a', '10'])

        p._process_command_line(['--a', '5'])

        p = Parser()
        a = p.float('a')
        c = p.float('b').unless((a < 0).or_(a > 10))
        p._process_command_line(['--a', '11'])
        p._process_command_line(['--a', '-1'])
        self.assertRaises(MissingRequiredArgumentError,
                p._process_command_line, ['--a', '0'])

        self.assertRaises(MissingRequiredArgumentError,
                p._process_command_line, ['--a', '10'])

        p = Parser()
        a = p.float('a')
        c = p.float('b').if_(a > 0).unless((a > 10).and_(a < 20))
        p._process_command_line(['--a', '11'])
        self.assertRaises(MissingRequiredArgumentError,
                p._process_command_line, ['--a', '1'])

        self.assertRaises(MissingRequiredArgumentError,
                p._process_command_line, ['--a', '5'])

        self.assertRaises(MissingRequiredArgumentError,
                p._process_command_line, ['--a', '20'])

    def test_redundant(self):
        try:
            with Parser() as p:
                p.float('a')
                p.int('a')
            self.fail()
        except ValueError:
            pass

    def test_groups(self):
        p = Parser()
        p.require_one(
            p.only_one_if_any(
                p.flag('a'),
                p.flag('b')
            ),
            p.only_one_if_any(
                p.flag('c'),
                p.flag('d')
            )
        )

        self.assertRaises(ManyAllowedNoneSpecifiedArgumentError, p._process_command_line, [])
        p._process_command_line(['--a'])
        p._process_command_line(['--b'])
        for char in 'abcd':
            for other in set('abcd') - set([char]):
                self.assertRaises(ConflictError, p._process_command_line, ['--%s' % char, '--%s' % other])

        p = Parser()
        p.only_one_if_any(
            p.flag('a'),
            p.flag('b')
        ).requires(
            p.only_one_if_any(
                p.flag('c'),
                p.flag('d')
            )
        )

        self.assertRaises(DependencyError, p._process_command_line, ['--a'])
        self.assertRaises(DependencyError, p._process_command_line, ['--b'])
        p._process_command_line(['--c'])
        p._process_command_line(['--d'])

        p._process_command_line(['--a', '--c'])
        p._process_command_line(['--b', '--c'])
        p._process_command_line(['--a', '--d'])
        p._process_command_line(['--b', '--d'])

    def test_float(self):
        p = Parser()
        p.float('a')
        p.float('c')
        self.assertRaises(FormatError, p._process_command_line, ['--a', 'b'])
        self.assertRaises(FormatError, p._process_command_line, ['--a', '1.2.3'])
        self.assertRaises(MissingValueError, p._process_command_line, ['--a'])
#        p._process_command_line(['--a', '--b'])  # XXX what shoudl correct behavior be?

    def test_errors(self):
        p = Parser()
        p.int('a')
        try:
            p._process_command_line([])
        except TypeError:
            self.fail()

#    def test_enum(self):
#        p = Parser()
#        default = '1'
#        p.enum('a', ['1', '2', 'b']).default(default)
#        self.assertRaises(InvalidEnumValueError, p._process_command_line, ['--a', 'c'])
#        self.assertRaises(InvalidEnumValueError, p._process_command_line, ['--a', '9'])
#        for arg in ('1', '2', 'b'):
#            self.assertEquals(p._process_command_line(['--a', arg])['a'], arg)
#
#        self.assertEquals(p._process_command_line([])['a'], default)

    def test_condition(self):
        p = Parser()
        p.str('a').condition(lambda x: x['b'] != 'c')
        p.str('b')

        p._process_command_line(['-a', '1', '-b', 'b'])
        self.assertRaises(FailedConditionError, p._process_command_line, ['-a', '1', '-b', 'c'])

    def test_localize(self):
        p = Parser.with_locals()
        p.str('multi-word').requires(p.str('another-multi-word'))
        vals = p._process_command_line(['--multi-word', 'a', '--another-multi-word', 'b'])
        self.assertTrue('multi_word' in vals)
        self.assertFalse('multi-word' in vals)
        self.assertTrue('multi_word' in locals())

    def test_multiword(self):
        p = Parser()
        p.multiword('aa')
        p.str('ab')

        vals = p._process_command_line(['--aa', 'a', '--ab', 'b'])
        self.assertEquals(vals['aa'], 'a')
        self.assertEquals(vals['ab'], 'b')

        vals = p._process_command_line(['--aa', 'a c d', '--ab', 'b'])
        self.assertEquals(vals['aa'], 'a c d')

        vals = p._process_command_line(['--aa', 'a', 'c', 'd', '--ab', 'b'])
        self.assertEquals(vals['aa'], 'a c d')

        p = Parser().set_single_prefix('+').set_double_prefix('M')
        p.multiword('aa')
        p.str('ab').shorthand('a')
        vals = p._process_command_line(['Maa', 'a', 'c', 'd', 'Mab', 'b'])
        self.assertEquals(vals['aa'], 'a c d')
        vals = p._process_command_line(['Maa', 'a', 'c', 'd', '+a', 'b'])
        self.assertEquals(vals['aa'], 'a c d')

        self.assertRaises(ValueError, Parser().set_single_prefix('++').set_double_prefix, '+')

    def x_test_with_files(self):
        d = TemporaryDirectory()

        p = Parser()
        p.add_file('f')
        p.flag('F')
        p.set_requires('f', 'F')

        f = d / File('hello')

        self.assertRaises(DependencyError, p._process_command_line, ['-f', str(f.path())])

        p = Parser()
        p.add_input_file('i').shorthand('input')
        f.writer(overwrite=True).write('sup')
        vals = p._process_command_line(['-i', str(f.path())])

        self.assertRaises(IOError, vals['i'].write, ('hi'))
        f.remove()

        p = Parser()
        p.add_input_file('i').shorthand('input')
        f = d / File('hello_world')
        f.writer(overwrite=True).write('sup')
        vals = p._process_command_line(['-i', str(f.path())])

    def test_shorthand(self):
        p = Parser()
        p.int('aa').shorthand('a')
        self.assertRaises(ValueError, lambda x: p.int('ab').shorthand(x), 'a')

    def test_range(self):
        def create():
            l = {}
            p = Parser(l)
            x = p.range('a')
            self.assertTrue(x is not None)
            return p, l

        def xrange_equals(x1, x2):
            return list(x1) == list(x2)

        p, l = create()
        p._process_command_line(['--a', '1:2'])
        self.assertTrue(xrange_equals(l['a'], xrange(1, 2)))

        p, l = create()
        self.assertRaises(FormatError, p._process_command_line, ['-a', '1:s2'])

        p, l = create()
        p._process_command_line(['-a', '1:-1'])
        self.assertTrue(xrange_equals(l['a'], xrange(1, 1)))

        v = p._process_command_line(['-a', '0', '9'])
        self.assertTrue(xrange_equals(v['a'], xrange(0, 9)))

        v = p._process_command_line(['-a', '9'])
        self.assertTrue(xrange_equals(v['a'], xrange(9)))

        v = p._process_command_line(['-a', '0', '9', '3'])
        self.assertTrue(xrange_equals(v['a'], xrange(0, 9, 3)))

        p.set_single_prefix('+')
        v = p._process_command_line(['+a', '0', '-1', '3'])
        self.assertTrue(xrange_equals(v['a'], xrange(0, -1, 3)))

    def test_multiple(self):
        p = Parser()
        p.str('x')

        self.assertRaises(MultipleSpecifiedArgumentError,
                p._process_command_line, ['-x', '1', '-x', '2'])

        p = Parser()
        x = p.str('x').multiple()
        self.assertTrue(x != None)

        p._process_command_line(['-x', '1', '-x', '2'])

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
            ['-y', 'a', 'unspecified_default'])

        p = Parser({})
        p.str('x').unspecified_default().conflicts(p.str('y'))
        self.assertRaises(ConflictError, p._process_command_line,
            ['unspecified_default', '-y', 'a'])

        # multiple
        p = Parser()
        p.str('x').unspecified_default()
        self.assertRaises(ValueError, p.str('y').unspecified_default)
    
    def test_with(self):
        import sys
        sys.argv[1:] = ['-x', 'yes']
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
        vals = p._process_command_line(['-x', 'hi'])
        self.assertEquals(vals['x'], 'hi')

        p = Parser(locals())
        p.str('x')
        p._process_command_line(['-x', 'hi'])
        self.assertTrue('x' in locals())

        p = Parser()
        p.str('x')
        vals = p._process_command_line(['-x=5'])
        self.assertEquals(vals['x'], '5')

    def test_default(self):
        p = Parser()
        p.int('x').default(5)
        vals = p._process_command_line([])
        self.assertEquals(vals['x'], 5)

        p = Parser()
        p.int('x').default(5)
        vals = p._process_command_line(['-x', '6'])
        self.assertEquals(vals['x'], 6)
    
    def test_cast(self):
        p = Parser()
        p.str('x').cast(int)
        vals = p._process_command_line(['-x', '1'])
        self.assertEquals(vals['x'], 1)
        self.assertRaises(ArgumentError, p._process_command_line, ['-x', 'a'])

        p = Parser()
        p.int('x')
        vals = p._process_command_line(['-x', '1'])

    def test_required(self):
        p = Parser()
        p.str('x').required()
        self.assertRaises(MissingRequiredArgumentError, p._process_command_line, [])

        p = Parser()
        p.str('x').required()
        self.assertRaises(MissingRequiredArgumentError,
                p._process_command_line, [])

        p = Parser()
        p.str('y')
        p.str('z')
        x = p.str('x').unless('y', 'z')
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
        y = p.flag('y')
        p.flag('x').requires(y)

        self.assertRaises(DependencyError, p._process_command_line, ['-x'])

    def test_depends(self):
        def create():
            p = Parser()
            p.str('x').requires(p.str('y'))

            return p

        self.assertRaises(DependencyError, create()._process_command_line, ['-x', 'hi'])
        try:
            create()._process_command_line(['-y', 'sup'])
        except:
            self.assertTrue(False)

        try:
            create()._process_command_line(['-x', 'hi', '-y', 'sup'])
        except:
            self.assertTrue(False)

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

        self.assertRaises(DependencyError, create()._process_command_line, ['-x', 'hi'])
        try:
            create()._process_command_line(['-y', 'sup'])
        except:
            self.fail()

        for v in permutations([('-y', 'sup'), ('-z', 'zup'), ('-w', 'wup')], 2):
            self.assertRaises(DependencyError, create()._process_command_line,
                    ['-x', 'hi'] + reduce(list.__add__, map(list, v)))

    def test_conflicts(self):
        def create():
            p = Parser()
            p.flag('x').conflicts(p.flag('y'))
            return p

        self.assertRaises(ConflictError, create()._process_command_line, ['-x', '-y'])
        create()._process_command_line(['-y'])

        try:
            create()._process_command_line(['-x'])
        except:
            self.assertTrue(False)

    def test_mutually_exclusive(self):
        def create():
            p = Parser()
            p.flag('x')
            p.flag('y')
            p.flag('z')

            p.only_one_if_any(*'xyz')
            return p

        self.assertRaises(ConflictError, create()._process_command_line, ['-x', '-y'])
        self.assertRaises(ConflictError, create()._process_command_line, ['-x', '-z'])
        self.assertRaises(ConflictError, create()._process_command_line, ['-y', '-z'])
        self.assertRaises(ConflictError, create()._process_command_line, ['-x', '-y', '-z'])

        create()._process_command_line(['-x'])
        create()._process_command_line(['-y'])
        create()._process_command_line(['-z'])
    
    def test_mutually_dependent(self):
        def create():
            p = Parser()
            p.all_if_any(
                p.flag('x'),
                p.flag('y'),
                p.flag('z')
            )

            return p

        self.assertRaises(DependencyError, create()._process_command_line, ['-x'])
        self.assertRaises(DependencyError, create()._process_command_line, ['-y'])
        self.assertRaises(DependencyError, create()._process_command_line, ['-z'])
        self.assertRaises(DependencyError, create()._process_command_line, ['-x', '-y'])
        self.assertRaises(DependencyError, create()._process_command_line, ['-x', '-z'])
        self.assertRaises(DependencyError, create()._process_command_line, ['-y', '-z'])

        create()._process_command_line(['-x', '-y', '-z'])

    def test_oo(self):
        p = Parser()
        p.flag('x')
        p.flag('y')
        p.flag('z').requires('y')
        x = p['x']
        x.requires('y', 'z')
        self.assertRaises(DependencyError, p._process_command_line, ['-x'])
        self.assertRaises(DependencyError, p._process_command_line, ['-z'])
        p._process_command_line(['-y'])

        p = Parser()
        p.flag('x')
        p.flag('y').conflicts('x')
        self.assertRaises(ConflictError, p._process_command_line, ['-y', '-x'])

#    def test_index(self):
#        p = Parser()
#        p.str('x')
#        self.assertEquals(p['y'], None)
    
    def test_set_at_least_one_required(self):
        def create():
            p = Parser()
            p.str('x')
            p.str('y')
            p.str('z')

            p.at_least_one('x', 'y', 'z')
            return p

        create()._process_command_line(['-x', '1'])
        create()._process_command_line(['-y', '1'])
        create()._process_command_line(['-z', '1'])
        create()._process_command_line(['-x', '1', '-y', '1'])
        self.assertRaises(ArgumentError, create()._process_command_line, [])

    def x_test_requires_n(self):
        p = Parser()
        p.flag('x')
        p.flag('y')
        p.flag('z')

        p.set_requires_n_of('x', 1, 'y', 'z')
        self.assertRaises(DependencyError, p._process_command_line, ['-x'])
        p._process_command_line(['-x', '-y'])
        p._process_command_line(['-x', '-z'])

        p.set_requires_n_of('x', 2, 'y', 'z')
        self.assertRaises(DependencyError, p._process_command_line, ['-x'])
        self.assertRaises(DependencyError, p._process_command_line, ['-x', '-y'])
        self.assertRaises(DependencyError, p._process_command_line, ['-x', '-z'])

        p._process_command_line(['-x', '-y', '-z'])

    def test_one_required(self):
        def create():
            p = Parser()
            p.str('x')
            p.str('y')
            p.str('z')

            p.require_one(*'xyz')
            return p

        create()._process_command_line(['-x', '1'])
        create()._process_command_line(['-y', '1'])
        create()._process_command_line(['-z', '1'])

        self.assertRaises(ConflictError, create()._process_command_line, ['-x', '1', '-y', '1'])
        self.assertRaises(ArgumentError, create()._process_command_line, [])

        p = Parser()
        p.flag('a')
        p.flag('b')
        p.require_one('a', 'b')
        p._process_command_line(['-b'])


if __name__ == '__main__':
    unittest.main()
