# -*- coding: utf-8 -*-

import os
import re
import sys
import shutil
from io import open

from setuptools import setup

try:
    from pypandoc import convert

    def read_md(f):
        return convert(f, 'rst')
except ImportError:
    print("warning: pypandoc module not found, could not convert Markdown to RST")

    def read_md(f):
        return open(f, 'r', encoding='utf-8').read()


def get_version(package):
    """ Return package version as listed in `__version__` in `init.py`. """
    init_py = open(os.path.join(package, '__init__.py')).read()
    return re.search("__version__ = ['\"]([^'\"]+)['\"]", init_py).group(1)


version = get_version('lamb')


def get_packages(package):
    """ Return root package and all sub-packages. """
    return [dirpath
            for dirpath, dirnames, filenames in os.walk(package)
            if os.path.exists(os.path.join(dirpath, '__init__.py'))]


def get_package_data(package):
    """ Return all files under the root package, that are not in a package themselves. """
    walk = [(dirpath.replace(package + os.sep, '', 1), filenames)
            for dirpath, dirnames, filenames in os.walk(package)
            if not os.path.exists(os.path.join(dirpath, '__init__.py'))]

    filepaths = []
    for base, filenames in walk:
        filepaths.extend([os.path.join(base, filename)
                          for filename in filenames])
    return {package: filepaths}


if sys.argv[-1] == 'publish':
    try:
        import pypandoc
    except ImportError:
        print("pypandoc not installed.\nUse `pip install pypandoc`.\nExiting.")
    if os.system("pip freeze | grep twine"):
        print("twine not installed.\nUse `pip install twine`.\nExiting.")
        sys.exit()
    os.system("python setup.py sdist bdist_wheel")
    os.system("twine upload dist/*")
    print("You probably want to also tag the version now:")
    print("  git tag -a %s -m 'version %s'" % (version, version))
    print("  git push --tags")
    shutil.rmtree('dist')
    shutil.rmtree('build')
    shutil.rmtree('lamb.egg-info')
    sys.exit()


setup(
    name='lamb',
    version=version,
    description='Lamb framework',
    long_description=read_md('README.md'),
    url='https://bitbucket.org/kovsyk/lamb-core.git',
    author='Vladimir Konev',
    author_email='konev.vn@gmail.com',
    license='MIT',
    packages=get_packages('lamb'),
    package_data=get_package_data('lamb'),
    zip_safe=False,
    install_requires=[
        'django>=2.0.0,<3.0',
        'boto3',
        'celery==4.4.2',
        'dpath @ git+https://git@github.com/MrJuicyBacon/dpath-python#egg=dpath',
        'sqlalchemy',
        'sqlalchemy-utils',
        'Pillow<7.0.0',
        'requests',
        'python-magic',
        'python-dateutil',
        'phonenumbers',
        'ipaddress',
        'geopy',
        'furl',
        'pushjack',
        'xmltodict',
        'lazy',
        'lxml',
        'uwsgi',
        'babel',
        'django-crequest',
        'pymemcache',
        'dataclasses',
        'openpyxl',
        'django-ipware',
        'asgiref',
        'python-redis-lock'
    ]
)
