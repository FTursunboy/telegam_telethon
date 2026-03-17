from prometheus_client import Counter, Gauge, Histogram

active_sessions = Gauge("active_sessions", "Active telegram sessions")
telegram_reconnect_total = Counter("telegram_reconnect_total", "Telegram reconnect total")
webhook_delivery_total = Counter("webhook_delivery_total", "Webhook delivery total", ["status"])
webhook_timeout_total = Counter("webhook_timeout_total", "Webhook timeout total")
api_request_duration_seconds = Histogram("api_request_duration_seconds", "API request duration", ["path"])
telegram_rpc_errors_total = Counter("telegram_rpc_errors_total", "Telegram RPC errors", ["type"])
