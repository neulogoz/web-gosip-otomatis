import httpx
import feedparser
from bs4 import BeautifulSoup
import google.generativeai as genai
import os
import re
from datetime import datetime
import random

# Konfigurasi Gemini API menggunakan Secret dari GitHub Actions
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

# Menggunakan model Gemini 1.5 Flash yang cepat dan ringan
model = genai.GenerativeModel('gemini-1.5-flash')

# 4 Sumber RSS Berita Gosip/Hiburan Indonesia
RSS_URLS = [
    "https://www.suara.com/rss/entertainment",
    "https://www.tribunnews.com/seleb/rss",
    "https://www.viva.co.id/showbiz/rss",
    "https://www.kapanlagi.com/feed/"
]

def bersihkan_judul(judul):
    # Membersihkan karakter aneh dan spasi untuk dijadikan URL (slug)
    slug = re.sub(r'[^a-zA-Z0-9\s]', '', judul).strip().replace(' ', '-')
    return slug.lower()

def ambil_konten_artikel(url):
    try:
        # Menggunakan headers menyerupai browser asli agar tidak diblokir web berita
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = httpx.get(url, headers=headers, timeout=15.0)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Mengambil semua teks di dalam tag <p> (paragraf)
        paragraphs = soup.find_all('p') 
        konten = " ".join([p.text for p in paragraphs if len(p.text) > 50])
        return konten
    except Exception as e:
        print(f"Gagal mengambil artikel dari {url}: {e}")
        return ""

def rewrite_dengan_gemini(teks_asli):
    # Perintah (Prompt) untuk Gemini agar artikel lolos plagiasi dan SEO Friendly
    prompt = f"""
    Tulis ulang teks berita gosip berikut dengan gaya bahasa gaul, asik, ala akun gosip Indonesia. 
    Ubah judulnya menjadi sedikit clickbait namun tetap sesuai fakta.
    Format output harus HTML (gunakan tag <p>, <h2>, <strong> dll).
    Jangan beri tag <html> atau <body>, cukup isi artikelnya saja. Pisahkan Judul dan Isi.
    
    Teks asli:
    {teks_asli}
    
    Format balasan (harus sama persis struktur ini):
    JUDUL: [Judul Baru]
    KONTEN: 
    [Isi Artikel HTML]
    """
    try:
        response = model.generate_content(prompt)
        hasil = response.text
        
        # Memisahkan antara Judul dan Konten HTML dari jawaban Gemini
        judul = hasil.split('KONTEN:')[0].replace('JUDUL:', '').strip()
        konten = hasil.split('KONTEN:')[1].strip()
        
        # Membersihkan tanda kutip markdown jika Gemini menambahkannya
        konten = konten.replace('```html', '').replace('```', '')
        return judul, konten
    except Exception as e:
        print(f"Error Gemini API: {e}")
        return None, None

def buat_halaman_html(judul, konten, image_url, slug):
    # Membaca template dari folder templates
    try:
        with open('templates/article.html', 'r', encoding='utf-8') as f:
            template = f.read()
        
        # Mengganti kode placeholder dengan hasil generate API
        html_final = template.replace('{{TITLE}}', judul)
        html_final = html_final.replace('{{DESCRIPTION}}', konten[:150] + "...") # Snippet untuk SEO
        html_final = html_final.replace('{{IMAGE_URL}}', image_url)
        html_final = html_final.replace('{{CONTENT}}', konten)
        
        # Menyimpan file baru ke folder content
        filepath = f"content/{slug}.html"
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_final)
        print(f"Sukses membuat halaman: {filepath}")
    except Exception as e:
        print(f"Gagal membuat file HTML: {e}")

def ekstrak_gambar(entry):
    # Menangkap gambar karena setiap portal berita punya struktur RSS berbeda
    if 'media_content' in entry and len(entry.media_content) > 0:
        return entry.media_content[0]['url']
    elif 'enclosures' in entry and len(entry.enclosures) > 0:
        return entry.enclosures[0]['href']
    elif 'summary' in entry:
        soup = BeautifulSoup(entry.summary, 'html.parser')
        img = soup.find('img')
        if img and img.has_attr('src'):
            return img['src']
    # Gambar cadangan jika artikel asli tidak punya gambar
    return "https://via.placeholder.com/600x400?text=Berita+Gosip+Terbaru"

def jalankan_bot():
    print(f"Memulai bot AGC pada {datetime.now()}")
    
    # Acak urutan sumber RSS agar website tidak didominasi 1 sumber pada waktu yang sama
    random.shuffle(RSS_URLS)
    
    total_artikel_dibuat = 0
    batas_artikel = 4 # Maksimal 4 artikel per eksekusi (16 artikel/hari) untuk keamanan kuota API
    
    for rss in RSS_URLS:
        if total_artikel_dibuat >= batas_artikel:
            break
            
        print(f"Mengekstrak RSS: {rss}")
        feed = feedparser.parse(rss)
        
        # Ambil maksimal 2 berita teratas dari sumber saat ini
        for entry in feed.entries[:2]:
            if total_artikel_dibuat >= batas_artikel:
                break
                
            url = entry.link
            image_url = ekstrak_gambar(entry)
            
            teks_asli = ambil_konten_artikel(url)
            
            # Pastikan teks cukup panjang untuk di-rewrite (mencegah artikel kosong/error)
            if len(teks_asli) > 300: 
                print(f"Memproses judul: {entry.title}")
                judul_baru, konten_baru = rewrite_dengan_gemini(teks_asli)
                
                if judul_baru and konten_baru:
                    slug = bersihkan_judul(judul_baru)
                    buat_halaman_html(judul_baru, konten_baru, image_url, slug)
                    total_artikel_dibuat += 1

if __name__ == "__main__":
    # Memastikan folder 'content' siap sebelum mulai
    os.makedirs('content', exist_ok=True)
    jalankan_bot()
    print("Selesai mengeksekusi bot AGC.")
