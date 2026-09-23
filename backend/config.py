import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-me')
    DATABASE_URL = os.getenv('DATABASE_URL')
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB
    JWT_EXPIRY_DAYS = 7
    FLASK_ENV = os.getenv('FLASK_ENV', 'production')

    # CORS - allow production domains
    CORS_ORIGINS = [
        'http://localhost:5500',
        'http://127.0.0.1:5500',
        'https://kitchen-analytics.pages.dev',       # Cloudflare Pages default
        'https://app.kitchenanalytics.in',            # Custom domain
        'https://kitchenanalytics.in',
    ]

    # Rate limiting
    RATELIMIT_STORAGE_URI = os.getenv('RATELIMIT_STORAGE_URI', 'memory://')
    RATELIMIT_DEFAULT = "200 per hour"
    RATELIMIT_AUTH = "20 per hour"

    # Payments (add later)
    RAZORPAY_KEY_ID = os.getenv('RAZORPAY_KEY_ID', '')
    RAZORPAY_KEY_SECRET = os.getenv('RAZORPAY_KEY_SECRET', '')




    