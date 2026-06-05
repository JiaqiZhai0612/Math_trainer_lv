"""Tkinter entry point for the math trainer prototype."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

from adaptive_engine import AdaptiveEngine
from database import Database
from question_generator import Question, QuestionGenerator


QUESTION_COUNT = 30
QUESTIONS_PER_COLUMN = 15
TOPIC_LABELS = {
    QuestionGenerator.ADDITION_TOPIC: "Saskaitīšana",
    QuestionGenerator.SUBTRACTION_TOPIC: "Atņemšana",
    QuestionGenerator.MULTIPLICATION_TOPIC: "Reizināšana",
    QuestionGenerator.DIVISION_TOPIC: "Dalīšana",
    QuestionGenerator.MIXED_TOPIC: "Jaukts",
    QuestionGenerator.WORD_PROBLEMS_TOPIC: "Teksta uzdevumi",
}
TOPIC_BY_LABEL = {label: topic for topic, label in TOPIC_LABELS.items()}


class MathTrainerApp:
    """Tkinter application that presents a full practice page."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Matemātikas treneris")
        self._maximize_window()

        self.database = Database()
        self.generator = QuestionGenerator()
        self.adaptive_engine = AdaptiveEngine()
        self.questions: list[Question] = []
        self.answer_entries: list[list[tk.Entry]] = []
        self.result_labels: list[tk.Label] = []
        self.correct_rows: set[int] = set()
        self.correct_value_label: tk.Label | None = None
        self.remaining_value_label: tk.Label | None = None
        self.selected_topic = tk.StringVar(value=TOPIC_LABELS[QuestionGenerator.MIXED_TOPIC])

        self._build_layout()
        self.load_next_page()

    def _maximize_window(self) -> None:
        """Open maximized when supported, with a fullscreen-like fallback."""
        try:
            self.root.state("zoomed")
        except tk.TclError:
            width = self.root.winfo_screenwidth()
            height = self.root.winfo_screenheight()
            self.root.geometry(f"{width}x{height}+0+0")

    def _build_layout(self) -> None:
        """Create the fixed controls and the scrollable question area."""
        header = tk.Label(
            self.root,
            text="Matemātikas vingrinājumi",
            font=("Arial", 26, "bold"),
        )
        header.pack(padx=24, pady=(18, 10), anchor="w")

        selector_frame = tk.Frame(self.root)
        selector_frame.pack(fill="x", padx=24, pady=(0, 10))

        selector_label = tk.Label(selector_frame, text="Tēma:", font=("Arial", 15, "bold"))
        selector_label.pack(side="left")

        topic_selector = tk.OptionMenu(
            selector_frame,
            self.selected_topic,
            TOPIC_LABELS[QuestionGenerator.ADDITION_TOPIC],
            TOPIC_LABELS[QuestionGenerator.SUBTRACTION_TOPIC],
            TOPIC_LABELS[QuestionGenerator.MULTIPLICATION_TOPIC],
            TOPIC_LABELS[QuestionGenerator.DIVISION_TOPIC],
            TOPIC_LABELS[QuestionGenerator.MIXED_TOPIC],
            TOPIC_LABELS[QuestionGenerator.WORD_PROBLEMS_TOPIC],
            command=self._topic_changed,
        )
        topic_selector.config(font=("Arial", 14), width=16)
        topic_selector.pack(side="left", padx=(8, 0))

        progress_frame = tk.Frame(self.root, padx=12, pady=8, relief=tk.GROOVE, bd=1)
        progress_frame.pack(fill="x", padx=24, pady=(0, 14))

        correct_label = tk.Label(progress_frame, text="Pareizi:", font=("Arial", 15, "bold"))
        correct_label.pack(side="left")

        self.correct_value_label = tk.Label(progress_frame, text="0 / 30", font=("Arial", 15))
        self.correct_value_label.pack(side="left", padx=(8, 28))

        remaining_label = tk.Label(progress_frame, text="Atlikuši:", font=("Arial", 15, "bold"))
        remaining_label.pack(side="left")

        self.remaining_value_label = tk.Label(progress_frame, text="30", font=("Arial", 15))
        self.remaining_value_label.pack(side="left", padx=(8, 0))

        button_frame = tk.Frame(self.root)
        button_frame.pack(side="bottom", fill="x", padx=24, pady=(0, 18))

        content_frame = tk.Frame(self.root)
        content_frame.pack(fill="both", expand=True, padx=24, pady=(0, 18))

        self.canvas = tk.Canvas(content_frame, highlightthickness=0)
        scrollbar = tk.Scrollbar(content_frame, orient="vertical", command=self.canvas.yview)
        self.question_frame = tk.Frame(self.canvas)
        self.question_frame.bind("<Configure>", self._update_scroll_region)
        self.question_frame.columnconfigure(0, weight=1)
        self.question_frame.columnconfigure(1, weight=1)

        self.canvas_window = self.canvas.create_window(
            (0, 0),
            window=self.question_frame,
            anchor="nw",
        )
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.bind("<Configure>", self._resize_question_frame)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.check_button = tk.Button(
            button_frame,
            text="Pārbaudīt atbildes",
            command=self.check_answers,
            font=("Arial", 14),
        )
        self.check_button.pack(side="left")

        self.next_page_button = tk.Button(
            button_frame,
            text="Nākamā lapa",
            command=self.load_next_page,
            font=("Arial", 14),
            state=tk.DISABLED,
        )
        self.next_page_button.pack(side="left", padx=(12, 0))

        self.statistics_button = tk.Button(
            button_frame,
            text="Statistika",
            command=self.show_statistics_window,
            font=("Arial", 14),
        )
        self.statistics_button.pack(side="left", padx=(12, 0))

    def _update_scroll_region(self, event: tk.Event | None = None) -> None:
        """Keep the canvas scrollable area matched to its contents."""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _resize_question_frame(self, event: tk.Event) -> None:
        """Let question rows use the full available canvas width."""
        self.canvas.itemconfigure(self.canvas_window, width=event.width)

    def load_next_page(self) -> None:
        """Generate and display a new page of 30 questions."""
        for widget in self.question_frame.winfo_children():
            widget.destroy()

        self.questions = []
        self.answer_entries = []
        self.result_labels = []
        self.correct_rows = set()
        self.next_page_button.config(state=tk.DISABLED)
        self._update_progress()

        difficulty = self.adaptive_engine.get_current_difficulty()
        selected_topic = self._get_selected_topic()
        accuracy_by_topic = None
        if selected_topic == QuestionGenerator.MIXED_TOPIC:
            accuracy_by_topic = self.database.get_accuracy_by_question_type()

        for index in range(QUESTION_COUNT):
            question = self.generator.generate_question(
                selected_topic,
                difficulty,
                accuracy_by_topic,
            )
            self.questions.append(question)
            self._add_question_row(index, question)

        if self.answer_entries:
            self.answer_entries[0][0].focus_set()

    def _topic_changed(self, selected_topic: str) -> None:
        """Start a fresh page when the selected topic changes."""
        self.load_next_page()

    def _get_selected_topic(self) -> str:
        """Return the internal topic name for the selected UI label."""
        return TOPIC_BY_LABEL[self.selected_topic.get()]

    def _add_question_row(self, index: int, question: Question) -> None:
        """Render one question row with answer input and result indicator."""
        column = 0 if index < QUESTIONS_PER_COLUMN else 1
        row_index = index % QUESTIONS_PER_COLUMN

        row = tk.Frame(self.question_frame)
        row.grid(row=row_index, column=column, sticky="ew", padx=(0, 24), pady=5)
        row.columnconfigure(1, weight=1)

        number_label = tk.Label(row, text=f"{index + 1}.", font=("Arial", 16), width=4, anchor="e")
        number_label.grid(row=0, column=0, padx=(0, 10))

        question_label = tk.Label(
            row,
            text=question.prompt,
            font=("Arial", 17),
            anchor="w",
            justify="left",
            wraplength=430,
        )
        question_label.grid(row=0, column=1, sticky="w")

        row_entries = []
        answer_entry = tk.Entry(row, font=("Arial", 16), justify="center", width=10)
        answer_entry.grid(row=0, column=2, padx=(12, 6))
        answer_entry.bind("<Return>", self.check_answers)
        row_entries.append(answer_entry)

        result_column = 3
        if question.remainder_answer is not None:
            remainder_label = tk.Label(row, text="atl.", font=("Arial", 15))
            remainder_label.grid(row=0, column=3, padx=(2, 4))

            remainder_entry = tk.Entry(row, font=("Arial", 16), justify="center", width=8)
            remainder_entry.grid(row=0, column=4, padx=(0, 6))
            remainder_entry.bind("<Return>", self.check_answers)
            row_entries.append(remainder_entry)
            result_column = 5

        result_label = tk.Label(row, text="", font=("Arial", 20, "bold"), width=3)
        result_label.grid(row=0, column=result_column, padx=(4, 0))

        self.answer_entries.append(row_entries)
        self.result_labels.append(result_label)

    def check_answers(self, event: tk.Event | None = None) -> None:
        """Check every editable answer and save each attempt."""
        for index, question in enumerate(self.questions):
            if index in self.correct_rows:
                continue

            entries = self.answer_entries[index]
            raw_answer = self._format_user_answer(entries, question)
            is_correct = self._is_answer_correct(question, entries)

            self.database.save_attempt(
                topic=question.topic,
                question_type=question.question_type,
                question_text=question.prompt,
                correct_answer=question.correct_answer,
                user_answer=raw_answer,
                is_correct=is_correct,
                difficulty=question.difficulty,
            )
            self.adaptive_engine.record_result(is_correct)

            if is_correct:
                self.correct_rows.add(index)
                for entry in entries:
                    entry.config(state=tk.DISABLED)
                self.result_labels[index].config(text="✓", fg="green")
            else:
                for entry in entries:
                    entry.config(state=tk.NORMAL)
                self.result_labels[index].config(text="✗", fg="red")

        if len(self.correct_rows) == len(self.questions):
            self.next_page_button.config(state=tk.NORMAL)

        self._update_progress()

    def _parse_answer(self, raw_answer: str) -> int | None:
        """Return an integer answer, or None for blank/non-number input."""
        try:
            return int(raw_answer)
        except ValueError:
            return None

    def _format_user_answer(self, entries: list[tk.Entry], question: Question) -> str:
        """Format one or two entry values for SQLite recording."""
        quotient_answer = entries[0].get().strip()
        if question.remainder_answer is None:
            return quotient_answer

        remainder_answer = entries[1].get().strip()
        return f"{quotient_answer} atl. {remainder_answer}"

    def _is_answer_correct(self, question: Question, entries: list[tk.Entry]) -> bool:
        """Validate either a single answer or quotient plus remainder."""
        quotient_answer = self._parse_answer(entries[0].get().strip())
        if quotient_answer != question.correct_answer:
            return False

        if question.remainder_answer is None:
            return True

        remainder_answer = self._parse_answer(entries[1].get().strip())
        return remainder_answer == question.remainder_answer

    def _update_progress(self) -> None:
        """Refresh the progress panel values."""
        correct_count = len(self.correct_rows)
        remaining_count = QUESTION_COUNT - correct_count

        if self.correct_value_label is not None:
            self.correct_value_label.config(text=f"{correct_count} / {QUESTION_COUNT}")
        if self.remaining_value_label is not None:
            self.remaining_value_label.config(text=str(remaining_count))

    def show_statistics_window(self) -> None:
        """Open a read-only statistics window using saved SQLite attempts."""
        statistics_window = tk.Toplevel(self.root)
        statistics_window.title("Statistika")
        statistics_window.geometry("620x420")
        statistics_window.transient(self.root)

        title_label = tk.Label(
            statistics_window,
            text="Vingrinājumu statistika",
            font=("Arial", 20, "bold"),
        )
        title_label.pack(padx=18, pady=(18, 12), anchor="w")

        statistics_content = tk.Frame(statistics_window)
        statistics_content.pack(fill="both", expand=True)

        reset_button = tk.Button(
            statistics_window,
            text="Atiestatīt statistiku",
            command=lambda: self.reset_statistics(statistics_content),
            font=("Arial", 12),
        )
        reset_button.pack(padx=18, pady=(0, 18), anchor="w")

        self._render_statistics_content(statistics_content)

    def _render_statistics_content(self, parent: tk.Frame) -> None:
        """Render current saved statistics into the statistics window."""
        for widget in parent.winfo_children():
            widget.destroy()

        overall = self.database.get_overall_statistics()
        by_topic = self.database.get_topic_statistics()

        summary_frame = tk.Frame(parent, padx=12, pady=10, relief=tk.GROOVE, bd=1)
        summary_frame.pack(fill="x", padx=18, pady=(0, 16))

        self._add_summary_value(
            summary_frame,
            "Mēģinājumi kopā:",
            str(overall["total_attempts"]),
            0,
        )
        self._add_summary_value(summary_frame, "Pareizi kopā:", str(overall["total_correct"]), 1)
        self._add_summary_value(
            summary_frame,
            "Precizitāte:",
            f"{overall['accuracy']:.1f}%",
            2,
        )

        table_frame = tk.Frame(parent)
        table_frame.pack(fill="both", expand=True, padx=18, pady=(0, 18))

        headers = ("Tēma", "Mēģinājumi", "Pareizi", "Precizitāte", "Nepareizi")
        for column, header in enumerate(headers):
            label = tk.Label(table_frame, text=header, font=("Arial", 12, "bold"), anchor="w")
            label.grid(row=0, column=column, sticky="ew", padx=6, pady=(0, 8))
            table_frame.columnconfigure(column, weight=1)

        if not by_topic:
            empty_label = tk.Label(
                table_frame,
                text="Vēl nav saglabātu mēģinājumu.",
                font=("Arial", 12),
                anchor="w",
            )
            empty_label.grid(row=1, column=0, columnspan=len(headers), sticky="w", padx=6)
            return

        for row_index, topic_stats in enumerate(by_topic, start=1):
            values = (
                self._topic_display_name(str(topic_stats["topic"])),
                topic_stats["total_attempts"],
                topic_stats["total_correct"],
                f"{topic_stats['accuracy']:.1f}%",
                topic_stats["wrong_attempts"],
            )
            for column, value in enumerate(values):
                label = tk.Label(table_frame, text=str(value), font=("Arial", 12), anchor="w")
                label.grid(row=row_index, column=column, sticky="ew", padx=6, pady=3)

    def reset_statistics(self, statistics_content: tk.Frame) -> None:
        """Confirm and clear saved answer history, then refresh statistics."""
        confirmed = messagebox.askyesno(
            "Atiestatīt statistiku",
            "Vai tiešām vēlaties dzēst visu mācību statistiku?",
            parent=statistics_content.winfo_toplevel(),
        )
        if not confirmed:
            return

        self.database.reset_statistics()
        self.adaptive_engine.reset()
        self._render_statistics_content(statistics_content)

    def _topic_display_name(self, topic: str) -> str:
        """Return a Latvian label for a stored internal topic value."""
        return TOPIC_LABELS.get(topic, topic)

    def _add_summary_value(
        self,
        parent: tk.Frame,
        label_text: str,
        value_text: str,
        column: int,
    ) -> None:
        """Render one summary metric in the statistics window."""
        metric_frame = tk.Frame(parent)
        metric_frame.grid(row=0, column=column, sticky="w", padx=(0, 28))

        label = tk.Label(metric_frame, text=label_text, font=("Arial", 12, "bold"))
        label.pack(anchor="w")

        value = tk.Label(metric_frame, text=value_text, font=("Arial", 14))
        value.pack(anchor="w")

    def close(self) -> None:
        """Close database resources before ending the application."""
        self.database.close()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    app = MathTrainerApp(root)
    root.protocol("WM_DELETE_WINDOW", app.close)
    root.mainloop()


if __name__ == "__main__":
    main()
