import os
import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()


class CleanCommand(setuptools.Command):
    """ Custom clean command to tidy up the project root. """
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        os.system('rm -vrf ./build ./dist ./*.pyc ./*.tgz ./*.egg-info')


class PrepublishCommand(setuptools.Command):
    """ Custom prepublish command. """
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        os.system('python setup.py clean')
        os.system('python setup.py sdist bdist_wheel')


setuptools.setup(
    cmdclass={
        'clean': CleanCommand,
        'prepublish': PrepublishCommand,
    },
    name='linkedin-dl',
    version='0.0.7',
    url='https://github.com/jmgomezsoriano/linkedin-dl',
    license='LGPL2',
    author='José Manuel Gómez Soriano',
    author_email='jmgomez.soriano@gmail.com',
    long_description=long_description,
    long_description_content_type='text/markdown',
    description='LinkedIn video downloader.',
    packages=setuptools.find_packages(exclude=["test"]),
    package_dir={'linkedin': 'linkedin'},
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
    install_requires=[
        'requests==2.28.0',
        'moviepy==1.0.3',
        'mysmallutils>=1.1.2,<1.2',
        'proglog==0.1.10'
    ],
    entry_points={
        'console_scripts': [
            'linkedin-dl=linkedin.download:main'
        ]
    }
)
