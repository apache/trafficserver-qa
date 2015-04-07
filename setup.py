try:
    from setuptools import setup
    from setuptools import find_packages
except ImportError:
    from distutils.core import setup

config = {
    'description': 'QA framework for Apache TrafficServer',
    'author': 'Thomas Jackson',
    'url': 'https://github.com/jacksontj/tsqa',
    #'download_url': 'Where to download it.',
    'author_email': 'jacksontj.89@gmail.com',
    'version': '0.1',
    'install_requires': ['nose', 'unittest2', 'requests', 'flask', 'httpbin'],
    'packages': ['tsqa'],
    'scripts': [],
    'name': 'tsqa'
}

setup(**config)
