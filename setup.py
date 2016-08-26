#!/usr/bin/env python

############################################################################
# Copyright (c) 2015-2016 Saint Petersburg State University
# Copyright (c) 2011-2015 Saint Petersburg Academic University
# All Rights Reserved
# See file LICENSE for details.
############################################################################

import os
import sys
from glob import glob
from os.path import join, isfile, abspath, dirname, isdir
import shutil

from libs import qconfig, qutils
qconfig.check_python_version()

from libs.log import get_logger
logger = get_logger(qconfig.LOGGER_DEFAULT_NAME)
logger.set_up_console_handler(debug=True)

try:
    from setuptools import setup, find_packages
except:
    logger.warn('Possibly outdated setuptool. Using setuptools built into '
                'the QUAST package instead.')
    from site import addsitedir
    addsitedir(os.path.join(qconfig.LIBS_LOCATION, 'site_packages'))
    from setuptools import setup, find_packages

from libs.search_references_meta import download_all_blast_binaries, download_blastdb
from libs.glimmer import compile_glimmer
from libs.gage import compile_gage
from libs.ca_utils.misc import compile_aligner
from libs.ra_utils import compile_reads_analyzer_tools, download_manta, compile_bwa, compile_bedtools

name = 'quast'
quast_package = 'libs'


if abspath(dirname(__file__)) != abspath(os.getcwd()):
    logger.error('Please, change to ' + dirname(__file__) + ' before running setup.py')
    sys.exit()


if sys.argv[-1] in ['clean', 'sdist']:
    logger.info('Cleaning up binary files...')
    compile_aligner(logger, only_clean=True)
    compile_glimmer(only_clean=True)
    compile_gage(only_clean=True)
    compile_bwa(only_clean=True)
    compile_bedtools(only_clean=True)
    for fpath in [fn for fn in glob(join('libs', '*.pyc'))]: os.remove(fpath)
    for fpath in [fn for fn in glob(join('libs', 'html_saver', '*.pyc'))]: os.remove(fpath)
    for fpath in [fn for fn in glob(join('libs', 'site_packages', '*', '*.pyc'))]: os.remove(fpath)

    if sys.argv[-1] == 'clean':
        if isdir('build'):
            shutil.rmtree('build')
        if isdir('dist'):
            shutil.rmtree('dist')
        if isdir('quast.egg-info'):
            shutil.rmtree(name + '.egg-info')
        download_manta(logger, only_clean=False)
        download_all_blast_binaries(logger, only_clean=True)
        download_blastdb(logger, only_clean=True)
        logger.info('Done.')
        sys.exit()


if sys.argv[-1] == 'test':
    os.system('quast.py --test')
    sys.exit()


def write_version_py():
    version_py = os.path.join(os.path.dirname(__file__), quast_package, 'version.py')

    with open('VERSION.txt') as f:
        v = f.read().strip().split('\n')[0]
    try:
        import subprocess
        git_revision = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).rstrip()
    except:
        git_revision = ''
        pass
    with open(version_py, 'w') as f:
        f.write((
            '# Do not edit this file, pipeline versioning is governed by git tags\n' +
            '__version__ = \'' + v + '\'\n' +
            '__git_revision__ = \'' + git_revision + '\''))
    return v

version = write_version_py()


if sys.argv[-1] == 'tag':
    cmdl = 'git tag -a %s -m "Version %s" && git push --tags' % (version, version)
    os.system(cmdl)
    sys.exit()


if sys.argv[-1] == 'publish':
    cmdl = 'python setup.py sdist && python setup.py sdist upload'
    os.system(cmdl)
    sys.exit()


def find_package_files(dirpath, package=quast_package):
    paths = []
    for (path, dirs, fnames) in os.walk(join(package, dirpath)):
        for fname in fnames:
            paths.append(qutils.relpath(join(path, fname), package))
    return paths


install_full = False
if sys.argv[-1] == 'install_full':
    install_full = True
    sys.argv[-1] = 'install'


