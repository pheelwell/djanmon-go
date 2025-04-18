# Frontend Dockerfile (frontend/Dockerfile)
FROM node:20-alpine

# Set work directory
WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm install

# Copy remaining frontend code
COPY . .

# Expose port
EXPOSE 5173

# Default command to run dev server
CMD ["npm", "run", "dev"] 