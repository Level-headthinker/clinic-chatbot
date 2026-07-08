"""Error monitoring + a single reporter so failures are never truly silent.

Sentry is off until SENTRY_DSN is set; even then, a lot of the app deliberately
*swallows* exceptions (background tasks, best-effort sends, audit writes) so one
failure can't take a request down. The danger is that "swallowed" becomes
"invisible". ``report_error`` is the fix: it ALWAYS logs at ERROR level (visible
in any log aggregator, with or without Sentry) and ALSO ships to Sentry when
configured. Route every swallow through it instead of ``print`` / ``pass``.
"""
import logging

from app.config import settings

logger = logging.getLogger("clinicbot")


def init_sentry() -> None:
    if not settings.SENTRY_DSN:
        return
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration

        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.ENVIRONMENT,
            integrations=[
                StarletteIntegration(),
                FastApiIntegration(),
                # Capture logger.error(...) / report_error(...) as Sentry events,
                # so the swallowed failures below surface even when the code
                # doesn't raise.
                LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
            ],
            traces_sample_rate=0.1,        # 10% perf traces — cheap, useful
            send_default_pii=False,        # don't ship patient data to Sentry
        )
        logger.info("Sentry error monitoring enabled (env=%s)", settings.ENVIRONMENT)
    except Exception:
        logger.exception("Sentry init failed — continuing without it")


def report_error(message: str, exc: Exception | None = None, **context) -> None:
    """Record a non-fatal failure so it's visible instead of silent.

    Use in place of ``print``/``pass`` in every best-effort code path
    (background tasks, message sends, audit writes, scheduled jobs).
    Never raises.
    """
    try:
        ctx = " ".join(f"{k}={v}" for k, v in context.items())
        line = f"{message}{(' | ' + ctx) if ctx else ''}"
        if exc is not None:
            logger.error("%s | %s: %s", line, type(exc).__name__, exc)
        else:
            logger.error(line)
        if settings.SENTRY_DSN:
            import sentry_sdk
            with sentry_sdk.push_scope() as scope:
                for k, v in context.items():
                    scope.set_tag(k, str(v)[:200])
                if exc is not None:
                    sentry_sdk.capture_exception(exc)
                else:
                    sentry_sdk.capture_message(message, level="error")
    except Exception:
        # Reporting must never itself break the caller.
        try:
            logger.error("report_error failed for: %s", message)
        except Exception:
            pass
