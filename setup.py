import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name='junkie',
    version='3.0.0.dev1',
    packages=setuptools.find_packages(exclude="test"),
    author='Stefan Richter',
    description='A dependency injection library for beginners',
    url="https://github.com/sealor/junkie",
    long_description=long_description,
    long_description_content_type="text/markdown",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.5',
)
