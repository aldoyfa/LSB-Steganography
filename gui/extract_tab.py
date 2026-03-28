import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading

from stego.lsb import extract

class ExtractTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.stego_path = tk.StringVar()
        self.a51_key = tk.StringVar()
        self.stego_key = tk.StringVar()

        self._build_ui()

    def _build_ui(self):
        pad = {'padx': 6, 'pady': 3}

        row = 0
        ttk.Label(self, text="Stego Video:").grid(row=row, column=0, sticky='w', **pad)
        ttk.Entry(self, textvariable=self.stego_path, width=50).grid(row=row, column=1, sticky='ew', **pad)
        ttk.Button(self, text="Browse", command=self._browse_stego).grid(row=row, column=2, **pad)

        row += 1
        ttk.Label(self, text="A5/1 Key (if encrypted):").grid(row=row, column=0, sticky='w', **pad)
        ttk.Entry(self, textvariable=self.a51_key, width=30).grid(row=row, column=1, sticky='w', **pad)

        row += 1
        ttk.Label(self, text="Stego-Key (if random):").grid(row=row, column=0, sticky='w', **pad)
        ttk.Entry(self, textvariable=self.stego_key, width=30).grid(row=row, column=1, sticky='w', **pad)

        row += 1
        self.extract_btn = ttk.Button(self, text="Extract", command=self._start_extract)
        self.extract_btn.grid(row=row, column=0, columnspan=3, pady=12)

        row += 1
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(self, textvariable=self.status_var, foreground='gray').grid(
            row=row, column=0, columnspan=3, sticky='w', **pad)

        # Result area
        row += 1
        ttk.Label(self, text="Extracted Message:").grid(row=row, column=0, sticky='nw', **pad)

        row += 1
        self.result_text = tk.Text(self, height=12, width=60, state='disabled')
        self.result_text.grid(row=row, column=0, columnspan=2, sticky='nsew', **pad)
        scrollbar = ttk.Scrollbar(self, command=self.result_text.yview)
        scrollbar.grid(row=row, column=2, sticky='ns')
        self.result_text.config(yscrollcommand=scrollbar.set)

        row += 1
        self.save_btn = ttk.Button(self, text="Save Extracted File", command=self._save_file, state='disabled')
        self.save_btn.grid(row=row, column=0, columnspan=3, pady=6)

        self.columnconfigure(1, weight=1)
        self.rowconfigure(row - 1, weight=1)

        self._extracted_data = None
        self._extracted_filename = None

    def _browse_stego(self):
        path = filedialog.askopenfilename(
            filetypes=[("Video Files", "*.avi *.mp4"), ("AVI", "*.avi"), ("MP4", "*.mp4")])
        if path:
            self.stego_path.set(path)

    def _start_extract(self):
        spath = self.stego_path.get()
        if not spath:
            messagebox.showwarning("Warning", "Select a stego video first")
            return

        key = self.a51_key.get() or None
        skey = self.stego_key.get() or None

        self.extract_btn.config(state='disabled')
        self.status_var.set("Extracting...")

        def _do():
            try:
                data, is_file, fname = extract(spath, a51_key=key, stego_key=skey)
                self.after(0, lambda: self._extract_done(data, is_file, fname))
            except Exception as e:
                err_msg = str(e)
                self.after(0, lambda msg=err_msg: self._extract_error(msg))

        threading.Thread(target=_do, daemon=True).start()

    def _extract_done(self, data, is_file, filename):
        self.extract_btn.config(state='normal')
        self.status_var.set("Extraction complete!")

        if is_file:
            self._extracted_data = data
            self._extracted_filename = filename
            self.save_btn.config(state='normal')
            self.result_text.config(state='normal')
            self.result_text.delete('1.0', 'end')
            self.result_text.insert('1.0', f"[File extracted: {filename}]\nSize: {len(data):,} bytes\n\nClick 'Save Extracted File' to save.")
            self.result_text.config(state='disabled')
        else:
            self.save_btn.config(state='disabled')
            try:
                text = data.decode('utf-8')
            except:
                text = data.decode('latin-1')
            self.result_text.config(state='normal')
            self.result_text.delete('1.0', 'end')
            self.result_text.insert('1.0', text)
            self.result_text.config(state='disabled')

    def _extract_error(self, msg):
        self.extract_btn.config(state='normal')
        self.status_var.set("Error")
        messagebox.showerror("Extract Error", msg)

    def _save_file(self):
        if self._extracted_data is None:
            return
        path = filedialog.asksaveasfilename(
            initialfile=self._extracted_filename or "extracted")
        if path:
            with open(path, 'wb') as f:
                f.write(self._extracted_data)
            messagebox.showinfo("Saved", f"File saved to {path}")