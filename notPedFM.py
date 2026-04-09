import os
from sifrele import AnahtarOlustur, Sifrele, SifreCoz
notlar = [] #Notları tutucak liste
normalFileADD = "C:\\Users\\USER\\Desktop\\notlar"
grmod = ""
def DosyaDüzenle(addressOfFile):
    with open(addressOfFile, "w") as dosya :
        print("Yazmak istediğinizi lütfen giriniz")
        dataInsideFile = ""
        while True :
            dataInsideFile = dataInsideFile+"\n"+input("YAZINIZ : \n")
            ask = input("Yazınız bittimi [y/N]\n").lower()
            if ask not in ["","n"] :
                break
        dosya.write(dataInsideFile)
def DosyaOlustur():
    while True:
        askName = input("Lütfen dosyanızın adını giriniz \n NOT LÜTFEN UZANTIYI GİRİN\n")
        if askName[-5:] == ".enot":
            fileName = askName[:-5]
            fileUz = ".enot"
        else:
            fileName, fileUz = os.path.splitext(askName)
        
        addressOfFile = normalFileADD + "\\" + fileName + fileUz
        if os.path.exists(addressOfFile) == True:
            print("Başka bir ad gir")
        else:
            with open(addressOfFile, "w") as dosya:
                print("Yazmak istediğinizi lütfen giriniz")
                dataInsideFile = ""
                while True:
                    dataInsideFile = dataInsideFile + "\n" + input("YAZINIZ : \n")
                    ask = input("Yazınız bittimi [y/N]\n").lower()
                    if ask not in ["", "n"]:
                        break
                
                # .enot dosyasıysa şifrele
                if fileUz == ".enot":
                    dataInsideFile = Sifrele(dataInsideFile)
                
                dosya.write(dataInsideFile)
            print("Bitti Dosya oluşturuldu : \n Dosya adı : " + fileName + "\nDosya uzantısı : " + fileUz)
        break
def DosyaAç():
    dosyalar = os.listdir(normalFileADD)
    for i, dosya in enumerate(dosyalar):
        print(str(i+1) + ". " + dosya)
    
    addressOfFile = input("Hangi dosyayı açacaksınız NOT : LÜTFEN UZANTIYI YAZINIZ")
    addressOfFile = normalFileADD + "\\" + addressOfFile
    print("Aranıyor:", addressOfFile)
    
    with open(addressOfFile, "r") as dosya:
        icerik = dosya.read()
    
    #ÇÖZÜM KISMI
    if addressOfFile.endswith(".enot"):
        print("\n Şifre çözülüyor...\n")
        cozulmus = SifreCoz(icerik)  # Şifreyi çöz
        if cozulmus:
            print(cozulmus)  # Çözülmüş metni göster
        else:
            print("Hata: Şifre çözülemedi!")
            return
    else:
        print(icerik)  # Düz metin dosyası ise direkt göster
    
    ask = input("\ndosyayı düzenlemek istermisiniz [y/N]").lower()
    if ask == "y":
        DosyaDüzenle(addressOfFile=addressOfFile)
    else:
        menu(1)
def DosyaSil(mod = 1):
    if mod == 1 :
        dosyalar = os.listdir(normalFileADD)
        for i, dosya in enumerate(dosyalar):
            print(str(i+1) + ". " + dosya)
        addressOfFile = input("Hangi dosyayı açacaksınız NOT : LÜTFEN UZANTIYI YAZINIZ")
        addressOfFile = normalFileADD + "\\" + addressOfFile
        print("Aranıyor:", addressOfFile)
        os.remove(addressOfFile)
        print("BİTTİ")
    elif mod == 2 :
        dosyalar = os.listdir(normalFileADD)
        for i, dosya in enumerate(dosyalar):
            print(str(i+1) + ". " + dosya)
        addressOfFile = input("Hangi dosyayı açacaksınız NOT : LÜTFEN UZANTIYI YAZINIZ")
        addressOfFile = normalFileADD + "\\" + addressOfFile
        print("Aranıyor:", addressOfFile)
        with open(addressOfFile , "r") as dosya:
            pass
        print("MOD 2 DAHA YAPILMADI LÜTFEN DÜZELTİN")  #Daha sonra yapmalıyım
    else :
        print("Mod doğru girilmemiş")
        modWant = int(input("Bu dosyayı tamamen yok mu etmek (1) istiyosun içinimi temizlemek?(2)"))
        DosyaSil(mod=modWant)
def menu(mod = None):
    if mod == None or mod == 0 :
        import random as salla
        selamlama = ["Merhaba" , "İyi günler" , "Yes Boss","hADİ ÇALIŞALIM","crupted","232322354352425335214352345","Nasılsınız","merhabalar patron","iş","00000010"]
        num = salla.randint(0,len(selamlama) - 1)
        print(selamlama[num]+"\n")
        global grMod
        grMod = input("terminalmi (t) yoksa GUI mı (g) kullanmak istersiniz NOT VARSAYILAN TERMİNALDİR").lower()
        if grMod == "":
            grMod = "t"
        print("Seçenekler : \n 1. Dosya oluşur \n 2. Dosya aç \n 3. Dosya sil \n 4. ÇIKIŞ")
        ask = input("Lütfen seçtiğiniz seçeneğin sayısını girin")
    else : 
        print("Seçenekler : \n 1. Dosya oluşur \n 2. Dosya aç \n 3. Dosya sil \n 4. ÇIKIŞ")
        ask = input("Lütfen seçtiğiniz seçeneğin sayısını girin")
    menuHelper(ask)
def menuHelper(askAnswer):
    if askAnswer in ["1" , "1."] :
        DosyaOlustur()
    elif askAnswer in ["2" , "2."]:
        DosyaAç()
    elif askAnswer in ["3" , "3."] :
        ask = input("Dosyayı yok mu etmek istersiniz(1.) içeriğinimi silmek isterisiniz(2.)")
        if ask in ("1" , "1."):
            DosyaSil(1)
        elif ask in ("2" , "2."):
            DosyaSil(2)
        else :
            print("ANLAŞILAMADI")
    elif askAnswer in ["4", "4."]:       #ÇIKIŞA GÖRE BU GÜNCELLENMELİ
        print("Çıkış yapılıyor. Hoşçakalın")
        quit()
    else :
        print("sanırım Yanlış bir numara tuşladınız lütfen tekrar deneyin")
        menu(mod=1)
# __________________________________________________________________ ÖZEL FONKSİYONLAR __________________________________________________________________
def LernFromN():   #Notlardan öğren
    pass            #Here it will have a AI wich will be at my local server network gonna learn everything from you write
# __________________________________________________________________ ÇALIŞMA BÖLGESI __________________________________________________________________
while True :
    AnahtarOlustur()   #Anahtar varmı diye bakıyor yoksa oluşturuyor
    menu()
