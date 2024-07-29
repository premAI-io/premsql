from setuptools import setup, find_packages

# Read the requirements from requirements.txt
with open('requirements.txt') as f:
    required = f.read().splitlines()

setup(
    name='text2sql',
    version='0.1.0',  # Change this as appropriate
    description='A package for text-to-SQL conversion',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/premAI-io/text2sql.git',
    author='Your Name',
    author_email='your.email@example.com',
    license='MIT',
    packages=find_packages(exclude=['tests', 'docs', 'examples']),
    install_requires=required,
    python_requires='>=3.6',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
    ],
    include_package_data=True,
)
