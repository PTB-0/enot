# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import sys
import json
import threading
import queue as _queue

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sifrele import AnahtarOlustur, Sifrele, SifreCoz

NOTLAR_DIR = r"C:\Users\USER\Desktop\notlar"
SETTINGS_FILE = os.path.join(NOTLAR_DIR, ".enot_settings.json")

_DEF = {
    "ai_provider": "ollama",
    "ollama_url": "http://localhost:11434",
    "ollama_model": "llama3.2",
    "anthropic_key": "",
    "anthropic_model": "claude-sonnet-4-6",
    "openai_key": "",
    "openai_model": "gpt-4o-mini",
}

C = {
    "bg": "#1e1e1e", "sidebar": "#252526", "toolbar": "#2d2d30",
    "btn": "#3e3e42", "sel": "#094771", "accent": "#007acc",
    "ai_bg": "#1a1a2e", "ai_hdr": "#16213e", "ai_acc": "#7c3aed",
    "txt": "#d4d4d4", "dim": "#858585", "folder": "#fbbf24",
    "enc": "#60a5fa", "green": "#065f46",
}


def _load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return {**_DEF, **json.load(f)}
        except Exception:
            pass
    return _DEF.copy()


def _save_settings(s):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(s, f, indent=2, ensure_ascii=False)


class EnotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("enot")
        self.root.geometry("1200x700")
        self.root.minsize(800, 500)
        self.root.configure(bg=C["bg"])

        self.current_file = None
        self.is_modified = False
        self.current_dir = NOTLAR_DIR
        self.ai_visible = False
        self._ai_running = False
        self._ai_stop = threading.Event()
        self._ai_q = _queue.Queue()
        self.settings = _load_settings()

        os.makedirs(NOTLAR_DIR, exist_ok=True)
        AnahtarOlustur()

        self._setup_grid()
        self._build_toolbar()
        self._build_sidebar()
        self._build_editor()
        self._build_ai_panel()
        self._build_statusbar()

        self._refresh_tree()
        self.root.bind("<Control-s>", lambda e: self._kaydet())
        self.root.bind("<Control-n>", lambda e: self._yeni_dosya())
        self.root.protocol("WM_DELETE_WINDOW", self._kapat)
        self.root.after(50, self._poll_q)

    # ----------------------------------------------------------------- grid --

    def _setup_grid(self):
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(1, weight=1)
        s = ttk.Style()
        s.theme_use("clam")
        s.configure("T.Treeview",
                     background=C["sidebar"], foreground=C["txt"],
                     fieldbackground=C["sidebar"], borderwidth=0,
                     rowheight=26, font=("Segoe UI", 10))
        s.map("T.Treeview",
               background=[("selected", C["sel"])],
               foreground=[("selected", "white")])

    # --------------------------------------------------------------- toolbar --

    def _build_toolbar(self):
        tb = tk.Frame(self.root, bg=C["toolbar"], pady=6)
        tb.grid(row=0, column=0, columnspan=3, sticky="ew")

        def btn(text, cmd, bg=C["btn"], fg="#cccccc", side="left"):
            b = tk.Button(tb, text=text, command=cmd, bg=bg, fg=fg,
                          relief="flat", font=("Segoe UI", 9), padx=10, pady=4,
                          activebackground="#505050", activeforeground="white",
                          cursor="hand2", bd=0)
            b.pack(side=side, padx=3, pady=2)
            return b

        btn("+ Not  Ctrl+N", self._yeni_dosya)
        btn("+ Klasor", self._yeni_klasor)
        btn("Kaydet  Ctrl+S", self._kaydet)
        btn("Sil", self._sil)
        btn("Yenile", self._refresh_tree)
        self._ai_btn = btn("  AI Asistan  ", self._toggle_ai,
                            bg=C["ai_acc"], fg="white", side="right")

    # --------------------------------------------------------------- sidebar --

    def _build_sidebar(self):
        sb = tk.Frame(self.root, bg=C["sidebar"], width=240)
        sb.grid(row=1, column=0, sticky="nsew")
        sb.grid_propagate(False)
        sb.rowconfigure(2, weight=1)
        sb.columnconfigure(0, weight=1)

        self._path_lbl = tk.Label(sb, text="NOTLARIM", bg=C["sidebar"],
                                   fg=C["dim"], font=("Segoe UI", 9, "bold"),
                                   anchor="w", padx=8, pady=6)
        self._path_lbl.grid(row=0, column=0, columnspan=2, sticky="ew")

        self._up_btn = tk.Button(sb, text="^ Yukari", command=self._geri,
                                  bg=C["sidebar"], fg=C["dim"], relief="flat",
                                  font=("Segoe UI", 8), pady=2, cursor="hand2",
                                  state="disabled")
        self._up_btn.grid(row=1, column=0, columnspan=2, sticky="ew", padx=4)

        self.tree = ttk.Treeview(sb, show="tree", style="T.Treeview",
                                  selectmode="browse")
        self.tree.grid(row=2, column=0, sticky="nsew", pady=(4, 0))
        self.tree.bind("<<TreeviewSelect>>", self._tree_sec)
        self.tree.bind("<Double-Button-1>", self._tree_dbl)

        scr = tk.Scrollbar(sb, orient="vertical", command=self.tree.yview)
        scr.grid(row=2, column=1, sticky="ns")
        self.tree.config(yscrollcommand=scr.set)

    # ---------------------------------------------------------------- editor --

    def _build_editor(self):
        ed = tk.Frame(self.root, bg=C["bg"])
        ed.grid(row=1, column=1, sticky="nsew")
        ed.columnconfigure(0, weight=1)
        ed.rowconfigure(1, weight=1)

        self._title_lbl = tk.Label(ed, text="Bir dosya secin veya yeni olusturun",
                                    bg=C["bg"], fg=C["dim"],
                                    font=("Segoe UI", 10), anchor="w", padx=12, pady=6)
        self._title_lbl.grid(row=0, column=0, columnspan=2, sticky="ew")

        self.text_area = tk.Text(ed, bg=C["bg"], fg=C["txt"],
                                  insertbackground="#aeafad",
                                  font=("Consolas", 12), relief="flat", bd=0,
                                  padx=16, pady=8, wrap="word", undo=True,
                                  selectbackground="#264f78")
        self.text_area.grid(row=1, column=0, sticky="nsew")
        self.text_area.bind("<<Modified>>", self._on_modified)

        scr = tk.Scrollbar(ed, orient="vertical", command=self.text_area.yview)
        scr.grid(row=1, column=1, sticky="ns")
        self.text_area.config(yscrollcommand=scr.set)

    # ------------------------------------------------------------- AI panel --

    def _build_ai_panel(self):
        self._ai_frm = tk.Frame(self.root, bg=C["ai_bg"], width=340)
        self._ai_frm.grid_propagate(False)
        self._ai_frm.rowconfigure(5, weight=1)
        self._ai_frm.columnconfigure(0, weight=1)

        # header
        hdr = tk.Frame(self._ai_frm, bg=C["ai_hdr"], pady=6)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.columnconfigure(0, weight=1)
        tk.Label(hdr, text="AI Asistan", bg=C["ai_hdr"], fg="#a78bfa",
                 font=("Segoe UI", 11, "bold"), anchor="w", padx=12).grid(row=0, column=0, sticky="w")
        tk.Button(hdr, text="x", command=self._toggle_ai,
                  bg=C["ai_hdr"], fg=C["dim"], relief="flat", cursor="hand2",
                  font=("Segoe UI", 10)).grid(row=0, column=1, padx=8)

        # provider
        pf = tk.Frame(self._ai_frm, bg=C["ai_bg"], pady=4)
        pf.grid(row=1, column=0, sticky="ew", padx=8)
        tk.Label(pf, text="Saglayici:", bg=C["ai_bg"], fg="#9ca3af",
                 font=("Segoe UI", 9)).pack(anchor="w")
        self._prov = tk.StringVar(value=self.settings["ai_provider"])
        cb = ttk.Combobox(pf, textvariable=self._prov,
                           values=["ollama", "anthropic", "openai"],
                           state="readonly", width=16)
        cb.pack(anchor="w", pady=2)
        cb.bind("<<ComboboxSelected>>", lambda e: self._rebuild_cfg())

        # config (dynamic)
        self._cfg = tk.Frame(self._ai_frm, bg=C["ai_bg"])
        self._cfg.grid(row=2, column=0, sticky="ew", padx=8)
        self._rebuild_cfg()

        # prompt
        prmf = tk.Frame(self._ai_frm, bg=C["ai_bg"], pady=4)
        prmf.grid(row=3, column=0, sticky="ew", padx=8)
        prmf.columnconfigure(0, weight=1)
        tk.Label(prmf, text="Istek / Prompt:", bg=C["ai_bg"], fg="#9ca3af",
                 font=("Segoe UI", 9)).grid(row=0, column=0, sticky="w")
        self._prm = tk.Text(prmf, height=4, bg="#252540", fg="#e2e8f0",
                             insertbackground="white", font=("Segoe UI", 10),
                             relief="flat", bd=4, wrap="word")
        self._prm.grid(row=1, column=0, sticky="ew")

        # action buttons
        af = tk.Frame(self._ai_frm, bg=C["ai_bg"], pady=2)
        af.grid(row=4, column=0, sticky="ew", padx=8)
        kw = dict(bg="#4c1d95", fg="white", relief="flat", cursor="hand2",
                   font=("Segoe UI", 9), padx=7, pady=3, activebackground="#5b21b6")
        tk.Button(af, text="Gonder", command=self._ai_gonder, **kw).pack(side="left", padx=2, pady=2)
        tk.Button(af, text="Devam Et", command=self._ai_devam, **kw).pack(side="left", padx=2, pady=2)
        tk.Button(af, text="Yeniden Yaz", command=self._ai_yeniden_yaz, **kw).pack(side="left", padx=2, pady=2)
        self._stop_btn = tk.Button(af, text="Dur", command=self._ai_dur,
                                    bg="#7f1d1d", fg="white", relief="flat", cursor="hand2",
                                    font=("Segoe UI", 9), padx=7, pady=3, state="disabled")
        self._stop_btn.pack(side="left", padx=2, pady=2)

        # response
        rf = tk.Frame(self._ai_frm, bg=C["ai_bg"])
        rf.grid(row=5, column=0, sticky="nsew", padx=8, pady=(4, 0))
        rf.columnconfigure(0, weight=1)
        rf.rowconfigure(1, weight=1)
        tk.Label(rf, text="Yanit:", bg=C["ai_bg"], fg="#9ca3af",
                 font=("Segoe UI", 9)).grid(row=0, column=0, sticky="w")
        self._resp = tk.Text(rf, bg="#0f172a", fg="#93c5fd",
                              font=("Consolas", 11), relief="flat", bd=4,
                              wrap="word", state="disabled")
        self._resp.grid(row=1, column=0, sticky="nsew")
        rscr = tk.Scrollbar(rf, orient="vertical", command=self._resp.yview)
        rscr.grid(row=1, column=1, sticky="ns")
        self._resp.config(yscrollcommand=rscr.set)

        tk.Button(self._ai_frm, text="Metne Ekle  (imleç konumuna)",
                  command=self._ai_ekle,
                  bg=C["green"], fg="white", relief="flat", cursor="hand2",
                  font=("Segoe UI", 9), pady=4
                  ).grid(row=6, column=0, sticky="ew", padx=8, pady=4)

    def _rebuild_cfg(self):
        for w in self._cfg.winfo_children():
            w.destroy()
        p = self._prov.get()
        lbl = dict(bg=C["ai_bg"], fg="#9ca3af", font=("Segoe UI", 9))
        ent = dict(bg="#252540", fg="white", insertbackground="white",
                   relief="flat", bd=4, font=("Segoe UI", 10))

        if p == "ollama":
            tk.Label(self._cfg, text="Ollama URL:", **lbl).pack(anchor="w", pady=(4, 0))
            self._ol_url = tk.StringVar(value=self.settings["ollama_url"])
            tk.Entry(self._cfg, textvariable=self._ol_url, **ent).pack(fill="x", pady=2)
            tk.Label(self._cfg, text="Model:", **lbl).pack(anchor="w")
            self._ol_mdl = tk.StringVar(value=self.settings["ollama_model"])
            tk.Entry(self._cfg, textvariable=self._ol_mdl, **ent).pack(fill="x", pady=2)
            tk.Button(self._cfg, text="Modelleri Getir", command=self._ollama_modeller,
                      bg="#1e3a5f", fg="white", relief="flat", cursor="hand2",
                      font=("Segoe UI", 8), pady=2).pack(anchor="w", pady=2)

        elif p == "anthropic":
            tk.Label(self._cfg, text="API Key:", **lbl).pack(anchor="w", pady=(4, 0))
            self._anth_key = tk.StringVar(value=self.settings["anthropic_key"])
            tk.Entry(self._cfg, textvariable=self._anth_key, show="*", **ent).pack(fill="x", pady=2)
            tk.Label(self._cfg, text="Model:", **lbl).pack(anchor="w")
            self._anth_mdl = tk.StringVar(value=self.settings["anthropic_model"])
            ttk.Combobox(self._cfg, textvariable=self._anth_mdl, state="readonly", width=28,
                          values=["claude-opus-4-7", "claude-sonnet-4-6", "claude-haiku-4-5-20251001"]
                          ).pack(anchor="w", pady=2)

        elif p == "openai":
            tk.Label(self._cfg, text="API Key:", **lbl).pack(anchor="w", pady=(4, 0))
            self._oai_key = tk.StringVar(value=self.settings["openai_key"])
            tk.Entry(self._cfg, textvariable=self._oai_key, show="*", **ent).pack(fill="x", pady=2)
            tk.Label(self._cfg, text="Model:", **lbl).pack(anchor="w")
            self._oai_mdl = tk.StringVar(value=self.settings["openai_model"])
            ttk.Combobox(self._cfg, textvariable=self._oai_mdl, state="readonly", width=28,
                          values=["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]
                          ).pack(anchor="w", pady=2)

        tk.Button(self._cfg, text="Ayarlari Kaydet", command=self._ayar_kaydet,
                  bg="#1e3a5f", fg="white", relief="flat", cursor="hand2",
                  font=("Segoe UI", 8), pady=2).pack(anchor="w", pady=(8, 2))

    # ------------------------------------------------------------- statusbar --

    def _build_statusbar(self):
        self._status = tk.StringVar(value="Hazir")
        tk.Label(self.root, textvariable=self._status,
                 bg=C["accent"], fg="white", anchor="w", padx=8, pady=3,
                 font=("Segoe UI", 9)).grid(row=2, column=0, columnspan=3, sticky="ew")

    # ------------------------------------------------------------------ tree --

    def _refresh_tree(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        rel = os.path.relpath(self.current_dir, NOTLAR_DIR)
        self._path_lbl.config(text="NOTLARIM" if rel == "." else f".../{rel}")
        self._up_btn.config(
            state="normal" if self.current_dir != NOTLAR_DIR else "disabled")
        if not os.path.exists(self.current_dir):
            return
        entries = sorted(os.scandir(self.current_dir),
                          key=lambda e: (not e.is_dir(), e.name.lower()))
        count = 0
        for e in entries:
            if e.name.startswith(".") or e.name == "secret.key":
                continue
            count += 1
            if e.is_dir():
                self.tree.insert("", tk.END, iid=e.path,
                                  text=f"  {e.name}/", tags=("dir",))
            else:
                pfx = "[enc] " if e.name.endswith(".enot") else "      "
                tag = "enot" if e.name.endswith(".enot") else "file"
                self.tree.insert("", tk.END, iid=e.path,
                                  text=pfx + e.name, tags=(tag,))
        self.tree.tag_configure("dir",  foreground=C["folder"])
        self.tree.tag_configure("enot", foreground=C["enc"])
        self.tree.tag_configure("file", foreground=C["txt"])
        self._status.set(f"{count} oge  |  Hazir")

    def _tree_sec(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        path = sel[0]
        if os.path.isfile(path):
            if self.is_modified and not self._kaydet_sor():
                return
            self._ac(path)

    def _tree_dbl(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        path = sel[0]
        if os.path.isdir(path):
            self.current_dir = path
            self._refresh_tree()

    def _geri(self):
        parent = os.path.normpath(os.path.dirname(self.current_dir))
        notlar = os.path.normpath(NOTLAR_DIR)
        rel = os.path.relpath(parent, notlar)
        self.current_dir = parent if not rel.startswith("..") else notlar
        self._refresh_tree()

    # ------------------------------------------------------------ file ops ---

    def _ac(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = f.read()
        except UnicodeDecodeError:
            with open(path, "r", encoding="cp1252") as f:
                raw = f.read()
        except Exception as e:
            messagebox.showerror("Hata", f"Okunamadi:\n{e}")
            return
        if path.endswith(".enot"):
            self._status.set("Sifre cozuluyor...")
            self.root.update_idletasks()
            dec = SifreCoz(raw)
            if dec is None:
                messagebox.showerror("Sifre Hatasi", "Dosya sifresini cozemedi.")
                self._status.set("Hata")
                return
            raw = dec
        self.text_area.delete("1.0", tk.END)
        self.text_area.insert("1.0", raw.lstrip("\n"))
        self.text_area.edit_modified(False)
        self.current_file = path
        self.is_modified = False
        name = os.path.basename(path)
        enc = "  [sifreli]" if path.endswith(".enot") else ""
        self._title_lbl.config(text=name + enc, fg=C["txt"])
        self._status.set(f"Acildi: {name}")

    def _kaydet(self):
        if self.current_file is None:
            self._yeni_dosya(save_current=True)
            return
        self._yaz(self.current_file)

    def _yaz(self, path):
        icerik = self.text_area.get("1.0", "end-1c")
        try:
            out = Sifrele(icerik) if path.endswith(".enot") else icerik
            with open(path, "w", encoding="utf-8") as f:
                f.write(out)
        except Exception as e:
            messagebox.showerror("Kayit Hatasi", f"Kaydedilemedi:\n{e}")
            return
        self.text_area.edit_modified(False)
        self.is_modified = False
        name = os.path.basename(path)
        enc = "  [sifreli]" if path.endswith(".enot") else ""
        self._title_lbl.config(text=name + enc, fg=C["txt"])
        self._status.set(f"Kaydedildi: {name}")

    def _yeni_dosya(self, save_current=False):
        if self.is_modified and not save_current and not self._kaydet_sor():
            return

        dlg = tk.Toplevel(self.root)
        dlg.title("Yeni Dosya")
        dlg.geometry("420x270")
        dlg.configure(bg=C["sidebar"])
        dlg.resizable(False, False)
        dlg.grab_set()

        tk.Label(dlg, text="Dosya adi:", bg=C["sidebar"], fg="#cccccc",
                 font=("Segoe UI", 10)).pack(pady=(16, 4), anchor="w", padx=20)
        name_ent = tk.Entry(dlg, font=("Segoe UI", 11), bg="#3c3c3c", fg="white",
                             insertbackground="white", relief="flat", bd=4)
        name_ent.pack(fill="x", padx=20)
        name_ent.insert(0, ".enot")
        name_ent.icursor(0)
        name_ent.focus_set()

        enc_var = tk.BooleanVar(value=True)

        def _toggle():
            b = os.path.splitext(name_ent.get())[0]
            name_ent.delete(0, tk.END)
            name_ent.insert(0, b + (".enot" if enc_var.get() else ".txt"))

        tk.Checkbutton(dlg, text="Sifreli kaydet (.enot)", variable=enc_var,
                       bg=C["sidebar"], fg="#cccccc", selectcolor="#3c3c3c",
                       activebackground=C["sidebar"], activeforeground="white",
                       command=_toggle).pack(pady=6, padx=20, anchor="w")

        # folder chooser row
        self._new_dir = self.current_dir
        frow = tk.Frame(dlg, bg=C["sidebar"])
        frow.pack(fill="x", padx=20, pady=4)
        tk.Label(frow, text="Klasor:", bg=C["sidebar"], fg="#9ca3af",
                 font=("Segoe UI", 9)).pack(side="left")
        rel = os.path.relpath(self._new_dir, NOTLAR_DIR)
        flbl = tk.Label(frow, text=rel if rel != "." else "(kok)",
                         bg=C["sidebar"], fg=C["folder"], font=("Segoe UI", 9))
        flbl.pack(side="left", padx=6)

        def _sec_dir():
            d = filedialog.askdirectory(initialdir=self._new_dir, parent=dlg)
            if d:
                self._new_dir = os.path.normpath(d)
                r = os.path.relpath(self._new_dir, NOTLAR_DIR)
                flbl.config(text=r if r != "." else "(kok)")

        tk.Button(frow, text="Degistir", command=_sec_dir,
                  bg="#1e3a5f", fg="white", relief="flat", cursor="hand2",
                  font=("Segoe UI", 8), padx=6, pady=2).pack(side="left")

        result = [None]

        def confirm():
            n = name_ent.get().strip()
            if not n:
                return
            if not os.path.splitext(n)[1]:
                n += ".enot" if enc_var.get() else ".txt"
            result[0] = n
            dlg.destroy()

        bf = tk.Frame(dlg, bg=C["sidebar"])
        bf.pack(pady=10)
        tk.Button(bf, text="Olustur", command=confirm,
                  bg="#0e639c", fg="white", relief="flat",
                  font=("Segoe UI", 9), padx=16, pady=4).pack(side="left", padx=6)
        tk.Button(bf, text="Iptal", command=dlg.destroy,
                  bg=C["btn"], fg="white", relief="flat",
                  font=("Segoe UI", 9), padx=16, pady=4).pack(side="left", padx=6)

        name_ent.bind("<Return>", lambda e: confirm())
        dlg.bind("<Escape>", lambda e: dlg.destroy())
        self.root.wait_window(dlg)

        if result[0] is None:
            return
        fpath = os.path.join(self._new_dir, result[0])
        if os.path.exists(fpath):
            messagebox.showwarning("Uyari", f"'{result[0]}' zaten mevcut!")
            return
        try:
            with open(fpath, "w", encoding="utf-8") as f:
                f.write("")
        except Exception as e:
            messagebox.showerror("Hata", f"Olusturulamadi:\n{e}")
            return
        self.current_file = fpath
        self.text_area.delete("1.0", tk.END)
        self.text_area.edit_modified(False)
        self.is_modified = False
        n = os.path.basename(fpath)
        enc = "  [sifreli]" if fpath.endswith(".enot") else ""
        self._title_lbl.config(text=n + enc, fg=C["txt"])
        self._status.set(f"Yeni dosya: {n}")
        self.current_dir = os.path.dirname(fpath)
        self._refresh_tree()

    def _yeni_klasor(self):
        dlg = tk.Toplevel(self.root)
        dlg.title("Yeni Klasor")
        dlg.geometry("340x150")
        dlg.configure(bg=C["sidebar"])
        dlg.resizable(False, False)
        dlg.grab_set()

        tk.Label(dlg, text="Klasor adi:", bg=C["sidebar"], fg="#cccccc",
                 font=("Segoe UI", 10)).pack(pady=(16, 4))
        ent = tk.Entry(dlg, font=("Segoe UI", 11), bg="#3c3c3c", fg="white",
                        insertbackground="white", relief="flat", bd=4)
        ent.pack(fill="x", padx=20)
        ent.focus_set()

        result = [None]

        def confirm():
            n = ent.get().strip()
            if n:
                result[0] = n
            dlg.destroy()

        bf = tk.Frame(dlg, bg=C["sidebar"])
        bf.pack(pady=12)
        tk.Button(bf, text="Olustur", command=confirm,
                  bg="#0e639c", fg="white", relief="flat",
                  font=("Segoe UI", 9), padx=16, pady=4).pack(side="left", padx=6)
        tk.Button(bf, text="Iptal", command=dlg.destroy,
                  bg=C["btn"], fg="white", relief="flat",
                  font=("Segoe UI", 9), padx=16, pady=4).pack(side="left", padx=6)

        ent.bind("<Return>", lambda e: confirm())
        dlg.bind("<Escape>", lambda e: dlg.destroy())
        self.root.wait_window(dlg)

        if result[0] is None:
            return
        nd = os.path.join(self.current_dir, result[0])
        try:
            os.makedirs(nd, exist_ok=True)
        except Exception as e:
            messagebox.showerror("Hata", f"Klasor olusturulamadi:\n{e}")
            return
        self._status.set(f"Klasor olusturuldu: {result[0]}")
        self._refresh_tree()

    def _sil(self):
        if self.current_file is None:
            messagebox.showinfo("Bilgi", "Once bir dosya secin.")
            return
        name = os.path.basename(self.current_file)
        if not messagebox.askyesno("Dosyayi Sil", f"'{name}' kalici olarak silinsin mi?"):
            return
        try:
            os.remove(self.current_file)
        except Exception as e:
            messagebox.showerror("Hata", f"Silinemedi:\n{e}")
            return
        self.current_file = None
        self.is_modified = False
        self.text_area.delete("1.0", tk.END)
        self.text_area.edit_modified(False)
        self._title_lbl.config(text="Bir dosya secin veya yeni olusturun", fg=C["dim"])
        self._status.set("Dosya silindi")
        self._refresh_tree()

    # ------------------------------------------------------------------- AI --

    def _toggle_ai(self):
        if self.ai_visible:
            self._ai_frm.grid_remove()
            self.root.columnconfigure(2, minsize=0, weight=0)
            self.ai_visible = False
        else:
            self._ai_frm.grid(row=1, column=2, sticky="nsew")
            self.root.columnconfigure(2, minsize=340, weight=0)
            self.ai_visible = True

    def _ayar_kaydet(self):
        p = self._prov.get()
        self.settings["ai_provider"] = p
        if p == "ollama":
            self.settings["ollama_url"] = self._ol_url.get()
            self.settings["ollama_model"] = self._ol_mdl.get()
        elif p == "anthropic":
            self.settings["anthropic_key"] = self._anth_key.get()
            self.settings["anthropic_model"] = self._anth_mdl.get()
        elif p == "openai":
            self.settings["openai_key"] = self._oai_key.get()
            self.settings["openai_model"] = self._oai_mdl.get()
        try:
            _save_settings(self.settings)
            self._status.set("Ayarlar kaydedildi")
        except Exception as e:
            messagebox.showerror("Hata", f"Kaydedilemedi:\n{e}")

    def _ollama_modeller(self):
        import urllib.request, json as _j
        url = self._ol_url.get().rstrip("/") + "/api/tags"
        try:
            with urllib.request.urlopen(url, timeout=5) as r:
                data = _j.loads(r.read())
            models = [m["name"] for m in data.get("models", [])]
        except Exception as e:
            messagebox.showerror("Baglanti", f"Ollama'ya baglanilamadi:\n{e}")
            return
        if not models:
            messagebox.showinfo("Ollama", "Yuklu model bulunamadi.")
            return
        win = tk.Toplevel(self.root)
        win.title("Ollama Modelleri")
        win.geometry("280x280")
        win.configure(bg=C["sidebar"])
        win.grab_set()
        lb = tk.Listbox(win, bg=C["bg"], fg=C["txt"], relief="flat",
                         font=("Segoe UI", 10), selectbackground=C["sel"])
        lb.pack(fill="both", expand=True, padx=8, pady=8)
        for m in models:
            lb.insert(tk.END, m)

        def use():
            sel = lb.curselection()
            if sel:
                self._ol_mdl.set(lb.get(sel[0]))
            win.destroy()

        tk.Button(win, text="Kullan", command=use,
                  bg="#0e639c", fg="white", relief="flat",
                  font=("Segoe UI", 9), pady=4).pack(fill="x", padx=8, pady=(0, 8))

    def _context(self):
        try:
            return self.text_area.get(tk.SEL_FIRST, tk.SEL_LAST)
        except tk.TclError:
            return self.text_area.get("1.0", "end-1c")

    def _ai_gonder(self):
        prmpt = self._prm.get("1.0", "end-1c").strip()
        if not prmpt:
            messagebox.showinfo("Bilgi", "Lutfen bir istek girin.")
            return
        ctx = self._context()
        full = f"{prmpt}\n\n---\nMetin:\n{ctx}" if ctx.strip() else prmpt
        self._run(full)

    def _ai_devam(self):
        ctx = self.text_area.get("1.0", "end-1c")
        if not ctx.strip():
            messagebox.showinfo("Bilgi", "Devam ettirilecek metin yok.")
            return
        extra = self._prm.get("1.0", "end-1c").strip()
        p = f"Su metni devam ettir. Sadece devam eden kismi yaz, onceki metni tekrar etme:\n\n{ctx}"
        if extra:
            p += f"\n\nEk yon: {extra}"
        self._run(p)

    def _ai_yeniden_yaz(self):
        ctx = self._context()
        if not ctx.strip():
            messagebox.showinfo("Bilgi", "Yeniden yazilacak metin yok.")
            return
        extra = self._prm.get("1.0", "end-1c").strip()
        p = f"Su metni daha iyi hale getirerek yeniden yaz:\n\n{ctx}"
        if extra:
            p += f"\n\nYon: {extra}"
        self._run(p)

    def _run(self, prompt):
        if self._ai_running:
            return
        self._ai_running = True
        self._ai_stop.clear()
        self._stop_btn.config(state="normal")
        self._status.set("AI calisiyor...")
        self._resp.config(state="normal")
        self._resp.delete("1.0", tk.END)
        self._resp.config(state="disabled")
        threading.Thread(target=self._ai_thread, args=(self._prov.get(), prompt),
                          daemon=True).start()

    def _ai_thread(self, provider, prompt):
        try:
            {"ollama": self._stream_ollama,
             "anthropic": self._stream_anthropic,
             "openai": self._stream_openai}[provider](prompt)
        except Exception as e:
            self._ai_q.put(("err", str(e)))
        finally:
            self._ai_q.put(("done", None))

    def _stream_ollama(self, prompt):
        import urllib.request, json as _j
        url = self._ol_url.get().rstrip("/") + "/api/generate"
        body = _j.dumps({"model": self._ol_mdl.get(),
                          "prompt": prompt, "stream": True}).encode()
        req = urllib.request.Request(url, data=body,
                                      headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            buf = b""
            while not self._ai_stop.is_set():
                chunk = resp.read(512)
                if not chunk:
                    break
                buf += chunk
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    if line.strip():
                        try:
                            tok = _j.loads(line).get("response", "")
                            if tok:
                                self._ai_q.put(("tok", tok))
                        except Exception:
                            pass

    def _stream_anthropic(self, prompt):
        try:
            import anthropic
        except ImportError:
            raise RuntimeError("anthropic paketi yuklu degil.\n\npip install anthropic")
        key = self._anth_key.get().strip()
        if not key:
            raise RuntimeError("Anthropic API key girilmemis.")
        client = anthropic.Anthropic(api_key=key)
        with client.messages.stream(
            model=self._anth_mdl.get(), max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            for tok in stream.text_stream:
                if self._ai_stop.is_set():
                    break
                self._ai_q.put(("tok", tok))

    def _stream_openai(self, prompt):
        try:
            from openai import OpenAI
        except ImportError:
            raise RuntimeError("openai paketi yuklu degil.\n\npip install openai")
        key = self._oai_key.get().strip()
        if not key:
            raise RuntimeError("OpenAI API key girilmemis.")
        client = OpenAI(api_key=key)
        for chunk in client.chat.completions.create(
            model=self._oai_mdl.get(), stream=True,
            messages=[{"role": "user", "content": prompt}],
        ):
            if self._ai_stop.is_set():
                break
            delta = chunk.choices[0].delta
            if delta.content:
                self._ai_q.put(("tok", delta.content))

    def _ai_dur(self):
        self._ai_stop.set()

    def _poll_q(self):
        try:
            while True:
                kind, data = self._ai_q.get_nowait()
                if kind == "tok":
                    self._resp.config(state="normal")
                    self._resp.insert(tk.END, data)
                    self._resp.see(tk.END)
                    self._resp.config(state="disabled")
                elif kind == "err":
                    messagebox.showerror("AI Hatasi", data)
                    self._ai_done()
                elif kind == "done":
                    self._ai_done()
        except _queue.Empty:
            pass
        self.root.after(50, self._poll_q)

    def _ai_done(self):
        self._ai_running = False
        self._stop_btn.config(state="disabled")
        self._status.set("AI tamamlandi")

    def _ai_ekle(self):
        text = self._resp.get("1.0", "end-1c")
        if not text.strip():
            return
        self.text_area.insert(tk.INSERT, "\n" + text)
        self.text_area.see(tk.INSERT)
        self._status.set("AI yaniti metne eklendi")

    # --------------------------------------------------------------- helpers --

    def _kaydet_sor(self):
        ans = messagebox.askyesnocancel(
            "Kaydedilmemis Degisiklikler",
            "Degisiklikler kaydedilmedi.\nKaydetmek ister misiniz?",
        )
        if ans is None:
            return False
        if ans:
            self._kaydet()
        return True

    def _on_modified(self, event=None):
        if self.text_area.edit_modified():
            self.is_modified = True
            if self.current_file:
                name = os.path.basename(self.current_file)
                enc = "  [sifreli]" if self.current_file.endswith(".enot") else ""
                self._title_lbl.config(text="* " + name + enc, fg=C["txt"])

    def _kapat(self):
        if self.is_modified and not self._kaydet_sor():
            return
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    EnotGUI(root)
    root.mainloop()
