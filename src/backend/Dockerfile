FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    MPLCONFIGDIR=/tmp/matplotlib \
    NLTK_DATA=/app/nltk_data

# Install system dependencies for OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create NLTK data directory and set permissions
RUN mkdir -p /app/nltk_data && \
    chmod -R 777 /app/nltk_data && \
    mkdir -p /tmp/matplotlib && \
    chmod -R 777 /tmp/matplotlib

# Change ownership to non-root user
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Pre-download NLTK data
RUN python -m nltk.downloader -d /app/nltk_data punkt averaged_perceptron_tagger_eng stopwords

# Expose port
EXPOSE 8000

# Run the application with hot-reloading in development
CMD ["uvicorn", "app.app:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]