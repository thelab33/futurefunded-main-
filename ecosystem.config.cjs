const path = require("path");

const ROOT = "/home/elCUCO/futurefunded-final";

module.exports = {
  apps: [
    {
      name: "futurefunded-web",
      cwd: ROOT,
      script: path.join(ROOT, ".venv/bin/python"),
      args: [
        "-m",
        "flask",
        "--app",
        "apps.web.app:create_app()",
        "run",
        "--host",
        "127.0.0.1",
        "--port",
        "5000",
        "--no-debugger",
        "--no-reload"
      ],
      interpreter: "none",
      autorestart: true,
      max_restarts: 20,
      min_uptime: "10s",
      restart_delay: 1500,
      watch: false,
      env: {
        FLASK_ENV: "production",
        FLASK_DEBUG: "0",
        FF_PUBLIC_BASE_URL: "https://getfuturefunded.com",
        FF_API_BASE_URL: "http://127.0.0.1:8000",
        FF_OPERATOR_ACCESS_TOKEN: process.env.FF_OPERATOR_ACCESS_TOKEN || "",
        PYTHONUNBUFFERED: "1"
      }
    },
    {
      name: "futurefunded-tunnel",
      cwd: ROOT,
      script: "cloudflared",
      args: [
        "tunnel",
        "run",
        "getfuturefunded"
      ],
      interpreter: "none",
      autorestart: true,
      max_restarts: 20,
      min_uptime: "10s",
      restart_delay: 2000,
      watch: false
    }
  ]
};
