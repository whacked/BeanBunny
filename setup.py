from setuptools import setup

setup(
    name="BeanBunny",
    version = "0.0.1",
    description = "assorted python files to interface with assorted file formats",
    packages = ["BeanBunny", "BeanBunny.io", "BeanBunny.conversion", "BeanBunny.data"],
    install_requires = [
        'flatten-dict',
    ],
)
