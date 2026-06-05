"""CustomTkinter entry point for the math trainer prototype."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from tkinter import TclError

import customtkinter as ctk

from adaptive_engine import AdaptiveEngine
from database import Database
from question_generator import Question, QuestionGenerator


QUESTION_COUNT = 30
QUESTIONS_PER_COLUMN = 15
SETTINGS_PATH = Path("app_settings.json")
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
    """CustomTkinter application that presents a full practice page."""

    def __init__(self, root: ctk.CTk) -> None:
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self.root = root
        self.root.title("Matemātikas treneris")
        self.root.configure(fg_color="#f6f8fb")
        self._apply_saved_window_state()

        self.database = Database()
        self.generator = QuestionGenerator()
        self.adaptive_engine = AdaptiveEngine()
        self.questions: list[Question] = []
        self.answer_entries: list[list[ctk.CTkEntry]] = []
        self.result_labels: list[ctk.CTkLabel] = []
        self.question_rows: list[ctk.CTkFrame] = []
        self.correct_rows: set[int] = set()
        self.correct_value_label: ctk.CTkLabel | None = None
        self.remaining_value_label: ctk.CTkLabel | None = None
        self.progress_bar: ctk.CTkProgressBar | None = None
        self.selected_topic = ctk.StringVar(value=TOPIC_LABELS[QuestionGenerator.MIXED_TOPIC])

        self.font_title = ctk.CTkFont(family="Arial", size=32, weight="bold")
        self.font_section = ctk.CTkFont(family="Arial", size=18, weight="bold")
        self.font_text = ctk.CTkFont(family="Arial", size=18)
        self.font_question = ctk.CTkFont(family="Arial", size=20)
        self.font_entry = ctk.CTkFont(family="Arial", size=22, weight="bold")
        self.font_button = ctk.CTkFont(family="Arial", size=17, weight="bold")

        self._build_layout()
        self.load_next_page()

    def _apply_saved_window_state(self) -> None:
        """Restore the previous window state, defaulting to maximized."""
        settings = self._load_window_settings()
        if settings is None or settings.get("maximized", True):
            self._maximize_window()
            return

        width = self._validated_dimension(settings.get("width"), 1100)
        height = self._validated_dimension(settings.get("height"), 760)
        x_position = self._validated_position(settings.get("x"), 80)
        y_position = self._validated_position(settings.get("y"), 60)
        self.root.geometry(f"{width}x{height}+{x_position}+{y_position}")

    def _load_window_settings(self) -> dict[str, object] | None:
        """Load saved window placement from the local settings file."""
        try:
            with SETTINGS_PATH.open("r", encoding="utf-8") as settings_file:
                loaded_settings = json.load(settings_file)
        except (OSError, json.JSONDecodeError):
            return None

        if not isinstance(loaded_settings, dict):
            return None

        return loaded_settings

    def _validated_dimension(self, value: object, fallback: int) -> int:
        """Return a usable saved width or height."""
        if isinstance(value, int) and value >= 640:
            return value
        return fallback

    def _validated_position(self, value: object, fallback: int) -> int:
        """Return a usable saved screen position."""
        if isinstance(value, int):
            return value
        return fallback

    def _maximize_window(self) -> None:
        """Open maximized when supported, with a fullscreen-like fallback."""
        try:
            self.root.state("zoomed")
        except TclError:
            width = self.root.winfo_screenwidth()
            height = self.root.winfo_screenheight()
            self.root.geometry(f"{width}x{height}+0+0")

    def _save_window_settings(self) -> None:
        """Persist the current window placement for the next startup."""
        self.root.update_idletasks()
        maximized = self._is_window_maximized()
        width, height, x_position, y_position = self._get_current_geometry_parts()

        settings = {
            "width": width,
            "height": height,
            "x": x_position,
            "y": y_position,
            "maximized": maximized,
        }

        with SETTINGS_PATH.open("w", encoding="utf-8") as settings_file:
            json.dump(settings, settings_file, indent=2)
            settings_file.write("\n")

    def _is_window_maximized(self) -> bool:
        """Return whether the root window is currently maximized."""
        try:
            return self.root.state() == "zoomed"
        except TclError:
            return False

    def _get_current_geometry_parts(self) -> tuple[int, int, int, int]:
        """Parse Tk geometry into width, height, x, and y values."""
        geometry = self.root.geometry()
        size_part, x_position, y_position = geometry.split("+", maxsplit=2)
        width, height = size_part.split("x", maxsplit=1)
        return int(width), int(height), int(x_position), int(y_position)

    def _build_layout(self) -> None:
        """Create the fixed controls and the scrollable question area."""
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(2, weight=1)

        header_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=32, pady=(24, 12))
        header_frame.grid_columnconfigure(0, weight=1)

        header = ctk.CTkLabel(
            header_frame,
            text="Matemātikas vingrinājumi",
            font=self.font_title,
            text_color="#1f2937",
        )
        header.grid(row=0, column=0, sticky="w")

        selector_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        selector_frame.grid(row=0, column=1, sticky="e")

        selector_label = ctk.CTkLabel(
            selector_frame,
            text="Tēma:",
            font=self.font_section,
            text_color="#334155",
        )
        selector_label.grid(row=0, column=0, padx=(0, 10))

        topic_selector = ctk.CTkOptionMenu(
            selector_frame,
            variable=self.selected_topic,
            values=[
                TOPIC_LABELS[QuestionGenerator.ADDITION_TOPIC],
                TOPIC_LABELS[QuestionGenerator.SUBTRACTION_TOPIC],
                TOPIC_LABELS[QuestionGenerator.MULTIPLICATION_TOPIC],
                TOPIC_LABELS[QuestionGenerator.DIVISION_TOPIC],
                TOPIC_LABELS[QuestionGenerator.MIXED_TOPIC],
                TOPIC_LABELS[QuestionGenerator.WORD_PROBLEMS_TOPIC],
            ],
            command=self._topic_changed,
            width=210,
            height=42,
            corner_radius=16,
            font=self.font_text,
            dropdown_font=self.font_text,
            fg_color="#2563eb",
            button_color="#1d4ed8",
            button_hover_color="#1e40af",
        )
        topic_selector.grid(row=0, column=1)

        progress_frame = ctk.CTkFrame(
            self.root,
            fg_color="#ffffff",
            corner_radius=18,
            border_width=1,
            border_color="#dbe3ef",
        )
        progress_frame.grid(row=1, column=0, sticky="ew", padx=32, pady=(0, 18))
        progress_frame.grid_columnconfigure(2, weight=1)

        self._add_progress_metric(progress_frame, "Pareizi:", "0 / 30", 0)
        self._add_progress_metric(progress_frame, "Atlikuši:", "30", 1)

        self.progress_bar = ctk.CTkProgressBar(
            progress_frame,
            height=22,
            corner_radius=12,
            fg_color="#e8eef7",
            progress_color="#22c55e",
        )
        self.progress_bar.grid(row=0, column=2, sticky="ew", padx=(18, 22), pady=22)
        self.progress_bar.set(0)

        content_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        content_frame.grid(row=2, column=0, sticky="nsew", padx=32, pady=(0, 18))
        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_rowconfigure(0, weight=1)

        self.question_frame = ctk.CTkScrollableFrame(
            content_frame,
            fg_color="transparent",
            scrollbar_button_color="#cbd5e1",
            scrollbar_button_hover_color="#94a3b8",
        )
        self.question_frame.grid(row=0, column=0, sticky="nsew")
        self.question_frame.grid_columnconfigure(0, weight=1, uniform="question-columns")
        self.question_frame.grid_columnconfigure(1, weight=1, uniform="question-columns")

        button_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        button_frame.grid(row=3, column=0, sticky="ew", padx=32, pady=(0, 24))
        button_frame.grid_columnconfigure(3, weight=1)

        self.check_button = ctk.CTkButton(
            button_frame,
            text="Pārbaudīt atbildes",
            command=self.check_answers,
            font=self.font_button,
            height=48,
            corner_radius=18,
            fg_color="#2563eb",
            hover_color="#1d4ed8",
        )
        self.check_button.grid(row=0, column=0, padx=(0, 12))

        self.next_page_button = ctk.CTkButton(
            button_frame,
            text="Nākamā lapa",
            command=self.load_next_page,
            font=self.font_button,
            height=48,
            corner_radius=18,
            fg_color="#16a34a",
            hover_color="#15803d",
            state="disabled",
        )
        self.next_page_button.grid(row=0, column=1, padx=(0, 12))

        self.statistics_button = ctk.CTkButton(
            button_frame,
            text="Statistika",
            command=self.show_statistics_window,
            font=self.font_button,
            height=48,
            corner_radius=18,
            fg_color="#64748b",
            hover_color="#475569",
        )
        self.statistics_button.grid(row=0, column=2)

    def _add_progress_metric(
        self,
        parent: ctk.CTkFrame,
        label_text: str,
        value_text: str,
        column: int,
    ) -> None:
        """Render a large progress metric and keep references to changing values."""
        metric_frame = ctk.CTkFrame(parent, fg_color="transparent")
        metric_frame.grid(row=0, column=column, padx=(22, 8), pady=16, sticky="w")

        label = ctk.CTkLabel(
            metric_frame,
            text=label_text,
            font=self.font_section,
            text_color="#475569",
        )
        label.grid(row=0, column=0, sticky="w")

        value = ctk.CTkLabel(
            metric_frame,
            text=value_text,
            font=ctk.CTkFont(family="Arial", size=26, weight="bold"),
            text_color="#0f172a",
        )
        value.grid(row=1, column=0, sticky="w")

        if label_text == "Pareizi:":
            self.correct_value_label = value
        else:
            self.remaining_value_label = value

    def load_next_page(self) -> None:
        """Generate and display a new page of 30 questions."""
        for widget in self.question_frame.winfo_children():
            widget.destroy()

        self.questions = []
        self.answer_entries = []
        self.result_labels = []
        self.question_rows = []
        self.correct_rows = set()
        self.next_page_button.configure(state="disabled")
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

        row = ctk.CTkFrame(
            self.question_frame,
            fg_color="#ffffff",
            corner_radius=14,
            border_width=2,
            border_color="#e2e8f0",
        )
        row.grid(row=row_index, column=column, sticky="ew", padx=(0, 16), pady=6)
        row.grid_columnconfigure(1, weight=1)

        number_label = ctk.CTkLabel(
            row,
            text=f"{index + 1}.",
            font=self.font_question,
            text_color="#64748b",
            width=46,
            anchor="e",
        )
        number_label.grid(row=0, column=0, padx=(12, 10), pady=12)

        question_label = ctk.CTkLabel(
            row,
            text=question.prompt,
            font=self.font_question,
            text_color="#111827",
            anchor="w",
            justify="left",
            wraplength=500,
        )
        question_label.grid(row=0, column=1, sticky="ew", pady=12)

        row_entries = []
        answer_entry = self._create_answer_entry(row, width=116)
        answer_entry.grid(row=0, column=2, padx=(14, 6), pady=12)
        row_entries.append(answer_entry)

        result_column = 3
        if question.remainder_answer is not None:
            remainder_label = ctk.CTkLabel(
                row,
                text="atl.",
                font=self.font_text,
                text_color="#475569",
            )
            remainder_label.grid(row=0, column=3, padx=(4, 4), pady=12)

            remainder_entry = self._create_answer_entry(row, width=94)
            remainder_entry.grid(row=0, column=4, padx=(0, 6), pady=12)
            row_entries.append(remainder_entry)
            result_column = 5

        result_label = ctk.CTkLabel(
            row,
            text="",
            font=ctk.CTkFont(family="Arial", size=26, weight="bold"),
            width=42,
            text_color="#64748b",
        )
        result_label.grid(row=0, column=result_column, padx=(4, 12), pady=12)

        self.question_rows.append(row)
        self.answer_entries.append(row_entries)
        self.result_labels.append(result_label)

    def _create_answer_entry(self, parent: ctk.CTkFrame, width: int) -> ctk.CTkEntry:
        """Create a large child-friendly numeric answer field."""
        entry = ctk.CTkEntry(
            parent,
            font=self.font_entry,
            justify="center",
            width=width,
            height=48,
            corner_radius=16,
            border_width=2,
            border_color="#cbd5e1",
            fg_color="#f8fafc",
            text_color="#0f172a",
        )
        entry.bind("<Return>", self.check_answers)
        return entry

    def check_answers(self, event: object | None = None) -> None:
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
                self._mark_row_correct(index)
            else:
                self._mark_row_incorrect(index)

        if len(self.correct_rows) == len(self.questions):
            self.next_page_button.configure(state="normal")

        self._update_progress()

    def _mark_row_correct(self, index: int) -> None:
        """Disable a solved row and show positive feedback."""
        for entry in self.answer_entries[index]:
            entry.configure(
                state="disabled",
                border_color="#22c55e",
                fg_color="#eefdf3",
                text_color="#166534",
            )
        self.question_rows[index].configure(fg_color="#f0fdf4", border_color="#22c55e")
        self.result_labels[index].configure(text="✓", text_color="#16a34a")

    def _mark_row_incorrect(self, index: int) -> None:
        """Keep an unsolved row editable and show clear corrective feedback."""
        for entry in self.answer_entries[index]:
            entry.configure(
                state="normal",
                border_color="#ef4444",
                fg_color="#fff7f7",
                text_color="#7f1d1d",
            )
        self.question_rows[index].configure(fg_color="#fff7f7", border_color="#ef4444")
        self.result_labels[index].configure(text="✕", text_color="#dc2626")

    def _parse_answer(self, raw_answer: str) -> int | None:
        """Return an integer answer, or None for blank/non-number input."""
        try:
            return int(raw_answer)
        except ValueError:
            return None

    def _format_user_answer(self, entries: list[ctk.CTkEntry], question: Question) -> str:
        """Format one or two entry values for SQLite recording."""
        quotient_answer = entries[0].get().strip()
        if question.remainder_answer is None:
            return quotient_answer

        remainder_answer = entries[1].get().strip()
        return f"{quotient_answer} atl. {remainder_answer}"

    def _is_answer_correct(self, question: Question, entries: list[ctk.CTkEntry]) -> bool:
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
            self.correct_value_label.configure(text=f"{correct_count} / {QUESTION_COUNT}")
        if self.remaining_value_label is not None:
            self.remaining_value_label.configure(text=str(remaining_count))
        if self.progress_bar is not None:
            self.progress_bar.set(correct_count / QUESTION_COUNT)

    def show_statistics_window(self) -> None:
        """Open a read-only statistics window using saved SQLite attempts."""
        statistics_window = ctk.CTkToplevel(self.root)
        statistics_window.title("Statistika")
        statistics_window.geometry("760x520")
        statistics_window.transient(self.root)
        statistics_window.configure(fg_color="#f6f8fb")
        statistics_window.grid_columnconfigure(0, weight=1)
        statistics_window.grid_rowconfigure(1, weight=1)

        title_label = ctk.CTkLabel(
            statistics_window,
            text="Vingrinājumu statistika",
            font=ctk.CTkFont(family="Arial", size=26, weight="bold"),
            text_color="#1f2937",
        )
        title_label.grid(row=0, column=0, padx=24, pady=(24, 14), sticky="w")

        statistics_content = ctk.CTkScrollableFrame(
            statistics_window,
            fg_color="transparent",
            scrollbar_button_color="#cbd5e1",
            scrollbar_button_hover_color="#94a3b8",
        )
        statistics_content.grid(row=1, column=0, sticky="nsew", padx=24, pady=(0, 16))

        reset_button = ctk.CTkButton(
            statistics_window,
            text="Atiestatīt statistiku",
            command=lambda: self.reset_statistics(statistics_content),
            font=ctk.CTkFont(family="Arial", size=15, weight="bold"),
            height=42,
            corner_radius=16,
            fg_color="#dc2626",
            hover_color="#b91c1c",
        )
        reset_button.grid(row=2, column=0, padx=24, pady=(0, 24), sticky="w")

        self._render_statistics_content(statistics_content)
        statistics_window.lift()
        statistics_window.focus_force()

    def _render_statistics_content(self, parent: ctk.CTkScrollableFrame) -> None:
        """Render current saved statistics into the statistics window."""
        for widget in parent.winfo_children():
            widget.destroy()

        overall = self.database.get_overall_statistics()
        by_topic = self.database.get_topic_statistics()

        summary_frame = ctk.CTkFrame(
            parent,
            fg_color="#ffffff",
            corner_radius=16,
            border_width=1,
            border_color="#dbe3ef",
        )
        summary_frame.pack(fill="x", pady=(0, 18))

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

        table_frame = ctk.CTkFrame(
            parent,
            fg_color="#ffffff",
            corner_radius=16,
            border_width=1,
            border_color="#dbe3ef",
        )
        table_frame.pack(fill="both", expand=True)

        headers = ("Tēma", "Mēģinājumi", "Pareizi", "Precizitāte", "Nepareizi")
        for column, header in enumerate(headers):
            label = ctk.CTkLabel(
                table_frame,
                text=header,
                font=ctk.CTkFont(family="Arial", size=15, weight="bold"),
                text_color="#334155",
                anchor="w",
            )
            label.grid(row=0, column=column, sticky="ew", padx=12, pady=(14, 8))
            table_frame.grid_columnconfigure(column, weight=1)

        if not by_topic:
            empty_label = ctk.CTkLabel(
                table_frame,
                text="Vēl nav saglabātu mēģinājumu.",
                font=self.font_text,
                text_color="#64748b",
                anchor="w",
            )
            empty_label.grid(row=1, column=0, columnspan=len(headers), sticky="w", padx=12, pady=14)
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
                label = ctk.CTkLabel(
                    table_frame,
                    text=str(value),
                    font=ctk.CTkFont(family="Arial", size=15),
                    text_color="#0f172a",
                    anchor="w",
                )
                label.grid(row=row_index, column=column, sticky="ew", padx=12, pady=5)

    def reset_statistics(self, statistics_content: ctk.CTkScrollableFrame) -> None:
        """Confirm and clear saved answer history, then refresh statistics."""
        self._show_confirmation_dialog(
            title="Atiestatīt statistiku",
            message="Vai tiešām vēlaties dzēst visu mācību statistiku?",
            on_confirm=lambda: self._reset_statistics_confirmed(statistics_content),
        )

    def _reset_statistics_confirmed(self, statistics_content: ctk.CTkScrollableFrame) -> None:
        """Clear statistics after the custom confirmation dialog accepts."""
        self.database.reset_statistics()
        self.adaptive_engine.reset()
        self._render_statistics_content(statistics_content)

    def _show_confirmation_dialog(
        self,
        title: str,
        message: str,
        on_confirm: Callable[[], None],
    ) -> None:
        """Show a CustomTkinter yes/no dialog."""
        dialog = ctk.CTkToplevel(self.root)
        dialog.title(title)
        dialog.geometry("460x220")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(fg_color="#f6f8fb")
        dialog.grid_columnconfigure(0, weight=1)

        title_label = ctk.CTkLabel(
            dialog,
            text=title,
            font=ctk.CTkFont(family="Arial", size=22, weight="bold"),
            text_color="#1f2937",
        )
        title_label.grid(row=0, column=0, padx=24, pady=(24, 10), sticky="w")

        message_label = ctk.CTkLabel(
            dialog,
            text=message,
            font=self.font_text,
            text_color="#334155",
            wraplength=400,
            justify="left",
        )
        message_label.grid(row=1, column=0, padx=24, pady=(0, 24), sticky="w")

        button_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        button_frame.grid(row=2, column=0, padx=24, pady=(0, 24), sticky="e")

        cancel_button = ctk.CTkButton(
            button_frame,
            text="Nē",
            command=dialog.destroy,
            font=self.font_button,
            height=42,
            width=96,
            corner_radius=16,
            fg_color="#64748b",
            hover_color="#475569",
        )
        cancel_button.grid(row=0, column=0, padx=(0, 10))

        def confirm_and_close() -> None:
            on_confirm()
            dialog.destroy()

        confirm_button = ctk.CTkButton(
            button_frame,
            text="Jā",
            command=confirm_and_close,
            font=self.font_button,
            height=42,
            width=96,
            corner_radius=16,
            fg_color="#dc2626",
            hover_color="#b91c1c",
        )
        confirm_button.grid(row=0, column=1)
        dialog.lift()
        dialog.focus_force()

    def _topic_display_name(self, topic: str) -> str:
        """Return a Latvian label for a stored internal topic value."""
        return TOPIC_LABELS.get(topic, topic)

    def _add_summary_value(
        self,
        parent: ctk.CTkFrame,
        label_text: str,
        value_text: str,
        column: int,
    ) -> None:
        """Render one summary metric in the statistics window."""
        metric_frame = ctk.CTkFrame(parent, fg_color="transparent")
        metric_frame.grid(row=0, column=column, sticky="w", padx=18, pady=18)

        label = ctk.CTkLabel(
            metric_frame,
            text=label_text,
            font=ctk.CTkFont(family="Arial", size=15, weight="bold"),
            text_color="#475569",
        )
        label.pack(anchor="w")

        value = ctk.CTkLabel(
            metric_frame,
            text=value_text,
            font=ctk.CTkFont(family="Arial", size=22, weight="bold"),
            text_color="#0f172a",
        )
        value.pack(anchor="w")

    def close(self) -> None:
        """Close database resources before ending the application."""
        self._save_window_settings()
        self.database.close()
        self.root.destroy()


def main() -> None:
    root = ctk.CTk()
    app = MathTrainerApp(root)
    root.protocol("WM_DELETE_WINDOW", app.close)
    root.mainloop()


if __name__ == "__main__":
    main()
