import os
import tempfile
import shutil
from typing import Optional, List

import tkinter as tk
from tkinter import filedialog, messagebox

from PIL import Image, ImageTk, ImageDraw
import fitz
from pypdf import PdfReader, PdfWriter


class PDFMergerApp(tk.Tk):

    def __init__(self) -> None:
        super().__init__()
        self.title("CombinedPDF")
        self.geometry("1100x700")
        self.minsize(1000, 620)

        self.pdf1_path: Optional[str] = None
        self.pdf2_path: Optional[str] = None
        self.merged_pdf_path: Optional[str] = None
        self._rendered_images: List[ImageTk.PhotoImage] = []
        self._page_labels: List[tk.Label] = []
        self._page_render_info: List[dict] = []

        self.preview_zoom: float = 1.0

        self.bg_color = "#1e1e1e"
        self.panel_color = "#2b2b2b"
        self.accent_blue = "#3fa7ff"
        self.accent_green = "#38d39f"
        self.accent_orange = "#ffb84d"
        self.accent_red = "#ff5d5d"
        self.text_color = "#e6e6e6"
        self.dim_text = "#c2c2c2"

        self.configure(bg=self.bg_color)
        self._set_window_icon()
        self._build_layout()

    def _build_layout(self) -> None:
        left = tk.Frame(self, bg=self.bg_color)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        right = tk.Frame(self, bg=self.bg_color)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        self._build_left_controls(left)
        self._build_right_preview(right)

    def _section(self, parent: tk.Widget, title: str) -> tk.Frame:
        frame = tk.LabelFrame(
            parent,
            text=title,
            bg=self.panel_color,
            fg=self.text_color,
            bd=1,
            labelanchor="nw",
            padx=10,
            pady=10,
        )
        frame.configure(highlightthickness=0)
        frame.pack(fill=tk.X, pady=8)
        return frame

    def _button(self, parent: tk.Widget, text: str, color: str, command) -> tk.Button:
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            bg=color,
            fg="#000000",
            activebackground=color,
            activeforeground="#000000",
            relief=tk.FLAT,
            padx=12,
            pady=6,
            cursor="hand2",
        )
        return btn

    def _label(self, parent: tk.Widget, text: str) -> tk.Label:
        return tk.Label(parent, text=text, bg=self.panel_color, fg=self.dim_text, anchor="w")

    def _build_left_controls(self, parent: tk.Widget) -> None:
        actions = self._section(parent, "Actions")
        self._button(actions, "Open PDF", self.accent_blue, self._open_single_pdf).pack(fill=tk.X)
        tk.Frame(actions, height=8, bg=self.panel_color).pack(fill=tk.X)
        self._button(actions, "Merge PDF", self.accent_green, self._open_merge_dialog).pack(fill=tk.X)

        tk.Frame(actions, height=12, bg=self.panel_color).pack(fill=tk.X)
        btn_row = tk.Frame(actions, bg=self.panel_color)
        btn_row.pack(fill=tk.X)
        self._button(btn_row, "Save As", self.accent_orange, self._save_as).pack(side=tk.LEFT, expand=True, fill=tk.X)
        tk.Frame(btn_row, width=8, bg=self.panel_color).pack(side=tk.LEFT)
        self._button(btn_row, "Clear", self.accent_red, self._clear_all).pack(side=tk.LEFT, expand=True, fill=tk.X)

        status_sec = self._section(parent, "Status")
        self.status_text = tk.Text(status_sec, height=14, bg="#151515", fg=self.text_color, bd=0)
        self.status_text.pack(fill=tk.BOTH, expand=True)
        self._log("Ready. Use Open PDF or Merge PDF.")

    def _build_right_preview(self, parent: tk.Widget) -> None:
        header = tk.Label(parent, text="Preview", bg=self.bg_color, fg=self.text_color, anchor="w")
        header.pack(fill=tk.X, pady=(0, 6))

        toolbar = tk.Frame(parent, bg=self.bg_color)
        toolbar.pack(fill=tk.X, pady=(0, 6))

        self._button(toolbar, "-", self.accent_blue, lambda: self._change_zoom(-0.1)).pack(side=tk.LEFT)
        self.zoom_scale = tk.Scale(
            toolbar,
            from_=50,
            to=200,
            orient=tk.HORIZONTAL,
            length=200,
            showvalue=True,
            bg=self.bg_color,
            troughcolor="#3a3a3a",
            fg=self.text_color,
            highlightthickness=0,
            command=self._on_zoom_slider,
        )
        self.zoom_scale.set(100)
        self.zoom_scale.pack(side=tk.LEFT, padx=8)
        self._button(toolbar, "+", self.accent_blue, lambda: self._change_zoom(+0.1)).pack(side=tk.LEFT)

        container = tk.Frame(parent, bg=self.bg_color)
        container.pack(fill=tk.BOTH, expand=True)

        self.preview_canvas = tk.Canvas(container, bg="#0f0f0f", highlightthickness=0)
        vscroll = tk.Scrollbar(container, orient="vertical", command=self.preview_canvas.yview)
        self.preview_canvas.configure(yscrollcommand=vscroll.set)

        self.preview_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vscroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.preview_inner = tk.Frame(self.preview_canvas, bg="#0f0f0f")
        self.preview_window = self.preview_canvas.create_window((0, 0), window=self.preview_inner, anchor="nw")

        def _on_configure(event):
            self.preview_canvas.configure(scrollregion=self.preview_canvas.bbox("all"))
            self.preview_canvas.itemconfig(self.preview_window, width=event.width)

        self.preview_inner.bind("<Configure>", lambda e: self.preview_canvas.configure(scrollregion=self.preview_canvas.bbox("all")))
        self.preview_canvas.bind("<Configure>", _on_configure)
        self.preview_canvas.bind_all("<Control-MouseWheel>", self._on_mousewheel_zoom)
        self.preview_canvas.bind("<MouseWheel>", self._on_mousewheel_scroll)
        self.preview_inner.bind("<MouseWheel>", self._on_mousewheel_scroll)
        self.preview_canvas.bind("<Button-4>", lambda e: self.preview_canvas.yview_scroll(-3, "units"))
        self.preview_canvas.bind("<Button-5>", lambda e: self.preview_canvas.yview_scroll(3, "units"))

        

    def _log(self, message: str) -> None:
        self.status_text.insert(tk.END, f"{message}\n")
        self.status_text.see(tk.END)

    def _pick_pdf1(self) -> None:
        path = filedialog.askopenfilename(
            title="Select PDF 1 (to be appended)",
            filetypes=[("PDF files", "*.pdf")],
        )
        if path:
            self.pdf1_path = path
            if hasattr(self, "pdf1_label"):
                try:
                    self.pdf1_label.configure(text=f"PDF 1: {os.path.basename(path)}")
                except Exception:
                    pass
            self._log(f"Selected PDF 1: {path}")

    def _pick_pdf2(self) -> None:
        path = filedialog.askopenfilename(
            title="Select PDF 2 (base document)",
            filetypes=[("PDF files", "*.pdf")],
        )
        if path:
            self.pdf2_path = path
            if hasattr(self, "pdf2_label"):
                try:
                    self.pdf2_label.configure(text=f"PDF 2: {os.path.basename(path)}")
                except Exception:
                    pass
            self._log(f"Selected PDF 2: {path}")

    def _open_single_pdf(self) -> None:
        path = filedialog.askopenfilename(
            title="Open PDF to Preview",
            filetypes=[("PDF files", "*.pdf")],
        )
        if path:
            self.merged_pdf_path = path
            self._log(f"Opened PDF for preview: {path}")
            self._render_preview(path)

    def _open_merge_dialog(self) -> None:
        dlg = tk.Toplevel(self)
        dlg.title("Merge PDF")
        dlg.configure(bg=self.panel_color)
        dlg.geometry("460x220")
        dlg.resizable(False, False)

        container = tk.Frame(dlg, bg=self.panel_color, padx=12, pady=12)
        container.pack(fill=tk.BOTH, expand=True)

        lbl1 = tk.Label(container, text="PDF 1: Not selected", bg=self.panel_color, fg=self.dim_text, anchor="w")
        lbl1.pack(fill=tk.X, pady=(0, 6))
        lbl2 = tk.Label(container, text="PDF 2: Not selected", bg=self.panel_color, fg=self.dim_text, anchor="w")
        lbl2.pack(fill=tk.X, pady=(0, 10))

        def choose1():
            path = filedialog.askopenfilename(parent=dlg, title="Select PDF 1 (to append)", filetypes=[("PDF files", "*.pdf")])
            if path:
                self.pdf1_path = path
                lbl1.configure(text=f"PDF 1: {os.path.basename(path)}")
                self._log(f"Selected PDF 1: {path}")

        def choose2():
            path = filedialog.askopenfilename(parent=dlg, title="Select PDF 2 (base)", filetypes=[("PDF files", "*.pdf")])
            if path:
                self.pdf2_path = path
                lbl2.configure(text=f"PDF 2: {os.path.basename(path)}")
                self._log(f"Selected PDF 2: {path}")

        row = tk.Frame(container, bg=self.panel_color)
        row.pack(fill=tk.X)
        self._button(row, "Open PDF 1", self.accent_blue, choose1).pack(side=tk.LEFT, expand=True, fill=tk.X)
        tk.Frame(row, width=8, bg=self.panel_color).pack(side=tk.LEFT)
        self._button(row, "Open PDF 2", self.accent_blue, choose2).pack(side=tk.LEFT, expand=True, fill=tk.X)

        tk.Frame(container, height=10, bg=self.panel_color).pack(fill=tk.X)
        action_row = tk.Frame(container, bg=self.panel_color)
        action_row.pack(fill=tk.X)
        self._button(action_row, "Merge", self.accent_green, lambda: self._merge_and_close(dlg)).pack(side=tk.LEFT, expand=True, fill=tk.X)
        tk.Frame(action_row, width=8, bg=self.panel_color).pack(side=tk.LEFT)
        self._button(action_row, "Cancel", self.accent_red, dlg.destroy).pack(side=tk.LEFT, expand=True, fill=tk.X)

    def _merge(self) -> None:
        if not self.pdf1_path or not self.pdf2_path:
            messagebox.showwarning("Missing Files", "Please select both PDF 1 and PDF 2.")
            return
        try:
            writer = PdfWriter()

            for src in (self.pdf2_path, self.pdf1_path):
                reader = PdfReader(src)
                for page in reader.pages:
                    writer.add_page(page)

            tmp_dir = tempfile.mkdtemp(prefix="pdf_merge_")
            merged_path = os.path.join(tmp_dir, "merged.pdf")
            with open(merged_path, "wb") as out:
                writer.write(out)

            self.merged_pdf_path = merged_path
            self._log(f"Merged created: {merged_path}")
            self._render_preview(merged_path)
        except Exception as exc:
            self._log(f"Error merging PDFs: {exc}")
            messagebox.showerror("Merge Error", str(exc))

    def _merge_and_close(self, dlg: tk.Toplevel) -> None:
        self._merge()
        try:
            dlg.destroy()
        except Exception:
            pass

    def _render_preview(self, pdf_path: str) -> None:
        try:
            for child in list(self.preview_inner.winfo_children()):
                try:
                    child.destroy()
                except Exception:
                    pass
        except Exception:
            pass
        self._page_labels.clear()
        self._rendered_images.clear()
        self._page_render_info.clear()
        try:
            self.preview_canvas.yview_moveto(0)
        except Exception:
            pass

        try:
            doc = fitz.open(pdf_path)
        except Exception as exc:
            self._log(f"Error opening merged PDF for preview: {exc}")
            return

        
        base_width = max(700, self.preview_canvas.winfo_width() - 20)
        target_width = base_width * max(0.5, min(2.0, self.preview_zoom))
        for i, page in enumerate(doc):
            zoom = target_width / page.rect.width
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            photo = ImageTk.PhotoImage(img)
            self._rendered_images.append(photo)
            page_container = tk.Frame(self.preview_inner, bg="#0f0f0f")
            page_container.pack(fill=tk.X, pady=6)

            lbl = tk.Label(page_container, image=photo, bg="#0f0f0f")
            lbl.pack(fill=tk.X)
            self._page_labels.append(lbl)
            self._page_render_info.append({"zoom": zoom})

            lbl.bind("<Button-3>", lambda e, idx=i: self._on_page_context_menu(idx, e))
            lbl.bind("<Button-1>", lambda e, idx=i: self._on_page_left_click(idx, e))

        self._log(f"Rendered {len(self._page_labels)} page(s) in preview.")
        doc.close()

    def _save_as(self) -> None:
        if not self.merged_pdf_path:
            messagebox.showinfo("Nothing to Save", "Merge a PDF first.")
            return
        dst = filedialog.asksaveasfilename(
            title="Save merged PDF",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
        )
        if dst:
            try:
                shutil.copyfile(self.merged_pdf_path, dst)
                self._log(f"Saved merged PDF to: {dst}")
            except Exception as exc:
                self._log(f"Error saving file: {exc}")
                messagebox.showerror("Save Error", str(exc))

    def _clear_all(self) -> None:
        self.pdf1_path = None
        self.pdf2_path = None
        self.merged_pdf_path = None
        self._render_preview_empty()
        self._log("Cleared selection and preview.")

    def _render_preview_empty(self) -> None:
        try:
            for child in list(self.preview_inner.winfo_children()):
                try:
                    child.destroy()
                except Exception:
                    pass
        except Exception:
            pass
        self._page_labels.clear()
        self._rendered_images.clear()

    def _change_zoom(self, delta: float) -> None:
        new_zoom = max(0.5, min(2.0, self.preview_zoom + delta))
        self.preview_zoom = new_zoom
        try:
            self.zoom_scale.set(int(round(new_zoom * 100)))
        except Exception:
            pass
        if self.merged_pdf_path:
            self._render_preview(self.merged_pdf_path)

    def _on_zoom_slider(self, value: str) -> None:
        try:
            self.preview_zoom = float(value) / 100.0
        except Exception:
            return
        if self.merged_pdf_path:
            self._render_preview(self.merged_pdf_path)

    def _on_mousewheel_zoom(self, event) -> None:
        direction = 1 if event.delta > 0 else -1
        self._change_zoom(0.1 * direction)

    def _on_mousewheel_scroll(self, event) -> None:
        try:
            if (event.state & 0x0004) != 0:
                return
        except Exception:
            pass
        delta = -1 if event.delta > 0 else 1
        self.preview_canvas.yview_scroll(delta * 3, "units")

    def _set_window_icon(self) -> None:
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            assets_dir = os.path.join(base_dir, "assets")
            os.makedirs(assets_dir, exist_ok=True)
            ico_path = os.path.join(assets_dir, "combinedpdf.ico")
            png_path = os.path.join(assets_dir, "combinedpdf.png")

            if not os.path.exists(ico_path):
                img = self._generate_icon_image(256)
                img.save(ico_path, format="ICO", sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
                img.save(png_path, format="PNG")
            else:
                if not os.path.exists(png_path):
                    Image.open(ico_path).save(png_path, format="PNG")

            try:
                self.iconbitmap(ico_path)
            except Exception:
                pass
            try:
                icon_img = tk.PhotoImage(file=png_path)
                self.iconphoto(True, icon_img)
                self._icon_photo = icon_img
            except Exception:
                pass
        except Exception:
            pass

    def _generate_icon_image(self, size: int) -> Image.Image:
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        margin = int(size * 0.06)
        d.ellipse([margin, margin, size - margin, size - margin], fill=(34, 34, 34, 255))
        pad = int(size * 0.22)
        rect = [pad, pad, size - pad, size - pad]
        d.rounded_rectangle(rect, radius=int(size * 0.06), fill=(255, 255, 255, 255))
        fold = int(size * 0.14)
        x1, y1, x2, y2 = rect
        fold_poly = [(x2 - fold, y1), (x2, y1), (x2, y1 + fold)]
        d.polygon(fold_poly, fill=(63, 167, 255, 255))
        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2
        r = int(size * 0.08)
        d.ellipse([cx - r - 14, cy - r, cx + r - 14, cy + r], outline=(63, 167, 255, 255), width=int(size * 0.03))
        d.ellipse([cx - r + 14, cy - r, cx + r + 14, cy + r], outline=(63, 167, 255, 255), width=int(size * 0.03))
        return img

    def _on_page_left_click(self, page_index: int, event) -> None:
        return

    def _on_page_context_menu(self, page_index: int, event) -> None:
        menu = tk.Menu(self, tearoff=0, bg="#2b2b2b", fg=self.text_color)
        menu.add_command(label="Save As...", command=self._save_as)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    


def main() -> None:
    app = PDFMergerApp()
    app.mainloop()


if __name__ == "__main__":
    main()


