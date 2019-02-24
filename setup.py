# https://packaging.python.org/tutorials/distributing-packages/
# Always prefer setuptools over distutils
from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='django-sakkada',

    # Versions should comply with PEP440. For a discussion on single-sourcing
    # the version across setup.py and the project code, see
    # https://packaging.python.org/en/latest/single_source_version.html
    version='.'.join(map(str, __import__('sakkada').VERSION)),

    description='Collection of custom extensions for the Django Framework',
    long_description=long_description,

    # The project's main homepage.
    url='https://github.com/sakkada/django-sakkada',

    # Author details
    author='Murat Guchetl',
    author_email='gmurka@gmail.com',

    license='MIT',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 4 - Beta',

        # Indicate who your project is intended for
        'Intended Audience :: Developers',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Database',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 2.0',
        'Framework :: Django :: 2.1',

        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: MIT License',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',

        'Operating System :: OS Independent',

        'Natural Language :: English',
    ],

    # What does your project relate to?
    keywords='django content database admin template tools',

    # You can just specify the packages manually here if your project is
    # simple. Or you can use find_packages().
    #   packages=find_packages(exclude=['contrib', 'docs', 'tests']),
    #   packages=['application',],
    packages=find_packages(exclude=['docs', 'tests',]),

    # List run-time dependencies here. These will be installed by pip when
    # your project is installed. For an analysis of "install_requires" vs pip's
    # requirements files see:
    # https://packaging.python.org/en/latest/requirements.html
    install_requires=[
        'django>=2.0.0,<3.0.0',
    ],

    # Extras (optional features with their own dependencies)
    extras_require={
        'testing': [
            'coverage>=3.7.0',
            'flake8>=2.2.0',
            'isort>=4.2.5',
        ],
    },

    python_requires='>=3.5,<4',

    include_package_data=True,
    zip_safe=False
)
