from setuptools import setup

setup(
    name='PyNF',
    url='https://github.com/tiborauer/pynf',
    author='Tibor Auer',
    author_email='tibor.auer@gmail.com',
    
    packages=['pynf'],
    install_requires=[],
    
    version='0.1',
    license='GPL-3.0',
    description='Python based games for neurofeedback training',
    
    long_description=open('README.md').read(),
)