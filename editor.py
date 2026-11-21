import tkinter as tk
import keyword
import tokenize
import io
import sys
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
        self.application_icon = tk.PhotoImage(
            master=main_window, file=str(Path(__file__).with_name("icons") / "run.png"))
        main_window.iconphoto(True, self.application_icon)
        self.documents = {}
        self.editor_font_size = 13
        self.result_font_size = 11
        self.language = "ru"
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
        self.workspace_splitter = tk.PanedWindow(
            document_area, orient="vertical", background=BUTTON_COLOR,
            sashwidth=8, sashrelief="flat", sashcursor="sb_v_double_arrow",
            borderwidth=0, opaqueresize=True)
        self.workspace_splitter.pack(fill="both", expand=True)
        editor_panel = ttk.Labelframe(self.workspace_splitter, text="Редактор кода Python", padding=5)
        results_panel = ttk.Labelframe(self.workspace_splitter, text="Результаты", padding=5)
        self.workspace_splitter.add(editor_panel, minsize=140, stretch="always")
        self.workspace_splitter.add(results_panel, minsize=110, stretch="never")
        self.document_tabs = ttk.Notebook(editor_panel, style="Documents.TNotebook")
        self.document_tabs.bind("<ButtonPress-1>", self.press_tab_close, add="+")
        self.document_tabs.bind("<ButtonRelease-1>", self.release_tab_close, add="+")
        self.pressed_close_tab = None
        self.document_tabs.pack(fill="both", expand=True)
        self.document_tabs.bind("<<NotebookTabChanged>>", self.activate_document)
        initial_page = ttk.Frame(self.document_tabs)
        self.document_tabs.add(initial_page, text="Без имени")
        self.input_widget = self.create_text_area(initial_page, undo=True, wrap="none", font=("Consolas", 13), padx=8, pady=8)
        self.input_widget.pack(fill="both", expand=True)
        horizontal_scrollbar = ttk.Scrollbar(initial_page, orient="horizontal", command=self.input_widget.xview)
        horizontal_scrollbar.pack(fill="x")
        self.input_widget.configure(xscrollcommand=horizontal_scrollbar.set)
        self.register_document(initial_page, self.input_widget)
        self.result_tabs = ttk.Notebook(results_panel)
        self.result_tabs.pack(fill="both", expand=True)
        messages_page = ttk.Frame(self.result_tabs)
        self.result_tabs.add(messages_page, text="Сообщения")
        self.output_widget = self.create_text_area(
            messages_page, height=7, wrap="word", state="disabled", font=("Consolas", 11))
        self.output_widget.pack(fill="both", expand=True)
        errors_page = ttk.Frame(self.result_tabs)
        self.result_tabs.add(errors_page, text="Ошибки")
        self.error_table = ttk.Treeview(errors_page, columns=("message", "line", "column"), show="headings", height=5)
        for key, label in [("message", "Сообщение"), ("line", "Строка"), ("column", "Столбец")]:
            self.error_table.heading(key, text=label)
        self.error_table.column("message", width=600)
        for key in ("line", "column"):
            self.error_table.column(key, width=90, stretch=False)
        scrollbar = ttk.Scrollbar(errors_page, orient="vertical", command=self.error_table.yview)
        scrollbar.pack(side="right", fill="y")
        self.error_table.configure(yscrollcommand=scrollbar.set)
        self.error_table.pack(fill="both", expand=True)
        self.error_table.bind("<<TreeviewSelect>>", self.select_error)
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
            ("Отменить", "Ctrl+Z", lambda: self.input_widget.edit_undo()), ("Повторить", "Ctrl+Y", lambda: self.input_widget.edit_redo()),
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
            ("save", "Сохранить", self.save_document), ("undo", "Отменить", lambda: self.input_widget.edit_undo()),
            ("redo", "Повторить", lambda: self.input_widget.edit_redo()),
            ("copy", "Копировать", lambda: self.send_edit_event("Copy")),
            ("cut", "Вырезать", lambda: self.send_edit_event("Cut")),
            ("paste", "Вставить", lambda: self.send_edit_event("Paste")), ("run", "Пуск", self.start_analysis),
            ("help", "Справка", self.show_user_guide), ("about", "О программе", self.show_about_dialog),
        ]:
            button_icon = tk.PhotoImage(master=main_window, file=str(icon_directory / f"{icon_name}.png")).subsample(2)
            self.command_icons[icon_name] = button_icon
            toolbar_button = ttk.Button(toolbar, image=button_icon, style="Toolbar.TButton",
                                        command=lambda handler=callback: self.execute_command(handler))
            self.add_button_tooltip(toolbar_button, button_label)
            toolbar_button.grid(row=0, column=column_number, sticky="ew", padx=2, pady=2)
            column_number += 1
        toolbar.update_idletasks()
        minimum_width = max(820, toolbar.winfo_reqwidth())
        main_window.minsize(minimum_width, 440)
        main_window.geometry(f"{max(1240, minimum_width)}x760")
        for shortcut_key, callback in {
            "<Control-n>": self.create_document, "<Control-o>": self.open_document, "<Control-s>": self.save_document,
            "<Control-Shift-S>": self.save_document_as, "<Control-a>": self.select_document,
            "<Control-z>": lambda: self.input_widget.edit_undo(), "<Control-y>": lambda: self.input_widget.edit_redo(),
        }.items():
            self.input_widget.bind(shortcut_key, lambda _event, handler=callback: self.execute_command(handler))
        view_menu = self.add_menu("Вид")
        self.add_menu_commands(view_menu, [
            ("Увеличить текст редактора", "Ctrl++", lambda: self.resize_text("editor", 1)),
            ("Уменьшить текст редактора", "Ctrl+-", lambda: self.resize_text("editor", -1)),
            ("Увеличить текст результатов", "", lambda: self.resize_text("results", 1)),
            ("Уменьшить текст результатов", "", lambda: self.resize_text("results", -1)),
            ("Закрыть вкладку", "Ctrl+W", self.close_document),
        ])
        language_menu = self.add_menu("Язык")
        language_menu.add_command(label="Русский", command=lambda: self.set_language("ru"))
        language_menu.add_command(label="English", command=lambda: self.set_language("en"))
        self.bind_document_shortcuts(self.input_widget)
        if sys.platform == "win32":
            self.enable_file_drop()
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
        theme_style.configure("Treeview", background=TEXT_AREA_COLOR,
                              fieldbackground=TEXT_AREA_COLOR, foreground=TEXT_COLOR,
                              bordercolor=BUTTON_COLOR)
        theme_style.map("Treeview", background=[("selected", SELECTION_COLOR)],
                        foreground=[("selected", TEXT_COLOR)])
        theme_style.configure("Treeview.Heading", background=BUTTON_COLOR,
                              foreground=TEXT_COLOR, relief="flat")
        theme_style.map("Treeview.Heading", background=[("active", "#36465c")])
        theme_style.configure("TNotebook", background=WINDOW_COLOR, borderwidth=0)
        theme_style.configure("TNotebook.Tab", background="#1c2a3e",
                              foreground=TEXT_COLOR, padding=(12, 6))
        theme_style.map("TNotebook.Tab",
                        background=[("selected", "#293e5b"), ("active", "#24364e")],
                        foreground=[("selected", TEXT_COLOR), ("active", TEXT_COLOR)],
                        padding=[("selected", (18, 10)), ("!selected", (12, 6))])
        self.tab_close_icon = tk.PhotoImage(master=self.main_window, width=24, height=16)
        for offset in range(4, 12):
            for thickness in (0, 1):
                self.tab_close_icon.put(TEXT_COLOR, (offset + 8, offset - 2 + thickness))
                self.tab_close_icon.put(TEXT_COLOR, (23 - offset, offset - 2 + thickness))
        theme_style.element_create("Document.close", "image", self.tab_close_icon)
        tab_layout = theme_style.layout("TNotebook.Tab")
        def add_close_element(elements):
            for name, options in elements:
                children = options.get("children", [])
                if any(child_name.endswith(".label") for child_name, _ in children):
                    for child_name, child_options in children:
                        if child_name.endswith(".label"):
                            child_options["side"] = "left"
                            child_options["sticky"] = "w"
                    children.insert(0, ("Document.close", {"side": "right", "sticky": "ne"}))
                else:
                    add_close_element(children)
        add_close_element(tab_layout)
        theme_style.layout("Documents.TNotebook.Tab", tab_layout)
        theme_style.configure("TButton", background=BUTTON_COLOR, padding=(5, 4))
        theme_style.configure("Toolbar.TButton", background="#1c2a3e", padding=(6, 5))
        theme_style.map("Toolbar.TButton",
                        background=[("pressed", "#293e5b"), ("active", "#24364e")])
        theme_style.map("TButton", background=[("pressed", SELECTION_COLOR), ("active", "#36465c")])
        for scrollbar_orientation in ("Vertical", "Horizontal"):
            theme_style.configure(f"{scrollbar_orientation}.TScrollbar", background=BUTTON_COLOR)
            theme_style.map(f"{scrollbar_orientation}.TScrollbar", background=[("active", SELECTION_COLOR)])

    def add_button_tooltip(self, button, label):
        pending = None
        popup = None

        def hide_tooltip(event=None):
            nonlocal pending, popup
            if pending is not None:
                button.after_cancel(pending)
                pending = None
            if popup is not None:
                popup.destroy()
                popup = None

        def show_tooltip():
            nonlocal pending, popup
            pending = None
            popup = tk.Toplevel(self.main_window)
            popup.overrideredirect(True)
            popup.geometry(f"+{button.winfo_rootx()}+{button.winfo_rooty() + button.winfo_height() + 4}")
            ttk.Label(popup, text=self.translate(label), padding=(8, 4)).pack()

        def schedule_tooltip(event):
            nonlocal pending
            hide_tooltip()
            pending = button.after(500, show_tooltip)

        button.bind("<Enter>", schedule_tooltip)
        button.bind("<Leave>", hide_tooltip)
        button.bind("<ButtonPress>", hide_tooltip)
        button.bind("<Destroy>", hide_tooltip)

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
        display_name = self.document_path.name if self.document_path else self.translate("Без имени")
        has_changes = self.read_document_text() != self.saved_text
        window_title = self.translate("Редактор кода Python")
        if self.document_path:
            window_title = f"{display_name} — {window_title}"
        self.main_window.title(f"{window_title}{' *' if has_changes else ''}")
        if hasattr(self, "document_tabs") and self.document_tabs.select() in self.documents:
            page = self.document_tabs.select()
            self.documents[page]["path"] = self.document_path
            self.documents[page]["saved"] = self.saved_text
            self.document_tabs.tab(page, text=f"{display_name}{' *' if has_changes else ''}")
        line, column = self.input_widget.index("insert").split(".")
        self.status_text.set(f"{display_name} | {line}:{int(column)+1}   |   {self.translate('Есть несохранённые изменения') if has_changes else self.translate('Нет несохранённых изменений')}")

    def on_text_changed(self, _event):
        if self.input_widget.edit_modified():
            self.input_widget.edit_modified(False)
            self.update_document_status()
            self.highlight_document()

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
        choice = messagebox.askyesnocancel(self.translate("Сохранение"), self.translate("Сохранить изменения?"), parent=self.main_window)
        return choice is False or (choice is True and self.save_document())

    def create_document(self):
        page = ttk.Frame(self.document_tabs)
        self.document_tabs.add(page, text="Без имени")
        widget = self.create_text_area(page, undo=True, wrap="none", font=("Consolas", self.editor_font_size), padx=8, pady=8)
        widget.pack(fill="both", expand=True)
        horizontal = ttk.Scrollbar(page, orient="horizontal", command=widget.xview)
        horizontal.pack(fill="x")
        widget.configure(xscrollcommand=horizontal.set)
        self.register_document(page, widget)
        self.document_tabs.select(page)
        self.activate_document()
        self.bind_document_shortcuts(widget)
        self.load_document("", None)

    def open_document(self):
        display_name = filedialog.askopenfilename(parent=self.main_window, filetypes=[("Python", "*.py"), ("Все файлы", "*.*")])
        if display_name:
            self.open_path(Path(display_name))

    def open_path(self, document_path):
        document_path = document_path.resolve()
        for page, document in self.documents.items():
            if document["path"] == document_path:
                self.document_tabs.select(page)
                return
        try:
            content = document_path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError) as failure:
            messagebox.showerror("Ошибка", str(failure), parent=self.main_window)
            return
        self.create_document()
        self.load_document(content, document_path)
        self.highlight_document()

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
        for page in list(self.documents):
            self.document_tabs.select(page)
            self.activate_document()
            if not self.confirm_discard():
                return
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
        self.output_widget.insert("1.0", self.translate(result_message))
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
        self.result_tabs.select(0)

    def show_text_dialog(self, caption, document_text):
        caption = self.translate(caption)
        dialog = tk.Toplevel(self.main_window)
        dialog.configure(background=WINDOW_COLOR)
        dialog.title(caption)
        dialog.geometry("750x480")
        displayed_text = self.create_text_area(dialog, wrap="word", padx=12, pady=12, font=("Segoe UI", 11))
        displayed_text.pack(fill="both", expand=True)
        displayed_text.insert("1.0", document_text)
        displayed_text.configure(state="disabled")
        ttk.Button(dialog, text=self.translate("Закрыть"), command=dialog.destroy).pack(pady=8)
        dialog.bind("<Escape>", lambda _event: dialog.destroy())

    def show_user_guide(self):
        guide_source = Path(__file__).with_name("README.md").read_text(encoding="utf-8")
        guide_lines = [line_text.lstrip("# ").replace("**", "").replace("`", "") for line_text in guide_source.splitlines()
                 if not line_text.startswith("![")]
        self.show_text_dialog("Руководство пользователя", "\n".join(guide_lines))

    def show_about_dialog(self):
        messagebox.showinfo(self.translate("О программе"), self.translate("Редактор кода Python") + "\n" + self.translate("Задание 2 — программная реализация GUI") + "\n" + self.translate("Автор: Рудик Дана"), parent=self.main_window)

    def register_document(self, page, widget):
        gutter = tk.Canvas(page, width=48, background=WINDOW_COLOR, highlightthickness=0)
        gutter.pack(side="left", fill="y", before=widget.frame)
        self.documents[str(page)] = {"widget": widget, "path": None, "saved": "", "gutter": gutter}
        widget.bind("<<Modified>>", self.on_text_changed)
        widget.bind("<KeyRelease>", lambda event: self.update_document_status(), add="+")
        widget.bind("<ButtonRelease-1>", lambda event: self.update_document_status(), add="+")
        widget.bind("<Configure>", lambda event: self.draw_line_numbers(), add="+")
        widget.configure(yscrollcommand=lambda first, last, field=widget: self.scroll_document(field, first, last))
        widget.tag_configure("keyword", foreground="#c792ea")
        widget.tag_configure("string", foreground="#c3e88d")
        widget.tag_configure("comment", foreground="#7f9a7a")
        widget.tag_configure("number", foreground="#f5ba75")

    def scroll_document(self, widget, first, last):
        widget.vbar.set(first, last)
        self.draw_line_numbers()

    def draw_line_numbers(self):
        if not hasattr(self, "document_tabs"):
            return
        page = self.document_tabs.select()
        if page not in self.documents:
            return
        document = self.documents[page]
        widget, gutter = document["widget"], document["gutter"]
        gutter.delete("all")
        index = widget.index("@0,0")
        while True:
            bounds = widget.dlineinfo(index)
            if bounds is None:
                break
            gutter.create_text(43, bounds[1], anchor="ne", text=index.split(".")[0],
                               fill="#8796aa", font=("Consolas", self.editor_font_size))
            index = widget.index(f"{index}+1line")

    def activate_document(self, event=None):
        page = self.document_tabs.select()
        if page not in self.documents:
            return
        document = self.documents[page]
        self.input_widget = document["widget"]
        self.document_path = document["path"]
        self.saved_text = document["saved"]
        self.update_document_status()
        self.draw_line_numbers()

    def bind_document_shortcuts(self, widget):
        commands = {
            "<Control-n>": self.create_document, "<Control-o>": self.open_document,
            "<Control-s>": self.save_document, "<Control-Shift-S>": self.save_document_as,
            "<Control-w>": self.close_document, "<Control-a>": self.select_document,
            "<Control-z>": lambda: self.input_widget.edit_undo(),
            "<Control-y>": lambda: self.input_widget.edit_redo(),
            "<Control-plus>": lambda: self.resize_text("editor", 1),
            "<Control-equal>": lambda: self.resize_text("editor", 1),
            "<Control-minus>": lambda: self.resize_text("editor", -1),
        }
        for shortcut, callback in commands.items():
            widget.bind(shortcut, lambda event, action=callback: self.execute_command(action))

    def press_tab_close(self, event):
        notebook = self.document_tabs
        if notebook.identify(event.x, event.y) == "Document.close":
            self.pressed_close_tab = notebook.tabs()[notebook.index(f"@{event.x},{event.y}")]
            return "break"

    def release_tab_close(self, event):
        page = self.pressed_close_tab
        self.pressed_close_tab = None
        if page is None:
            return
        notebook = self.document_tabs
        if notebook.identify(event.x, event.y) == "Document.close":
            released_page = notebook.tabs()[notebook.index(f"@{event.x},{event.y}")]
            if released_page == page:
                notebook.select(page)
                self.activate_document()
                self.close_document()
        return "break"

    def close_document(self):
        if not self.confirm_discard():
            return
        page = self.document_tabs.select()
        self.document_tabs.forget(page)
        del self.documents[page]
        self.main_window.nametowidget(page).destroy()
        if not self.documents:
            self.create_document()
        self.activate_document()

    def resize_text(self, target, delta):
        if target == "editor":
            self.editor_font_size = max(8, min(32, self.editor_font_size + delta))
            for document in self.documents.values():
                document["widget"].configure(font=("Consolas", self.editor_font_size))
            self.draw_line_numbers()
        else:
            self.result_font_size = max(8, min(32, self.result_font_size + delta))
            self.output_widget.configure(font=("Consolas", self.result_font_size))
            style = ttk.Style(self.main_window)
            style.configure("Treeview", font=("Consolas", self.result_font_size),
                            rowheight=self.result_font_size * 2)

    def highlight_document(self):
        widget = self.input_widget
        for tag in ("keyword", "string", "comment", "number"):
            widget.tag_remove(tag, "1.0", "end")
        try:
            for token in tokenize.generate_tokens(io.StringIO(self.read_document_text()).readline):
                tag = {tokenize.STRING: "string", tokenize.COMMENT: "comment", tokenize.NUMBER: "number"}.get(token.type)
                if token.type == tokenize.NAME and keyword.iskeyword(token.string):
                    tag = "keyword"
                if tag:
                    widget.tag_add(tag, f"{token.start[0]}.{token.start[1]}", f"{token.end[0]}.{token.end[1]}")
        except (tokenize.TokenError, IndentationError, SyntaxError):
            pass
        self.draw_line_numbers()

    def show_errors(self, errors):
        """errors contains (message, line, column) for the current document."""
        self.error_table.delete(*self.error_table.get_children())
        self.error_document = self.document_tabs.select()
        for message, line, column in errors:
            self.error_table.insert("", "end", values=(message, line, column))
        self.result_tabs.select(1)

    def select_error(self, event=None):
        selected = self.error_table.selection()
        page = getattr(self, "error_document", None)
        if selected and page in self.documents:
            self.document_tabs.select(page)
            self.activate_document()
            _, line, column = self.error_table.item(selected[0], "values")
            self.move_to_error((int(line), int(column)))

    def enable_file_drop(self):
        import ctypes
        from ctypes import wintypes

        user32, shell32 = ctypes.windll.user32, ctypes.windll.shell32
        user32.GetParent.argtypes = [wintypes.HWND]
        user32.GetParent.restype = wintypes.HWND
        setter = user32.SetWindowLongPtrW if ctypes.sizeof(ctypes.c_void_p) == 8 else user32.SetWindowLongW
        setter.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
        setter.restype = ctypes.c_void_p
        user32.CallWindowProcW.argtypes = [
            ctypes.c_void_p, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        user32.CallWindowProcW.restype = ctypes.c_ssize_t
        shell32.DragQueryFileW.argtypes = [
            wintypes.HANDLE, wintypes.UINT, wintypes.LPWSTR, wintypes.UINT]
        shell32.DragFinish.argtypes = [wintypes.HANDLE]
        shell32.DragAcceptFiles.argtypes = [wintypes.HWND, wintypes.BOOL]
        procedure_type = ctypes.WINFUNCTYPE(
            ctypes.c_ssize_t, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
        self.drop_handlers = {}

        def install_handler(window):
            if not window or window in self.drop_handlers:
                return

            def procedure(handle, message, wparam, lparam):
                if message == 0x233:
                    paths = []
                    try:
                        count = shell32.DragQueryFileW(wparam, 0xffffffff, None, 0)
                        for index in range(count):
                            length = shell32.DragQueryFileW(wparam, index, None, 0)
                            buffer = ctypes.create_unicode_buffer(length + 1)
                            shell32.DragQueryFileW(wparam, index, buffer, length + 1)
                            paths.append(Path(buffer.value))
                    finally:
                        shell32.DragFinish(wparam)
                    for path in paths:
                        self.main_window.after_idle(self.open_path, path)
                    return 0
                result = user32.CallWindowProcW(previous, handle, message, wparam, lparam)
                if message == 0x82:
                    self.drop_handlers.pop(handle, None)
                return result

            callback = procedure_type(procedure)
            previous = setter(window, -4, ctypes.cast(callback, ctypes.c_void_p))
            if not previous:
                raise ctypes.WinError()
            self.drop_handlers[window] = (callback, previous)
            shell32.DragAcceptFiles(window, True)

        def register_widget(widget):
            if widget.winfo_exists():
                install_handler(widget.winfo_id())
                if widget is self.main_window:
                    install_handler(user32.GetParent(widget.winfo_id()))
                for child in widget.winfo_children():
                    if not isinstance(child, (tk.Toplevel, tk.Menu)):
                        register_widget(child)

        def register_mapped_widget(event):
            if event.widget.winfo_toplevel() is self.main_window:
                self.main_window.after_idle(register_widget, event.widget)

        self.main_window.bind("<Map>", register_mapped_widget, add="+")
        self.main_window.after_idle(register_widget, self.main_window)

    def translate(self, text):
        if self.language == "ru":
            return text
        return {
            "Создать": "New", "Открыть": "Open", "Сохранить": "Save",
            "Отменить": "Undo", "Повторить": "Redo", "Копировать": "Copy",
            "Вырезать": "Cut", "Вставить": "Paste", "Пуск": "Run", "Справка": "Help",
            "Редактор кода Python": "Python code editor", "Без имени": "Untitled",
            "Есть несохранённые изменения": "Unsaved changes", "Нет несохранённых изменений": "Saved",
            "Сохранение": "Save", "Сохранить изменения?": "Save changes?",
            "Пока не реализовано": "Not implemented yet", "Закрыть": "Close",
            "О программе": "About", "Руководство пользователя": "User guide",
            "Задание 2 — программная реализация GUI": "Assignment 2 — GUI implementation",
            "Автор: Рудик Дана": "Author: Dana Rudik",
        }.get(text, text)

    def set_language(self, language):
        translations = {
            "Файл": "File", "Создать": "New", "Открыть": "Open", "Сохранить": "Save",
            "Сохранить как": "Save as", "Выход": "Exit", "Правка": "Edit",
            "Отменить": "Undo", "Повторить": "Redo", "Вырезать": "Cut", "Копировать": "Copy",
            "Вставить": "Paste", "Удалить": "Delete", "Выделить все": "Select all",
            "Текст": "Text", "Пуск": "Run", "Справка": "Help", "Вызов справки": "User guide",
            "О программе": "About", "Вид": "View", "Язык": "Language", "Закрыть": "Close",
            "Редактор кода Python": "Python code editor", "Результаты": "Results",
            "Сообщения": "Messages", "Ошибки": "Errors", "Сообщение": "Message",
            "Строка": "Line", "Столбец": "Column", "Закрыть вкладку": "Close tab",
            "Увеличить текст редактора": "Increase editor font", "Уменьшить текст редактора": "Decrease editor font",
            "Увеличить текст результатов": "Increase results font", "Уменьшить текст результатов": "Decrease results font",
            "Постановка задачи": "Task", "Грамматика": "Grammar", "Классификация грамматики": "Grammar classification",
            "Метод анализа": "Analysis method", "Тестовый пример": "Example",
            "Список литературы": "References", "Исходный код программы": "Source code",
        }
        mapping = translations if language == "en" else {v: k for k, v in translations.items()}
        def translate(widget):
            if isinstance(widget, tk.Menu):
                last = widget.index("end")
                for index in range((last or 0) + 1):
                    try:
                        label = widget.entrycget(index, "label")
                        widget.entryconfigure(index, label=mapping.get(label, label))
                    except tk.TclError:
                        pass
            else:
                try:
                    label = widget.cget("text")
                    widget.configure(text=mapping.get(label, label))
                except tk.TclError:
                    pass
            if isinstance(widget, ttk.Notebook):
                for page in widget.tabs():
                    label = widget.tab(page, "text")
                    widget.tab(page, text=mapping.get(label, label))
            for child in widget.winfo_children():
                translate(child)
        translate(self.main_window)
        for column in self.error_table["columns"]:
            label = self.error_table.heading(column, "text")
            self.error_table.heading(column, text=mapping.get(label, label))
        previous_message = self.output_widget.get("1.0", "end-1c")
        self.language = language
        if previous_message in ("Пока не реализовано", "Not implemented yet"):
            self.display_result("Пока не реализовано")
        self.update_document_status()


if __name__ == "__main__":
    main_window = tk.Tk()
    PythonEditor(main_window)
    main_window.mainloop()
