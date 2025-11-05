"""
Setup configuration for the Pretix Sortir! plugin
"""

from setuptools import setup, find_packages
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='pretix-sortir',
    version='1.0.0',
    description='Pretix plugin for Sortir! reduced fare integration via APRAS API',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/valentin-gosselin/pretix-sortir',
    author='Pretix Sortir Plugin Contributors',
    license='MIT',

    # Classification
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Plugins',
        'Framework :: Django',
        'Framework :: Django :: 3.2',
        'Intended Audience :: Developers',
        'Intended Audience :: Other Audience',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],

    keywords='pretix plugin sortir apras korrigo tickets',

    # Package configuration
    packages=['pretix_sortir'],
    include_package_data=True,

    # Dependencies
    install_requires=[
        'requests>=2.25.0',
        'django-extensions>=3.0.0',
        'cryptography>=41.0.0',
    ],

    python_requires='>=3.8',

    # Entry point for Pretix
    entry_points={
        'pretix.plugin': [
            'pretix_sortir = pretix_sortir:SortirPluginConfig',
        ],
    },

    # Package data
    package_data={
        'pretix_sortir': [
            'templates/pretix_sortir/*.html',
            'static/pretix_sortir/css/*.css',
            'static/pretix_sortir/js/*.js',
            'locale/*/LC_MESSAGES/*.po',
            'locale/*/LC_MESSAGES/*.mo',
        ],
    },

    # Project URLs
    project_urls={
        'Documentation': 'https://github.com/valentin-gosselin/pretix-sortir/blob/main/README.md',
        'Bug Reports': 'https://github.com/valentin-gosselin/pretix-sortir/issues',
        'Source': 'https://github.com/valentin-gosselin/pretix-sortir',
    },
)