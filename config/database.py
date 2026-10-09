"""PostgreSQL configuration; URLs take precedence over legacy DB_* fields."""
import re
from urllib.parse import parse_qsl, unquote, urlsplit

from django.core.exceptions import ImproperlyConfigured


def database_config(env):
    url = env("DATABASE_URL", default="")
    options = {}
    if url:
        try:
            parsed = urlsplit(url)
            if (parsed.scheme not in ("postgres", "postgresql") or not parsed.hostname
                    or not parsed.username or parsed.password is None or not parsed.password
                    or parsed.fragment or parsed.netloc.count("@") != 1
                    or re.search(r"%(?![0-9a-fA-F]{2})", url)
                    or any(char.isspace() for char in url)):
                raise ValueError
            name = unquote(parsed.path.removeprefix("/"))
            if not name or "/" in name:
                raise ValueError
            # Encode all reserved characters in credentials, including extra colons.
            if ":" in parsed.password:
                raise ValueError
            port = parsed.port if parsed.port is not None else 5432
            if not 1 <= port <= 65535:
                raise ValueError
            query = parse_qsl(parsed.query, keep_blank_values=True, strict_parsing=True)
            if len(dict(query)) != len(query) or any(key not in ("sslmode", "sslrootcert") or not value for key, value in query):
                raise ValueError
            options.update(query)
            connection = dict(NAME=name, USER=unquote(parsed.username), PASSWORD=unquote(parsed.password),
                              HOST=parsed.hostname, PORT=port)
        except (ValueError, TypeError, UnicodeError):
            # Never include the supplied URL/password in exceptions or startup logs.
            raise ImproperlyConfigured("DATABASE_URL không hợp lệ. Dùng PostgreSQL URL và mã hóa ký tự đặc biệt trong mật khẩu; chỉ hỗ trợ sslmode/sslrootcert trong query.") from None
    else:
        connection = {field: env("DB_" + field) for field in ("NAME", "USER", "PASSWORD", "HOST", "PORT")}
    options.setdefault("sslmode", env("DB_SSLMODE", default="require"))
    options.update(connect_timeout=env.int("DB_CONNECT_TIMEOUT", default=10),
                   options="-c search_path=costing,public")
    return dict(ENGINE="django.db.backends.postgresql", **connection,
                CONN_MAX_AGE=env.int("DB_CONN_MAX_AGE", default=60), CONN_HEALTH_CHECKS=True,
                OPTIONS=options)
