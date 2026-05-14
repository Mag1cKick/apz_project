consul {
  address = "consul:8500"

  retry {
    enabled  = true
    attempts = 12
    backoff  = "250ms"
  }
}

template {
  source      = "/etc/nginx/nginx.conf.tmpl"
  destination = "/etc/nginx/nginx.conf"

  # After rendering, test the config then reload nginx gracefully.
  # If no nginx is running yet (first render), start it.
  command = <<EOF
nginx -t && (nginx -s reload 2>/dev/null || nginx -g 'daemon off;' &)
EOF

  command_timeout = "10s"
}