# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set container name
LABEL name="fme-tech-debt-validator"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy app source code to .
COPY app/ /myapp/

# Copy test files and config
COPY tests/ /mytests/
COPY pytest.ini /mytests/

# Entry point to run the CI test script
ENTRYPOINT ["python", "/myapp/main.py"]
