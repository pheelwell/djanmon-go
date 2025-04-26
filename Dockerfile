# --- Stage 1: Build Frontend ---
FROM node:18-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy frontend package files
COPY frontend/package.json frontend/package-lock.json* ./

# Install frontend dependencies
RUN npm install

# Copy the rest of the frontend code
COPY frontend/ ./

# Build the frontend
# Ensure your build script outputs to the 'dist' directory
RUN npm run build

# --- Stage 2: Build Backend ---
FROM python:3.11-slim AS backend-builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app

# Install system dependencies if needed (e.g., for postgresql client)
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     build-essential libpq-dev \
#  && rm -rf /var/lib/apt/lists/*

# Copy the requirements file first to leverage Docker cache
COPY djanmongo/requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entrypoint script
COPY ./entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Copy the backend application code (djanmongo directory)
COPY ./djanmongo /app/djanmongo

# --- Copy Built Frontend Assets ---
# Copy the built frontend from the previous stage into a place
# where Django's collectstatic can find it.
COPY --from=frontend-builder /app/frontend/dist /app/frontend_dist/

# --- Static Files ---
# Ensure the static_cdn directory exists before collectstatic runs
RUN mkdir -p /app/djanmongo/static_cdn

# Ensure STATIC_ROOT is set in settings.py, e.g., /app/staticfiles
# Collect static files (including the copied frontend assets)
RUN python djanmongo/manage.py collectstatic --noinput --clear

# Expose the port Gunicorn will run on
EXPOSE 8000

# Set the entrypoint script to run migrations and then start the main process
ENTRYPOINT ["/app/entrypoint.sh"]

# Specify the command to run your application using Gunicorn
# Ensure djanmongo/wsgi.py exists and is configured
CMD ["gunicorn", "--pythonpath", "djanmongo", "djanmongo.wsgi:application", "--bind", "0.0.0.0:8000"] 