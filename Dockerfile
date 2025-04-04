# Base image
FROM python:3.11-slim

# Metadata & labels
LABEL maintainer="twanariens"
LABEL description="Afbeelding optimizer Flask API"
LABEL org.opencontainers.image.title="Ariens Design Optimizer"
LABEL org.opencontainers.image.description="Automatische beeldoptimalisatie via Flask API"
LABEL org.opencontainers.image.source="https://github.com/twanariens/ariensdesignoptimizer"
ARG VERSION
LABEL org.opencontainers.image.version="${VERSION}"

# Set working directory
WORKDIR /app

# Install image optimization dependencies
RUN apt-get update && apt-get install -y \
    webp \
    jpegoptim \
    pngquant \
 && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app.py .

# Expose port for Flask API via Gunicorn
EXPOSE 5000

# Default environment (can be overridden by docker-compose)
ENV API_TOKEN=default_token

# Run app using Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
