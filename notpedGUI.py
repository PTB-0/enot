# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os, sys, json, threading, queue as _queue, urllib.request, re, io, base64

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sifrele import AnahtarOlustur, Sifrele, SifreCoz

_DEFAULT_DIR = r"C:\Users\USER\Desktop\notlar"

if getattr(sys, "frozen", False):
    _APP_DIR = os.path.dirname(sys.executable)
else:
    _APP_DIR = os.path.dirname(os.path.abspath(__file__))

SETTINGS_FILE = os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")), "enot", "settings.json"
)

_DEF = {
    "ai_provider": "ollama",
    "ollama_url": "http://localhost:11434",
    "ollama_model": "llama3.2",
    "anthropic_key": "",
    "anthropic_model": "claude-sonnet-4-6",
    "openai_key": "",
    "openai_model": "gpt-4o-mini",
    "notes_dir": _DEFAULT_DIR,
}

C = {
    "bg": "#1e1e1e", "sidebar": "#252526", "toolbar": "#2d2d30",
    "btn": "#3e3e42", "sel": "#094771", "accent": "#007acc",
    "ai_bg": "#1a1a2e", "ai_hdr": "#16213e", "ai_acc": "#7c3aed",
    "txt": "#d4d4d4", "dim": "#858585", "folder": "#fbbf24",
    "enc": "#60a5fa", "green": "#065f46",
}

_IMG_PAT = re.compile(
    r'https?://[^\s<>"\']+\.(?:png|jpe?g|gif|webp|bmp)(?:\?[^\s]*)?',
    re.IGNORECASE,
)


def _load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return {**_DEF, **json.load(f)}
        except Exception:
            pass
    return _DEF.copy()


def _save_settings(s):
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(s, f, indent=2, ensure_ascii=False)


class EnotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("enot")
        self.root.geometry("1200x700")
        self.root.minsize(800, 500)
        self.root.configure(bg=C["bg"])

        self.settings = _load_settings()
        self.notes_dir = self.settings.get("notes_dir", _DEFAULT_DIR)
        self.current_dir = self.notes_dir
        self.ai_visible = False
        self._ai_running = False
        self._ai_stop = threading.Event()
        self._ai_q = _queue.Queue()

        # frm -> {"file": str|None, "modified": bool, "text": Text, "images": list}
        self._tabs = {}

        os.makedirs(self.notes_dir, exist_ok=True)
        AnahtarOlustur()

        self._setup_grid()
        self._build_toolbar()
        self._build_sidebar()
        self._build_notebook()
        self._build_ai_panel()
        self._build_statusbar()

        self._refresh_tree()
        self._new_tab()

        self.root.bind("<Control-s>", lambda e: self._kaydet())
        self.root.bind("<Control-n>", lambda e: self._yeni_dosya())
        self.root.bind("<Control-w>", lambda e: self._kapat_sekme())
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
        s.configure("TNotebook", background=C["toolbar"], borderwidth=0)
        s.configure("TNotebook.Tab", background=C["btn"], foreground=C["txt"],
                    padding=[10, 4], font=("Segoe UI", 9))
        s.map("TNotebook.Tab",
               background=[("selected", C["bg"])],
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
        btn("Kapat Sekme  Ctrl+W", self._kapat_sekme)
        btn("Yenile", self._refresh_tree)
        self._ai_btn = btn("  AI Asistan  ", self._toggle_ai,
                            bg=C["ai_acc"], fg="white", side="right")

    # --------------------------------------------------------------- sidebar --

    def _build_sidebar(self):
        sb = tk.Frame(self.root, bg=C["sidebar"], width=240)
        sb.grid(row=1, column=0, sticky="nsew")
        sb.grid_propagate(False)
        sb.rowconfigure(3, weight=1)
        sb.columnconfigure(0, weight=1)

        hdr = tk.Frame(sb, bg=C["sidebar"])
        hdr.grid(row=0, column=0, columnspan=2, sticky="ew")
        hdr.columnconfigure(0, weight=1)
        self._path_lbl = tk.Label(hdr, text="NOTLARIM", bg=C["sidebar"],
                                   fg=C["dim"], font=("Segoe UI", 9, "bold"),
                                   anchor="w", padx=8, pady=4)
        self._path_lbl.grid(row=0, column=0, sticky="ew")
        tk.Button(hdr, text="Yol Degistir", command=self._degistir_yol,
                  bg=C["sidebar"], fg=C["accent"], relief="flat",
                  font=("Segoe UI", 7, "bold"), padx=4, pady=2,
                  cursor="hand2", activebackground=C["btn"],
                  activeforeground=C["accent"]).grid(row=0, column=1, padx=(0, 4))

        self._dir_lbl = tk.Label(sb, text=self._short_dir(self.notes_dir),
                                  bg=C["sidebar"], fg=C["dim"],
                                  font=("Segoe UI", 7), anchor="w", padx=8, pady=2)
        self._dir_lbl.grid(row=1, column=0, columnspan=2, sticky="ew")

        self._up_btn = tk.Button(sb, text="^ Yukari", command=self._geri,
                                  bg=C["sidebar"], fg=C["dim"], relief="flat",
                                  font=("Segoe UI", 8), pady=2, cursor="hand2",
                                  state="disabled")
        self._up_btn.grid(row=2, column=0, columnspan=2, sticky="ew", padx=4)

        self.tree = ttk.Treeview(sb, show="tree", style="T.Treeview",
                                  selectmode="browse")
        self.tree.grid(row=3, column=0, sticky="nsew", pady=(4, 0))
        self.tree.bind("<<TreeviewSelect>>", self._tree_sec)
        self.tree.bind("<Double-Button-1>", self._tree_dbl)

        scr = tk.Scrollbar(sb, orient="vertical", command=self.tree.yview)
        scr.grid(row=3, column=1, sticky="ns")
        self.tree.config(yscrollcommand=scr.set)

    def _short_dir(self, path):
        home = os.path.expanduser("~")
        short = ("~" + path[len(home):]) if path.lower().startswith(home.lower()) else path
        return short[:36] + "..." if len(short) > 39 else short

    def _degistir_yol(self):
        d = filedialog.askdirectory(initialdir=self.notes_dir, parent=self.root,
                                     title="Notlar Klasorunu Sec")
        if not d:
            return
        d = os.path.normpath(d)
        self.notes_dir = d
        self.current_dir = d
        self.settings["notes_dir"] = d
        try:
            _save_settings(self.settings)
        except Exception as e:
            messagebox.showerror("Hata", f"Ayarlar kaydedilemedi:\n{e}")
            return
        os.makedirs(d, exist_ok=True)
        self._dir_lbl.config(text=self._short_dir(d))
        self._refresh_tree()
        self._status.set(f"Notlar klasoru: {d}")

    # ------------------------------------------------------------ notebook ---

    def _build_notebook(self):
        ed = tk.Frame(self.root, bg=C["bg"])
        ed.grid(row=1, column=1, sticky="nsew")
        ed.columnconfigure(0, weight=1)
        ed.rowconfigure(0, weight=1)
        self.notebook = ttk.Notebook(ed)
        self.notebook.grid(row=0, column=0, sticky="nsew")
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

    def _new_tab(self, file=None, content=""):
        frm = tk.Frame(self.notebook, bg=C["bg"])
        frm.columnconfigure(0, weight=1)
        frm.rowconfigure(0, weight=1)

        txt = tk.Text(frm, bg=C["bg"], fg=C["txt"],
                       insertbackground="#aeafad",
                       font=("Consolas", 12), relief="flat", bd=0,
                       padx=16, pady=8, wrap="word", undo=True,
                       selectbackground="#264f78")
        txt.grid(row=0, column=0, sticky="nsew")
        scr = tk.Scrollbar(frm, orient="vertical", command=txt.yview)
        scr.grid(row=0, column=1, sticky="ns")
        txt.config(yscrollcommand=scr.set)

        st = {"file": file, "modified": False, "text": txt, "images": []}
        self._tabs[frm] = st

        label = os.path.basename(file) if file else "Yeni Not"
        self.notebook.add(frm, text=f"  {label}  ")
        self.notebook.select(frm)

        if content:
            txt.insert("1.0", content)
            txt.edit_modified(False)

        txt.bind("<<Modified>>", lambda e, f=frm: self._on_tab_modified(f))
        txt.bind("<<Paste>>", lambda e, f=frm: self.root.after(10, lambda: self._on_paste(f)))
        return frm

    def _active_tab(self):
        try:
            name = self.notebook.select()
            if not name:
                return None
            for frm in self._tabs:
                if str(frm) == name:
                    return frm
        except Exception:
            pass
        return None

    def _active_state(self):
        frm = self._active_tab()
        return self._tabs.get(frm) if frm else None

    def _on_tab_changed(self, event=None):
        st = self._active_state()
        if st:
            f = st["file"]
            name = os.path.basename(f) if f else "Yeni Not"
            enc = "  [sifreli]" if f and f.endswith(".enot") else ""
            pfx = "* " if st["modified"] else ""
            self._status.set(f"Sekme: {pfx}{name}{enc}")

    def _on_tab_modified(self, frm):
        st = self._tabs.get(frm)
        if st and st["text"].edit_modified():
            st["modified"] = True
            self._update_tab_label(frm)

    def _update_tab_label(self, frm):
        st = self._tabs.get(frm)
        if not st:
            return
        f = st["file"]
        name = os.path.basename(f) if f else "Yeni Not"
        pfx = "* " if st["modified"] else ""
        try:
            self.notebook.tab(frm, text=f"  {pfx}{name}  ")
        except Exception:
            pass

    def _kapat_sekme(self):
        frm = self._active_tab()
        if frm is None:
            return
        st = self._tabs[frm]
        if st["modified"]:
            ans = messagebox.askyesnocancel(
                "Kaydedilmemis Degisiklikler",
                "Kapatmadan once kaydetmek ister misiniz?")
            if ans is None:
                return
            if ans:
                self._kaydet()
        self.notebook.forget(frm)
        del self._tabs[frm]
        frm.destroy()
        if not self._tabs:
            self._new_tab()

    # ---------------------------------------------------------------- tree ---

    def _refresh_tree(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        try:
            rel = os.path.relpath(self.current_dir, self.notes_dir)
        except ValueError:
            rel = self.current_dir
        self._path_lbl.config(text="NOTLARIM" if rel == "." else f".../{rel}")
        self._up_btn.config(
            state="normal" if os.path.normpath(self.current_dir) != os.path.normpath(self.notes_dir) else "disabled")
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
        if not os.path.isfile(path):
            return
        for frm, st in self._tabs.items():
            if st["file"] == path:
                self.notebook.select(frm)
                return
        frm = self._active_tab()
        st = self._tabs.get(frm)
        if st and st["file"] is None and not st["modified"]:
            self._ac_in_tab(frm, path)
        else:
            frm = self._new_tab()
            self._ac_in_tab(frm, path)

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
        notes = os.path.normpath(self.notes_dir)
        try:
            rel = os.path.relpath(parent, notes)
            self.current_dir = parent if not rel.startswith("..") else notes
        except ValueError:
            self.current_dir = notes
        self._refresh_tree()

    # ------------------------------------------------------------ file ops ---

    def _ac_in_tab(self, frm, path):
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
        st = self._tabs[frm]
        txt = st["text"]
        txt.delete("1.0", tk.END)
        txt.insert("1.0", raw.lstrip("\n"))
        txt.edit_modified(False)
        st["file"] = path
        st["modified"] = False
        self._update_tab_label(frm)
        name = os.path.basename(path)
        enc = "  [sifreli]" if path.endswith(".enot") else ""
        self._status.set(f"Acildi: {name}{enc}")

    def _kaydet(self):
        frm = self._active_tab()
        if frm is None:
            return
        st = self._tabs[frm]
        if st["file"] is None:
            self._yeni_dosya(save_current=True)
            return
        self._yaz(frm, st["file"])

    def _yaz(self, frm, path):
        st = self._tabs[frm]
        icerik = st["text"].get("1.0", "end-1c")
        try:
            out = Sifrele(icerik) if path.endswith(".enot") else icerik
            with open(path, "w", encoding="utf-8") as f:
                f.write(out)
        except Exception as e:
            messagebox.showerror("Kayit Hatasi", f"Kaydedilemedi:\n{e}")
            return
        st["text"].edit_modified(False)
        st["modified"] = False
        self._update_tab_label(frm)
        name = os.path.basename(path)
        enc = "  [sifreli]" if path.endswith(".enot") else ""
        self._status.set(f"Kaydedildi: {name}{enc}")

    def _yeni_dosya(self, save_current=False):
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

        self._new_dir = self.current_dir
        frow = tk.Frame(dlg, bg=C["sidebar"])
        frow.pack(fill="x", padx=20, pady=4)
        tk.Label(frow, text="Klasor:", bg=C["sidebar"], fg="#9ca3af",
                 font=("Segoe UI", 9)).pack(side="left")
        try:
            rel = os.path.relpath(self._new_dir, self.notes_dir)
        except ValueError:
            rel = self._new_dir
        flbl = tk.Label(frow, text=rel if rel != "." else "(kok)",
                         bg=C["sidebar"], fg=C["folder"], font=("Segoe UI", 9))
        flbl.pack(side="left", padx=6)

        def _sec_dir():
            d = filedialog.askdirectory(initialdir=self._new_dir, parent=dlg)
            if d:
                self._new_dir = os.path.normpath(d)
                try:
                    r = os.path.relpath(self._new_dir, self.notes_dir)
                except ValueError:
                    r = self._new_dir
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

        frm = self._active_tab()
        st = self._tabs.get(frm)
        if st and st["file"] is None and not st["modified"]:
            st["file"] = fpath
            st["modified"] = False
            self._update_tab_label(frm)
        else:
            self._new_tab(file=fpath)

        n = os.path.basename(fpath)
        enc = "  [sifreli]" if fpath.endswith(".enot") else ""
        self._status.set(f"Yeni dosya: {n}{enc}")
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
        frm = self._active_tab()
        st = self._tabs.get(frm)
        if not st or st["file"] is None:
            messagebox.showinfo("Bilgi", "Once bir dosya secin.")
            return
        name = os.path.basename(st["file"])
        if not messagebox.askyesno("Dosyayi Sil", f"'{name}' kalici olarak silinsin mi?"):
            return
        try:
            os.remove(st["file"])
        except Exception as e:
            messagebox.showerror("Hata", f"Silinemedi:\n{e}")
            return
        self.notebook.forget(frm)
        del self._tabs[frm]
        frm.destroy()
        if not self._tabs:
            self._new_tab()
        self._status.set(f"Silindi: {name}")
        self._refresh_tree()

    # --------------------------------------------------------- image paste ---

    def _on_paste(self, frm):
        try:
            clip = self.root.clipboard_get()
        except Exception:
            return
        urls = _IMG_PAT.findall(clip.strip())
        if not urls:
            return
        for url in urls[:3]:
            self._status.set(f"Gorsel yukleniyor...")
            threading.Thread(target=self._fetch_and_embed,
                              args=(frm, url), daemon=True).start()

    def _fetch_and_embed(self, frm, url):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                data = r.read()
            photo = self._make_photo(data)
            if photo:
                self._ai_q.put(("img", (frm, url, photo)))
            else:
                self._ai_q.put(("img_err", f"Desteklenmeyen format"))
        except Exception as e:
            self._ai_q.put(("img_err", str(e)))

    def _make_photo(self, data):
        try:
            from PIL import Image, ImageTk
            img = Image.open(io.BytesIO(data))
            img.thumbnail((500, 400))
            return ImageTk.PhotoImage(img)
        except ImportError:
            pass
        try:
            b64 = base64.b64encode(data).decode()
            return tk.PhotoImage(data=b64)
        except Exception:
            return None

    def _embed_image(self, frm, url, photo):
        st = self._tabs.get(frm)
        if not st:
            return
        txt = st["text"]
        st["images"].append(photo)
        pos = txt.search(url, "1.0", stopindex=tk.END)
        if pos:
            txt.delete(pos, f"{pos}+{len(url)}c")
            txt.image_create(pos, image=photo, padx=4, pady=4)
        else:
            txt.insert(tk.END, "\n")
            txt.image_create(tk.END, image=photo, padx=4, pady=4)
        self._status.set("Gorsel yuklendi")

    # ------------------------------------------------------------- AI panel --

    def _build_ai_panel(self):
        self._ai_frm = tk.Frame(self.root, bg=C["ai_bg"], width=340)
        self._ai_frm.grid_propagate(False)
        self._ai_frm.rowconfigure(5, weight=1)
        self._ai_frm.columnconfigure(0, weight=1)

        hdr = tk.Frame(self._ai_frm, bg=C["ai_hdr"], pady=6)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.columnconfigure(0, weight=1)
        tk.Label(hdr, text="AI Asistan", bg=C["ai_hdr"], fg="#a78bfa",
                 font=("Segoe UI", 11, "bold"), anchor="w", padx=12).grid(row=0, column=0, sticky="w")
        tk.Button(hdr, text="x", command=self._toggle_ai,
                  bg=C["ai_hdr"], fg=C["dim"], relief="flat", cursor="hand2",
                  font=("Segoe UI", 10)).grid(row=0, column=1, padx=8)

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

        self._cfg = tk.Frame(self._ai_frm, bg=C["ai_bg"])
        self._cfg.grid(row=2, column=0, sticky="ew", padx=8)
        self._rebuild_cfg()

        prmf = tk.Frame(self._ai_frm, bg=C["ai_bg"], pady=4)
        prmf.grid(row=3, column=0, sticky="ew", padx=8)
        prmf.columnconfigure(0, weight=1)
        tk.Label(prmf, text="Istek / Prompt:", bg=C["ai_bg"], fg="#9ca3af",
                 font=("Segoe UI", 9)).grid(row=0, column=0, sticky="w")
        self._prm = tk.Text(prmf, height=4, bg="#252540", fg="#e2e8f0",
                             insertbackground="white", font=("Segoe UI", 10),
                             relief="flat", bd=4, wrap="word")
        self._prm.grid(row=1, column=0, sticky="ew")

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
                  font=("Segoe UI", 9), pady=4,
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
                          values=["claude-opus-4-7", "claude-sonnet-4-6", "claude-haiku-4-5-20251001"],
                          ).pack(anchor="w", pady=2)

        elif p == "openai":
            tk.Label(self._cfg, text="API Key:", **lbl).pack(anchor="w", pady=(4, 0))
            self._oai_key = tk.StringVar(value=self.settings["openai_key"])
            tk.Entry(self._cfg, textvariable=self._oai_key, show="*", **ent).pack(fill="x", pady=2)
            tk.Label(self._cfg, text="Model:", **lbl).pack(anchor="w")
            self._oai_mdl = tk.StringVar(value=self.settings["openai_model"])
            ttk.Combobox(self._cfg, textvariable=self._oai_mdl, state="readonly", width=28,
                          values=["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
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
        import json as _j
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
        st = self._active_state()
        if not st:
            return ""
        txt = st["text"]
        try:
            return txt.get(tk.SEL_FIRST, tk.SEL_LAST)
        except tk.TclError:
            return txt.get("1.0", "end-1c")

    def _ai_gonder(self):
        prmpt = self._prm.get("1.0", "end-1c").strip()
        if not prmpt:
            messagebox.showinfo("Bilgi", "Lutfen bir istek girin.")
            return
        ctx = self._context()
        full = f"{prmpt}\n\n---\nMetin:\n{ctx}" if ctx.strip() else prmpt
        self._run(full)

    def _ai_devam(self):
        st = self._active_state()
        ctx = st["text"].get("1.0", "end-1c") if st else ""
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
        import json as _j
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
                elif kind == "img":
                    frm, url, photo = data
                    self._embed_image(frm, url, photo)
                elif kind == "img_err":
                    self._status.set(f"Gorsel yuklenemedi: {data[:60]}")
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
        st = self._active_state()
        if st:
            st["text"].insert(tk.INSERT, "\n" + text)
            st["text"].see(tk.INSERT)
        self._status.set("AI yaniti metne eklendi")

    # --------------------------------------------------------------- helpers --

    def _kapat(self):
        modified = [st for st in self._tabs.values() if st["modified"]]
        if modified:
            ans = messagebox.askyesnocancel(
                "Kaydedilmemis Degisiklikler",
                f"{len(modified)} sekme kaydedilmedi.\nKaydetmek ister misiniz?")
            if ans is None:
                return
            if ans:
                for frm, st in list(self._tabs.items()):
                    if st["modified"] and st["file"]:
                        self._yaz(frm, st["file"])
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    EnotGUI(root)
    root.mainloop()
