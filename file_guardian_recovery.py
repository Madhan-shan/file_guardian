"""
FILE GUARDIAN — Recovery Mode
==============================
Simple UI with folder selector + Decrypt button.
Use this to recover all test-encrypted files.
Password: Cybermad@143
"""

import os, sys, base64, hashlib, threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "cryptography"])
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes

# ── Password hash ──────────────────────────────────────────────────────────────
_PASSWORD_HASH = "81470fef81d17f6d65347996dbe3a5e7611f32fc55cf9b7944810fa77dac63f5"

# ── Constants ──────────────────────────────────────────────────────────────────
ENCRYPTED_EXT = ".guardian"
SALT_FILENAME = ".guardian_salt"

SKIP_DIRS = {
    "windows", "program files", "program files (x86)", "programdata",
    "$recycle.bin", "system volume information", "appdata", "boot",
    "recovery", "perflogs", "__pycache__", ".git"
}

# ── Crypto ─────────────────────────────────────────────────────────────────────
def _get_salt(folder):
    salt_path = os.path.join(folder, SALT_FILENAME)
    if os.path.exists(salt_path):
        with open(salt_path, "rb") as f:
            return f.read()
    return None

def _derive_key(salt):
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32,
                     salt=salt, iterations=390_000)
    return base64.urlsafe_b64encode(kdf.derive(_PASSWORD_HASH.encode()))

def _collect_encrypted(folder):
    for dirpath, dirs, files in os.walk(folder, topdown=True):
        dirs[:] = [d for d in dirs if d.lower() not in SKIP_DIRS]
        for fname in files:
            if fname.endswith(ENCRYPTED_EXT):
                yield os.path.join(dirpath, fname)

def decrypt_file(fpath, fernet):
    try:
        with open(fpath, "rb") as f:
            data = f.read()
        decrypted = fernet.decrypt(data)
        out = fpath[: -len(ENCRYPTED_EXT)]
        with open(out, "wb") as f:
            f.write(decrypted)
        os.remove(fpath)
        return True
    except Exception:
        return False

# ── Find all guardian_salt folders under a root ───────────────────────────────
def find_salt_folders(root):
    """Walk root and find every folder that contains a .guardian_salt file."""
    found = []
    for dirpath, dirs, files in os.walk(root, topdown=True):
        dirs[:] = [d for d in dirs if d.lower() not in SKIP_DIRS]
        if SALT_FILENAME in files:
            found.append(dirpath)
    return found

