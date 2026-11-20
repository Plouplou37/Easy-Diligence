import logging
import time

from app.core.config import settings

logger = logging.getLogger(__name__)


class RateLimiter:
    """Optional pauses between questions.

    Every rule is off by default. Measurements on the account show 10 000
    requests/min and 10 000 000 tokens/min available while a run consumes about
    0.5 request/min, so throttling protects nothing; 429s are handled upstream by
    DDProcessor's exponential backoff and circuit breaker.

    The rules survive as an escape hatch, switchable from the environment without
    a redeploy. Setting a rule's duration to 0 disables it.

    Historical note: this class used to sleep 90s whenever a question exceeded
    ``token_threshold`` (3 000) and then RETURN, which skipped the batch rule
    entirely. Since a real question costs 8 000 to 46 000 tokens, the 90s pause
    fired every single time and the batch rule was dead code -- about 69% of a
    DD's runtime was spent in that pause. Rules now compose instead of
    short-circuiting each other.
    """

    def __init__(self):
        self.questions_processed = 0

    def _pending_delays(self, tokens_used: int) -> list[tuple[str, float]]:
        """Delays to apply after the question just processed, as (reason, seconds)."""
        delays: list[tuple[str, float]] = []

        if settings.inter_question_delay_seconds > 0:
            delays.append(
                (
                    "delai entre questions",
                    float(settings.inter_question_delay_seconds),
                )
            )

        if settings.high_token_sleep_seconds > 0 and tokens_used > settings.token_threshold:
            delays.append(
                (
                    f"forte consommation ({tokens_used} tokens)",
                    float(settings.high_token_sleep_seconds),
                )
            )

        if (
            settings.batch_sleep_minutes > 0
            and settings.max_questions_per_batch > 0
            and self.questions_processed % settings.max_questions_per_batch == 0
        ):
            delays.append(
                (
                    f"lot de {settings.max_questions_per_batch} questions",
                    settings.batch_sleep_minutes * 60.0,
                )
            )

        return delays

    def check_and_sleep_sync(self, tokens_used: int = 0):
        """Apply the configured pauses after a question.

        Synchronous on purpose: the engine runs questions in a background thread
        with no event loop (see DDProcessor._process_single_question).
        """
        self.questions_processed += 1
        for reason, seconds in self._pending_delays(tokens_used):
            logger.info("Pause de %.0fs (%s)", seconds, reason)
            time.sleep(seconds)
