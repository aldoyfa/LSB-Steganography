import tkinter as tk
from tkinter import ttk
import numpy as np
import cv2

import matplotlib
matplotlib.use('TkAgg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class HistogramWindow(tk.Toplevel):
    def __init__(self, parent, orig_path, stego_path):
        super().__init__(parent)
        self.title("Histogram Comparison")
        self.geometry("900x550")

        self.orig_path = orig_path
        self.stego_path = stego_path
        self._orig_frames = []
        self._stego_frames = []

        self._load_frames()

        ctrl = ttk.Frame(self)
        ctrl.pack(fill='x', padx=8, pady=4)
        ttk.Label(ctrl, text="Frame:").pack(side='left')
        self.frame_var = tk.IntVar(value=0)
        n = max(len(self._orig_frames) - 1, 0)
        self.spin = ttk.Spinbox(ctrl, from_=0, to=n, textvariable=self.frame_var, width=6,
                                command=self._update_plot)
        self.spin.pack(side='left', padx=4)
        ttk.Button(ctrl, text="Refresh", command=self._update_plot).pack(side='left', padx=4)

        self.avg_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(ctrl, text="Average All Frames", variable=self.avg_var,
                        command=self._on_avg_toggle).pack(side='left', padx=10)

        self.fig = Figure(figsize=(9, 4.5), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(fill='both', expand=True)

        self._update_plot()

    def _on_avg_toggle(self):
        if self.avg_var.get():
            self.spin.config(state='disabled')
        else:
            self.spin.config(state='normal')
        self._update_plot()

    def _load_frames(self):
        for path, store in [(self.orig_path, self._orig_frames),
                            (self.stego_path, self._stego_frames)]:
            cap = cv2.VideoCapture(path)
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                store.append(frame)
            cap.release()

    def _compute_average_histograms(self):
        self._cached_orig_hists_avg = [np.zeros(256, dtype=np.float64) for _ in range(3)]
        self._cached_stego_hists_avg = [np.zeros(256, dtype=np.float64) for _ in range(3)]

        n_orig = max(len(self._orig_frames), 1)
        for f in self._orig_frames:
            for i in range(3):
                hist = cv2.calcHist([f], [i], None, [256], [0, 256]).ravel()
                self._cached_orig_hists_avg[i] += hist / n_orig

        n_stego = max(len(self._stego_frames), 1)
        for f in self._stego_frames:
            for i in range(3):
                hist = cv2.calcHist([f], [i], None, [256], [0, 256]).ravel()
                self._cached_stego_hists_avg[i] += hist / n_stego

    def _update_plot(self):
        self.fig.clear()
        colors = ['b', 'g', 'r']
        labels = ['Blue', 'Green', 'Red']

        if self.avg_var.get():
            if not hasattr(self, '_cached_orig_hists_avg'):
                self._compute_average_histograms()

            orig_hists = self._cached_orig_hists_avg
            stego_hists = self._cached_stego_hists_avg

            for i, (color, label) in enumerate(zip(colors, labels)):
                ax = self.fig.add_subplot(1, 3, i + 1)
                ax.bar(np.arange(256), orig_hists[i], width=1, color=color, alpha=0.5, label='Original')
                ax.bar(np.arange(256), stego_hists[i], width=1, color='orange', alpha=0.5, label='Stego')
                ax.set_title(f"{label} (Avg)")
                ax.legend(fontsize=7)
                ax.set_xlim(0, 256)
        else:
            idx = self.frame_var.get()
            if idx >= len(self._orig_frames) or idx >= len(self._stego_frames):
                return

            orig = self._orig_frames[idx]
            stego = self._stego_frames[idx]

            for i, (color, label) in enumerate(zip(colors, labels)):
                ax = self.fig.add_subplot(1, 3, i + 1)
                ax.hist(orig[:, :, i].ravel(), bins=256, range=(0, 256),
                        alpha=0.5, color=color, label='Original')
                ax.hist(stego[:, :, i].ravel(), bins=256, range=(0, 256),
                        alpha=0.5, color='orange', label='Stego')
                ax.set_title(f"{label} (Frame {idx})")
                ax.legend(fontsize=7)
                ax.set_xlim(0, 256)

        self.fig.tight_layout()
        self.canvas.draw()
