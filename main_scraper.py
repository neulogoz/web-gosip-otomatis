import os
import random
import re
import glob
import feedparser
import httpx
import xml.etree.ElementTree as ET
from datetime import datetime
import google.generativeai as genai
from curl_cffi import requests as cffi_requests

# Konfigurasi Gemini API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

# URL RSS Detik diperbarui ke jalur resmi
RSS_URLS = [
    "https://rss.detik.com/index.php/hot",
    "https://www.insertlive.com/rss",
    "https://www.suara.com/rss/entertainment",
    "https://www.liputan6.com/rss/showbiz"
]

def ekstrak_gambar(entry):
    if 'media_content' in entry:
        return entry.media_content[0]['url']
    elif 'links' in entry:
        for link in entry.links:
            if link.get('type', '').startswith('image/'):
                return link.href
    return "https://via.placeholder.com/800x450?text=HotDeals+Gosip"

def dapatkan_google_trends():
    try:
        url = "https://trends.google.com/trends/trendingsearches/daily/rss?geo=ID"
        response = httpx.get(url, timeout=10.0)
        root = ET.fromstring(response.text)
        trends = [item.find('title').text for item in root.findall('.//item')[:5]]
        return ", ".join(trends)
    except Exception as e:
        print(f"[!] Gagal Google Trends: {e}")
        return "gosip viral, artis indonesia"

def rewrite_dengan_gemini(teks_asli):
    kata_kunci_trending = dapatkan_google_trends()
    try:
        prompt = f"""
        Tulis ulang artikel/berita hiburan berikut ini.
        ATURAN:
        1. TANPA EMOJI.
        2. Gaya bahasa natural ala portal berita.
        3. Baris PERTAMA wajib berisi Judul clickbait.
        4. Baris KEDUA dan seterusnya adalah isi paragraf.
        5. Sisipkan kata kunci trending: {kata_kunci_trending}.
        
        Artikel asli: {teks_asli}
        """
        
        pengaturan_sensor = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ]
        
        print("    -> Sedang meminta AI menulis artikel...")
        response = model.generate_content(prompt, safety_settings=pengaturan_sensor)
        teks_hasil = response.text.strip()
        
        baris_teks = [b.strip() for b in teks_hasil.split('\n') if b.strip()]
        
        if len(baris_teks) > 1:
            judul = baris_teks[0].replace('"', '').replace('*', '').replace('Judul:', '').strip()
            konten = '\n'.join(baris_teks[1:])
            
            konten_html = "".join([f"<p>{p.strip()}</p>\n" for p in konten.split('\n') if p.strip()])
            print("    -> AI BERHASIL menulis artikel!")
            return judul, konten_html
        else:
            print("    -> [!] AI menjawab terlalu pendek.")
            return None, None
    except Exception as e:
        print(f"    -> [!] ERROR AI GEMINI: {e}")
        return None, None

def bersihkan_judul(judul):
    judul_bersih = re.sub(r'[^a-zA-Z0-9\s-]', '', judul)
    return re.sub(r'\s+', '-', judul_bersih.strip()).lower()

def buat_halaman_html(judul, konten, image_url, slug):
    html_template = """<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>[JUDUL]</title>
    <style>
        :root { --primary: #e63946; --bg: #f3f4f6; --text: #374151; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background-color: var(--bg); color: var(--text); line-height: 1.7; margin: 0; padding: 0; }
        header { background: #fff; border-bottom: 3px solid var(--primary); padding: 15px 20px; text-align: center; }
        header a { text-decoration: none; color: var(--primary); font-size: 24px; font-weight: 800; }
        .container { max-width: 680px; margin: 25px auto; background: #fff; padding: 30px; border-radius: 10px; }
        .hero-img { width: 100%; height: auto; border-radius: 8px; margin-bottom: 25px; }
    </style>
</head>
<body>
    <header><a href="/">HotDeals Gosip</a></header>
    <main class="container">
        
        <div style="text-align: center; margin-bottom: 20px;">
            <script>
              atOptions = { 'key' : '34e8a8453e65d906ec3b64040798743a', 'format' : 'iframe', 'height' : 50, 'width' : 320, 'params' : {} };
            </script>
            <script src="https://www.highrevenueformat.com/34e8a8453e65d906ec3b64040798743a/invoke.js"></script>
        </div>

        <h1>[JUDUL]</h1>
        <img src="[IMAGE_URL]" alt="Gambar Berita" class="hero-img">
        <div class="content">[KONTEN]</div>
        
        <div style="text-align: center; margin-top: 20px;">
            <script>
              atOptions = { 'key' : '34e8a8453e65d906ec3b64040798743a', 'format' : 'iframe', 'height' : 50, 'width' : 320, 'params' : {} };
            </script>
            <script src="https://www.highrevenueformat.com/34e8a8453e65d906ec3b64040798743a/invoke.js"></script>
        </div>
    </main>
    <script src="https://pl31470708.profitableratecpmnetwork.com/6f/e7/76/6fe776724aa6c362b50373f1a2c3d422.js"></script>
</body>
</html>"""
    
    html_final = html_template.replace("[JUDUL]", judul).replace("[IMAGE_URL]", image_url).replace("[KONTEN]", konten)
    filepath = f"content/{slug}.html"
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_final)
    print(f"    -> [SUKSES] File {slug}.html berhasil disimpan!")

