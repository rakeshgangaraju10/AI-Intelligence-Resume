# Production image: build the SPA with Node, serve it with nginx.
# nginx also reverse-proxies /api and /admin to the Django container, so the
# browser sees one origin (session + CSRF cookies work without CORS).

FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* ./
# Use the lockfile when it exists (reproducible); fall back to package.json ranges.
RUN if [ -f package-lock.json ]; then npm ci --no-audit --no-fund; \
    else npm install --no-audit --no-fund; fi
COPY . .
RUN npm run build

FROM nginx:1.28-alpine
ENV BACKEND_UPSTREAM=backend:8000
# The official image runs envsubst on /etc/nginx/templates/*.template at start,
# substituting only variables that are set (nginx's own $vars are untouched).
COPY nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY nginx/spa-headers.conf /etc/nginx/snippets/spa-headers.conf
COPY nginx/proxy_params_careerforge /etc/nginx/proxy_params_careerforge
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
