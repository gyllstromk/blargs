from blargs import *

from itertools import permutations
import unittest


class TestCase(unittest.TestCase):
    def test_errors(self):
        p = Parser()
        p.add_int('a')
        try:
            p._process_command_line([])
        except TypeError:
            self.fail()

    def test_localize(self):
        p = Parser.with_locals()
        p.add_option('multi-word')
        p.add_option('another-multi-word')
        p.set_requires('multi-word', 'another-multi-word')
        vals = p._process_command_line(['--multi-word', 'a', '--another-multi-word', 'b'])
        self.assertTrue('multi_word' in vals)
        self.assertFalse('multi-word' in vals)
        self.assertTrue('multi_word' in locals())

    def x_test_with_files(self):
        d = TemporaryDirectory()

        p = Parser()
        p.add_file('f')
        p.add_flag('F')
        p.set_requires('f', 'F')

        f = d / File('hello')

        self.assertRaises(DependencyError, p._process_command_line, ['-f', str(f.path())])

        p = Parser()
        p.add_input_file('i', alias='input')
        f.writer(overwrite=True).write('sup')
        vals = p._process_command_line(['-i', str(f.path())])

        self.assertRaises(IOError, vals['i'].write, ('hi'))
        f.remove()

        p = Parser()
        p.add_input_file('i', alias='input')
        f = d / File('hello_world')
        f.writer(overwrite=True).write('sup')
        vals = p._process_command_line(['-i', str(f.path())])

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
            p.add_option('x')

            return p

        self.assertRaises(MultipleSpecifiedArgumentError,
                create()._process_command_line, ['-x', '1', '-x', '2'])

        p = create()
        p.set_multiple('x')

        p._process_command_line(['-x', '1', '-x', '2'])

#        p = create()
#        p.set_unspecified_default('x')
#        vals = p._process_command_line(['-x', '1', 'a', '2'])

    def test_unspecified_default(self):
        p = Parser({})
        p.add_option('x', unspecified_default=True)
        self.assertRaises(ValueError, p.add_option, 'y',
                unspecified_default=True)

        vals = {}
        p = Parser(vals)
        p.add_option('x', unspecified_default=True, required=True)
        p._process_command_line(['ok'])
        self.assertEqual(vals['x'], 'ok')

        p = Parser({})
        p.add_option('x', unspecified_default=True)
        p.add_option('y')
        p.set_conflicts('x', 'y')
        self.assertRaises(ConflictError, p._process_command_line,
            ['-y', 'a', 'unspecified_default'])
        p = Parser({})
        p.add_option('x', unspecified_default=True)
        p.add_option('y')
        p.set_conflicts('x', 'y')
        self.assertRaises(ConflictError, p._process_command_line,
            ['unspecified_default', '-y', 'a'])
    
    def test_with(self):
        import sys
        sys.argv[1:] = ['-x', 'yes']
        d = {'test_x': None}

        p = Parser(d)
        with p:
            p.add_option('x', 'test-x')

    def test_bad_format(self):
        p = Parser()
        p.add_option('f')
        p.add_option('m')

        # This no longer fails because (I think) -m is a value for -m, and x
        # being extra is now ok
        # self.assertRaises(ArgumentError, p._process_command_line, '-f -m x'.split())

    def test_basic(self):
        p = Parser()
        p.add_option('x')
        p.add_flag('y')
        vals = p._process_command_line([])
        self.assertTrue(vals['x'] is None)
