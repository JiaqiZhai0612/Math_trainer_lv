"""Minimal adaptive difficulty logic for the math trainer."""

from __future__ import annotations


class AdaptiveEngine:
    """Tracks recent answers and chooses a simple difficulty level."""

    def __init__(self, starting_difficulty: int = 1) -> None:
        self.current_difficulty = starting_difficulty
        self.correct_streak = 0

    def get_current_difficulty(self) -> int:
        """Return the difficulty level to use for the next question."""
        return self.current_difficulty

    def record_result(self, is_correct: bool) -> None:
        """Update difficulty using a deliberately small adaptive rule."""
        if is_correct:
            self.correct_streak += 1
            if self.correct_streak >= 3:
                self.current_difficulty = min(10, self.current_difficulty + 1)
                self.correct_streak = 0
            return

        self.correct_streak = 0
        self.current_difficulty = max(1, self.current_difficulty - 1)

    def reset(self) -> None:
        """Reset adaptive learning state to its starting values."""
        self.current_difficulty = 1
        self.correct_streak = 0
