# Base image
FROM python:3.11-slim

# Metadata
LABEL maintainer="twanariens"
LABEL description="Afbeelding optimizer Flask API"
LABEL org.opencontainers.image.title="Ariens Design Optimizer"
LABEL org.opencontainers.image.description="Automatische beeldoptimalisatie via Flask API"
LABEL org.opencontainers.image.source="https://github.com/twanariens/ariensdesignoptimizer"
ARG VERSION
LABEL org.opencontainers.image.version="${VERSION}"

# Set working directory
WORKDIR /app

# Copy requirements & install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install system dependencies for optimalisatie
RUN apt-get update && apt-get install -y \
    webp \
    jpegoptim \
    pngquant \
 && rm -rf /var/lib/apt/lists/*

# Copy app code
COPY app.py .

# Environment default (kan overschreven worden in compose)
ENV API_TOKEN=default_token

# Expose poort voor Gunicorn
EXPOSE 5000

# Default command (Gunicorn server)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
