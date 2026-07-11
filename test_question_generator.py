"""Focused validation for math question generation rules."""

from __future__ import annotations

import random
import re
import unittest

from question_generator import QuestionGenerator


def _numbers_from_prompt(prompt: str) -> tuple[int, int]:
    first, second = re.findall(r"\d+", prompt)
    return int(first), int(second)


def _addition_carry_count(first_number: int, second_number: int) -> int:
    carry = 0
    carry_count = 0
    for _ in range(max(len(str(first_number)), len(str(second_number)))):
        digit_sum = first_number % 10 + second_number % 10 + carry
        carry = 1 if digit_sum >= 10 else 0
        if carry:
            carry_count += 1
        first_number //= 10
        second_number //= 10
    return carry_count


def _subtraction_borrow_count(first_number: int, second_number: int) -> int:
    borrow = 0
    borrow_count = 0
    for _ in range(max(len(str(first_number)), len(str(second_number)))):
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


class QuestionGeneratorTests(unittest.TestCase):
    def setUp(self) -> None:
        random.seed(20260711)
        self.generator = QuestionGenerator()

    def test_addition_requires_carry_and_uses_expected_sizes(self) -> None:
        questions = [self.generator.generate_addition_question() for _ in range(1000)]
        four_digit_count = 0
        multiple_carry_count = 0

        for question in questions:
            first_number, second_number = _numbers_from_prompt(question.prompt)
            self.assertEqual(question.correct_answer, first_number + second_number)
            self.assertGreaterEqual(first_number, 100)
            self.assertGreaterEqual(second_number, 100)
            self.assertLessEqual(first_number, 9999)
            self.assertLessEqual(second_number, 9999)
            self.assertGreaterEqual(_addition_carry_count(first_number, second_number), 1)
            if first_number >= 1000 or second_number >= 1000:
                four_digit_count += 1
            if _addition_carry_count(first_number, second_number) >= 2:
                multiple_carry_count += 1

        self.assertGreater(four_digit_count, 220)
        self.assertLess(four_digit_count, 380)
        self.assertGreater(multiple_carry_count, 250)

    def test_subtraction_requires_borrow_and_uses_expected_sizes(self) -> None:
        questions = [self.generator.generate_subtraction_question() for _ in range(1000)]
        four_digit_count = 0
        multiple_borrow_count = 0
        zero_case_count = 0

        for question in questions:
            first_number, second_number = _numbers_from_prompt(question.prompt)
            self.assertEqual(question.correct_answer, first_number - second_number)
            self.assertGreaterEqual(question.correct_answer, 0)
            self.assertGreaterEqual(first_number, 100)
            self.assertGreaterEqual(second_number, 100)
            self.assertLessEqual(first_number, 9999)
            self.assertLessEqual(second_number, 9999)
            self.assertGreaterEqual(_subtraction_borrow_count(first_number, second_number), 1)
            if first_number >= 1000 or second_number >= 1000:
                four_digit_count += 1
            if _subtraction_borrow_count(first_number, second_number) >= 2:
                multiple_borrow_count += 1
            if "0" in str(first_number):
                zero_case_count += 1

        self.assertGreater(four_digit_count, 220)
        self.assertLess(four_digit_count, 380)
        self.assertGreater(multiple_borrow_count, 250)
        self.assertGreater(zero_case_count, 50)

    def test_multiplication_uses_two_digit_by_one_digit_or_table(self) -> None:
        questions = [self.generator.generate_multiplication_question() for _ in range(1000)]
        two_digit_count = 0

        for question in questions:
            first_number, second_number = _numbers_from_prompt(question.prompt)
            self.assertEqual(question.correct_answer, first_number * second_number)
            if first_number >= 12:
                two_digit_count += 1
                self.assertLessEqual(first_number, 99)
                self.assertGreaterEqual(second_number, 2)
                self.assertLessEqual(second_number, 9)
            else:
                self.assertGreaterEqual(first_number, 2)
                self.assertLessEqual(first_number, 10)
                self.assertGreaterEqual(second_number, 2)
                self.assertLessEqual(second_number, 10)

        self.assertGreater(two_digit_count, 620)
        self.assertLess(two_digit_count, 780)

    def test_division_uses_one_digit_divisors_and_valid_remainders(self) -> None:
        questions = [self.generator.generate_division_question() for _ in range(1000)]
        remainder_count = 0
        exact_count = 0

        for question in questions:
            dividend, divisor = _numbers_from_prompt(question.prompt)
            self.assertGreaterEqual(divisor, 2)
            self.assertLessEqual(divisor, 9)
            self.assertGreaterEqual(question.correct_answer, 2)
            self.assertLessEqual(question.correct_answer, 99)
            self.assertLessEqual(dividend, 999)
            if question.remainder_answer is None:
                exact_count += 1
                self.assertEqual(dividend, divisor * question.correct_answer)
            else:
                remainder_count += 1
                self.assertGreater(question.remainder_answer, 0)
                self.assertLess(question.remainder_answer, divisor)
                self.assertEqual(
                    dividend,
                    divisor * question.correct_answer + question.remainder_answer,
                )

        self.assertGreater(exact_count, 350)
        self.assertGreater(remainder_count, 350)

    def test_mixed_uses_only_active_topics(self) -> None:
        questions = [
            self.generator.generate_question(QuestionGenerator.MIXED_TOPIC)
            for _ in range(200)
        ]
        self.assertEqual(
            {question.topic for question in questions},
            set(QuestionGenerator.QUESTION_TYPES),
        )


if __name__ == "__main__":
    unittest.main()
