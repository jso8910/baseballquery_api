FROM nginxproxy/nginx-proxy

RUN rm /etc/nginx/conf.d/default.conf
# COPY nginx.conf /etc/nginx/conf.d
COPY vhost.d/baseballapi.jasoner.net_location /etc/nginx/vhost.d/baseballapi.jasoner.net_location