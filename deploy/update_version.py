main = 'blargs.py'
tmp = '_tmp.py'

with open(main) as f:
    lines = f.readlines()
    version = lines[-1].split()
    assert version[0] == '__version__'
    digits = version[2].split('\'')[1].split('.')
    minor = digits[-1]
    minor_digit = ''
    if not minor[-1].isdigit():
        minor_digit = minor[-1]
        minor = minor[:-1]

    version = '.'.join(digits[:-1] + [str(int(minor) + 1) + minor_digit])

with open(tmp, 'w') as f:
    f.write(''.join(lines[:-1] + ['__version__ = \'{0}\'\n'.format(version)]))

with open(main) as f1, open(tmp) as f2:
    lines1, lines2 = f1.readlines(), f2.readlines()
    assert lines1[:-1] == lines2[:-1]
    assert lines1[-1] != lines2[-1]

import os
os.rename(tmp, main)
