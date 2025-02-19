from setuptools import setup, find_packages

setup(
    name="civic_tracker",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "Flask==2.0.1",
        "Werkzeug==2.0.3",
        "Flask-SQLAlchemy==2.5.1",
        "SQLAlchemy==1.4.23",
        "beautifulsoup4==4.12.2",
        "feedparser==6.0.10",
        "Flask-Caching==2.1.0",
        "requests==2.31.0",
    ],
    python_requires=">=3.8",
)
