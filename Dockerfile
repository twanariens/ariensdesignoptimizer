# Base image
FROM python:3.11-slim

# Metadata (optioneel)
LABEL maintainer="twanariens"
LABEL version="1.0"
LABEL description="Afbeelding optimizer Flask API"

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY app.py .

# Expose port (belangrijk voor transparantie)
EXPOSE 5000

# Use environment variable for token
ENV API_TOKEN=default_token

#install dependencies
RUN apt-get update && apt-get install -y \
    webp \
    jpegoptim \
    pngquant \
 && rm -rf /var/lib/apt/lists/*

#Extra information for certain OS
LABEL org.opencontainers.image.title="Ariens Design Optimizer" \
      org.opencontainers.image.description="Automatische beeldoptimalisatie via Flask API" \
      org.opencontainers.image.source="https://github.com/twanariens/ariensdesignoptimizer"
ARG VERSION
LABEL org.opencontainers.image.version="${VERSION}"

# Start the app
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]