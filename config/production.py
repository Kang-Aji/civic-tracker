import os

# Production configuration
DEBUG = False
TESTING = False

# Database configuration
SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///civic_tracker.db')
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Security settings
SECRET_KEY = os.getenv('SECRET_KEY')  # Make sure to set this in environment
SESSION_COOKIE_SECURE = True
REMEMBER_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True

# Cache configuration
CACHE_TYPE = 'redis'
CACHE_REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
CACHE_DEFAULT_TIMEOUT = 3600

# Rate limiting
RATELIMIT_ENABLED = True
RATELIMIT_STORAGE_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/1')

# Logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
