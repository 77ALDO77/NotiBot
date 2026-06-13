# Stage 1: build Angular app
FROM node:22-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY angular.json tsconfig.json tsconfig.app.json tsconfig.spec.json ./
COPY public/ ./public/
COPY src/ ./src/

RUN npm run build

# Stage 2: serve with nginx
FROM nginx:alpine AS runtime

COPY nginx.conf /etc/nginx/conf.d/default.conf

COPY --from=builder /app/dist/frontend/browser /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
