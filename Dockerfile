FROM python:3.11-slim

# Keep Python output unbuffered (helpful for logs)
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system deps needed by some Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python requirements
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . /app

# Default command
CMD ["python", "main.py"]
