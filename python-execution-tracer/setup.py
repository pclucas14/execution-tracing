from setuptools import setup, find_packages

setup(
    name="python-execution-tracer",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="A command-line program to extract the runtime execution trace of any Python program, logging function calls and their arguments.",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        # Add runtime dependencies here
    ],
    extras_require={
        "dev": [
            # Add development dependencies here
        ],
    },
    entry_points={
        "console_scripts": [
            "tracer=cli.main:main",  # Assuming main function in cli/main.py
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)