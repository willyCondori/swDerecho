import hashlib

from django.conf import settings
from django.core.cache import caches
from rest_framework.throttling import SimpleRateThrottle


class SecurityThrottle(SimpleRateThrottle):
    """Cache compartida en PostgreSQL, independiente de la cache de resultados."""
    def get_rate(self):
        return settings.API_RATE_LIMITS[self.scope]

    @property
    def cache(self):
        return caches["security_throttles"]

    def get_cache_key(self, request, view):
        identity = str(request.user.pk) if self.scope.startswith("analysis") else self.get_ident(request)
        digest = hashlib.sha256(identity.encode()).hexdigest()
        return self.cache_format % {"scope": self.scope, "ident": digest}


class LoginThrottle(SecurityThrottle):
    scope = "login"


class RecoveryThrottle(SecurityThrottle):
    scope = "recovery"


class RecoveryConfirmThrottle(SecurityThrottle):
    scope = "recovery_confirm"


class AnalysisBurstThrottle(SecurityThrottle):
    scope = "analysis_burst"


class AnalysisDailyThrottle(SecurityThrottle):
    scope = "analysis_daily"


ANALYSIS_THROTTLES = [AnalysisBurstThrottle, AnalysisDailyThrottle]
