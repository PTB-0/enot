import os
import sys
from cryptography.fernet import Fernet
 
 
def _get_key_dir():
    """
    Nuitka onefile: sys.executable temp klasörünü gösterir.
    Gerçek exe yolu için __nuitka_binary_directory__ kullanılır.
    PyInstaller frozen için sys.executable doğrudur.
    Script olarak çalışırken __file__ kullanılır.
    """
    # Nuitka onefile — en güvenilir yöntem
    nuitka_dir = getattr(sys, '__nuitka_binary_directory__', None)
    if nuitka_dir:
        return nuitka_dir
 
    # Ortam değişkeni (Nuitka bazı versiyonlarda set eder)
    nuitka_env = os.environ.get('NUITKA_ONEFILE_PARENT', None)
    if nuitka_env:
        return os.path.dirname(nuitka_env)
 
    # PyInstaller
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
 
    # Normal script
    return os.path.dirname(os.path.abspath(__file__))
 
 
def _get_key_file():
    return os.path.join(_get_key_dir(), 'secret.key')
 
 
def AnahtarOlustur(mod=None):
    keyFile = _get_key_file()
 
    if not os.path.exists(keyFile):
        try:
            import tkinter as tk
            from tkinter import messagebox, filedialog
 
            _root = tk.Tk()
            _root.withdraw()
 
            cevap = messagebox.askyesno(
                "Şifreleme Anahtarı Bulunamadı",
                f"Anahtar dosyası şurada bulunamadı:\n{keyFile}\n\n"
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
                    return
            else:
                _root.destroy()
                return
 
            _root.destroy()
 
        except Exception:
            pass
 
        try:
            os.makedirs(os.path.dirname(keyFile) or '.', exist_ok=True)
            anahtar = Fernet.generate_key()
            with open(keyFile, 'wb') as kf:
                kf.write(anahtar)
            print(f"Şifreleme anahtarı oluşturuldu: {keyFile}")
        except Exception as e:
            print(f"Anahtar oluşturulamadı: {e}")
 
    if mod is not None:
        print("its me , mario!!!!!")  # easter egg
 
 
def AnahtarYukle():
    keyFile = _get_key_file()
    if not os.path.exists(keyFile):
        raise FileNotFoundError(
            f"Anahtar bulunamadı: {keyFile}\n"
            f"Tespit edilen dizin: {_get_key_dir()}\n"
            f"sys.executable: {sys.executable}\n"
            f"__nuitka_binary_directory__: {getattr(sys, '__nuitka_binary_directory__', 'YOK')}\n"
            f"NUITKA_ONEFILE_PARENT: {os.environ.get('NUITKA_ONEFILE_PARENT', 'YOK')}"
        )
    with open(keyFile, 'rb') as kf:
        return kf.read()
 
 
def Sifrele(metin):
    f = Fernet(AnahtarYukle())
    return f.encrypt(metin.encode()).decode()
 
 
def SifreCoz(sifreli_metin):
    f = Fernet(AnahtarYukle())
    try:
        return f.decrypt(sifreli_metin.encode()).decode()
    except Exception:
        print("Şifre çözülemedi. Dosya bozuk olabilir.")
        return None
 