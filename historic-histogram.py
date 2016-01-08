import shutil
import subprocess

number = 0
logs = subprocess.check_output(["git", "log", "--oneline"])
logs = logs.strip().split('\n')

failed = open('failed_shas.txt', 'w')
skip = []
try:
    with open('skip_shas.txt', 'r') as f:
        skip = f.readlines()
except:
    pass

skip = [
    '78855e4efa0c92d6b0db09758a8983e9764d0d8d',
    'fc3665d34573ba618c1e5805c60c0ff7f50793f3',
    '53db2cd2a804850ad11a07a83e318ae75a873ed0',
]

for i, line in enumerate(logs):
    number += 1
    sha = line.split()[0]
    if sha in skip:
        print "Explicitly skipping:", sha
        continue

    print "doing:", sha
    try:
        subprocess.check_call(['git', 'checkout', sha])
        subprocess.check_call(['/home/mike/src/cuv-ner/clean-pyc'])
        # XXX needs to clean out *.pyc too (for some cases)
        subprocess.call(['pip', 'install', '-r', 'dev-requirements.txt'])
        subprocess.call(['pip', 'install', '-r', 'requirements.txt'])
        subprocess.check_call(['pip', 'install', '-e', '.'])
        subprocess.check_call(['make', 'coverage'])
        subprocess.check_call(['cuv', 'pixel'])
        #subprocess.check_call(['python', '/home/mike/src/pycoven/histogram-coverage.py', 'txtorcon'])
        shutil.move('coverage_cascade_pixel.png', 'coverage-%04d-%s.png' % (number, sha))
    except subprocess.CalledProcessError as e:
        print '{} failed because {}'.format(sha, e)
        failed.write('{}\n'.format(sha))
        failed.flush()
        continue
