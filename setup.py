"""
Blargs!
-------

Blargs command line parser.
"""
import blargs

import os
from setuptools import setup

setup(name='blargs',
      version=blargs.__version__,
      url='https://github.com/gyllstromk/blargs',
      license='BSD',
      author='Karl Gyllstrom',
      author_email='karl.gyllstrom+blargs@gmail.com',
      description='Blargs command line parser',
      long_description=open(os.path.join(os.path.dirname(__file__), 'README.rst')).read(),
      py_modules=['blargs'],
      include_package_data=True,
      platforms='any',
      test_suite='test',
      classifiers = [
          'Intended Audience :: Developers',
          'License :: OSI Approved :: BSD License',
          'Programming Language :: Python :: 2.6',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3.1',
          'Programming Language :: Python :: 3.2',
          'Topic :: Software Development :: Libraries :: Python Modules',
       ]
     )
