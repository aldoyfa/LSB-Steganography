import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os

from stego.lsb import embed, get_capacity
from stego.utils import sha256_digest
from gui.histogram_window import HistogramWindow

class EmbedTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.cover_path = tk.StringVar()
        self.msg_type = tk.StringVar(value="text")
        self.file_path = tk.StringVar()
        self.scheme = tk.StringVar(value="3-3-2")
        self.use_encrypt = tk.BooleanVar(value=False)
        self.a51_key = tk.StringVar()
        self.insert_mode = tk.StringVar(value="sequential")
        self.stego_key = tk.StringVar()
        self.output_name = tk.StringVar()

        self._cover_video_path = None
        self._out_path = None
        self._last_mse = None
        self._last_psnr = None
        self._last_payload_hash = None

        self._build_ui()

    def _build_ui(self):
        pad = {'padx': 6, 'pady': 3}

        row = 0
        ttk.Label(self, text="Video Format:").grid(row=row, column=0, sticky='w', **pad)
        fmt_frame = ttk.Frame(self)
        fmt_frame.grid(row=row, column=1, sticky='w', **pad)
        self.video_format = tk.StringVar(value="avi")
        ttk.Radiobutton(fmt_frame, text="AVI", variable=self.video_format, value="avi",
                        command=self._on_format_change).pack(side='left', padx=4)
        ttk.Radiobutton(fmt_frame, text="MP4", variable=self.video_format, value="mp4",
                        command=self._on_format_change).pack(side='left', padx=4)

        # Cover video
        row += 1
        ttk.Label(self, text="Cover Video:").grid(row=row, column=0, sticky='w', **pad)
        ttk.Entry(self, textvariable=self.cover_path, width=50).grid(row=row, column=1, sticky='ew', **pad)
        ttk.Button(self, text="Browse", command=self._browse_cover).grid(row=row, column=2, **pad)

        # Message type
        row += 1
        ttk.Label(self, text="Message Type:").grid(row=row, column=0, sticky='w', **pad)
        type_frame = ttk.Frame(self)
        type_frame.grid(row=row, column=1, sticky='w', **pad)
        ttk.Radiobutton(type_frame, text="Text", variable=self.msg_type, value="text",
                        command=self._toggle_msg_type).pack(side='left', padx=4)
        ttk.Radiobutton(type_frame, text="File", variable=self.msg_type, value="file",
                        command=self._toggle_msg_type).pack(side='left', padx=4)

        # Text input
        row += 1
        self.text_label = ttk.Label(self, text="Message:")
        self.text_label.grid(row=row, column=0, sticky='nw', **pad)
        self.text_area = tk.Text(self, height=5, width=50)
        self.text_area.grid(row=row, column=1, columnspan=2, sticky='ew', **pad)

        # File input
        row += 1
        self.file_label = ttk.Label(self, text="File:")
        self.file_entry = ttk.Entry(self, textvariable=self.file_path, width=50)
        self.file_btn = ttk.Button(self, text="Browse", command=self._browse_file)
        self.file_row = row

        # Scheme
        row += 1
        ttk.Label(self, text="LSB Scheme:").grid(row=row, column=0, sticky='w', **pad)
        self.scheme_combo = ttk.Combobox(self, textvariable=self.scheme,
                     values=["3-3-2", "4-2-2", "2-3-3"],
                     state='readonly', width=10)
        self.scheme_combo.grid(row=row, column=1, sticky='w', **pad)

        # Encryption
        row += 1
        ttk.Checkbutton(self, text="Encrypt (A5/1)", variable=self.use_encrypt,
                        command=self._toggle_encrypt).grid(row=row, column=0, sticky='w', **pad)
        self.key_entry = ttk.Entry(self, textvariable=self.a51_key, width=30, state='disabled')
        self.key_entry.grid(row=row, column=1, sticky='w', **pad)
        self.key_label = ttk.Label(self, text="A5/1 Key")
        self.key_label.grid(row=row, column=2, sticky='w', **pad)

        # Insertion mode
        row += 1
        ttk.Label(self, text="Insert Mode:").grid(row=row, column=0, sticky='w', **pad)
        mode_frame = ttk.Frame(self)
        mode_frame.grid(row=row, column=1, sticky='w', **pad)
        self.seq_radio = ttk.Radiobutton(mode_frame, text="Sequential", variable=self.insert_mode, value="sequential",
                        command=self._toggle_random)
        self.seq_radio.pack(side='left', padx=4)
        self.rand_radio = ttk.Radiobutton(mode_frame, text="Random", variable=self.insert_mode, value="random",
                        command=self._toggle_random)
        self.rand_radio.pack(side='left', padx=4)

        row += 1
        self.skey_label = ttk.Label(self, text="Stego-Key:")
        self.skey_label.grid(row=row, column=0, sticky='w', **pad)
        self.skey_entry = ttk.Entry(self, textvariable=self.stego_key, width=30, state='disabled')
        self.skey_entry.grid(row=row, column=1, sticky='w', **pad)

        # Output
        row += 1
        ttk.Label(self, text="Output File:").grid(row=row, column=0, sticky='w', **pad)
        ttk.Entry(self, textvariable=self.output_name, width=50).grid(row=row, column=1, sticky='ew', **pad)
        ttk.Button(self, text="Browse", command=self._browse_output).grid(row=row, column=2, **pad)

        # Buttons
        row += 1
        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=row, column=0, columnspan=3, pady=10)
        ttk.Button(btn_frame, text="Check Capacity", command=self._check_capacity).pack(side='left', padx=8)
        self.embed_btn = ttk.Button(btn_frame, text="Embed", command=self._start_embed)
        self.embed_btn.pack(side='left', padx=8)
        self.hist_btn = ttk.Button(btn_frame, text="Histogram", command=self._show_histogram, state='disabled')
        self.hist_btn.pack(side='left', padx=8)

        # Progress
        row += 1
        self.progress = ttk.Progressbar(self, mode='determinate')
        self.progress.grid(row=row, column=0, columnspan=3, sticky='ew', padx=8, pady=4)

        # Status
        row += 1
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(self, textvariable=self.status_var, foreground='gray').grid(
            row=row, column=0, columnspan=3, sticky='w', **pad)

        # Results
        row += 1
        self.result_var = tk.StringVar()
        ttk.Label(self, textvariable=self.result_var, font=('Consolas', 10)).grid(
            row=row, column=0, columnspan=3, sticky='w', **pad)

        self.columnconfigure(1, weight=1)
        self._toggle_msg_type()
        self._on_format_change()

    def _on_format_change(self):
        if self.video_format.get() == "mp4":
            self.scheme_combo.config(state='disabled')
            self.seq_radio.config(state='disabled')
            self.rand_radio.config(state='disabled')
            self.skey_entry.config(state='disabled')
        else:
            self.scheme_combo.config(state='readonly')
            self.seq_radio.config(state='normal')
            self.rand_radio.config(state='normal')
            self._toggle_random()

    def _browse_cover(self):
        ext = self.video_format.get()
        path = filedialog.askopenfilename(
            filetypes=[(ext.upper(), f"*.{ext}")])
        if path:
            self.cover_path.set(path)

    def _browse_file(self):
        path = filedialog.askopenfilename()
        if path:
            self.file_path.set(path)

    def _browse_output(self):
        ext = self.video_format.get()
        path = filedialog.asksaveasfilename(
            defaultextension=f".{ext}",
            filetypes=[(ext.upper(), f"*.{ext}")])
        if path:
            self.output_name.set(path)

    def _toggle_msg_type(self):
        pad = {'padx': 6, 'pady': 3}
        if self.msg_type.get() == "text":
            self.text_label.grid()
            self.text_area.grid()
            self.file_label.grid_remove()
            self.file_entry.grid_remove()
            self.file_btn.grid_remove()
        else:
            self.text_label.grid_remove()
            self.text_area.grid_remove()
            self.file_label.grid(row=self.file_row, column=0, sticky='w', **pad)
            self.file_entry.grid(row=self.file_row, column=1, sticky='ew', **pad)
            self.file_btn.grid(row=self.file_row, column=2, **pad)

    def _toggle_encrypt(self):
        st = 'normal' if self.use_encrypt.get() else 'disabled'
        self.key_entry.config(state=st)

    def _toggle_random(self):
        st = 'normal' if self.insert_mode.get() == 'random' else 'disabled'
        self.skey_entry.config(state=st)

    def _check_capacity(self):
        cover = self.cover_path.get()
        if not cover:
            messagebox.showwarning("Warning", "Select a cover video first")
            return
        try:
            is_mp4 = self.video_format.get() == 'mp4'
            cap = get_capacity(cover, self.scheme.get())
            if is_mp4:
                msg = (f"Max capacity: {cap:,} bytes ({cap/1024:.1f} KB)\n"
                       "Mode: MP4 container (parity encoding in mdat)")
            else:
                msg = f"Max capacity: {cap:,} bytes ({cap/1024:.1f} KB)"

            payload_size = self._get_payload_size()
            if payload_size is not None:
                if payload_size <= cap:
                    msg += f"\nPayload size: {payload_size:,} bytes ✓"
                else:
                    msg += f"\nPayload size: {payload_size:,} bytes ✗"
            messagebox.showinfo("Capacity", msg)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _get_payload_size(self):
        if self.msg_type.get() == "text":
            txt = self.text_area.get("1.0", "end-1c")
            if txt:
                return len(txt.encode('utf-8'))
        else:
            fp = self.file_path.get()
            if fp and os.path.isfile(fp):
                return os.path.getsize(fp)
        return None

    def _start_embed(self):
        cover = self.cover_path.get()
        out = self.output_name.get()
        if not cover:
            messagebox.showwarning("Warning", "Select a cover video")
            return
        if not out:
            messagebox.showwarning("Warning", "Specify output file path")
            return

        is_file = self.msg_type.get() == "file"
        if is_file:
            fpath = self.file_path.get()
            if not fpath or not os.path.isfile(fpath):
                messagebox.showwarning("Warning", "Select a valid file to embed")
                return
            with open(fpath, 'rb') as f:
                payload = f.read()
            filename = os.path.basename(fpath)
        else:
            txt = self.text_area.get("1.0", "end-1c")
            if not txt:
                messagebox.showwarning("Warning", "Enter a message to embed")
                return
            payload = txt.encode('utf-8')
            filename = ""

        use_enc = self.use_encrypt.get()
        key = self.a51_key.get() if use_enc else None
        use_rand = self.insert_mode.get() == "random"
        skey = self.stego_key.get() if use_rand else None

        if use_enc and not key:
            messagebox.showwarning("Warning", "Enter an A5/1 encryption key")
            return
        if use_rand and not skey:
            messagebox.showwarning("Warning", "Enter a stego-key for random insertion")
            return

        self._cover_video_path = cover
        self._out_path = out
        self.embed_btn.config(state='disabled')
        self.status_var.set("Embedding...")
        self.progress['value'] = 0
        self.result_var.set("")

        def _do():
            try:
                def progress(cur, total):
                    pct = int(cur / max(total, 1) * 100)
                    self.after(0, lambda: self.progress.config(value=pct))

                avg_mse, avg_psnr, _, _ = embed(
                    cover, out, payload, self.scheme.get(), is_file, filename,
                    use_enc, key, use_rand, skey, progress_cb=progress)

                self._last_mse = avg_mse
                self._last_psnr = avg_psnr
                self._last_payload_hash = sha256_digest(payload)

                self.after(0, lambda: self._embed_done(avg_mse, avg_psnr, self._last_payload_hash))
            except Exception as e:
                err_msg = str(e)
                self.after(0, lambda msg=err_msg: self._embed_error(msg))

        threading.Thread(target=_do, daemon=True).start()

    def _embed_done(self, mse, psnr, payload_hash):
        self.embed_btn.config(state='normal')
        self.hist_btn.config(state='normal')
        self.progress['value'] = 100
        self.status_var.set("Embedding complete!")
        if mse == 0.0 and psnr == float('inf'):
            quality = "MSE: 0.0  |  PSNR: ∞ dB  (MP4 container mode (frames unmodified))"
        else:
            psnr_str = f"{psnr:.2f}" if psnr != float('inf') else "∞"
            quality = f"Avg MSE: {mse:.4f}  |  Avg PSNR: {psnr_str} dB"
        self.result_var.set(f"{quality}\nSHA-256: {payload_hash}")

    def _embed_error(self, msg):
        self.embed_btn.config(state='normal')
        self.progress['value'] = 0
        self.status_var.set("Error")
        messagebox.showerror("Embed Error", msg)

    def _show_histogram(self):
        if self._cover_video_path and self._out_path:
            HistogramWindow(self, self._cover_video_path, self._out_path)