# ── GUI ────────────────────────────────────────────────────────────────────────
class RecoveryApp:
    BG      = "#0a0e1a"
    SURFACE = "#111827"
    CARD    = "#1a2235"
    ACCENT  = "#00e5b0"
    BLUE    = "#0077ff"
    TEXT    = "#f0f4ff"
    MUTED   = "#6b7a99"
    BORDER  = "#1e2d45"
    DANGER  = "#ff4d6d"

    def __init__(self, root):
        self.root = root
        self.root.title("File Guardian — Recovery Mode")
        self.root.configure(bg=self.BG)
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.root.destroy)
        self._center(520, 500)
        self._build_ui()

    def _center(self, w, h):
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    def _build_ui(self):
        tk.Frame(self.root, bg=self.BLUE, height=3).pack(fill="x")

        # Header
        hdr = tk.Frame(self.root, bg=self.SURFACE, pady=16)
        hdr.pack(fill="x")
        tk.Label(hdr, text="🔓", font=("Segoe UI Emoji", 38),
                 bg=self.SURFACE).pack()
        tk.Label(hdr, text="F I L E   G U A R D I A N",
                 font=("Consolas", 16, "bold"),
                 bg=self.SURFACE, fg=self.TEXT).pack(pady=(4, 2))
        tk.Label(hdr, text="Recovery Mode — Decrypt Your Files",
                 font=("Segoe UI", 9), bg=self.SURFACE, fg=self.MUTED).pack()

        body = tk.Frame(self.root, bg=self.BG, padx=28, pady=16)
        body.pack(fill="both", expand=True)

        # ── Folder selector ──
        tk.Label(body, text="📁  SELECT FOLDER TO DECRYPT",
                 bg=self.BG, fg=self.MUTED,
                 font=("Consolas", 8, "bold"), anchor="w").pack(fill="x")

        folder_card = tk.Frame(body, bg=self.CARD, padx=12, pady=10)
        folder_card.pack(fill="x", pady=(4, 12))

        row = tk.Frame(folder_card, bg=self.CARD)
        row.pack(fill="x")
        self.folder_var = tk.StringVar(value=os.path.expanduser("~\\Documents"))
        tk.Entry(row, textvariable=self.folder_var,
                 bg="#0d1526", fg=self.TEXT,
                 insertbackground=self.ACCENT,
                 relief="flat", font=("Consolas", 9),
                 bd=0, highlightthickness=1,
                 highlightbackground=self.BORDER,
                 highlightcolor=self.ACCENT).pack(side="left", fill="x",
                                                   expand=True, ipady=7, ipadx=6)
        tk.Button(row, text="Browse", command=self._browse,
                  bg=self.BLUE, fg=self.TEXT,
                  font=("Segoe UI", 9, "bold"),
                  relief="flat", padx=12, pady=6,
                  cursor="hand2").pack(side="left", padx=(8, 0))

        tk.Label(folder_card,
                 text="💡  Tip: Select a parent folder — it will scan ALL subfolders automatically",
                 bg=self.CARD, fg=self.MUTED,
                 font=("Segoe UI", 8), anchor="w").pack(fill="x", pady=(6, 0))

        # ── Status ──
        tk.Label(body, text="⚡  STATUS",
                 bg=self.BG, fg=self.MUTED,
                 font=("Consolas", 8, "bold"), anchor="w").pack(fill="x")

        status_card = tk.Frame(body, bg=self.CARD, padx=12, pady=10)
        status_card.pack(fill="x", pady=(4, 12))

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("R.Horizontal.TProgressbar",
                        troughcolor="#0d1526", background=self.BLUE,
                        thickness=8, bordercolor="#0d1526",
                        lightcolor=self.BLUE, darkcolor=self.BLUE)
        self.progress = ttk.Progressbar(status_card, mode="indeterminate",
                                        style="R.Horizontal.TProgressbar")
        self.progress.pack(fill="x", pady=(0, 6))

        self.status_var = tk.StringVar(value="Ready — select a folder and click Decrypt.")
        tk.Label(status_card, textvariable=self.status_var,
                 bg=self.CARD, fg=self.ACCENT,
                 font=("Consolas", 8), wraplength=440,
                 justify="left", anchor="w").pack(fill="x")

        # ── Divider ──
        tk.Frame(body, bg=self.BORDER, height=1).pack(fill="x", pady=(4, 12))

        # ── DECRYPT button ──
        tk.Button(body,
                  text="🔓   DECRYPT — RESTORE ALL FILES",
                  command=self._start_decrypt,
                  bg=self.BLUE, fg=self.TEXT,
                  font=("Segoe UI", 12, "bold"),
                  relief="flat", pady=14,
                  cursor="hand2", bd=0,
                  activebackground="#0055cc",
                  activeforeground=self.TEXT).pack(fill="x")

        tk.Frame(self.root, bg=self.BORDER, height=1).pack(fill="x")
        tk.Label(self.root,
                 text="AES-128 · PBKDF2-SHA256 · Scans all subfolders automatically",
                 bg=self.BG, fg=self.BORDER,
                 font=("Consolas", 7)).pack(pady=8)

    def _browse(self):
        path = filedialog.askdirectory(title="Select folder to decrypt")
        if path:
            self.folder_var.set(path)

    def _start_decrypt(self):
        folder = self.folder_var.get().strip()
        if not os.path.isdir(folder):
            messagebox.showerror("Error", "Please select a valid folder.")
            return
        if not messagebox.askyesno("Confirm Decrypt",
                f"This will decrypt all .guardian files in:\n\n{folder}\n\n"
                "and all its subfolders.\n\nProceed?"):
            return
        threading.Thread(target=self._run_decrypt, args=(folder,), daemon=True).start()

    def _run_decrypt(self, root_folder):
        self.progress.start(10)
        self.status_var.set("Searching for encrypted folders…")
        try:
            # Find every subfolder that has a salt file
            salt_folders = find_salt_folders(root_folder)

            # Also check root itself
            if root_folder not in salt_folders:
                root_salt = os.path.join(root_folder, SALT_FILENAME)
                if os.path.exists(root_salt):
                    salt_folders.insert(0, root_folder)

            if not salt_folders:
                self.progress.stop()
                self.status_var.set("❌ No encrypted data found in this folder.")
                messagebox.showerror("Not Found",
                    "No encrypted data found.\n\n"
                    "Make sure you selected the correct folder.\n"
                    "Try selecting a parent folder like C:\\Users\\MAD")
                return

            self.status_var.set(f"Found {len(salt_folders)} encrypted location(s). Building file list…")

            # Build fernet for each salt folder
            fernets = {}
            for sf in salt_folders:
                salt = _get_salt(sf)
                if salt:
                    fernets[sf] = Fernet(_derive_key(salt))

            # Collect all .guardian files under root
            files  = list(_collect_encrypted(root_folder))
            total  = len(files)
            failed = 0

            if total == 0:
                self.progress.stop()
                self.status_var.set("⚠ No .guardian files found to decrypt.")
                messagebox.showinfo("Nothing to decrypt",
                    "No encrypted (.guardian) files were found in this folder.")
                return

            self.status_var.set(f"Decrypting {total} file(s)…")

            for i, fpath in enumerate(files, 1):
                self.status_var.set(f"Decrypting {i}/{total}: {os.path.basename(fpath)}")

                # Match the best fernet for this file
                best = None
                best_len = 0
                for sf, fnt in fernets.items():
                    if fpath.lower().startswith(sf.lower()) and len(sf) > best_len:
                        best = fnt
                        best_len = len(sf)

                # Fallback to first available
                if not best and fernets:
                    best = next(iter(fernets.values()))

                if best and not decrypt_file(fpath, best):
                    failed += 1

            self.progress.stop()
            success = total - failed
            self.status_var.set(f"✅ Done — {success}/{total} file(s) restored.")

            if failed == total:
                messagebox.showerror("Failed",
                    "❌ Could not decrypt any files.\n\n"
                    "The salt file may be missing or corrupted.\n"
                    "Try selecting a different parent folder.")
            elif failed > 0:
                messagebox.showwarning("Partial Success",
                    f"⚠ {success} file(s) decrypted successfully.\n"
                    f"{failed} file(s) could not be decrypted.")
            else:
                self._popup_done(total)

        except Exception as e:
            self.progress.stop()
            self.status_var.set(f"❌ Error: {e}")
            messagebox.showerror("Error", str(e))

    def _popup_done(self, total):
        win = tk.Toplevel(self.root)
        win.title("Recovery Complete")
        win.configure(bg=self.SURFACE)
        win.resizable(False, False)
        W, H = 380, 220
        win.geometry(f"{W}x{H}+{(self.root.winfo_screenwidth()-W)//2}+{(self.root.winfo_screenheight()-H)//2}")
        win.grab_set()
        tk.Frame(win, bg=self.BLUE, height=4).pack(fill="x")
        tk.Label(win, text="🔓", font=("Segoe UI Emoji", 40),
                 bg=self.SURFACE).pack(pady=(14, 2))
        tk.Label(win, text="DATA RESTORED", font=("Consolas", 13, "bold"),
                 bg=self.SURFACE, fg=self.BLUE).pack()
        tk.Label(win,
                 text=f"✅  {total} file(s) decrypted successfully.\n\nAll your files are back to normal.",
                 font=("Segoe UI", 9), bg=self.SURFACE, fg=self.TEXT,
                 justify="center", wraplength=340).pack(pady=10)
        tk.Button(win, text="   OK   ", command=win.destroy,
                  bg=self.BLUE, fg=self.TEXT,
                  font=("Segoe UI", 10, "bold"),
                  relief="flat", padx=24, pady=7,
                  cursor="hand2").pack()


if __name__ == "__main__":
    root = tk.Tk()
    RecoveryApp(root)
    root.mainloop()
