FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install --no-audit --no-fund
COPY . .
RUN npm run build

FROM nginx:alpine
ENV API_HOST=api \
    API_PORT=8000 \
    API_BASE_URL= \
    FRONTEND_HEALTH_PATH=/
COPY nginx.conf /etc/nginx/templates/default.conf.template
COPY docker-entrypoint/30-render-templates.sh /docker-entrypoint.d/30-render-templates.sh
RUN chmod +x /docker-entrypoint.d/30-render-templates.sh
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
