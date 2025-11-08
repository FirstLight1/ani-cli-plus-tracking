from setuptools import setup

setup(
    name='ani-cli-tracker',
    version='0.1.0',
    py_modules=['updateAnilist'],
    install_requires=[
        'requests>=2.31.0',
        'python-dotenv>=1.0.0',
        'requests-oauthlib>=1.3.1',
    ],
    entry_points={
        'console_scripts': [
            'ani-tracker=updateAnilist:main',
        ],
    },
    python_requires='>=3.8',
)