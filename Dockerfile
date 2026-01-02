# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container at /app
COPY . .

# Create a volume for persistent data and results
VOLUME ["/app/results", "/app/data"]

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Expose ports for Streamlit and other services
EXPOSE 8501 8000

# Define environment variable for results directory to match container path
ENV TRADINGAGENTS_RESULTS_DIR=/app/results

# Default command to run the CLI (can be overridden)
CMD ["python", "-m", "cli.main"]
