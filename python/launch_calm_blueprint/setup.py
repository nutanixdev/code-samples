from setuptools import setup, find_packages

with open('readme.rst', encoding='UTF-8') as f:
    readme = f.read()

setup(
    name='launch_calm_blueprint_v3',
    version='1.0',
    description='Use Prism Central v3 API to launch a Nutanix Calm blueprint.',
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
