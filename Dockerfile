FROM python:3.9

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create necessary directories
RUN mkdir -p temp static templates

# Expose port
EXPOSE 8000

# Command to run the application
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
