# Stage 1: Build the React app
FROM node:20-alpine AS build

WORKDIR /app

# Install dependencies
COPY package.json package-lock.json ./
RUN npm install

# Build the app with VITE_API_URL empty so it uses relative paths
COPY . .
ENV VITE_API_URL=""
RUN npm run build

# Stage 2: Serve with Nginx
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
# Nginx configuration will be mounted via docker-compose
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
