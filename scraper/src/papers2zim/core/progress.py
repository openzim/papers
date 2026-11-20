import json
import threading
from math import ceil

from schedule import Scheduler

from papers2zim.constants import logger


class ScraperProgress:
    """Helper class to computer scraper progress"""

    def __init__(self, stats_filename: str | None):
        self._lock = threading.Lock()
        self._total = 1
        self._progress = 0
        self._stats_filename = stats_filename
        self._books_attempted = 0
        self._books_succeeded = 0
        # per-instance scheduler: jobs must not leak into schedule's global
        # default scheduler (they would pin this instance and fire from
        # unrelated instances' run_pending calls)
        self._scheduler = Scheduler()

        if self._stats_filename:
            self.report_progress()
            # set a timer to report progress only every 10 seconds,
            # no need to do it more often
            self._scheduler.every(10).seconds.do(self.report_progress)

    def increase_total(self, increment: int):
        with self._lock:
            self._total += increment
            self._scheduler.run_pending()

    def increase_progress(self, increment: int = 1):
        with self._lock:
            self._progress += increment
            self._scheduler.run_pending()

    def set_book_totals(self, *, attempted: int, succeeded: int):
        """Record the outcome of the book-processing phase."""
        with self._lock:
            self._books_attempted = attempted
            self._books_succeeded = succeeded
        self.report_progress()

    def report_progress(self):
        if not self._stats_filename:
            return
        books = (
            f" ({self._books_succeeded}/{self._books_attempted} books succeeded)"
            if self._books_attempted
            else ""
        )
        logger.info(
            f"Progress: {self._progress}/{self._total} "
            f"({ceil(self._progress*1000/self._total)/10}%){books}"
        )
        progress = {
            "done": self._progress,
            "total": self._total,
            "books_attempted": self._books_attempted,
            "books_succeeded": self._books_succeeded,
        }
        with open(self._stats_filename, "w") as outfile:
            json.dump(progress, outfile, indent=2)
