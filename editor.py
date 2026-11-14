import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText


WINDOW_COLOR = "#161b22"
TEXT_AREA_COLOR = "#10151c"
BUTTON_COLOR = "#293344"
TEXT_COLOR = "#e6edf5"
SELECTION_COLOR = "#385679"


class PythonEditor:
    def __init__(self, main_window):
        self.main_window = main_window
        self.document_path = None
        self.saved_text = ""
        self.apply_dark_theme()
        main_window.protocol("WM_DELETE_WINDOW", self.close_editor)
        self.main_menu = tk.Menu(main_window, **self.menu_palette)
        main_window.config(menu=self.main_menu)
        toolbar = ttk.Frame(main_window, padding=6)
        toolbar.pack(fill="x")
        document_area = ttk.Frame(main_window, padding=(8, 4))
        document_area.pack(fill="both", expand=True)
        document_area.columnconfigure(0, weight=1)
        document_area.rowconfigure(0, weight=1)
        editor_panel = ttk.Labelframe(document_area, text="Редактор кода Python", padding=5)
        results_panel = ttk.Labelframe(document_area, text="Результаты", padding=5)
        editor_panel.grid(row=0, column=0, sticky="nsew", pady=(0, 6))
        results_panel.grid(row=1, column=0, sticky="ew")
        self.input_widget = self.create_text_area(editor_panel, undo=True, wrap="none", font=("Consolas", 13), padx=8, pady=8)
        self.input_widget.pack(fill="both", expand=True)
        horizontal_scrollbar = ttk.Scrollbar(editor_panel, orient="horizontal", command=self.input_widget.xview)
        horizontal_scrollbar.pack(fill="x")
        self.input_widget.configure(xscrollcommand=horizontal_scrollbar.set)
        self.output_widget = self.create_text_area(results_panel, height=7, wrap="word", state="disabled", font=("Consolas", 11))
        self.output_widget.pack(fill="both", expand=True)
        self.status_text = tk.StringVar()
        ttk.Label(main_window, textvariable=self.status_text, padding=(10, 4)).pack(fill="x")
        self.input_widget.bind("<<Modified>>", self.on_text_changed)
        file_menu = self.add_menu("Файл")
        editing_menu = self.add_menu("Правка")
        topics_menu = self.add_menu("Текст")
        support_menu = tk.Menu(self.main_menu, tearoff=False, **self.menu_palette)
        self.add_menu_commands(file_menu, [
            ("Создать", "Ctrl+N", self.create_document), ("Открыть", "Ctrl+O", self.open_document),
            ("Сохранить", "Ctrl+S", self.save_document), ("Сохранить как", "Ctrl+Shift+S", self.save_document_as),
            ("Выход", "", self.close_editor),
        ])
        self.add_menu_commands(editing_menu, [
            ("Отменить", "Ctrl+Z", self.input_widget.edit_undo), ("Повторить", "Ctrl+Y", self.input_widget.edit_redo),
            ("Вырезать", "Ctrl+X", lambda: self.send_edit_event("Cut")),
            ("Копировать", "Ctrl+C", lambda: self.send_edit_event("Copy")),
            ("Вставить", "Ctrl+V", lambda: self.send_edit_event("Paste")),
            ("Удалить", "", self.delete_text), ("Выделить все", "Ctrl+A", self.select_document),
        ])
        topic_contents = {
            "Постановка задачи": "Проверяется запись имени переменной, знака = и списка в квадратных скобках. Элемент списка может быть целым числом или именем переменной. Допускаются пустой список и завершающая запятая.",
            "Грамматика": "Формальная грамматика будет описана на следующем этапе работы.",
            "Классификация грамматики": "Тип по Хомскому будет определён после построения грамматики.",
            "Метод анализа": "Ручной синтаксический анализатор будет разработан на следующем этапе.",
            "Тестовый пример": "Корректно: items = [1, value, -2,]\nОшибка: items = [1 value] (пропущена запятая).",
            "Список литературы": "Список источников будет дополнен при подготовке отчёта по парсеру.",
            "Исходный код программы": Path(__file__).read_text(encoding="utf-8"),
        }
        for caption, displayed_text in topic_contents.items():
            topics_menu.add_command(label=caption, command=lambda topic_title=caption, topic_body=displayed_text: self.show_text_dialog(topic_title, topic_body))
        self.main_menu.add_command(label="Пуск", command=self.start_analysis)
        self.main_menu.add_cascade(label="Справка", menu=support_menu)
        self.add_menu_commands(support_menu, [("Вызов справки", "", self.show_user_guide), ("О программе", "", self.show_about_dialog)])
        icon_directory = Path(__file__).with_name("icons")
        self.command_icons = {}
        column_number = 0
        for icon_name, button_label, callback in [
            ("new", "Создать", self.create_document), ("open", "Открыть", self.open_document),
            ("save", "Сохранить", self.save_document), ("undo", "Отменить", self.input_widget.edit_undo),
            ("redo", "Повторить", self.input_widget.edit_redo),
            ("copy", "Копировать", lambda: self.send_edit_event("Copy")),
            ("cut", "Вырезать", lambda: self.send_edit_event("Cut")),
            ("paste", "Вставить", lambda: self.send_edit_event("Paste")), ("run", "Пуск", self.start_analysis),
            ("help", "Справка", self.show_user_guide), ("about", "О программе", self.show_about_dialog),
        ]:
            button_icon = tk.PhotoImage(master=main_window, file=str(icon_directory / f"{icon_name}.png")).subsample(3)
            self.command_icons[icon_name] = button_icon
            toolbar_button = ttk.Button(toolbar, text=button_label, image=button_icon, compound="left",
                                command=lambda handler=callback: self.execute_command(handler))
            if icon_name == "run":
                toolbar_button.grid(row=1, column=0, sticky="w", padx=2, pady=2)
            else:
                toolbar_button.grid(row=0, column=column_number, sticky="ew", padx=2, pady=2)
                column_number += 1
        toolbar.update_idletasks()
        minimum_width = max(820, toolbar.winfo_reqwidth())
        main_window.minsize(minimum_width, 440)
        main_window.geometry(f"{max(1240, minimum_width)}x760")
        for shortcut_key, callback in {
            "<Control-n>": self.create_document, "<Control-o>": self.open_document, "<Control-s>": self.save_document,
            "<Control-Shift-S>": self.save_document_as, "<Control-a>": self.select_document,
            "<Control-z>": self.input_widget.edit_undo, "<Control-y>": self.input_widget.edit_redo,
        }.items():
            self.input_widget.bind(shortcut_key, lambda _event, handler=callback: self.execute_command(handler))
        self.load_document("", None)
        self.display_result("«Пуск» — запуск языкового процессора.")

    def apply_dark_theme(self):
        self.main_window.configure(background=WINDOW_COLOR)
        self.menu_palette = dict(background=WINDOW_COLOR, foreground=TEXT_COLOR,
                                activebackground=SELECTION_COLOR, activeforeground=TEXT_COLOR)
        theme_style = ttk.Style(self.main_window)
        theme_style.theme_use("clam")
        theme_style.configure(".", background=WINDOW_COLOR, foreground=TEXT_COLOR,
                        bordercolor=BUTTON_COLOR, lightcolor=WINDOW_COLOR, darkcolor=WINDOW_COLOR,
                        troughcolor=TEXT_AREA_COLOR, arrowcolor=TEXT_COLOR)
        theme_style.configure("TButton", background=BUTTON_COLOR, padding=(5, 4))
        theme_style.map("TButton", background=[("pressed", SELECTION_COLOR), ("active", "#36465c")])
        for scrollbar_orientation in ("Vertical", "Horizontal"):
            theme_style.configure(f"{scrollbar_orientation}.TScrollbar", background=BUTTON_COLOR)
            theme_style.map(f"{scrollbar_orientation}.TScrollbar", background=[("active", SELECTION_COLOR)])

    def create_text_area(self, container, **widget_options):
        displayed_text = ScrolledText(container, background=TEXT_AREA_COLOR, foreground=TEXT_COLOR,
                            insertbackground=TEXT_COLOR, selectbackground=SELECTION_COLOR,
                            selectforeground=TEXT_COLOR, highlightthickness=1,
                            highlightbackground=BUTTON_COLOR, highlightcolor=SELECTION_COLOR,
                            relief="flat", borderwidth=0, **widget_options)
        displayed_text.frame.configure(background=WINDOW_COLOR)
        displayed_text.vbar.destroy()
        displayed_text.vbar = ttk.Scrollbar(displayed_text.frame, orient="vertical", command=displayed_text.yview)
        displayed_text.vbar.pack(side="right", fill="y")
        displayed_text.configure(yscrollcommand=displayed_text.vbar.set)
        return displayed_text

    def add_menu(self, display_name):
        target_menu = tk.Menu(self.main_menu, tearoff=False, **self.menu_palette)
        self.main_menu.add_cascade(label=display_name, menu=target_menu)
        return target_menu

    def add_menu_commands(self, target_menu, menu_items):
        for caption, accelerator, callback in menu_items:
            target_menu.add_command(label=caption, accelerator=accelerator, command=lambda handler=callback: self.execute_command(handler))

    def execute_command(self, callback):
        try:
            callback()
        except tk.TclError as failure:
            if str(failure) not in {"nothing to undo", "nothing to redo"}:
                messagebox.showerror("Ошибка", str(failure), parent=self.main_window)
        return "break"

    def read_document_text(self):
        return self.input_widget.get("1.0", "end-1c")

    def update_document_status(self):
        display_name = self.document_path.name if self.document_path else "Без имени"
        has_changes = self.read_document_text() != self.saved_text
        window_title = "Редактор кода Python"
        if self.document_path:
            window_title = f"{display_name} — {window_title}"
        self.main_window.title(f"{window_title}{' *' if has_changes else ''}")
        self.status_text.set(f"{display_name}   |   {'Есть несохранённые изменения' if has_changes else 'Нет несохранённых изменений'}")

    def on_text_changed(self, _event):
        if self.input_widget.edit_modified():
            self.input_widget.edit_modified(False)
            self.update_document_status()

    def load_document(self, document_text, document_path):
        self.input_widget.delete("1.0", "end")
        self.input_widget.insert("1.0", document_text)
        self.input_widget.mark_set("insert", "1.0")
        self.input_widget.edit_reset()
        self.input_widget.edit_modified(False)
        self.document_path, self.saved_text = document_path, document_text
        self.update_document_status()
        self.input_widget.focus_set()

    def confirm_discard(self):
        if self.read_document_text() == self.saved_text:
            return True
        choice = messagebox.askyesnocancel("Сохранение", "Сохранить изменения?", parent=self.main_window)
        return choice is False or (choice is True and self.save_document())

    def create_document(self):
        if self.confirm_discard():
            self.load_document("", None)
            self.display_result("Создан новый документ.")

    def open_document(self):
        if not self.confirm_discard():
            return
        display_name = filedialog.askopenfilename(parent=self.main_window, filetypes=[("Python", "*.py"), ("Все файлы", "*.*")])
        if display_name:
            document_path = Path(display_name)
            try:
                document_text = document_path.read_text(encoding="utf-8-sig")
            except (OSError, UnicodeError) as failure:
                messagebox.showerror("Не удалось открыть файл", str(failure), parent=self.main_window)
                return
            self.load_document(document_text, document_path)
            self.display_result(f"Открыт файл {document_path.name}.")

    def save_document(self):
        return self.store_document(self.document_path) if self.document_path else self.save_document_as()

    def save_document_as(self):
        display_name = filedialog.asksaveasfilename(parent=self.main_window, defaultextension=".py",
                                           initialfile=self.document_path.name if self.document_path else "",
                                           filetypes=[("Python", "*.py"), ("Текст", "*.txt"), ("Все файлы", "*.*")])
        return bool(display_name) and self.store_document(Path(display_name))

    def store_document(self, document_path):
        document_text = self.read_document_text()
        try:
            document_path.write_text(document_text, encoding="utf-8")
        except OSError as failure:
            messagebox.showerror("Не удалось сохранить файл", str(failure), parent=self.main_window)
            return False
        self.document_path, self.saved_text = document_path, document_text
        self.update_document_status()
        return True

    def close_editor(self):
        if self.confirm_discard():
            self.main_window.destroy()

    def send_edit_event(self, callback):
        self.input_widget.focus_set()
        self.input_widget.event_generate(f"<<{callback}>>")

    def delete_text(self):
        selection_ranges = self.input_widget.tag_ranges("sel")
        if selection_ranges:
            self.input_widget.delete(*selection_ranges)
        else:
            self.input_widget.delete("insert")

    def select_document(self):
        self.input_widget.tag_add("sel", "1.0", "end-1c")
        self.input_widget.focus_set()

    def display_result(self, result_message, error_location=None):
        self.output_widget.configure(state="normal")
        self.output_widget.delete("1.0", "end")
        self.output_widget.insert("1.0", result_message)
        if error_location is not None:
            self.output_widget.tag_add("position", "1.0", "end-1c")
            self.output_widget.tag_configure("position", foreground="#8cc8ff", underline=True)
            self.output_widget.tag_bind("position", "<Button-1>", lambda _event: self.move_to_error(error_location))
        self.output_widget.configure(state="disabled")

    def move_to_error(self, error_location):
        line_number, column_number = error_location
        cursor_index = f"{line_number}.{column_number - 1}"
        self.input_widget.mark_set("insert", cursor_index)
        self.input_widget.see(cursor_index)
        self.input_widget.focus_set()

    def start_analysis(self):
        self.display_result("Пока не реализовано")

    def show_text_dialog(self, caption, document_text):
        dialog = tk.Toplevel(self.main_window)
        dialog.configure(background=WINDOW_COLOR)
        dialog.title(caption)
        dialog.geometry("750x480")
        displayed_text = self.create_text_area(dialog, wrap="word", padx=12, pady=12, font=("Segoe UI", 11))
        displayed_text.pack(fill="both", expand=True)
        displayed_text.insert("1.0", document_text)
        displayed_text.configure(state="disabled")
        ttk.Button(dialog, text="Закрыть", command=dialog.destroy).pack(pady=8)
        dialog.bind("<Escape>", lambda _event: dialog.destroy())

    def show_user_guide(self):
        guide_source = Path(__file__).with_name("README.md").read_text(encoding="utf-8")
        guide_lines = [line_text.lstrip("# ").replace("**", "").replace("`", "") for line_text in guide_source.splitlines()
                 if not line_text.startswith("![")]
        self.show_text_dialog("Руководство пользователя", "\n".join(guide_lines))

    def show_about_dialog(self):
        messagebox.showinfo("О программе", "Редактор кода Python\nЗадание 2 — программная реализация GUI\nАвтор: Рудик Дана", parent=self.main_window)


if __name__ == "__main__":
    main_window = tk.Tk()
    PythonEditor(main_window)
    main_window.mainloop()
