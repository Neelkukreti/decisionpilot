"""
Application configuration
Loads environment variables and provides app-wide settings
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# AWS Configuration
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')

# Bedrock Model IDs
NOVA_LITE_MODEL_ID = os.getenv('NOVA_LITE_MODEL_ID', 'amazon.nova-lite-v1')
NOVA_ACT_MODEL_ID = os.getenv('NOVA_ACT_MODEL_ID', 'amazon.nova-act-v1')
NOVA_EMBED_MODEL_ID = os.getenv('NOVA_EMBED_MODEL_ID', 'amazon.nova-embed-multimodal-v1')

# Database
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/decisionpilot')
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')

# Pinecone
PINECONE_API_KEY = os.getenv('PINECONE_API_KEY')
PINECONE_ENVIRONMENT = os.getenv('PINECONE_ENVIRONMENT', 'us-east-1-aws')
PINECONE_INDEX_NAME = os.getenv('PINECONE_INDEX_NAME', 'decisionpilot-meetings')

# Jira
JIRA_URL = os.getenv('JIRA_URL')
JIRA_EMAIL = os.getenv('JIRA_EMAIL')
JIRA_API_TOKEN = os.getenv('JIRA_API_TOKEN')

# Application
UPLOAD_DIR = os.getenv('UPLOAD_DIR', './uploads')
MAX_FILE_SIZE_MB = int(os.getenv('MAX_FILE_SIZE_MB', 100))

# Mock Mode (for testing without AWS/Pinecone/PostgreSQL)
MOCK_MODE = os.getenv('MOCK_MODE', 'true').lower() == 'true'

# PostgreSQL Configuration
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = int(os.getenv('DB_PORT', 5432))
DB_NAME = os.getenv('DB_NAME', 'decisionpilot')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'postgres')

# Pinecone Configuration
PINECONE_ENV = os.getenv('PINECONE_ENVIRONMENT', 'us-east-1-aws')
PINECONE_INDEX = os.getenv('PINECONE_INDEX_NAME', 'decisionpilot-meetings')

# Ensure upload directory exists
os.makedirs(UPLOAD_DIR, exist_ok=True)


class Config:
    """Configuration object for easy access"""
    AWS_REGION = AWS_REGION
    AWS_ACCESS_KEY_ID = AWS_ACCESS_KEY_ID
    AWS_SECRET_ACCESS_KEY = AWS_SECRET_ACCESS_KEY
    NOVA_LITE_MODEL_ID = NOVA_LITE_MODEL_ID
    NOVA_ACT_MODEL_ID = NOVA_ACT_MODEL_ID
    NOVA_EMBED_MODEL_ID = NOVA_EMBED_MODEL_ID
    DATABASE_URL = DATABASE_URL
    REDIS_URL = REDIS_URL
    PINECONE_API_KEY = PINECONE_API_KEY
    PINECONE_ENV = PINECONE_ENV
    PINECONE_INDEX = PINECONE_INDEX
    JIRA_URL = JIRA_URL
    JIRA_EMAIL = JIRA_EMAIL
    JIRA_API_TOKEN = JIRA_API_TOKEN
    UPLOAD_DIR = UPLOAD_DIR
    MAX_FILE_SIZE_MB = MAX_FILE_SIZE_MB
    MOCK_MODE = MOCK_MODE
    DB_HOST = DB_HOST
    DB_PORT = DB_PORT
    DB_NAME = DB_NAME
    DB_USER = DB_USER
    DB_PASSWORD = DB_PASSWORD


def get_config():
    """Get configuration object"""
    return Config()


print("✓ Configuration loaded")
print(f"  AWS Region: {AWS_REGION}")
print(f"  Upload Directory: {UPLOAD_DIR}")
print(f"  Mock Mode: {MOCK_MODE}")
