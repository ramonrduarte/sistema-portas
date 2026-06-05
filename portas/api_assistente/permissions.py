from django.conf import settings
from rest_framework.permissions import BasePermission
from rest_framework.throttling import SimpleRateThrottle


class IsGPTAssistant(BasePermission):
    def has_permission(self, request, view):
        token = getattr(settings, "GPT_API_TOKEN", "")
        if not token:
            return False
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            auth = auth[7:]
        return auth == token


class AssistenteThrottle(SimpleRateThrottle):
    scope = "assistente"

    def get_cache_key(self, request, view):
        import hashlib
        # Identifica pelo hash do token — evita caracteres especiais na chave do cache
        raw = request.headers.get("Authorization", "anonymous")
        ident = hashlib.md5(raw.encode(), usedforsecurity=False).hexdigest()
        return self.cache_format % {"scope": self.scope, "ident": ident}
