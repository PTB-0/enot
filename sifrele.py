import os
import sys
from cryptography.fernet import Fernet

# --- Anahtar konumu dinamik olarak belirlenir ---
def _get_key_dir():
    """Exe'nin veya script'in bulunduğu klasörü döndürür."""
    if getattr(sys, 'frozen', False):
        # Nuitka onefile: sys.executable geçici temp değil, gerçek exe yolu
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

def _get_key_file():
    return os.path.join(_get_key_dir(), 'secret.key')

# ----------------------------------------------------------------

def AnahtarOlustur(mod=None):
    keyFile = _get_key_file()

    if not os.path.exists(keyFile):
        # tkinter import'u lazy yapıyoruz — GUI başlamadan önce çalışabilir
        try:
            import tkinter as tk
            from tkinter import messagebox, filedialog

            # Gizli root penceresi (askdirectory için gerekli)
            _root = tk.Tk()
            _root.withdraw()

            cevap = messagebox.askyesno(
                "Şifreleme Anahtarı Bulunamadı",
                f"Anahtar dosyası bulunamadı:\n{keyFile}\n\n"
                "Yeni bir konum seçip oluşturmak ister misiniz?\n"
                "(Hayır dersen şifreleme devre dışı kalır)"
            )

            if cevap:
                klasor = filedialog.askdirectory(
                    title="Anahtarın oluşturulacağı klasörü seçin",
                    initialdir=_get_key_dir()
                )
                if klasor:
                    keyFile = os.path.join(klasor, 'secret.key')
                else:
                    _root.destroy()
                    return  # kullanıcı iptal etti
            else:
                _root.destroy()
                return  # kullanıcı istemedi

            _root.destroy()

        except Exception:
            # GUI yoksa (headless) sadece default yola oluştur
            pass

        try:
            os.makedirs(os.path.dirname(keyFile), exist_ok=True)
            anahtar = Fernet.generate_key()
            with open(keyFile, 'wb') as kf:
                kf.write(anahtar)
            print(f"Şifreleme anahtarı oluşturuldu: {keyFile}")
        except Exception as e:
            print(f"Anahtar oluşturulamadı: {e}")
            return

    if mod is not None:
        print("its me , mario!!!!!")  # easter egg


def AnahtarYukle():
    """Kaydedilmiş anahtarı yükle."""
    keyFile = _get_key_file()
    with open(keyFile, 'rb') as kf:
        return kf.read()


def Sifrele(metin):
    """Metni şifrele."""
    f = Fernet(AnahtarYukle())
    return f.encrypt(metin.encode()).decode()


def SifreCoz(sifreli_metin):
    """Şifreli metni çöz."""
    f = Fernet(AnahtarYukle())
    try:
        return f.decrypt(sifreli_metin.encode()).decode()
    except Exception:
        print("Şifre çözülemedi. Dosya bozuk olabilir.")
        return None
