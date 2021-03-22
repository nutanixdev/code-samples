from setuptools import setup, find_packages

with open('readme.rst', encoding='UTF-8') as f:
    readme = f.read()

setup(
    name='create-detailed-vm',
    version='1.1',
    description='Use the Prism Central API to create a detailed Virtual Machine.',
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