# Easy Diligence entry point: nginx in front of the frontend and the backend.
# Built by docker-compose.yml (service `proxy`); the versions are in VERSION.md.

FROM nginx:1.30.7-alpine

# The services behind, and the proxies trusted in front, as docker compose has
# them: the services by their compose name, nothing trusted in front.
# The clouds set their own (infra/azure/apps.tf, infra/aws/services.tf).
# NGINX_ENTRYPOINT_LOCAL_RESOLVERS has the image export the container's DNS
# server as NGINX_LOCAL_RESOLVERS, for the resolver of the template.
ENV BACKEND_UPSTREAM=http://backend:8000 \
    FRONTEND_UPSTREAM=http://frontend:80 \
    TRUSTED_PROXIES=127.0.0.1/32 \
    NGINX_ENTRYPOINT_LOCAL_RESOLVERS=1

# Rendered into /etc/nginx/conf.d/default.conf when the container starts.
COPY default.conf.template /etc/nginx/templates/default.conf.template
