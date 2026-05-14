FROM nginx:alpine

# Install consul-template
ARG CT_VERSION=0.39.1
RUN wget -qO /tmp/ct.zip \
      https://releases.hashicorp.com/consul-template/${CT_VERSION}/consul-template_${CT_VERSION}_linux_amd64.zip \
    && unzip /tmp/ct.zip -d /usr/local/bin \
    && rm /tmp/ct.zip

# consul-template config
COPY consul-template.hcl /etc/consul-template.hcl

# nginx template — consul-template renders this into /etc/nginx/nginx.conf
COPY nginx.conf.tmpl /etc/nginx/nginx.conf.tmpl

# Entrypoint: run consul-template which manages nginx
CMD ["consul-template", "-config=/etc/consul-template.hcl"]