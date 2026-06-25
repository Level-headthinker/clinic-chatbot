"""Error monitoring — Sentry, off by default.

Set SENTRY_DSN to turn it on; with no DSN this is a no-op, so it's safe to call
unconditionally at startup. When enabled, unhandled exceptions across the API
(and the background scheduler) are captured with the environment label.
"""
import logging

from app.config import settings

logger = logging.getLogger(__name__)


def init_sentry() -> None:
    if not settings.SENTRY_DSN:
        return
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration

        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.ENVIRONMENT,
            integrations=[StarletteIntegration(), FastApiIntegration()],
            traces_sample_rate=0.1,        # 10% perf traces — cheap, useful
            send_default_pii=False,        # don't ship patient data to Sentry
        )
        logger.info("Sentry error monitoring enabled (env=%s)", settings.ENVIRONMENT)
    except Exception:
        logger.exception("Sentry init failed — continuing without it")
