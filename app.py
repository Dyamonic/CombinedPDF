import os
import shutil
import tempfile
from tkinter import filedialog, messagebox
from typing import Dict, List, Optional

import customtkinter as ctk
import fitz  # PyMuPDF
from PIL import Image, ImageTk
from pypdf import PdfReader, PdfWriter


class CombinedPDFApp(ctk.CTk):
    """
    A modern PDF utility to merge, view, and manage PDF files with a polished UI.
    """
    FONT_FAMILY = "Segoe UI"

    def __init__(self):
        super().__init__()
        self.title("CombinedPDF — A Modern Utility")
        self.geometry("1250x750")
        self.minsize(1050, 650)

        self.color_schemes = {
            "dark": {
                "bg_sidebar": "#1a1a1a", "bg_primary": "#212121", "bg_secondary": "#2b2b2b",
                "bg_tertiary": "#1e1e1e", "text_primary": "#e0e0e0", "text_secondary": "gray70",
                "accent_primary": "#3fa7ff", "accent_success": "#38d39f", "accent_warning": "#ffb84d",
                "accent_danger": "#ff5d5d", "hover_primary": "#338ed3", "hover_success": "#2aa880",
                "hover_danger": "#cc4b4b",
            },
            "light": {
                "bg_sidebar": "#e0e0e0", "bg_primary": "#f0f0f0", "bg_secondary": "#ffffff",
                "bg_tertiary": "#e5e5e5", "text_primary": "#1a1a1a", "text_secondary": "#505050",
                "accent_primary": "#0078d4", "accent_success": "#107c10", "accent_warning": "#f7630c",
                "accent_danger": "#d13438", "hover_primary": "#005a9e", "hover_success": "#0d530d",
                "hover_danger": "#a4262c",
            }
        }
        self._set_initial_mode("dark")

        self.pdf_list: List[str] = []
        self.merged_path: Optional[str] = None
        self.current_view: str = "home"
        self.current_pdf: Optional[str] = None
        self.current_page: int = 0
        self.total_pages: int = 0
        self.preview_zoom: float = 1.0

        self._build_ui()

    def _set_initial_mode(self, mode: str):
        ctk.set_appearance_mode(mode)
        self.appearance_mode = ctk.get_appearance_mode().lower()
        self.colors: Dict[str, str] = self.color_schemes.get(self.appearance_mode, self.color_schemes["dark"])

    def _build_ui(self):
        self._build_sidebar()
        self._build_main_area()
        self._show_page("home")

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=80, corner_radius=0, fg_color=self.colors["bg_sidebar"])
        self.sidebar.pack(side="left", fill="y")
        self.sidebar_buttons = {}
        buttons_data = [("home", "🏠"), ("merge", "🔗"), ("viewer", "📄"), ("settings", "⚙️")]

        for name, icon in buttons_data:
            btn = ctk.CTkButton(
                self.sidebar, text=icon, width=60, height=55, font=(self.FONT_FAMILY, 26),
                fg_color="transparent", text_color=self.colors["text_secondary"],
                hover_color=self.colors["bg_secondary"], command=lambda n=name: self._show_page(n)
            )
            btn.pack(pady=18, padx=10)
            self.sidebar_buttons[name] = btn

    def _build_main_area(self):
        self.main_frame = ctk.CTkFrame(self, fg_color=self.colors["bg_primary"], corner_radius=0)
        self.main_frame.pack(side="left", fill="both", expand=True)


    def _show_page(self, name: str):
        self.current_view = name
        for btn_name, btn in self.sidebar_buttons.items():
            is_active = btn_name == name
            btn.configure(
                fg_color=self.colors["bg_secondary"] if is_active else "transparent",
                text_color=self.colors["text_primary"] if is_active else self.colors["text_secondary"]
            )
        for widget in self.main_frame.winfo_children(): widget.destroy()
        getattr(self, f"_build_{name}_page", self._build_home_page)()

    def _build_home_page(self):
        container = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        container.pack(expand=True)
        ctk.CTkLabel(container, text="📚 CombinedPDF", font=(self.FONT_FAMILY, 52, "bold"), text_color=self.colors["accent_primary"]).pack(pady=(0, 10))
        ctk.CTkLabel(container, text="A sleek utility to merge and view your PDF files.", font=(self.FONT_FAMILY, 18), text_color=self.colors["text_secondary"]).pack(pady=(0, 60))
        ctk.CTkButton(container, text="🔗 Start Merging", width=240, height=55, font=(self.FONT_FAMILY, 16, "bold"), fg_color=self.colors["accent_success"], hover_color=self.colors["hover_success"], command=lambda: self._show_page("merge")).pack(pady=10)
        ctk.CTkButton(container, text="📄 Open & View PDF", width=240, height=55, font=(self.FONT_FAMILY, 16, "bold"), fg_color=self.colors["accent_primary"], hover_color=self.colors["hover_primary"], command=lambda: self._show_page("viewer")).pack(pady=10)

    def _build_merge_page(self):
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(self.main_frame, text="🔗 PDF Merger", font=(self.FONT_FAMILY, 36, "bold"), text_color=self.colors["accent_success"]).grid(row=0, column=0, pady=(40, 20), sticky="n")

        controls_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        controls_frame.grid(row=1, column=0, pady=(0, 10))

        btn_style = {"width": 160, "height": 45, "font": (self.FONT_FAMILY, 14, "bold")}
        ctk.CTkButton(controls_frame, text="➕ Add Files", command=self._add_pdfs, **btn_style).pack(side="left", padx=10)
        ctk.CTkButton(controls_frame, text="🔗 Combine PDFs", command=self._merge_pdfs, fg_color=self.colors["accent_success"], hover_color=self.colors["hover_success"], **btn_style).pack(side="left", padx=10)
        ctk.CTkButton(controls_frame, text="💾 Export Result", command=self._save_as, fg_color=self.colors["accent_primary"], hover_color=self.colors["hover_primary"], **btn_style).pack(side="left", padx=10)
        ctk.CTkButton(controls_frame, text="🧹 Clear All", command=self._clear_merge, fg_color=self.colors["accent_danger"], hover_color=self.colors["hover_danger"], **btn_style).pack(side="left", padx=10)

        ctk.CTkFrame(self.main_frame, height=1, fg_color=self.colors["bg_secondary"]).grid(row=2, column=0, sticky="ew", padx=50, pady=20)
        self.pdf_list_frame = ctk.CTkScrollableFrame(self.main_frame, label_text="Files to Merge (in order)", label_font=(self.FONT_FAMILY, 14), label_text_color=self.colors["text_secondary"], fg_color=self.colors["bg_primary"])
        self.pdf_list_frame.grid(row=2, column=0, sticky="nsew", padx=50, pady=(0, 20))
        self._update_pdf_list_ui()

        self.status_label = ctk.CTkLabel(self.main_frame, text="Ready to combine your PDFs.", text_color=self.colors["text_secondary"], font=(self.FONT_FAMILY, 14))
        self.status_label.grid(row=3, column=0, pady=20, sticky="s")

    def _update_pdf_list_ui(self):
        for widget in self.pdf_list_frame.winfo_children(): widget.destroy()
        if not self.pdf_list:
            ctk.CTkLabel(self.pdf_list_frame, text="Click '➕ Add Files' to begin.", font=(self.FONT_FAMILY, 16), text_color=self.colors["text_secondary"]).pack(expand=True, pady=50)
            return
        for i, pdf_path in enumerate(self.pdf_list):
            file_frame = ctk.CTkFrame(self.pdf_list_frame, fg_color=self.colors["bg_secondary"], corner_radius=8)
            file_frame.pack(fill="x", padx=10, pady=5)
            label = ctk.CTkLabel(file_frame, text=f"{i+1}. {os.path.basename(pdf_path)}", anchor="w", text_color=self.colors["text_primary"])
            label.pack(side="left", fill="x", expand=True, padx=15, pady=10)
            btn_size = {"width": 32, "height": 32, "font": ("Arial", 16)}
            ctk.CTkButton(file_frame, text="🗑️", command=lambda idx=i: self._remove_pdf(idx), fg_color=self.colors["accent_danger"], hover_color=self.colors["hover_danger"], **btn_size).pack(side="right", padx=(5, 10))
            ctk.CTkButton(file_frame, text="▼", command=lambda idx=i: self._move_pdf(idx, 1), state="disabled" if i == len(self.pdf_list) - 1 else "normal", **btn_size).pack(side="right", padx=5)
            ctk.CTkButton(file_frame, text="▲", command=lambda idx=i: self._move_pdf(idx, -1), state="disabled" if i == 0 else "normal", **btn_size).pack(side="right", padx=5)

    def _add_pdfs(self):
        files = filedialog.askopenfilenames(title="Select PDF files", filetypes=[("PDF files", "*.pdf")])
        if files:
            self.pdf_list.extend(files)
            self._update_pdf_list_ui()
            self.status_label.configure(text=f"✔ Added {len(files)} new file(s).", text_color=self.colors["text_primary"])

    def _remove_pdf(self, index: int):
        self.pdf_list.pop(index)
        self._update_pdf_list_ui()
        self.status_label.configure(text="File removed.", text_color=self.colors["text_primary"])

    def _move_pdf(self, index: int, direction: int):
        if 0 <= index + direction < len(self.pdf_list):
            self.pdf_list[index], self.pdf_list[index + direction] = self.pdf_list[index + direction], self.pdf_list[index]
            self._update_pdf_list_ui()

    def _merge_pdfs(self):
        if len(self.pdf_list) < 2:
            messagebox.showwarning("Not Enough Files", "Please add at least two PDFs to merge.")
            return
        try:
            writer = PdfWriter()
            for path in self.pdf_list:
                reader = PdfReader(path)
                for page in reader.pages: writer.add_page(page)
            tmp_dir = tempfile.mkdtemp(prefix="combinedpdf_")
            out_path = os.path.join(tmp_dir, "merged.pdf")
            with open(out_path, "wb") as f: writer.write(f)
            self.merged_path, self.current_pdf = out_path, out_path
            self.status_label.configure(text="✔ Merge successful! You can now export the file.", text_color=self.colors["accent_success"])
        except Exception as e:
            self.status_label.configure(text=f"✖ Error: {e}", text_color=self.colors["accent_danger"])
            messagebox.showerror("Merge Error", f"An error occurred: {e}")

    def _save_as(self):
        if not self.merged_path:
            messagebox.showinfo("Nothing to Export", "Please merge some PDFs first.")
            return
        dest = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")], initialfile="merged_document.pdf")
        if dest:
            shutil.copyfile(self.merged_path, dest)
            self.status_label.configure(text=f"✔ Saved to: {os.path.basename(dest)}", text_color=self.colors["accent_success"])

    def _clear_merge(self):
        self.pdf_list.clear()
        self.merged_path = None
        self._update_pdf_list_ui()
        self.status_label.configure(text="Cleared all files.", text_color=self.colors["text_secondary"])

    def _build_viewer_page(self):
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(2, weight=1)
        ctk.CTkLabel(self.main_frame, text="📄 PDF Viewer", font=(self.FONT_FAMILY, 36, "bold"), text_color=self.colors["accent_primary"]).grid(row=0, column=0, pady=(40, 20), sticky="n")

        toolbar = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        toolbar.grid(row=1, column=0, pady=10)
        btn_style = {"width": 120, "height": 40, "font": (self.FONT_FAMILY, 14, "bold")}
        ctk.CTkButton(toolbar, text="📂 Open PDF", command=self._open_pdf_in_viewer, **btn_style).pack(side="left", padx=8)
        ctk.CTkButton(toolbar, text="❮ Previous", command=lambda: self._flip_page(-1), **btn_style).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="Next ❯", command=lambda: self._flip_page(1), **btn_style).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="🔍 Zoom Out", command=lambda: self._zoom(-0.2), **btn_style).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="🔍 Zoom In", command=lambda: self._zoom(0.2), **btn_style).pack(side="left", padx=5)

        self.page_label = ctk.CTkLabel(toolbar, text="Page 0 of 0", font=(self.FONT_FAMILY, 14), text_color=self.colors["text_secondary"])
        self.page_label.pack(side="left", padx=20)
        self.viewer_frame = ctk.CTkScrollableFrame(self.main_frame, fg_color=self.colors["bg_tertiary"], corner_radius=15)
        self.viewer_frame.grid(row=2, column=0, sticky="nsew", padx=40, pady=20)
        if self.current_pdf: self._render_page()
        else: ctk.CTkLabel(self.viewer_frame, text="Open a PDF to begin viewing", font=(self.FONT_FAMILY, 16), text_color=self.colors["text_secondary"]).pack(expand=True)

    def _open_pdf_in_viewer(self):
        file = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if file:
            self.current_pdf, self.current_page, self.preview_zoom = file, 0, 1.0
            self._render_page()

    def _render_page(self):
        for widget in self.viewer_frame.winfo_children(): widget.destroy()
        if not self.current_pdf:
            ctk.CTkLabel(self.viewer_frame, text="No PDF loaded.", text_color=self.colors["text_secondary"]).pack(expand=True)
            return
        try:
            doc = fitz.open(self.current_pdf)
            self.total_pages = len(doc)
            page = doc.load_page(self.current_page)
            pix = page.get_pixmap(matrix=fitz.Matrix(self.preview_zoom, self.preview_zoom))
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            photo = ImageTk.PhotoImage(img)
            lbl = ctk.CTkLabel(self.viewer_frame, image=photo, text="")
            lbl.image = photo
            lbl.pack(pady=20, padx=20)
            doc.close()
            self.page_label.configure(text=f"Page {self.current_page + 1} of {self.total_pages}")
        except Exception as e:
            ctk.CTkLabel(self.viewer_frame, text=f"✖ Error loading PDF: {e}", text_color=self.colors["accent_danger"]).pack(expand=True)
            self.page_label.configure(text="Error")

    def _flip_page(self, delta: int):
        if self.total_pages > 0:
            self.current_page = (self.current_page + delta) % self.total_pages
            self._render_page()

    def _zoom(self, delta: float):
        self.preview_zoom = max(0.5, min(3.5, self.preview_zoom + delta))
        self._render_page()
        
    def _build_settings_page(self):
        container = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        container.pack(expand=True)
        ctk.CTkLabel(container, text="⚙️ Settings", font=(self.FONT_FAMILY, 36, "bold"), text_color=self.colors["accent_warning"]).pack(pady=(0, 20))
        ctk.CTkLabel(container, text="Customize the application's look and feel.", font=(self.FONT_FAMILY, 16), text_color=self.colors["text_secondary"]).pack(pady=(0, 30))

        settings_frame = ctk.CTkFrame(container, fg_color=self.colors["bg_secondary"])
        settings_frame.pack(padx=20, pady=20, ipadx=30, ipady=20)
        ctk.CTkLabel(settings_frame, text="Appearance Mode", font=(self.FONT_FAMILY, 16, "bold"), text_color=self.colors["text_primary"]).pack(pady=(10, 10))
        mode_menu = ctk.CTkOptionMenu(settings_frame, values=["Dark", "Light", "System"], command=self._change_appearance_mode)
        mode_menu.set(ctk.get_appearance_mode())
        mode_menu.pack(pady=(0, 10), padx=20)

    def _change_appearance_mode(self, new_mode: str):
        ctk.set_appearance_mode(new_mode)
        self.appearance_mode = ctk.get_appearance_mode().lower()
        self.colors = self.color_schemes.get(self.appearance_mode, self.color_schemes["dark"])
        self.sidebar.configure(fg_color=self.colors["bg_sidebar"])
        self.main_frame.configure(fg_color=self.colors["bg_primary"])
        self._show_page(self.current_view)

if __name__ == "__main__":
    app = CombinedPDFApp()
    app.mainloop()