#from version import getversion

from distutils.core import setup

setup(name='blargs',
      version='0.2.10a',
#      version=getversion(),
      py_modules=['blargs'],
      description='Blargs command line parser',
      author='Karl Gyllstrom',
      author_email='karl.gyllstrom+blargs@gmail.com',
      url='https://bitbucket.org/gyllstromk/blargs',
     )

# deploy
# export LC_ALL='en.UTF-8'
# python setup.py sdist upload
