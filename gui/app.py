from pathlib import Path
import tkinter as tk
from tkinter import ttk
from gui.embed_tab import EmbedTab
from gui.extract_tab import ExtractTab

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("LSB Steganography")
        self.geometry("780x680")
        self.minsize(700, 600)

        icon_path = Path(__file__).resolve().parent.parent / "logo.ico"
        if icon_path.exists():
            self.iconbitmap(default=str(icon_path))

        style = ttk.Style()
        style.theme_use('clam')

        notebook = ttk.Notebook(self)
        notebook.pack(fill='both', expand=True, padx=8, pady=8)

        self.embed_tab = EmbedTab(notebook)
        self.extract_tab = ExtractTab(notebook)

        notebook.add(self.embed_tab, text="  Embed  ")
        notebook.add(self.extract_tab, text="  Extract  ")