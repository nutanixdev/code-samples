from setuptools import setup, find_packages

with open('readme.rst', encoding='UTF-8') as f:
    readme = f.read()

setup(
    name='get_host_details',
    version='1.0',
    description='Use Python and the Nutanix Prism Element v2.0 APIs to collect configuration details of a cluster\'s physical hosts.',
    long_description=readme,
    author='Aditya Gawade',
    author_email='aditya.gawade@nutanix.com',
    install_requires=[
        'requests',
        'urllib3',
        'XlsxWriter'
    ],
    packages=find_packages('.'),
    package_dir={'': '.'}
)
