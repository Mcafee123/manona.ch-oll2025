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

# Install system dependencies for OpenCV and additional tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libmagic-dev \
    poppler-utils \
    tesseract-ocr \
    libreoffice \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install pandoc (ensure version 2.14.2 or newer) for both arm64 and amd64
RUN apt-get update && apt-get install -y --no-install-recommends wget && \
    ARCH=$(dpkg --print-architecture) && \
    if [ "$ARCH" = "arm64" ]; then \
        wget https://github.com/jgm/pandoc/releases/download/2.14.2/pandoc-2.14.2-linux-arm64.tar.gz && \
        tar -xvzf pandoc-2.14.2-linux-arm64.tar.gz --strip-components 1 -C /usr/local/ && \
        rm pandoc-2.14.2-linux-arm64.tar.gz; \
    elif [ "$ARCH" = "amd64" ]; then \
        wget https://github.com/jgm/pandoc/releases/download/2.14.2/pandoc-2.14.2-linux-amd64.tar.gz && \
        tar -xvzf pandoc-2.14.2-linux-amd64.tar.gz --strip-components 1 -C /usr/local/ && \
        rm pandoc-2.14.2-linux-amd64.tar.gz; \
    else \
        echo "Unsupported architecture: $ARCH" && exit 1; \
    fi && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

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