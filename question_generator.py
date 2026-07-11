"""Question generation for supported math topics."""

from __future__ import annotations

from dataclasses import dataclass
from random import choice, choices, randint, random


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
            accuracy = float(accuracy_by_topic.get(topic, {}).get("accuracy", 0.0))
            error_rate = 1.0 - accuracy
            weights.append(max(0.1, error_rate))

        return choices(self.QUESTION_TYPES, weights=weights, k=1)[0]

    def generate_addition_question(self, difficulty: int = 1) -> Question:
        """Generate addition with required carrying."""
        require_multiple_carries = random() < 0.4
        while True:
            first_number, second_number = self._addition_numbers()
            carry_count = self._addition_carry_count(first_number, second_number)
            if carry_count >= 1 and (carry_count >= 2 or not require_multiple_carries):
                break

        return Question(
            prompt=f"{first_number} + {second_number} = ?",
            correct_answer=first_number + second_number,
            topic=self.ADDITION_TOPIC,
            question_type=self.ADDITION_TOPIC,
            difficulty=difficulty,
        )

    def _addition_numbers(self) -> tuple[int, int]:
        """Return numbers matching the requested addition size distribution."""
        if random() < 0.7:
            return randint(100, 999), randint(100, 999)

        first_number = randint(1000, 9999)
        second_number = randint(1000, 9999) if choice((True, False)) else randint(100, 999)
        return first_number, second_number

    def _addition_carry_count(self, first_number: int, second_number: int) -> int:
        """Count digit positions where addition creates a carry."""
        carry = 0
        carry_count = 0
        larger_width = max(len(str(first_number)), len(str(second_number)))
        for _ in range(larger_width):
            first_digit = first_number % 10
            second_digit = second_number % 10
            digit_sum = first_digit + second_digit + carry
            carry = 1 if digit_sum >= 10 else 0
            if carry:
                carry_count += 1
            first_number //= 10
            second_number //= 10
        return carry_count

    def generate_subtraction_question(self, difficulty: int = 1) -> Question:
        """Generate subtraction with required borrowing and no negative answer."""
        require_multiple_borrows = random() < 0.4
        while True:
            first_number, second_number = self._subtraction_numbers()
            borrow_count = self._subtraction_borrow_count(first_number, second_number)
            if borrow_count >= 1 and (borrow_count >= 2 or not require_multiple_borrows):
                break

        return Question(
            prompt=f"{first_number} - {second_number} = ?",
            correct_answer=first_number - second_number,
            topic=self.SUBTRACTION_TOPIC,
            question_type=self.SUBTRACTION_TOPIC,
            difficulty=difficulty,
        )

    def _subtraction_numbers(self) -> tuple[int, int]:
        """Return numbers matching the requested subtraction size distribution."""
        if random() < 0.7:
            first_number = (
                choice((300, 400, 500, 600, 700, 800, 900))
                if random() < 0.2
                else randint(100, 999)
            )
            second_number = randint(100, first_number)
            return first_number, second_number

        first_number = (
            choice((1000, 2000, 3000, 4000, 5000, 9000))
            if random() < 0.2
            else randint(1000, 9999)
        )
        second_minimum = 1000 if choice((True, False)) else 100
        second_number = randint(second_minimum, first_number)
        return first_number, second_number

    def _subtraction_borrow_count(self, first_number: int, second_number: int) -> int:
        """Count digit positions where subtraction requires borrowing."""
        borrow = 0
        borrow_count = 0
        larger_width = max(len(str(first_number)), len(str(second_number)))
        for _ in range(larger_width):
            first_digit = first_number % 10 - borrow
            second_digit = second_number % 10
            if first_digit < second_digit:
                borrow = 1
                borrow_count += 1
            else:
                borrow = 0
            first_number //= 10
            second_number //= 10
        return borrow_count

    def generate_multiplication_question(self, difficulty: int = 1) -> Question:
        """Generate multiplication weighted toward two-digit by one-digit."""
        if random() < 0.7:
            first_number = randint(12, 99)
            second_number = randint(2, 9)
        else:
            weighted_table_numbers = [2, 3, 4, 5, 6, 6, 7, 7, 8, 8, 9, 9, 10, 10]
            first_number = choice(weighted_table_numbers)
            second_number = choice(weighted_table_numbers)

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
        """Generate an exact division question with a one-digit divisor."""
        divisor = randint(2, 9)
        quotient = randint(2, min(99, 999 // divisor))
        dividend = divisor * quotient

        return Question(
            prompt=f"{dividend} ÷ {divisor} = ?",
            correct_answer=quotient,
            topic=self.DIVISION_TOPIC,
            question_type=self.DIVISION_TOPIC,
            difficulty=difficulty,
        )

    def generate_division_with_remainder_question(self, difficulty: int = 1) -> Question:
        """Generate division with a valid non-zero remainder."""
        divisor = randint(2, 9)
        remainder = randint(1, divisor - 1)
        max_quotient = min(99, (999 - remainder) // divisor)
        quotient = randint(2, max_quotient)
        dividend = divisor * quotient + remainder

        return Question(
            prompt=f"{dividend} ÷ {divisor} = ?",
            correct_answer=quotient,
            topic=self.DIVISION_TOPIC,
            question_type=self.DIVISION_TOPIC,
            difficulty=difficulty,
            remainder_answer=remainder,
        )
