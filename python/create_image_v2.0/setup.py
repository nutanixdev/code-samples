from setuptools import setup, find_packages

with open('readme.rst', encoding='UTF-8') as f:
    readme = f.read()

setup(
    name='create-image-v2.0',
    version='1.1',
    description='Use the Prism Element v2.0 API to create a disk image.',
    long_description=readme,
    author='Chris Rasmussen',
    author_email='crasmussen@nutanix.com',
    install_requires=[
        'requests',
        'urllib3'
    ],
    packages=find_packages('.'),
    package_dir={'': '.'}
)