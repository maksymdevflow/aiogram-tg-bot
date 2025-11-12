"""
Security Middleware for aiogram3 Bot
Provides protection against spam, DDoS attacks, and malicious users
while allowing normal survey completion flow.
"""

import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any

from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, TelegramObject
from logging_config import log_info, log_warning

logger = logging.getLogger(__name__)


@dataclass
class UserActivity:
    """Track user activity for security analysis"""

    user_id: int
    message_count: int = 0
    callback_count: int = 0
    last_activity: float = field(default_factory=time.time)
    request_times: deque = field(default_factory=lambda: deque(maxlen=100))
    identical_messages: deque = field(default_factory=lambda: deque(maxlen=10))
    suspicious_score: int = 0
    blocked_until: float | None = None
    survey_start_time: float | None = None
    last_state: str | None = None
    state_changes: deque = field(
        default_factory=lambda: deque(maxlen=100)
    )
    last_command_time: float | None = None
    callback_times: deque = field(default_factory=lambda: deque(maxlen=50))  # Track callback frequency
    last_callback_data: str | None = None  # Track identical callbacks


class SecurityMiddleware(BaseMiddleware):
    """
    Comprehensive security middleware for aiogram3 bot.

    Features:
    - Rate limiting per user
    - Spam detection (repeated messages, suspicious patterns)
    - DDoS protection (request flooding detection)
    - User behavior analysis
    - Survey flow protection (allows normal completion)
    - Whitelist/Blacklist support
    """

    def __init__(
        self,
        max_requests_per_minute: int = 30,
        max_requests_per_hour: int = 200,
        max_requests_per_day: int = 1000,
        max_identical_messages: int = 5,
        identical_message_window: int = 60,
        min_message_interval: float = 0.5,
        burst_threshold: int = 10,
        burst_window: float = 2.0,
        max_survey_duration: int = 3600,
        max_state_changes_per_minute: int = 20,
        initial_block_duration: int = 300,
        max_block_duration: int = 86400,
        whitelist: set[int] | None = None,
        blacklist: set[int] | None = None,
        # Callback protection
        max_callbacks_per_second: float = 5.0,  # Allow rapid toggle operations
        max_identical_callbacks: int = 10,  # Same callback spam threshold
        identical_callback_window: float = 3.0,  # seconds
    ):
        super().__init__()

        self.max_requests_per_minute = max_requests_per_minute
        self.max_requests_per_hour = max_requests_per_hour
        self.max_requests_per_day = max_requests_per_day
        self.max_identical_messages = max_identical_messages
        self.identical_message_window = identical_message_window
        self.min_message_interval = min_message_interval
        self.burst_threshold = burst_threshold
        self.burst_window = burst_window
        self.max_survey_duration = max_survey_duration
        self.max_state_changes_per_minute = max_state_changes_per_minute
        self.initial_block_duration = initial_block_duration
        self.max_block_duration = max_block_duration
        self.max_callbacks_per_second = max_callbacks_per_second
        self.max_identical_callbacks = max_identical_callbacks
        self.identical_callback_window = identical_callback_window

        self.user_activities: dict[int, UserActivity] = defaultdict(lambda: UserActivity(user_id=0))

        self.whitelist: set[int] = whitelist or set()
        self.blacklist: set[int] = blacklist or set()

        self._last_cleanup = time.time()
        self._cleanup_interval = 3600

    def _cleanup_old_data(self) -> None:
        """Remove old user activity data to prevent memory leaks"""
        current_time = time.time()
        if current_time - self._last_cleanup < self._cleanup_interval:
            return

        cutoff_time = current_time - 86400
        users_to_remove = []

        for user_id, activity in self.user_activities.items():
            if (
                activity.blocked_until is None
                and activity.last_activity < cutoff_time
                and len(activity.request_times) == 0
            ):
                users_to_remove.append(user_id)

        for user_id in users_to_remove:
            del self.user_activities[user_id]

        self._last_cleanup = current_time

    def _is_whitelisted(self, user_id: int) -> bool:
        """Check if user is whitelisted"""
        return user_id in self.whitelist

    def _is_blacklisted(self, user_id: int) -> bool:
        """Check if user is blacklisted"""
        return user_id in self.blacklist

    def _is_blocked(self, user_id: int) -> bool:
        """Check if user is currently blocked"""
        activity = self.user_activities[user_id]
        if activity.blocked_until is None:
            return False

        if time.time() < activity.blocked_until:
            return True

        activity.blocked_until = None
        activity.suspicious_score = max(0, activity.suspicious_score - 10)
        return False

    def _block_user(self, user_id: int, duration: int | None = None) -> None:
        """Block user for specified duration"""
        activity = self.user_activities[user_id]

        if duration is None:
            if activity.suspicious_score < 20:
                duration = self.initial_block_duration
            elif activity.suspicious_score < 50:
                duration = self.initial_block_duration * 2
            else:
                duration = self.max_block_duration

        activity.blocked_until = time.time() + duration
        activity.suspicious_score += 5

        log_warning(
            logger,
            action="user_blocked",
            reason=f"Blocked for {duration} seconds",
            user_id=user_id,
            duration=duration,
            suspicious_score=activity.suspicious_score,
        )

    def _check_rate_limit(self, user_id: int) -> tuple[bool, str]:
        """Check if user exceeds rate limits"""
        activity = self.user_activities[user_id]
        current_time = time.time()

        requests_last_minute = sum(1 for t in activity.request_times if current_time - t < 60)
        requests_last_hour = sum(1 for t in activity.request_times if current_time - t < 3600)
        requests_last_day = sum(1 for t in activity.request_times if current_time - t < 86400)

        if requests_last_minute > self.max_requests_per_minute:
            return False, f"Rate limit exceeded: {requests_last_minute} requests per minute"

        if requests_last_hour > self.max_requests_per_hour:
            return False, f"Rate limit exceeded: {requests_last_hour} requests per hour"

        if requests_last_day > self.max_requests_per_day:
            return False, f"Rate limit exceeded: {requests_last_day} requests per day"

        return True, ""

    def _check_burst_protection(self, user_id: int) -> tuple[bool, str]:
        """Check for request bursts (DDoS pattern)"""
        activity = self.user_activities[user_id]
        current_time = time.time()

        recent_requests = [
            t for t in activity.request_times if current_time - t < self.burst_window
        ]

        if len(recent_requests) >= self.burst_threshold:
            activity.suspicious_score += 10
            return False, f"Burst detected: {len(recent_requests)} requests in {self.burst_window}s"

        return True, ""

    def _check_spam_detection(
        self, user_id: int, message_text: str | None = None
    ) -> tuple[bool, str]:
        """Detect spam patterns"""
        activity = self.user_activities[user_id]
        current_time = time.time()

        if message_text:
            while (
                activity.identical_messages
                and current_time - activity.identical_messages[0][0] > self.identical_message_window
            ):
                activity.identical_messages.popleft()

            identical_count = sum(
                1 for _, text in activity.identical_messages if text == message_text
            )

            if identical_count >= self.max_identical_messages:
                activity.suspicious_score += 15
                return False, f"Spam detected: {identical_count} identical messages"

            activity.identical_messages.append((current_time, message_text))

        if activity.request_times:
            time_since_last = current_time - activity.request_times[-1]
            if time_since_last < self.min_message_interval:
                activity.suspicious_score += 5
                return False, f"Messages too frequent: {time_since_last:.2f}s interval"

        return True, ""

    async def _check_survey_protection(
        self, user_id: int, state: FSMContext | None = None
    ) -> tuple[bool, str]:
        """Protect survey flow while detecting abuse"""
        activity = self.user_activities[user_id]
        current_time = time.time()

        if state:
            try:
                current_state = await state.get_state()
            except Exception as e:
                logger.warning(f"Failed to get FSM state for user {user_id}: {e}")
                return True, ""

            if current_state and activity.survey_start_time is None:
                activity.survey_start_time = current_time
                activity.last_state = str(current_state)
                activity.state_changes.append(current_time)
                return True, ""

            if current_state and activity.survey_start_time:
                survey_duration = current_time - activity.survey_start_time
                if survey_duration > self.max_survey_duration:
                    return False, f"Survey duration exceeded: {survey_duration:.0f}s"

                if str(current_state) != activity.last_state:
                    activity.state_changes.append(current_time)
                    activity.last_state = str(current_state)

                    while activity.state_changes and current_time - activity.state_changes[0] > 60:
                        activity.state_changes.popleft()

                    state_changes_last_minute = len(activity.state_changes)
                    if state_changes_last_minute > self.max_state_changes_per_minute:
                        activity.suspicious_score += 10
                        return (
                            False,
                            f"Too many state changes: {state_changes_last_minute} in last minute",
                        )

                return True, ""

        if activity.survey_start_time:
            try:
                if state:
                    current_state = await state.get_state()
                    if not current_state:
                        activity.survey_start_time = None
                        activity.state_changes.clear()
                        activity.last_state = None
                else:
                    activity.survey_start_time = None
                    activity.state_changes.clear()
                    activity.last_state = None
            except Exception:
                pass

        return True, ""

    def _update_activity(self, user_id: int, is_callback: bool = False) -> None:
        """Update user activity tracking"""
        activity = self.user_activities[user_id]
        activity.user_id = user_id
        current_time = time.time()

        activity.last_activity = current_time
        activity.request_times.append(current_time)

        if is_callback:
            activity.callback_count += 1
        else:
            activity.message_count += 1

    def _check_command_spam(self, user_id: int, is_command: bool) -> tuple[bool, str]:
        """Check for command spam (repeated /start, /create_resume, etc.)"""
        if not is_command:
            return True, ""

        activity = self.user_activities[user_id]
        current_time = time.time()

        if activity.last_command_time and (current_time - activity.last_command_time) < 2.0:
            activity.suspicious_score += 3
            return False, "Command spam detected: too frequent commands"

        activity.last_command_time = current_time
        return True, ""

    def _check_callback_spam(
        self, user_id: int, callback_data: str | None, is_callback: bool
    ) -> tuple[bool, str]:
        """Check for callback spam (rapid button clicking, especially toggle operations)"""
        if not is_callback or not callback_data:
            return True, ""

        activity = self.user_activities[user_id]
        current_time = time.time()

        # Remove old callback times (older than 1 second)
        while activity.callback_times and current_time - activity.callback_times[0] > 1.0:
            activity.callback_times.popleft()

        # Check callback frequency (callbacks per second)
        if len(activity.callback_times) >= self.max_callbacks_per_second:
            activity.suspicious_score += 5
            return False, f"Callback spam: {len(activity.callback_times)} callbacks per second"

        # Check for identical callbacks (same button pressed repeatedly)
        if callback_data == activity.last_callback_data:
            # Count identical callbacks in window
            identical_count = sum(
                1
                for t in activity.callback_times
                if current_time - t < self.identical_callback_window
            )
            if identical_count >= self.max_identical_callbacks:
                activity.suspicious_score += 8
                return (
                    False,
                    f"Identical callback spam: {identical_count} identical callbacks in {self.identical_callback_window}s",
                )

        activity.callback_times.append(current_time)
        activity.last_callback_data = callback_data
        return True, ""

    async def __call__(self, handler, event: TelegramObject, data: dict[str, Any]) -> Any:
        """Main middleware handler"""
        self._cleanup_old_data()

        user_id = None
        message_text = None
        callback_data = None
        is_callback = False
        is_command = False
        state: FSMContext | None = None

        if isinstance(event, Message):
            user_id = event.from_user.id if event.from_user else None
            message_text = event.text
            state = data.get("state")
            is_command = message_text and message_text.startswith("/") if message_text else False
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id if event.from_user else None
            is_callback = True
            callback_data = event.data if hasattr(event, "data") else None
            state = data.get("state")

        if not user_id:
            return await handler(event, data)

        if self._is_whitelisted(user_id):
            return await handler(event, data)

        if self._is_blacklisted(user_id):
            log_warning(
                logger,
                action="blacklisted_user_blocked",
                reason="User is in blacklist",
                user_id=user_id,
            )
            return

        if self._is_blocked(user_id):
            log_warning(
                logger,
                action="blocked_user_request",
                reason="User is currently blocked",
                user_id=user_id,
            )
            return

        self._update_activity(user_id, is_callback)

        checks = [
            ("rate_limit", self._check_rate_limit(user_id)),
            ("burst", self._check_burst_protection(user_id)),
            ("command_spam", self._check_command_spam(user_id, is_command)),
        ]

        # Callback spam check
        if is_callback:
            checks.append(("callback_spam", self._check_callback_spam(user_id, callback_data, is_callback)))

        if message_text:
            checks.append(("spam", self._check_spam_detection(user_id, message_text)))

        if state:
            checks.append(("survey", await self._check_survey_protection(user_id, state)))

        for check_name, (passed, reason) in checks:
            if not passed:
                activity = self.user_activities[user_id]
                activity.suspicious_score += 5

                log_warning(
                    logger,
                    action="security_check_failed",
                    reason=f"{check_name}: {reason}",
                    user_id=user_id,
                    check=check_name,
                    suspicious_score=activity.suspicious_score,
                )

                if activity.suspicious_score >= 20:
                    self._block_user(user_id)

                return

        return await handler(event, data)

    def add_to_whitelist(self, user_id: int) -> None:
        """Add user to whitelist"""
        self.whitelist.add(user_id)
        log_info(logger, action="user_whitelisted", user_id=user_id)

    def remove_from_whitelist(self, user_id: int) -> None:
        """Remove user from whitelist"""
        self.whitelist.discard(user_id)
        log_info(logger, action="user_removed_from_whitelist", user_id=user_id)

    def add_to_blacklist(self, user_id: int) -> None:
        """Add user to blacklist"""
        self.blacklist.add(user_id)
        log_warning(
            logger, action="user_blacklisted", reason="User added to blacklist", user_id=user_id
        )

    def remove_from_blacklist(self, user_id: int) -> None:
        """Remove user from blacklist"""
        self.blacklist.discard(user_id)
        log_info(logger, action="user_removed_from_blacklist", user_id=user_id)

    def get_user_stats(self, user_id: int) -> dict[str, Any]:
        """Get security statistics for a user"""
        activity = self.user_activities.get(user_id)
        if not activity:
            return {"error": "User not found"}

        current_time = time.time()
        return {
            "user_id": user_id,
            "message_count": activity.message_count,
            "callback_count": activity.callback_count,
            "suspicious_score": activity.suspicious_score,
            "is_blocked": self._is_blocked(user_id),
            "blocked_until": activity.blocked_until,
            "is_whitelisted": self._is_whitelisted(user_id),
            "is_blacklisted": self._is_blacklisted(user_id),
            "last_activity": activity.last_activity,
            "survey_active": activity.survey_start_time is not None,
            "state_changes_last_minute": len(
                [t for t in activity.state_changes if current_time - t < 60]
            ),
            "callbacks_per_second": len(
                [t for t in activity.callback_times if current_time - t < 1.0]
            ),
        }
