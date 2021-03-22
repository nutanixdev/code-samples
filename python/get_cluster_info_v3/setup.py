from setuptools import setup, find_packages

with open('readme.rst', encoding='UTF-8') as f:
    readme = f.read()

setup(
    name='nutanix-cluster-info',
    version='3.1',
    description='Use the Prism Central API to get Nutanix environment info, then generate an HTML report from it.',
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
