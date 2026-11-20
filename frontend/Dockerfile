# Easy Diligence frontend: built by Node, then served as static files by nginx.
# Built by docker-compose.yml (service `frontend`); the versions are in VERSION.md.
# The routing (/api to the backend) is the proxy's, not this image's.

FROM node:24.22.3-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.30.7-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
