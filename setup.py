from setuptools import setup, find_packages

setup(
    name="ai-personal-knowledge-base",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "streamlit",
        "python-dotenv",
        "chromadb",
        "fastembed",
        "notion-client",
        "google-api-python-client",
        "google-auth-httplib2",
        "google-auth-oauthlib",
        "pdfplumber",
        "python-docx",
        "requests",
        "groq",
        "loguru",
        "numpy",
    ],
)
