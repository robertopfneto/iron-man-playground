"""
Configuração da instância única da API do Escritório 2D (Entrega 1).
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("DJANGO_DATA_DIR", "/app/data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load_or_create_secret_key() -> str:
    """Usa DJANGO_SECRET_KEY se definida; senão persiste uma chave gerada no volume."""
    env_key = os.environ.get("DJANGO_SECRET_KEY")
    if env_key:
        return env_key

    key_path = DATA_DIR / "secret_key.txt"
    if key_path.exists():
        return key_path.read_text().strip()

    from django.core.management.utils import get_random_secret_key

    key = get_random_secret_key()
    key_path.write_text(key)
    key_path.chmod(0o600)
    return key


SECRET_KEY = _load_or_create_secret_key()

DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"

ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")
    if h.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
    "conhecimento",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# SQLite em volume persistente. Única instância da API no piloto.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": DATA_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Campo_Grande"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = os.environ.get("DJANGO_STATIC_ROOT", "/app/staticfiles")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Serviço web (Caddy) e API ficam na mesma origem; cookies de sessão/CSRF
# não precisam de SameSite=None nem de domínios cruzados no piloto.
CSRF_TRUSTED_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "DJANGO_CSRF_TRUSTED_ORIGINS", "http://127.0.0.1:8000,http://localhost:8000"
    ).split(",")
    if o.strip()
]
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

# Base de conhecimento. O token de leitura do GitHub (GITHUB_TOKEN_LEITURA) é lido
# só do ambiente pelo módulo de Git e nunca vai para o banco ou para logs.
CONHECIMENTO_DIR_ESPELHOS = os.environ.get("CONHECIMENTO_DIR_ESPELHOS", str(DATA_DIR / "git"))
CONHECIMENTO_DIR_FONTES_LOCAIS = os.environ.get("CONHECIMENTO_DIR_FONTES_LOCAIS", str(DATA_DIR / "fontes_demo"))
CONHECIMENTO_EMBEDDER = os.environ.get("CONHECIMENTO_EMBEDDER", "conhecimento.embeddings.OllamaEmbedder")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://ollama:11434")
EMBEDDINGS_MODELO = os.environ.get("EMBEDDINGS_MODELO", "bge-m3")
