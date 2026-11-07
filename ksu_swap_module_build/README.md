# OneOS Switcher & Superuser Bridge Helper Module (KernelSU)

Bu KernelSU modülü, **OneOS (Mualiy.net & Fahad Ali Team)** projesinde Samsung One UI ile konuk sistemler (ColorOS, PixelOS, NothingOS vb.) arasında geçiş yaparken yaşanan iki kritik sorunu kesin olarak çözer:

1. **Dead Userdata / FBE Ekran Kilidi Çökmesi:** Şifrelenmiş ekran kilidi kaldırılmadan konuk sisteme geçilirse Samsung FBE (File-Based Encryption) anahtarları bozulur ve telefon bootloop'a ya da veri sıfırlamaya düşer. Modül geçiş öncesinde güvenli `locksettings` protokolüyle kilidi kaldırır, dönüşte ise tekrar PIN'i kurarak güvenliği sağlar.
2. **Superuser Yetkilerinin Sıfırlanması & Kesin Override:** Geçiş sonrasında One UI'a dönüldüğünde root yetkileri sıfırlanmaz; snapshot yedeği birebir geri yüklenir. Örneğin yedek alındığında 5 rootlu uygulama varsa, aradaki sürede 6'ya çıksa dahi geri yükleme anında önceki listeyi tamamen ezerek (override) tam 5 uygulamaya geri sabitler.

---

## 📦 Kurulum

1. `OneOS_Switcher_SU_Bridge_v1.2.0.zip` dosyasını telefonunuza aktarın.
2. **KernelSU Manager** (veya **KernelSU Next / MMRL / APatch**) uygulamasını açın.
3. **Modüller (Modules)** sekmesine gelin -> **Yükle (Install)** diyerek zip dosyasını seçin.
4. Kurulum tamamlandıktan sonra cihazı yeniden başlatın.

---

## 🌐 WebUI Yönetim Paneli

Modül kurulduktan sonra **KernelSU Manager** içerisindeki modül kartında **"WebUI"** butonu aktifleşir. Dokunduğunuzda dahili yönetim paneli açılır:

- **İlk Kurulum Sihirbazı:** Başlangıçta sayısal PIN, alfanümerik şifre veya şifresiz seçeneklerinden birini seçip kaydedin. Şifrenizi `****` şeklinde gizler ve yanındaki göz butonu ile kontrol edebilirsiniz.
- **Güvenlik Durumu:** İlk kurulum yapılmadan butonlar kilitlidir. Kayıt yapıldıktan sonra kilitler açılır ve tekrar şifre istemez.
- **SwapOUT:** Rootlu uygulama listesini ve KernelSU veritabanını snapshot alır, ardından ekran kilidini kaldırıp cihazı GSI geçişine hazırlar.
- **SwapIN:** One UI'a dönüldüğünde yedeklenen Superuser izinlerini kesin override ederek yükler, ksud'u yeniler ve PIN'inizi otomatik yeniden aktif eder.
- **ManuelSUBak:** İstediğiniz her an tek tıkla rootlu uygulamaların güncel yedeğini alır.
- **Canlı Konsol:** Yapılan işlemler, çalıştırılan shell kodları ve başarı durumları anlık olarak ekrandan izlenebilir.
- **Tema & Görünüm:** Sol üstteki buton ile Karanlık/Aydınlık mod, sağ üstteki çark ikonundan ise **OneUI**, **Material 3 Expressive** ve **MiuiX (HyperOS-like)** temaları arasında anında geçiş yapılabilir.

---

## 💻 Terminal / CLI Kullanımı

Dilerseniz Termux veya ADB Shell üzerinden root (`su`) ile doğrudan da kontrol edebilirsiniz:

```bash
# SwapOUT (Geçişe hazırlan - SU Yedekle + Kilidi Kaldır)
oneos-bridge swapout

# SwapIN (Geri Dönüş - SU Override Restore + PIN Aktif Et)
oneos-bridge swapin

# Manuel Anlık SU Yedeği
oneos-bridge manuelsubak

# Durum Bilgisi (JSON)
oneos-bridge status

# Logları Oku
oneos-bridge log
```

---

## 🛠️ Bağımlılıklar (Dependencies)
Bu modül harici hiçbir ağır bağımlılık (Python, Node.js veya harici binary) **GEREKTİRMEZ**. Android'in kendi dahili `toybox`, `sh`, `locksettings` ve KernelSU'nun dahili `ksud` altyapısını kullanacak şekilde sıfır hata toleransıyla optimize edilmiştir.
