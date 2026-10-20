# nginx получает готовый frontend/dist; npm-зависимости устанавливаются вне Docker.
FROM nginx:alpine

RUN rm -f /etc/nginx/conf.d/default.conf
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf
COPY frontend/dist/ /usr/share/nginx/html/

EXPOSE 80
