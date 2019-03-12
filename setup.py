from setuptools import setup

setup(
    name='PyNF',
    url='https://github.com/tiborauer/pynf',
    author='Tibor Auer',
    author_email='tibor.auer@gmail.com',
    
    packages=['pynf', 'pynf.flappybird'],
    include_package_data=True,
    install_requires=['numpy','scipy','matplotlib','pydicom','pyniexp@git+https://github.com/tiborauer/pyniexp.git'],
	
    version='0.8.2',
    license='GPL-3.0',
    description='Python based games for neurofeedback training',
    
    long_description=open('README.md').read(),
)
