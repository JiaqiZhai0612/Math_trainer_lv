"""Question generation for supported math topics."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from random import choice, choices, randint


@dataclass(frozen=True)
class Question:
    """A generated question and the metadata needed to save the result."""

    prompt: str
    correct_answer: int
    topic: str
    question_type: str
    difficulty: int
    remainder_answer: int | None = None


class QuestionGenerator:
    """Creates math questions for the trainer."""

    ADDITION_TOPIC = "Addition"
    SUBTRACTION_TOPIC = "Subtraction"
    MULTIPLICATION_TOPIC = "Multiplication"
    DIVISION_TOPIC = "Division"
    MIXED_TOPIC = "Mixed"
    WORD_PROBLEMS_TOPIC = "Word Problems"
    WORD_PROBLEMS_PATH = Path("word_problems.json")
    QUESTION_TYPES = (
        ADDITION_TOPIC,
        SUBTRACTION_TOPIC,
        MULTIPLICATION_TOPIC,
        DIVISION_TOPIC,
    )

    def generate_question(
        self,
        question_type: str,
        difficulty: int = 1,
        accuracy_by_topic: dict[str, dict[str, int | float]] | None = None,
    ) -> Question:
        """Generate one question for the selected type."""
        if question_type == self.MIXED_TOPIC:
            question_type = self._choose_mixed_topic(accuracy_by_topic)

        if question_type == self.SUBTRACTION_TOPIC:
            return self.generate_subtraction_question(difficulty)
        if question_type == self.MULTIPLICATION_TOPIC:
            return self.generate_multiplication_question(difficulty)
        if question_type == self.DIVISION_TOPIC:
            return self.generate_division_question(difficulty)
        if question_type == self.WORD_PROBLEMS_TOPIC:
            return self.generate_word_problem(difficulty)

        return self.generate_addition_question(difficulty)

    def _choose_mixed_topic(
        self,
        accuracy_by_topic: dict[str, dict[str, int | float]] | None,
    ) -> str:
        """Choose Mixed topics adaptively once enough history exists."""
        minimum_attempts = 5
        if accuracy_by_topic is None:
            return choice(self.QUESTION_TYPES)

        has_enough_history = all(
            accuracy_by_topic.get(topic, {}).get("total_attempts", 0) >= minimum_attempts
            for topic in self.QUESTION_TYPES
        )
        if not has_enough_history:
            return choice(self.QUESTION_TYPES)

        weights = []
        for topic in self.QUESTION_TYPES:
            accuracy = float(accuracy_by_topic[topic]["accuracy"])
            error_rate = 1.0 - accuracy
            weights.append(max(0.1, error_rate))

        return choices(self.QUESTION_TYPES, weights=weights, k=1)[0]

    def generate_addition_question(self, difficulty: int = 1) -> Question:
        """Generate an addition question with three-digit numbers."""
        first_number = randint(100, 999)
        second_number = randint(100, 999)

        return Question(
            prompt=f"{first_number} + {second_number} = ?",
            correct_answer=first_number + second_number,
            topic=self.ADDITION_TOPIC,
            question_type=self.ADDITION_TOPIC,
            difficulty=difficulty,
        )

    def generate_subtraction_question(self, difficulty: int = 1) -> Question:
        """Generate a three-digit subtraction question with no negative answer."""
        first_number = randint(100, 999)
        second_number = randint(100, first_number)

        return Question(
            prompt=f"{first_number} - {second_number} = ?",
            correct_answer=first_number - second_number,
            topic=self.SUBTRACTION_TOPIC,
            question_type=self.SUBTRACTION_TOPIC,
            difficulty=difficulty,
        )

    def generate_multiplication_question(self, difficulty: int = 1) -> Question:
        """Generate a multiplication-table question weighted toward 6 to 10."""
        table_numbers = [1, 2, 3, 4, 5, 6, 6, 7, 7, 8, 8, 9, 9, 10, 10]
        first_number = choice(table_numbers)
        second_number = choice(table_numbers)

        return Question(
            prompt=f"{first_number} × {second_number} = ?",
            correct_answer=first_number * second_number,
            topic=self.MULTIPLICATION_TOPIC,
            question_type=self.MULTIPLICATION_TOPIC,
            difficulty=difficulty,
        )

    def generate_division_question(self, difficulty: int = 1) -> Question:
        """Generate division with or without a remainder."""
        if choice((True, False)):
            return self.generate_division_without_remainder_question(difficulty)

        return self.generate_division_with_remainder_question(difficulty)

    def generate_division_without_remainder_question(self, difficulty: int = 1) -> Question:
        """Generate a division question from the 6 to 10 tables with no remainder."""
        divisor = randint(6, 10)
        quotient = randint(6, 10)
        dividend = divisor * quotient

        return Question(
            prompt=f"{dividend} ÷ {divisor} = ?",
            correct_answer=quotient,
            topic=self.DIVISION_TOPIC,
            question_type=self.DIVISION_TOPIC,
            difficulty=difficulty,
        )

    def generate_division_with_remainder_question(self, difficulty: int = 1) -> Question:
        """Generate a Grade 3 division question with a small remainder."""
        divisor = randint(2, 10)
        quotient = randint(2, 9)
        remainder = randint(1, min(divisor - 1, 4))
        dividend = divisor * quotient + remainder

        return Question(
            prompt=f"{dividend} ÷ {divisor} = ?",
            correct_answer=quotient,
            topic=self.DIVISION_TOPIC,
            question_type=self.DIVISION_TOPIC,
            difficulty=difficulty,
            remainder_answer=remainder,
        )

    def generate_word_problem(self, difficulty: int = 1) -> Question:
        """Generate a manually added word problem from word_problems.json."""
        word_problems = self._load_word_problems()
        problem = choice(word_problems)

        return Question(
            prompt=problem["question_text"],
            correct_answer=int(problem["answer"]),
            topic=problem["topic"],
            question_type=self.WORD_PROBLEMS_TOPIC,
            difficulty=difficulty,
        )

    def _load_word_problems(self) -> list[dict[str, str | int]]:
        """Load valid manually added word problems from the local JSON file."""
        with self.WORD_PROBLEMS_PATH.open("r", encoding="utf-8") as file:
            loaded_problems = json.load(file)

        valid_problems = []
        for problem in loaded_problems:
            required_fields = {"question_text", "answer", "topic", "subtopic"}
            if not required_fields.issubset(problem):
                continue

            try:
                int(problem["answer"])
            except (TypeError, ValueError):
                continue

            valid_problems.append(problem)

        if not valid_problems:
            raise ValueError("word_problems.json does not contain any valid word problems.")

        return valid_problems
