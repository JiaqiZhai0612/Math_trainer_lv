"""SQLite storage helpers for the math trainer."""

from __future__ import annotations

import sqlite3
from pathlib import Path


class Database:
    """Owns the SQLite connection and result persistence."""

    def __init__(self, db_path: str | Path = "math_trainer.db") -> None:
        self.db_path = Path(db_path)
        self.connection = sqlite3.connect(self.db_path)
        self._create_tables()
        self._migrate_tables()

    def _create_tables(self) -> None:
        """Create the attempts table used by the prototype."""
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,
                question_type TEXT NOT NULL DEFAULT 'Addition',
                question_text TEXT NOT NULL,
                correct_answer INTEGER NOT NULL,
                user_answer TEXT NOT NULL,
                is_correct INTEGER NOT NULL,
                difficulty INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.connection.commit()

    def _migrate_tables(self) -> None:
        """Add new columns when opening an older prototype database."""
        columns = {
            row[1]
            for row in self.connection.execute("PRAGMA table_info(attempts)").fetchall()
        }
        if "question_type" not in columns:
            self.connection.execute(
                "ALTER TABLE attempts ADD COLUMN question_type TEXT NOT NULL DEFAULT 'Addition'"
            )
            self.connection.commit()

    def save_attempt(
        self,
        topic: str,
        question_type: str,
        question_text: str,
        correct_answer: int,
        user_answer: int | str,
        is_correct: bool,
        difficulty: int,
    ) -> None:
        """Store a single answered question in SQLite."""
        self.connection.execute(
            """
            INSERT INTO attempts (
                topic,
                question_type,
                question_text,
                correct_answer,
                user_answer,
                is_correct,
                difficulty
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                topic,
                question_type,
                question_text,
                correct_answer,
                user_answer,
                int(is_correct),
                difficulty,
            ),
        )
        self.connection.commit()

    def get_overall_statistics(self) -> dict[str, int | float]:
        """Return total attempts, correct answers, and overall accuracy."""
        row = self.connection.execute(
            """
            SELECT
                COUNT(*) AS total_attempts,
                COALESCE(SUM(is_correct), 0) AS total_correct
            FROM attempts
            """
        ).fetchone()

        total_attempts = int(row[0])
        total_correct = int(row[1])
        accuracy = (total_correct / total_attempts * 100) if total_attempts else 0.0

        return {
            "total_attempts": total_attempts,
            "total_correct": total_correct,
            "accuracy": accuracy,
        }

    def get_topic_statistics(self) -> list[dict[str, int | float | str]]:
        """Return accuracy and wrong-attempt counts for each question type."""
        rows = self.connection.execute(
            """
            SELECT
                question_type,
                COUNT(*) AS total_attempts,
                COALESCE(SUM(is_correct), 0) AS total_correct,
                COALESCE(SUM(CASE WHEN is_correct = 0 THEN 1 ELSE 0 END), 0) AS wrong_attempts
            FROM attempts
            GROUP BY question_type
            ORDER BY question_type
            """
        ).fetchall()

        statistics = []
        for question_type, total_attempts, total_correct, wrong_attempts in rows:
            accuracy = (total_correct / total_attempts * 100) if total_attempts else 0.0
            statistics.append(
                {
                    "topic": question_type,
                    "total_attempts": int(total_attempts),
                    "total_correct": int(total_correct),
                    "accuracy": accuracy,
                    "wrong_attempts": int(wrong_attempts),
                }
            )

        return statistics

    def get_accuracy_by_question_type(self) -> dict[str, dict[str, int | float]]:
        """Return attempt counts and accuracy keyed by question type."""
        rows = self.connection.execute(
            """
            SELECT
                question_type,
                COUNT(*) AS total_attempts,
                COALESCE(SUM(is_correct), 0) AS total_correct
            FROM attempts
            GROUP BY question_type
            """
        ).fetchall()

        accuracy_by_type = {}
        for question_type, total_attempts, total_correct in rows:
            accuracy = (total_correct / total_attempts) if total_attempts else 0.0
            accuracy_by_type[question_type] = {
                "total_attempts": int(total_attempts),
                "accuracy": accuracy,
            }

        return accuracy_by_type

    def reset_statistics(self) -> None:
        """Delete saved answer history without changing the database structure."""
        self.connection.execute("DELETE FROM attempts")
        self.connection.commit()

    def close(self) -> None:
        """Close the SQLite connection."""
        self.connection.close()
