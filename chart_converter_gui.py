import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from chart_converter import load_json, save_json, vslice_to_psych, psych_to_vslice, LOG_FILE_NAME

class ConverterGUI(tk.Tk):
    """Minimal Tkinter GUI hooking into chart_converter core functions."""

    def __init__(self):
        super().__init__()
        self.title("FNF Chart Converter - VSlice ⬌ Psych")
        self.geometry("620x360")
        self.resizable(False, False)

        # --- variables -------------------------------------------------------
        self.operation = tk.StringVar(value="vslice2psych")
        self.chart_file = tk.StringVar()
        self.meta_file = tk.StringVar()
        self.psych_file = tk.StringVar()
        self.outdir = tk.StringVar(value=os.getcwd())
        self.status_msg = tk.StringVar()

        self._build_widgets()
        self._update_mode()

    # ---------------------------------------------------------------------
    def _build_widgets(self):
        frm = ttk.Frame(self, padding=12)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="Modo de conversión:").grid(row=0, column=0, sticky="w")
        ttk.Radiobutton(frm, text="VSlice → Psych", variable=self.operation, value="vslice2psych", command=self._update_mode).grid(row=0, column=1, sticky="w")
        ttk.Radiobutton(frm, text="Psych → VSlice", variable=self.operation, value="psych2vslice", command=self._update_mode).grid(row=0, column=2, sticky="w")

        # --- rows filled dynamically -------------------------------------
        self.lbl_chart = ttk.Label(frm, text="chart.json:")
        self.ent_chart = ttk.Entry(frm, textvariable=self.chart_file, width=45)
        self.btn_chart = ttk.Button(frm, text="...", width=3, command=self._browse_chart)

        self.lbl_meta = ttk.Label(frm, text="metadata.json:")
        self.ent_meta = ttk.Entry(frm, textvariable=self.meta_file, width=45)
        self.btn_meta = ttk.Button(frm, text="...", width=3, command=self._browse_meta)

        self.lbl_psych = ttk.Label(frm, text="Psych chart (.json):")
        self.ent_psych = ttk.Entry(frm, textvariable=self.psych_file, width=45)
        self.btn_psych = ttk.Button(frm, text="...", width=3, command=self._browse_psych)

        # output dir
        ttk.Label(frm, text="Salida:").grid(row=5, column=0, sticky="w", pady=(18, 0))
        ttk.Entry(frm, textvariable=self.outdir, width=45).grid(row=5, column=1, columnspan=1, sticky="ew", pady=(18, 0))
        ttk.Button(frm, text="...", width=3, command=self._browse_outdir).grid(row=5, column=2, sticky="w", pady=(18, 0))

        ttk.Button(frm, text="Convertir", command=self._convert, width=20).grid(row=6, column=0, columnspan=3, pady=20)

        ttk.Label(self, textvariable=self.status_msg, foreground="green").pack(side="bottom", pady=6)

        frm.columnconfigure(1, weight=1)

    # ------------------------------------------------------------------
    def _update_mode(self):
        for w in [self.lbl_chart, self.ent_chart, self.btn_chart,
                  self.lbl_meta, self.ent_meta, self.btn_meta,
                  self.lbl_psych, self.ent_psych, self.btn_psych]:
            w.grid_remove()
        row = 1
        op = self.operation.get()
        if op == "vslice2psych":
            self.lbl_chart.grid(row=row, column=0, sticky="w", pady=4)
            self.ent_chart.grid(row=row, column=1, sticky="ew", pady=4)
            self.btn_chart.grid(row=row, column=2, pady=4, sticky="w")
            row += 1
            self.lbl_meta.grid(row=row, column=0, sticky="w", pady=4)
            self.ent_meta.grid(row=row, column=1, sticky="ew", pady=4)
            self.btn_meta.grid(row=row, column=2, pady=4, sticky="w")
        else:
            self.lbl_psych.grid(row=row, column=0, sticky="w", pady=4)
            self.ent_psych.grid(row=row, column=1, sticky="ew", pady=4)
            self.btn_psych.grid(row=row, column=2, pady=4, sticky="w")

    # ------------------------------------------------------------------
    def _browse_chart(self):
        f = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if f:
            self.chart_file.set(f)

    def _browse_meta(self):
        f = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if f:
            self.meta_file.set(f)

    def _browse_psych(self):
        f = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if f:
            self.psych_file.set(f)

    def _browse_outdir(self):
        d = filedialog.askdirectory()
        if d:
            self.outdir.set(d)

    # ------------------------------------------------------------------
    def _convert(self):
        op = self.operation.get()
        outdir = self.outdir.get()
        if not outdir:
            messagebox.showerror("Error", "Selecciona carpeta de salida")
            return
        os.makedirs(outdir, exist_ok=True)

        try:
            if op == "vslice2psych":
                if not (self.chart_file.get() and self.meta_file.get()):
                    messagebox.showerror("Error", "Selecciona chart.json y metadata.json")
                    return
                vs_chart = load_json(self.chart_file.get())
                vs_meta = load_json(self.meta_file.get())
                res = vslice_to_psych(vs_chart, vs_meta)
                for diff, data in res.items():
                    save_json(data, os.path.join(outdir, f"{diff}.json"))
                self.status_msg.set(f"¡Conversión OK! {len(res)} archivos. Revisa {LOG_FILE_NAME}")
            else:
                if not self.psych_file.get():
                    messagebox.showerror("Error", "Selecciona JSON de Psych")
                    return
                psy_chart = load_json(self.psych_file.get())
                pack = psych_to_vslice(psy_chart)
                save_json(pack['chart'], os.path.join(outdir, "chart.json"))
                save_json(pack['metadata'], os.path.join(outdir, "metadata.json"))
                self.status_msg.set(f"¡Exportación OK! Revisa {LOG_FILE_NAME}")
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.status_msg.set("Error. Ver log")


if __name__ == "__main__":
    app = ConverterGUI()
    app.mainloop()