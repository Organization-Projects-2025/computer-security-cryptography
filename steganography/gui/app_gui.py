# gui/app_gui.py
import os
import csv
import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import numpy as np

from utils.image_io import load_image, pil_to_numpy, numpy_to_pil
from utils.metrics import compute_psnr, compute_ssim
from lsb.lsb_stego import lsb_hide, lsb_reveal
from stegformer_infer import StegFormerInfer

STEGO_SIZE = (256, 256)    # StegFormer input
DISPLAY_SIZE = (256, 256)  # GUI thumbnails


class StegoApp(tk.Tk):
    def __init__(self, weights_path: str):
        super().__init__()

        # ---------- window ----------
        self.title("Steganography Lab – LSB vs StegFormer")
        self.geometry("1350x750")
        self.minsize(1150, 650)

        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        bg = "#f4f6fb"
        style.configure(".", background=bg)
        style.configure("App.TFrame", background=bg)
        style.configure("App.TLabel", background=bg, font=("Segoe UI", 10))
        style.configure(
            "AppTitle.TLabel",
            background=bg,
            font=("Segoe UI", 16, "bold"),
        )

        # primary / secondary buttons
        style.configure(
            "Primary.TButton",
            font=("Segoe UI", 10, "bold"),
            padding=8,
            foreground="white",
            background="#2563eb",
            borderwidth=0,
        )
        style.map("Primary.TButton", background=[("active", "#1d4ed8")])

        style.configure(
            "Secondary.TButton",
            font=("Segoe UI", 10),
            padding=6,
            foreground="white",
            background="#10b981",
            borderwidth=0,
        )
        style.map("Secondary.TButton", background=[("active", "#059669")])

        # ---------- models ----------
        self.stegformer = StegFormerInfer(weights_path)

        # ---------- data ----------
        self.cover_np = None   # 256×256×3
        self.secret_np = None

        self.stego_lsb = None
        self.rec_lsb = None
        self.stego_steg = None
        self.rec_steg = None

        self._tk_images = {}

        self.metrics = {
            "LSB": {"cov_psnr": None, "cov_ssim": None,
                    "sec_psnr": None, "sec_ssim": None},
            "StegFormer": {"cov_psnr": None, "cov_ssim": None,
                           "sec_psnr": None, "sec_ssim": None},
        }

        self.metrics_lsb_var = tk.StringVar(
            value="LSB: PSNR/SSIM – not computed"
        )
        self.metrics_steg_var = tk.StringVar(
            value="StegFormer: PSNR/SSIM – not computed"
        )
        self.status_var = tk.StringVar(value="Ready")

        # detailed metrics vars
        self.lsb_cov_psnr_var = tk.StringVar(value="-")
        self.lsb_cov_ssim_var = tk.StringVar(value="-")
        self.lsb_sec_psnr_var = tk.StringVar(value="-")
        self.lsb_sec_ssim_var = tk.StringVar(value="-")

        self.steg_cov_psnr_var = tk.StringVar(value="-")
        self.steg_cov_ssim_var = tk.StringVar(value="-")
        self.steg_sec_psnr_var = tk.StringVar(value="-")
        self.steg_sec_ssim_var = tk.StringVar(value="-")

        # ---------- layout ----------
        self._build_layout()

    # ======================================================================
    # Layout
    # ======================================================================

    def _build_layout(self):
        top = ttk.Frame(self, style="App.TFrame", padding=(10, 5))
        top.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(top, text="Steganography Comparison",
                  style="AppTitle.TLabel").pack(side=tk.LEFT)

        ttk.Label(
            top,
            textvariable=self.status_var,
            style="App.TLabel",
            anchor=tk.E,
        ).pack(side=tk.RIGHT, fill=tk.X, expand=True)

        main = ttk.Frame(self, style="App.TFrame", padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        # sidebar
        sidebar = ttk.Frame(main, style="App.TFrame")
        sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        self._build_sidebar(sidebar)

        # center: originals
        center = ttk.Frame(main, style="App.TFrame")
        center.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._build_originals(center)

        # right: tabs + metrics
        right = ttk.Frame(main, style="App.TFrame")
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._build_tabs_and_metrics(right)

    def _build_sidebar(self, parent):
        ttk.Label(parent, text="Run Algorithms",
                  style="App.TLabel").pack(anchor=tk.W, pady=(0, 5))

        ttk.Button(
            parent,
            text="Run LSB",
            command=self.run_lsb,
            style="Secondary.TButton",
        ).pack(fill=tk.X, pady=3)

        ttk.Button(
            parent,
            text="Run StegFormer",
            command=self.run_stegformer,
            style="Secondary.TButton",
        ).pack(fill=tk.X, pady=3)

        ttk.Separator(parent, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        ttk.Label(parent, text="Session",
                  style="App.TLabel").pack(anchor=tk.W, pady=(0, 5))

        ttk.Button(
            parent,
            text="Clear Results",
            command=self.clear_results,
            style="Primary.TButton",
        ).pack(fill=tk.X, pady=3)

        ttk.Button(
            parent,
            text="Export Results",
            command=self.export_results,
            style="Primary.TButton",
        ).pack(fill=tk.X, pady=3)

    def _build_originals(self, parent):
        ttk.Label(parent, text="Original Images",
                  style="App.TLabel").pack(anchor=tk.W, pady=(0, 5))

        frame = ttk.Frame(parent, style="App.TFrame")
        frame.pack(fill=tk.BOTH, expand=True)

        # Cover tile
        cover_frame = ttk.LabelFrame(frame, text="Cover", padding=5)
        cover_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=5)

        self.cover_tile = ttk.Frame(cover_frame, style="App.TFrame")
        self.cover_tile.pack(expand=True, fill=tk.BOTH)

        self.lbl_cover = ttk.Label(self.cover_tile, anchor=tk.CENTER)
        self.lbl_cover.pack(expand=True)

        # big + overlay that stays, but text is semi‑transparent over image
        self.cover_overlay = ttk.Button(
            self.cover_tile,
            text="+  Click to upload / change cover",
            style="Primary.TButton",
            command=self.load_cover,
        )
        self.cover_overlay.place(relx=0.5, rely=0.5, anchor="center")

        # Secret tile
        secret_frame = ttk.LabelFrame(frame, text="Secret", padding=5)
        secret_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=5)

        self.secret_tile = ttk.Frame(secret_frame, style="App.TFrame")
        self.secret_tile.pack(expand=True, fill=tk.BOTH)

        self.lbl_secret = ttk.Label(self.secret_tile, anchor=tk.CENTER)
        self.lbl_secret.pack(expand=True)

        self.secret_overlay = ttk.Button(
            self.secret_tile,
            text="+  Click to upload / change secret",
            style="Primary.TButton",
            command=self.load_secret,
        )
        self.secret_overlay.place(relx=0.5, rely=0.5, anchor="center")

    def _build_tabs_and_metrics(self, parent):
        ttk.Label(parent, text="Algorithm Outputs",
                  style="App.TLabel").pack(anchor=tk.W, pady=(0, 5))

        self.notebook = ttk.Notebook(parent)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # LSB tab
        tab_lsb = ttk.Frame(self.notebook, style="App.TFrame")
        self.notebook.add(tab_lsb, text="LSB")
        self._build_algo_tab(
            tab_lsb, "LSB", "lbl_lsb_stego", "lbl_lsb_rec", self.metrics_lsb_var
        )

        # StegFormer tab
        tab_steg = ttk.Frame(self.notebook, style="App.TFrame")
        self.notebook.add(tab_steg, text="StegFormer")
        self._build_algo_tab(
            tab_steg,
            "StegFormer",
            "lbl_steg_stego",
            "lbl_steg_rec",
            self.metrics_steg_var,
        )

        self._build_metrics_table(parent)

    def _build_algo_tab(self, parent, name, stego_attr, rec_attr, summary_var):
        img_frame = ttk.Frame(parent, style="App.TFrame")
        img_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

        f1 = ttk.LabelFrame(img_frame, text=f"{name} Stego", padding=5)
        f1.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=5)
        lbl_stego = ttk.Label(f1, anchor=tk.CENTER)
        lbl_stego.pack(expand=True)
        setattr(self, stego_attr, lbl_stego)

        f2 = ttk.LabelFrame(img_frame, text=f"{name} Recovered Secret", padding=5)
        f2.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=5)
        lbl_rec = ttk.Label(f2, anchor=tk.CENTER)
        lbl_rec.pack(expand=True)
        setattr(self, rec_attr, lbl_rec)

        sum_frame = ttk.Frame(parent, style="App.TFrame")
        sum_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(sum_frame, textvariable=summary_var,
                  style="App.TLabel").pack(anchor=tk.W)

    def _build_metrics_table(self, parent):
        table_frame = ttk.LabelFrame(parent, text="Metrics Comparison", padding=5)
        table_frame.pack(fill=tk.X, pady=10)

        headers = [
            "Algorithm",
            "Cover PSNR",
            "Cover SSIM",
            "Secret PSNR",
            "Secret SSIM",
        ]
        for c, h in enumerate(headers):
            ttk.Label(
                table_frame,
                text=h,
                style="App.TLabel",
                font=("Segoe UI", 9, "bold"),
            ).grid(row=0, column=c, padx=4, pady=2, sticky="w")

        # LSB row
        ttk.Label(table_frame, text="LSB", style="App.TLabel").grid(
            row=1, column=0, padx=4, pady=2, sticky="w"
        )
        ttk.Label(table_frame, textvariable=self.lsb_cov_psnr_var,
                  style="App.TLabel").grid(row=1, column=1, padx=4, pady=2)
        ttk.Label(table_frame, textvariable=self.lsb_cov_ssim_var,
                  style="App.TLabel").grid(row=1, column=2, padx=4, pady=2)
        ttk.Label(table_frame, textvariable=self.lsb_sec_psnr_var,
                  style="App.TLabel").grid(row=1, column=3, padx=4, pady=2)
        ttk.Label(table_frame, textvariable=self.lsb_sec_ssim_var,
                  style="App.TLabel").grid(row=1, column=4, padx=4, pady=2)

        # StegFormer row
        ttk.Label(table_frame, text="StegFormer", style="App.TLabel").grid(
            row=2, column=0, padx=4, pady=2, sticky="w"
        )
        ttk.Label(table_frame, textvariable=self.steg_cov_psnr_var,
                  style="App.TLabel").grid(row=2, column=1, padx=4, pady=2)
        ttk.Label(table_frame, textvariable=self.steg_cov_ssim_var,
                  style="App.TLabel").grid(row=2, column=2, padx=4, pady=2)
        ttk.Label(table_frame, textvariable=self.steg_sec_psnr_var,
                  style="App.TLabel").grid(row=2, column=3, padx=4, pady=2)
        ttk.Label(table_frame, textvariable=self.steg_sec_ssim_var,
                  style="App.TLabel").grid(row=2, column=4, padx=4, pady=2)

    # ======================================================================
    # Image helpers
    # ======================================================================

    def _pil_fixed(self, pil_img: Image.Image) -> Image.Image:
        return pil_img.resize(DISPLAY_SIZE, Image.BICUBIC)

    def _set_label_image(self, label: ttk.Label, pil_img: Image.Image, key: str):
        fixed = self._pil_fixed(pil_img)
        tk_img = ImageTk.PhotoImage(fixed)
        self._tk_images[key] = tk_img
        label.configure(image=tk_img)

    # ======================================================================
    # Input loading
    # ======================================================================

    def load_cover(self):
        path = filedialog.askopenfilename(
            title="Select Cover Image",
            filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.bmp")],
        )
        if not path:
            return
        pil_img = load_image(path)
        pil_fixed = self._pil_fixed(pil_img)
        self.cover_np = pil_to_numpy(pil_fixed)
        self._set_label_image(self.lbl_cover, pil_fixed, "cover")
        # keep overlay so user can click again; no place_forget
        self.status_var.set(f"Loaded cover image: {os.path.basename(path)}")

    def load_secret(self):
        path = filedialog.askopenfilename(
            title="Select Secret Image",
            filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.bmp")],
        )
        if not path:
            return
        pil_img = load_image(path)
        pil_fixed = self._pil_fixed(pil_img)
        self.secret_np = pil_to_numpy(pil_fixed)
        self._set_label_image(self.lbl_secret, pil_fixed, "secret")
        self.status_var.set(f"Loaded secret image: {os.path.basename(path)}")

    # ======================================================================
    # Checks / resize for StegFormer
    # ======================================================================

    def _check_inputs(self) -> bool:
        if self.cover_np is None or self.secret_np is None:
            messagebox.showwarning(
                "Missing input", "Load both cover and secret images."
            )
            return False
        if self.cover_np.shape != self.secret_np.shape:
            messagebox.showwarning(
                "Size mismatch",
                "Cover and secret must have the same size (256×256×3).",
            )
            return False
        return True

    def _resize_for_steg(self, img_np: np.ndarray) -> np.ndarray:
        pil_img = numpy_to_pil(img_np)
        pil_resized = pil_img.resize(STEGO_SIZE, Image.BICUBIC)
        return pil_to_numpy(pil_resized)

    # ======================================================================
    # Clear / export
    # ======================================================================

    def clear_results(self):
        self.stego_lsb = None
        self.rec_lsb = None
        self.stego_steg = None
        self.rec_steg = None

        for key, lbl_name in [
            ("lsb_stego", "lbl_lsb_stego"),
            ("lsb_rec", "lbl_lsb_rec"),
            ("steg_stego", "lbl_steg_stego"),
            ("steg_rec", "lbl_steg_rec"),
        ]:
            lbl = getattr(self, lbl_name, None)
            if lbl is not None:
                lbl.configure(image="")
            self._tk_images.pop(key, None)

        self.metrics = {
            "LSB": {"cov_psnr": None, "cov_ssim": None,
                    "sec_psnr": None, "sec_ssim": None},
            "StegFormer": {"cov_psnr": None, "cov_ssim": None,
                           "sec_psnr": None, "sec_ssim": None},
        }

        self.metrics_lsb_var.set("LSB: PSNR/SSIM – not computed")
        self.metrics_steg_var.set("StegFormer: PSNR/SSIM – not computed")

        for v in [
            self.lsb_cov_psnr_var,
            self.lsb_cov_ssim_var,
            self.lsb_sec_psnr_var,
            self.lsb_sec_ssim_var,
            self.steg_cov_psnr_var,
            self.steg_cov_ssim_var,
            self.steg_sec_psnr_var,
            self.steg_sec_ssim_var,
        ]:
            v.set("-")

        self.status_var.set("Results cleared")

    def export_results(self):
        if self.cover_np is None or self.secret_np is None:
            messagebox.showwarning(
                "No data", "Load images and run at least one algorithm."
            )
            return

        dest_root = filedialog.askdirectory(title="Select export folder")
        if not dest_root:
            return

        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        root = os.path.join(dest_root, f"stego_run_{ts}")
        os.makedirs(root, exist_ok=True)

        numpy_to_pil(self.cover_np).save(os.path.join(root, "cover_256.png"))
        numpy_to_pil(self.secret_np).save(os.path.join(root, "secret_256.png"))

        if self.stego_lsb is not None:
            numpy_to_pil(self.stego_lsb).save(os.path.join(root, "lsb_stego.png"))
        if self.rec_lsb is not None:
            numpy_to_pil(self.rec_lsb).save(os.path.join(root, "lsb_recovered.png"))
        if self.stego_steg is not None:
            numpy_to_pil(self.stego_steg).save(
                os.path.join(root, "stegformer_stego.png")
            )
        if self.rec_steg is not None:
            numpy_to_pil(self.rec_steg).save(
                os.path.join(root, "stegformer_recovered.png")
            )

        csv_path = os.path.join(root, "metrics.csv")
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                ["algorithm", "cover_psnr", "cover_ssim", "secret_psnr", "secret_ssim"]
            )
            for algo, vals in self.metrics.items():
                writer.writerow(
                    [
                        algo,
                        vals["cov_psnr"] if vals["cov_psnr"] is not None else "",
                        vals["cov_ssim"] if vals["cov_ssim"] is not None else "",
                        vals["sec_psnr"] if vals["sec_psnr"] is not None else "",
                        vals["sec_ssim"] if vals["sec_ssim"] is not None else "",
                    ]
                )

        messagebox.showinfo("Export complete", f"Results saved to:\n{root}")
        self.status_var.set(f"Exported results to {root}")

    # ======================================================================
    # LSB
    # ======================================================================

    def run_lsb(self):
        if not self._check_inputs():
            return

        self.status_var.set("Running LSB...")
        self.update_idletasks()

        stego = lsb_hide(self.cover_np, self.secret_np)
        rec = lsb_reveal(stego)

        self.stego_lsb = stego
        self.rec_lsb = rec

        self._set_label_image(self.lbl_lsb_stego, numpy_to_pil(stego), "lsb_stego")
        self._set_label_image(self.lbl_lsb_rec, numpy_to_pil(rec), "lsb_rec")

        cov_psnr = compute_psnr(self.cover_np, stego)
        cov_ssim = compute_ssim(self.cover_np, stego)
        sec_psnr = compute_psnr(self.secret_np, rec)
        sec_ssim = compute_ssim(self.secret_np, rec)

        self.metrics["LSB"] = {
            "cov_psnr": cov_psnr,
            "cov_ssim": cov_ssim,
            "sec_psnr": sec_psnr,
            "sec_ssim": sec_ssim,
        }

        self.metrics_lsb_var.set(
            f"LSB: Cover/Stego PSNR={cov_psnr:.2f}, SSIM={cov_ssim:.3f} | "
            f"Secret/Rec PSNR={sec_psnr:.2f}, SSIM={sec_ssim:.3f}"
        )

        self.lsb_cov_psnr_var.set(f"{cov_psnr:.2f}")
        self.lsb_cov_ssim_var.set(f"{cov_ssim:.3f}")
        self.lsb_sec_psnr_var.set(f"{sec_psnr:.2f}")
        self.lsb_sec_ssim_var.set(f"{sec_ssim:.3f}")

        self.status_var.set("LSB run completed")

    # ======================================================================
    # StegFormer
    # ======================================================================

    def run_stegformer(self):
        if not self._check_inputs():
            return

        self.status_var.set("Running StegFormer...")
        self.update_idletasks()

        try:
            cov = self._resize_for_steg(self.cover_np)
            sec = self._resize_for_steg(self.secret_np)

            stego = self.stegformer.hide(cov, sec)
            rec = self.stegformer.reveal(stego)
        except Exception as e:
            messagebox.showerror("StegFormer error", str(e))
            self.status_var.set("StegFormer failed")
            return

        self.stego_steg = stego
        self.rec_steg = rec

        self._set_label_image(self.lbl_steg_stego, numpy_to_pil(stego), "steg_stego")
        self._set_label_image(self.lbl_steg_rec, numpy_to_pil(rec), "steg_rec")

        cov_psnr = compute_psnr(cov, stego)
        cov_ssim = compute_ssim(cov, stego)
        sec_psnr = compute_psnr(sec, rec)
        sec_ssim = compute_ssim(sec, rec)

        self.metrics["StegFormer"] = {
            "cov_psnr": cov_psnr,
            "cov_ssim": cov_ssim,
            "sec_psnr": sec_psnr,
            "sec_ssim": sec_ssim,
        }

        self.metrics_steg_var.set(
            f"StegFormer: Cover/Stego PSNR={cov_psnr:.2f}, SSIM={cov_ssim:.3f} | "
            f"Secret/Rec PSNR={sec_psnr:.2f}, SSIM={sec_ssim:.3f}"
        )

        self.steg_cov_psnr_var.set(f"{cov_psnr:.2f}")
        self.steg_cov_ssim_var.set(f"{cov_ssim:.3f}")
        self.steg_sec_psnr_var.set(f"{sec_psnr:.2f}")
        self.steg_sec_ssim_var.set(f"{sec_ssim:.3f}")

        self.status_var.set("StegFormer run completed")
