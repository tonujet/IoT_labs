# MapView WebSocket server
# Runs the FastAPI/WebSocket server component (server.py)
# The Kivy GUI client (main.py) is intended to run on the host machine

FROM python:3.10-slim

WORKDIR /app

# Install system dependencies for scipy, pandas, matplotlib, etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libgfortran5 \
    libopenblas-dev \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --upgrade pip

# Copy requirements and install Python dependencies
# Use requirements_nokivy.txt which excludes Kivy and Windows-specific packages
COPY requirements_nokivy.txt .

# Install dependencies, excluding Windows-specific packages that are not needed in Linux containers
RUN pip install --no-cache-dir \
    $(grep -v -E "^(pypiwin32|pywin32)" requirements_nokivy.txt | tr '\n' ' ') \
    uvicorn

# Copy application source and data files
COPY server.py .
COPY car_cor.csv .

# Expose the WebSocket server port
EXPOSE 8000

# Run the FastAPI WebSocket server with Uvicorn
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
