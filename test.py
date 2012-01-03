from blargs import *

from itertools import permutations
import unittest


class TestCase(unittest.TestCase):
    def test_errors(self):
        p = Parser()
        p.int('a')
        try:
            p._process_command_line([])
        except TypeError:
            self.fail()

    def test_localize(self):
        p = Parser.with_locals()
        p.str('multi-word')
        p.str('another-multi-word')
        p.set_requires('multi-word', 'another-multi-word')
        vals = p._process_command_line(['--multi-word', 'a', '--another-multi-word', 'b'])
        self.assertTrue('multi_word' in vals)
        self.assertFalse('multi-word' in vals)
        self.assertTrue('multi_word' in locals())

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
            p.add_range('a')
            return p, l

        def xrange_equals(x1, x2):
            return list(x1) == list(x2)

        p, l = create()
        p._process_command_line(['-a', '1:2'])
        self.assertTrue(xrange_equals(l['a'], xrange(1, 2)))

        p, l = create()
        self.assertRaises(FormatError, p._process_command_line, ['-a', '1:s2'])

        p, l = create()
        p._process_command_line(['-a', '1:-1'])
        self.assertTrue(xrange_equals(l['a'], xrange(1, 1)))

    def test_multiple(self):
        def create():
            p = Parser()
            p.str('x')

            return p

        self.assertRaises(MultipleSpecifiedArgumentError,
                create()._process_command_line, ['-x', '1', '-x', '2'])

        p = create()
        p.set_multiple('x')

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
        p.str('x').unspecified_default()
        p.str('y')
        p.set_conflicts('x', 'y')
        self.assertRaises(ConflictError, p._process_command_line,
            ['-y', 'a', 'unspecified_default'])
        p = Parser({})
        p.str('x').unspecified_default()
        p.str('y')
        p.set_conflicts('x', 'y')
        self.assertRaises(ConflictError, p._process_command_line,
            ['unspecified_default', '-y', 'a'])
    
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
        self.assertRaises(MissingRequiredArgumentError,
                p._process_command_line, [])

        p = Parser()
        p.str('x').required()
        self.assertRaises(MissingRequiredArgumentError,
                p._process_command_line, [])

    def test_requires(self):
        p = Parser()
        p.str('x')
        self.assertRaises(ValueError, p.set_requires, 'x', 'y')
        p.str('y')
        try:
            p.set_requires('x', 'y')
        except:
            self.fail()

        p = Parser()
        y = p.flag('y')
        p.flag('x').requires(y)

        self.assertRaises(DependencyError, p._process_command_line, ['-x'])

    def test_depends(self):
        def create():
            p = Parser()
            p.str('x')
            p.str('y')
            p.set_requires('x', 'y')

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
            p.str('x')
            p.str('y')
            p.str('z')
            p.str('w')

            for v in 'yzw':
                p.set_requires('x', v)

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
            p.flag('x')
            p.flag('y')
            p.set_conflicts('x', 'y')
            return p

        self.assertRaises(ConflictError, create()._process_command_line, ['-x', '-y'])
        try:
            create()._process_command_line(['-y'])
        except:
            self.assertTrue(False)

        try:
            create()._process_command_line(['-x'])
        except:
            self.assertTrue(False)

#    def test_type_checking(self):
#        self.assertRaises(TypeError, p.set_mutually_exclusive, 'hello')
#        self.assertRaises(TypeError, p.set_mutually_dependent, 'hello')
#        self.assertRaises(TypeError, p.set_at_least_one_required, 'hello')
#        self.assertRaises(TypeError, p.set_one_required, 'hello')
    
    def test_mutually_exclusive(self):
        def create():
            p = Parser()
            p.flag('x')
            p.flag('y')
            p.flag('z')

            p.set_mutually_exclusive(*'xyz')
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
            p.flag('x')
            p.flag('y')
            p.flag('z')

            p.set_mutually_dependent(*'xyz')
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

            p.set_at_least_one_required('x', 'y', 'z')
            return p

        create()._process_command_line(['-x', '1'])
        create()._process_command_line(['-y', '1'])
        create()._process_command_line(['-z', '1'])
        create()._process_command_line(['-x', '1', '-y', '1'])
        self.assertRaises(ManyAllowedNoneSpecifiedArgumentError, create()._process_command_line, [])

    def test_requires_n(self):
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

            p.set_one_required(*'xyz')
            return p

        create()._process_command_line(['-x', '1'])
        create()._process_command_line(['-y', '1'])
        create()._process_command_line(['-z', '1'])

        self.assertRaises(ConflictError, create()._process_command_line, ['-x', '1', '-y', '1'])
        self.assertRaises(ManyAllowedNoneSpecifiedArgumentError, create()._process_command_line, [])

        p = Parser()
        p.flag('a')
        p.flag('b')
        p.set_one_required('a', 'b')
        p._process_command_line(['-b'])

if __name__ == '__main__':
    unittest.main()