#        self.assertEqual(vals['x'], x)
#        self.assertEqual(vals['y'], y)
        self.assertFalse(vals['y'])

    def test_add(self):
        p = Parser()
        p.add_option('x')
        vals = p._process_command_line(['-x', 'hi'])
        self.assertEquals(vals['x'], 'hi')

        p = Parser(locals())
        p.add_option('x')
        p._process_command_line(['-x', 'hi'])
        self.assertTrue('x' in locals())

        p = Parser()
        p.add_option('x')
        vals = p._process_command_line(['-x=5'])
        self.assertEquals(vals['x'], '5')

    def test_default(self):
        p = Parser()
        p.add_int('x', default=5)
        vals = p._process_command_line([])
        self.assertEquals(vals['x'], 5)

        p = Parser()
        p.add_int('x', default=5)
        vals = p._process_command_line(['-x', '6'])
        self.assertEquals(vals['x'], 6)
    
    def test_cast(self):
        p = Parser()
        p.add_option('x', cast=int)
        vals = p._process_command_line(['-x', '1'])
        self.assertEquals(vals['x'], 1)
        self.assertRaises(ArgumentError, p._process_command_line, ['-x', 'a'])

        p = Parser()
        p.add_int('x')
        vals = p._process_command_line(['-x', '1'])

    def test_required(self):
        p = Parser()
        p.add_option('x')
        p.set_required('x')
        self.assertRaises(MissingRequiredArgumentError,
                p._process_command_line, [])

    def test_requires(self):
        p = Parser()
        p.add_option('x')
        self.assertRaises(ValueError, p.set_requires, 'x', 'y')
        p.add_option('y')
        try:
            p.set_requires('x', 'y')
        except:
            self.fail()

        p = Parser()
        y = p.add_flag('y')
        p.add_flag('x').requires(y)

        self.assertRaises(DependencyError, p._process_command_line, ['-x'])

    def test_depends(self):
        def create():
            p = Parser()
            p.add_option('x')
            p.add_option('y')
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
            p.add_option('x')
            p.add_option('y')
            p.add_option('z')
            p.add_option('w')

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
            p.add_flag('x')
            p.add_flag('y')
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
            p.add_flag('x')
            p.add_flag('y')
            p.add_flag('z')

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
            p.add_flag('x')
            p.add_flag('y')
            p.add_flag('z')

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
        p.add_flag('x')
        p.add_flag('y')
        p.add_flag('z').requires('y')
        x = p['x']
        x.requires('y', 'z')
        self.assertRaises(DependencyError, p._process_command_line, ['-x'])
        self.assertRaises(DependencyError, p._process_command_line, ['-z'])
        p._process_command_line(['-y'])

        p = Parser()
        p.add_flag('x')
        p.add_flag('y').conflicts('x')
        self.assertRaises(ConflictError, p._process_command_line, ['-y', '-x'])

#    def test_index(self):
#        p = Parser()
#        p.add_option('x')
#        self.assertEquals(p['y'], None)
    
    def test_set_at_least_one_required(self):
        def create():
            p = Parser()
            p.add_option('x')
            p.add_option('y')
            p.add_option('z')

            p.set_at_least_one_required('x', 'y', 'z')
            return p

        create()._process_command_line(['-x', '1'])
        create()._process_command_line(['-y', '1'])
        create()._process_command_line(['-z', '1'])
        create()._process_command_line(['-x', '1', '-y', '1'])
        self.assertRaises(ManyAllowedNoneSpecifiedArgumentError, create()._process_command_line, [])

    def test_requires_n(self):
        p = Parser()
        p.add_flag('x')
        p.add_flag('y')
        p.add_flag('z')

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
            p.add_option('x')
            p.add_option('y')
            p.add_option('z')

            p.set_one_required(*'xyz')
            return p

        create()._process_command_line(['-x', '1'])
        create()._process_command_line(['-y', '1'])
        create()._process_command_line(['-z', '1'])

        self.assertRaises(ConflictError, create()._process_command_line, ['-x', '1', '-y', '1'])
        self.assertRaises(ManyAllowedNoneSpecifiedArgumentError, create()._process_command_line, [])

        p = Parser()
        p.add_flag('a')
        p.add_flag('b')
        p.set_one_required('a', 'b')
        p._process_command_line(['-b'])

if __name__ == '__main__':
    unittest.main()