def buat_index_html():
    html = """<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HotDeals Gosip - Berita Terkini</title>
    <style>
        :root { --primary: #e63946; --bg: #f3f4f6; --text: #333; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background-color: var(--bg); color: var(--text); margin: 0; padding: 0; }
        header { background: #fff; border-bottom: 3px solid var(--primary); padding: 15px 20px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        header h2 { margin: 0; font-size: 24px; color: var(--primary); font-weight: 800; text-transform: uppercase; }
        .container { max-width: 800px; margin: 30px auto; padding: 0 20px; }
        .grid { display: flex; flex-direction: column; gap: 12px; }
        .card { background: #fff; padding: 18px 20px; border-radius: 8px; border-left: 4px solid var(--primary); box-shadow: 0 2px 4px rgba(0,0,0,0.04); }
        .card a { text-decoration: none; color: #1f2937; font-size: 17px; font-weight: 600; display: block; }
    </style>
</head>
<body>
    <header><h2>HotDeals Gosip</h2></header>
    <div class="container"><div class="grid">"""
    
    for filepath in glob.glob("content/*.html"):
        filename = os.path.basename(filepath)
        if filename != "index.html":
            slug = filename.replace('.html', '')
            html += f'<div class="card"><a href="/{slug}">{slug.replace("-", " ").title()}</a></div>\n'
            
    html += """</div></div></body></html>"""
    with open("content/index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("\n[OK] Index.html diperbarui.")

def jalankan_bot():
    print(f"=== MEMULAI BOT PADA {datetime.now()} ===")
    random.shuffle(RSS_URLS)
    total_artikel_dibuat = 0
    batas_artikel = 4 
    
    for rss in RSS_URLS:
        if total_artikel_dibuat >= batas_artikel: break
        print(f"\n[+] Mengekstrak dari: {rss}")
        try:
            # Menggunakan curl_cffi dengan impersonate Chrome untuk tembus Cloudflare
            response = cffi_requests.get(rss, impersonate="chrome110", timeout=30.0)
            print(f"    Status HTTP: {response.status_code}")
            
            feed = feedparser.parse(response.content)
            print(f"    Ditemukan {len(feed.entries)} berita.")
            
            for entry in feed.entries[:2]:
                if total_artikel_dibuat >= batas_artikel: break
                
                print(f"  - Judul Asli: {entry.title}")
                teks_mentah = entry.get('description', '') or entry.get('summary', '') or entry.title
                teks_asli = re.sub(r'<[^>]+>', '', teks_mentah) 
                
                if len(teks_asli) > 20: 
                    judul_baru, konten_baru = rewrite_dengan_gemini(teks_asli)
                    if judul_baru and konten_baru:
                        slug = bersihkan_judul(judul_baru)
                        buat_halaman_html(judul_baru, konten_baru, ekstrak_gambar(entry), slug)
                        total_artikel_dibuat += 1
                else:
                    print("    -> [LEWAT] Teks dari sumber terlalu pendek.")
        except Exception as e:
            print(f"[!] Error saat memproses {rss}: {e}")

    buat_index_html()

if __name__ == "__main__":
    os.makedirs('content', exist_ok=True)
    jalankan_bot()
    print("=== SELESAI ===")