if sys.argv[-1] in ['install', 'develop', 'build', 'build_ext']:
    logger.info('* Compiling aligner *')
    compile_aligner(logger)
    logger.info('* Compiling Glimmer *')
    compile_glimmer()
    logger.info('* Compiling GAGE *')
    compile_gage()
    if install_full:
        logger.info('* Compiling read analisis tools *')
        compile_reads_analyzer_tools(logger)
        logger.info('* Downloading SILVA 16S rRNA gene database and BLAST *')
        download_all_blast_binaries(logger)
        download_blastdb(logger)

    logger.info('')


if qconfig.platform_name == 'macosx':
    nucmer_files = find_package_files('E-MEM-osx')
    sambamba_files = [join('sambamba', 'sambamba_osx')]
else:
    nucmer_files = find_package_files('MUMmer3.23-linux') + find_package_files('E-MEM-linux')
    sambamba_files = [join('sambamba', 'sambamba_linux')]

bwa_files = [
    join('bwa', fp) for fp in os.listdir(join(quast_package, 'bwa'))
    if isfile(join(quast_package, 'bwa', fp)) and fp.startswith('bwa')]
full_install_tools = (
    bwa_files +
    find_package_files('manta') +
    find_package_files('blast') +
    ['bedtools/bin/*'] +
    sambamba_files
)

setup(
    name=name,
    version=version,
    author='Alexei Gurevich',
    author_email='alexeigurevich@gmail.com',
    description='Genome assembly evaluation tool',
    long_description='''QUAST evaluates genome assemblies.
It works both with and without references genome.
The tool accepts multiple assemblies, thus is suitable for comparison.''',
    keywords=['bioinformatics', 'genome assembly', 'metagenome assembly', 'visualization'],
    url='quast.sf.net',
    license='GPLv2',

    packages=find_packages(),
    package_data={
        quast_package:
            find_package_files('html_saver') +
            nucmer_files +
            find_package_files('genemark/' + qconfig.platform_name) +
            find_package_files('genemark-es/' + qconfig.platform_name) +
            find_package_files('genemark-es/lib') +
            find_package_files('glimmer') +
            find_package_files('gage') +
           (full_install_tools if install_full else [])
    },
    include_package_data=True,
    zip_safe=False,
    scripts=['quast.py', 'metaquast.py', 'icarus.py'],
    data_files=[
        ('', [
            'README.txt',
            'CHANGES.txt',
            'VERSION.txt',
            'LICENSE.txt',
            'manual.html',
        ]),
        ('test_data', find_package_files('test_data', package='')),
    ],
    install_requires=[
        'matplotlib',
        'joblib',
        'simplejson',
    ],
    classifiers=[
        'Environment :: Console',
        'Environment :: Web Environment',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
        'Natural Language :: English',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: POSIX',
        'Operating System :: Unix',
        'Programming Language :: Python',
        'Programming Language :: JavaScript',
        'Topic :: Scientific/Engineering',
        'Topic :: Scientific/Engineering :: Bio-Informatics',
        'Topic :: Scientific/Engineering :: Visualization',
    ],
)


if sys.argv[-1] == 'install':
    if not install_full:
        logger.info('''
----------------------------------------------
QUAST version {} installation complete.

For help in running QUAST, please see the documentation available
at quast.bioinf.spbau.ru/manual.html, or run quast.py --help

Usage:
$ quast.py test_data/contigs_1.fasta \\
           test_data/contigs_2.fasta \\
        -R test_data/reference.fasta.gz \\
        -G test_data/genes.txt \\
        -o output_directory
----------------------------------------------'''.format(version))

    else:
        logger.info('''
----------------------------------------------
QUAST version {} installation complete.

The full package is installed, with the features for reference
sequence detection in MetaQUAST, and structural variant detection
for misassembly events refinement.

For help in running QUAST, please see the documentation available
at quast.bioinf.spbau.ru/manual.html, or run quast.py --help

Usage:
$ quast.py test_data/contigs_1.fasta \\
           test_data/contigs_2.fasta \\
        -R test_data/reference.fasta.gz \\
        -G test_data/genes.txt \\
        -1 test_data/reads1.fastq.gz -2 test_data/reads2.fastq.gz
        -o output_directory
----------------------------------------------'''.format(version))
