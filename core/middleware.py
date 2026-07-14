"""Custom middleware for AI Resume Optimizer Pro."""
import logging
import time

logger = logging.getLogger('resume_optimizer')


class RequestLoggingMiddleware:
    """Logs every request with timing information and flags slow AI calls."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.time()
        response = self.get_response(request)
        duration = time.time() - start
        if request.path.startswith('/analysis/') or request.path.startswith('/interview/'):
            logger.info(
                "AI_ROUTE %s %s user=%s status=%s duration=%.2fs",
                request.method, request.path,
                getattr(request.user, 'username', 'anonymous'),
                response.status_code, duration,
            )
        if duration > 5:
            logger.warning("SLOW_REQUEST %s took %.2fs", request.path, duration)
        return response
