from blargs import Parser

import os
import subprocess
import sys


def cmd(command):
    subprocess.call(command.split())


def update_version(major):
    tmpname = 'blargs_update.py'

    lines = open('blargs.py').readlines()
    if '__version__' not in lines[-1]:
        print('last line not version')
        sys.exit(1)

    version = lines[-1].split('=')[1].strip()[1:-1].split('.')
    if major:
        version[1] = int(version[1]) + 1
    else:
        modifier = version[2][-1]
        version[2] = str(int(version[2][:-1]) + 1) + modifier

    version = '__version__ = \'%s\'\n' % '.'.join(version)
    open(tmpname, 'w').write(''.join(lines[:-1] + [version]))
    out = subprocess.Popen(['diff', 'blargs.py', tmpname], stdout=subprocess.PIPE)
    diff = out.communicate()[0].splitlines()
    if len(diff) != 4:
        os.remove(tmpname)
    else:
        os.rename(tmpname, 'blargs.py')


def git_merge():
    cmd('git commit -a -m \'deployment\'')
    cmd('git checkout master')
    cmd('git merge exp')
    cmd('git push')


def publish():
    cmd('python setup.py sdist upload')


def cleanup():
    cmd('git checkout exp')


def test():
    cmd('./deploy/test')


if __name__ == '__main__':
    with Parser(locals()) as p:
        p.flag('major')

    update_version(major)
    git_merge()
    publish()
    test()
    cleanup()
