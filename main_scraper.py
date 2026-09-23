import httpx
import feedparser
from bs4 import BeautifulSoup
from google import genai
import os
import re
from datetime import datetime
import random

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

RSS_URLS = [
    "https://www.suara.com/rss/entertainment",
    "https://www.tribunnews.com/seleb/rss",
    "https://www.viva.co.id/showbiz/rss",
    "https://www.kapanlagi.com/feed/"
]

def bersihkan_judul(judul):
    slug = re.sub(r'[^a-zA-Z0-9\s]', '', judul).strip().replace(' ', '-')
    return slug.lower()

def ambil_konten_artikel(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = httpx.get(url, headers=headers, timeout=15.0)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        paragraphs = soup.find_all('p') 
        konten = " ".join([p.text for p in paragraphs if len(p.text) > 50])
        return konten
    except Exception as e:
        print(f"Gagal mengambil artikel dari {url}: {e}")
        return ""

def rewrite_dengan_gemini(teks_asli):
    prompt = f"""
    Tulis ulang teks berita gosip berikut dengan gaya bahasa gaul, asik, ala akun gosip Indonesia. 
    Ubah judulnya menjadi sedikit clickbait namun tetap sesuai fakta.
    Format output harus HTML. Pisahkan Judul dan Isi.
    
    Teks asli:
    {teks_asli}
    
    Format balasan:
    JUDUL: [Judul Baru]
    KONTEN: 
    [Isi Artikel HTML]
    """
    
    # Kita masukkan kembali gemini-1.5-flash karena pada SDK terbaru, versi ini seharusnya didukung lagi
    model_pilihan = ['gemini-1.5-flash', 'gemini-2.0-flash', 'gemini-2.5-flash']
    
    for nama_model in model_pilihan:
        try:
            response = client.models.generate_content(
                model=nama_model,
                contents=prompt
            )
            hasil = response.text
            
            judul = hasil.split('KONTEN:')[0].replace('JUDUL:', '').strip()
            konten = hasil.split('KONTEN:')[1].strip()
            konten = konten.replace('```html', '').replace('```', '')
            return judul, konten
            
        except Exception as e:
            # DI SINI KITA AKAN MELIHAT ERROR ASLINYA DARI GOOGLE
            print(f"-> Gagal model {nama_model}. Alasan dari Google: {str(e)}")
            continue 
            
    print("Error fatal: Semua percobaan model gagal.")
    return None, None

def buat_halaman_html(judul, konten, image_url, slug):
    try:
        with open('templates/article.html', 'r', encoding='utf-8') as f:
            template = f.read()
        
        html_final = template.replace('{{TITLE}}', judul).replace('{{DESCRIPTION}}', konten[:150] + "...").replace('{{IMAGE_URL}}', image_url).replace('{{CONTENT}}', konten)
        
        filepath = f"content/{slug}.html"
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_final)
        print(f"Sukses membuat halaman: {filepath}")
    except Exception as e:
        print(f"Gagal membuat file HTML: {e}")

def ekstrak_gambar(entry):
    if 'media_content' in entry and len(entry.media_content) > 0:
        return entry.media_content[0]['url']
    elif 'enclosures' in entry and len(entry.enclosures) > 0:
        return entry.enclosures[0]['href']
    elif 'summary' in entry:
        soup = BeautifulSoup(entry.summary, 'html.parser')
        img = soup.find('img')
        if img and img.has_attr('src'):
            return img['src']
    return "https://via.placeholder.com/600x400?text=Berita+Gosip+Terbaru"

def jalankan_bot():
    print(f"Memulai bot AGC pada {datetime.now()}")
    
    # --- FITUR DETEKTIF BARU ---
    try:
        print("Mengecek daftar model AI yang diizinkan untuk API Key Anda...")
        models = client.models.list()
        tersedia = [m.name for m in models if 'flash' in m.name or 'pro' in m.name]
        print(f"Model yang aktif di akun Anda: {tersedia}")
    except Exception as e:
        print(f"Gagal mengecek daftar model: {str(e)}")
    # ---------------------------

    random.shuffle(RSS_URLS)
    total_artikel_dibuat = 0
    batas_artikel = 4 
    
    for rss in RSS_URLS:
        if total_artikel_dibuat >= batas_artikel:
            break
            
        print(f"Mengekstrak RSS: {rss}")
        feed = feedparser.parse(rss)
        
        for entry in feed.entries[:2]:
            if total_artikel_dibuat >= batas_artikel:
                break
                
            url = entry.link
            image_url = ekstrak_gambar(entry)
            teks_asli = ambil_konten_artikel(url)
            
            if len(teks_asli) > 300: 
                print(f"Memproses judul: {entry.title}")
                judul_baru, konten_baru = rewrite_dengan_gemini(teks_asli)
                
                if judul_baru and konten_baru:
                    slug = bersihkan_judul(judul_baru)
                    buat_halaman_html(judul_baru, konten_baru, image_url, slug)
                    total_artikel_dibuat += 1

if __name__ == "__main__":
    os.makedirs('content', exist_ok=True)
    jalankan_bot()
    print("Selesai mengeksekusi bot AGC.")
