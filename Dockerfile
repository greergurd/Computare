# Use an official Python image with build tools
FROM python:3.11-slim

# Install build tools and system packages needed by scikit-learn
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    cython \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy project files into the container
COPY . .

# Install Python dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Expose the port your app runs on
EXPOSE 10000

# Command to run the app
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:10000"]
