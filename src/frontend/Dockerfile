# Stage 1: Build the Vue.js application
FROM node:18-alpine AS builder

# Set working directory
WORKDIR /app

# Copy package files and install dependencies
COPY package.json package-lock.json ./
RUN npm install

# Copy the rest of the application files
COPY . .

# Build the Vue.js app for production
RUN npm run build

# Stage 2: Serve the built files with NGINX
FROM nginx:1.27.4-alpine-slim

# Set working directory to NGINX's default static file location
WORKDIR /usr/share/nginx/html

# Remove default NGINX static assets
RUN rm -rf ./*

# Copy the built files from the builder stage
COPY --from=builder /app/dist .

# Expose port 80
EXPOSE 80

# Run NGINX in the foreground
ENTRYPOINT ["nginx", "-g", "daemon off;"]
