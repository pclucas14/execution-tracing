from setuptools import setup, find_packages

setup(
    name="my-tracer",
    version="0.1.0",
    description="Python execution tracer",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    entry_points={
        'console_scripts': [
            'trace_program=cli.main:main',
            'trace_pytest=cli.main:trace_pytest_main',
        ],
    },
    python_requires='>=3.6',
    install_requires=[
        # Add any dependencies here if needed
    ],
)