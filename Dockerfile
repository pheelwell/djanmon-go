# Backend Dockerfile (djanmongo/Dockerfile)
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install dependencies
# Copy only requirements first to leverage Docker cache
COPY ./djanmongo/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy project code
# Ensure this path is relative to the docker-compose.yml location if building from there
COPY ./djanmongo /app/

# Expose port
EXPOSE 8000

# Default command (can be overridden in docker-compose)
# CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
# Using a simple sleep for now; entrypoint script recommended for production/complex setups
CMD ["sleep", "infinity"] 