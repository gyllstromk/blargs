def getversion():
    import os
    import sys
    for item in sys.path:
        try:
            return open(item + os.path.sep + 'VERSION').read().rstrip()
        except IOError:
            pass


def _getversion(full):
    import subprocess
    pipe = subprocess.Popen(['git', 'tag'], stdout=subprocess.PIPE)
    val = pipe.communicate()[0].splitlines()[-1].rstrip()
    if full:
        return val

    major, minor, sub = val.split('.')
    return '.'.join((major, minor)), sub


if __name__ == '__main__':
    from blargs import Parser

    with Parser(locals()) as p:
        p.flag('update')
        p.flag('get')

    if get:
        print getversion()
    elif update:
        version = getversion()
        toks = version.split('.')
        val = str(int(toks[-1][:-1]) + 1) + toks[-1][-1]
        open('VERSION', 'w').write('.'.join(toks[:2] + [val]) + '\n')
