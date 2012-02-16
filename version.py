def getversion(full):
    import subprocess
    pipe = subprocess.Popen(['git', 'tag'], stdout=subprocess.PIPE)
    val = pipe.communicate()[0].splitlines()[-1].rstrip()
    if full:
        return val

    major, minor, sub = val.split('.')
    return '.'.join((major, minor)), sub


if __name__ == '__main__':
    print getversion(True)
