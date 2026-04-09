import os
from cryptography.fernet import Fernet
keyFile= "C:\\Users\\USER\\Desktop\\notlar\\secret.key"
def AnahtarOlustur(mod = None):
    if not os.path.exists(keyFile):
        anahtar = Fernet.generate_key()
        with open(keyFile, "wb") as key_file:
            key_file.write(anahtar)
        print("Şifreleme anahtarı oluşturuldu")
    if mod != None :
        print("its me , mario!!!!!")    #eanster egg
def AnahtarYukle():
    """Kaydedilmiş anahtarı yükle"""
    with open(keyFile, "rb") as key_file:
        return key_file.read()

def Sifrele(metin):
    """Metni şifrele"""
    f = Fernet(AnahtarYukle())
    return f.encrypt(metin.encode()).decode()

def SifreCoz(sifreli_metin):
    """Şifreli metni çöz"""
    f = Fernet(AnahtarYukle())
    try:
        return f.decrypt(sifreli_metin.encode()).decode()
    except:
        print("Şifre çözülemedi Dosya bozuk olabilir.")
        return None