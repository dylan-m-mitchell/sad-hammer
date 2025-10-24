FROM node:22-bookworm-slim AS build
WORKDIR /app
# Copy only package.json to let npm resolve platform-specific optional deps (Rollup) in Linux.
COPY frontend/package.json ./
RUN npm install --include=dev --no-audit --no-fund
COPY frontend/ .
# Ensure deps are in sync if package.json changed during copy
RUN npm install --include=dev --no-audit --no-fund
RUN npm run build

FROM nginx:alpine
WORKDIR /usr/share/nginx/html
RUN rm -rf ./*
COPY --from=build /app/dist/ ./
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
