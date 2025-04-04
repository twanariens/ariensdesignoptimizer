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

# Start the app
CMD ["python", "app.py"]