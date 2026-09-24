import os
import random
import re
import glob
import time
import feedparser
import httpx
import xml.etree.ElementTree as ET
from datetime import datetime
from curl_cffi import requests as cffi_requests

RSS_URLS = [
    "https://www.kapanlagi.com/feed/",
    "https://www.antaranews.com/rss/hiburan",
    "https://daerah.sindonews.com/rss"
]

def ekstrak_gambar(entry):
    if 'media_content' in entry:
        return entry.media_content[0]['url']
    elif 'links' in entry:
        for link in entry.links:
            if link.get('type', '').startswith('image/'):
                return link.href
    return "https://images.unsplash.com/photo-1598899134739-24c46f58b8c0?auto=format&fit=crop&w=800&q=80"

def dapatkan_google_trends():
    try:
        url = "https://trends.google.com/trends/trendingsearches/daily/rss?geo=ID"
        response = cffi_requests.get(url, impersonate="chrome110", timeout=10.0)
        root = ET.fromstring(response.content)
        trends = [item.find('title').text for item in root.findall('.//item')[:5]]
        return ", ".join(trends)
    except Exception as e:
        return "gosip selebriti, artis viral, berita hiburan"

def rewrite_dengan_gemini(teks_asli):
    kata_kunci_trending = dapatkan_google_trends()
    api_key = os.getenv("GEMINI_API_KEY")
    
    # PROMPT DIPERBARUI AGAR ARTIKEL LEBIH PANJANG (Ramah SEO & Adsterra)
    prompt = f"""
    Kembangkan informasi singkat hiburan berikut menjadi sebuah artikel/berita gosip yang PANJANG dan utuh (minimal 5-7 paragraf).
    
    ATURAN:
    1. DILARANG KERAS menggunakan emoji.
    2. Gaya bahasa jurnalisme santai yang mengundang rasa penasaran pembaca.
    3. Baris PERTAMA wajib berisi Judul clickbait yang sangat memancing.
    4. Baris KEDUA dan seterusnya adalah isi berita. Berikan opini netral dan dramatisasi ala wartawan hiburan agar teks menjadi panjang.
    5. Sisipkan kata kunci trending berikut secara natural: {kata_kunci_trending}.
    
    Informasi asli: {teks_asli}
    """
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key={api_key}"
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ]
    }
    
    for percobaan in range(3):
        try:
            print(f"    -> Sedang meminta AI meracik artikel (Percobaan {percobaan + 1}/3)...")
            response = httpx.post(url, json=payload, headers={'Content-Type': 'application/json'}, timeout=40.0)
            data = response.json()
            
            if "candidates" in data:
                teks_hasil = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                baris_teks = [b.strip() for b in teks_hasil.split('\n') if b.strip()]
                
                if len(baris_teks) > 1:
                    judul = baris_teks[0].replace('"', '').replace('*', '').replace('Judul:', '').strip()
                    konten = '\n'.join(baris_teks[1:])
                    konten_html = "".join([f"<p>{p.strip()}</p>\n" for p in konten.split('\n') if p.strip()])
                    print("    -> [BERHASIL] AI selesai menulis artikel!")
                    return judul, konten_html
            
            error_msg = data.get('error', {}).get('message', 'Tidak diketahui')
            print(f"    -> [!] AI menolak: {error_msg}")
            
            if "high demand" in error_msg.lower() or "503" in str(data):
                print("    -> [SABAR] Server Google sedang padat. Menunggu 30 detik...")
                time.sleep(30)
                continue
            else:
                return None, None
                
        except Exception as e:
            print(f"    -> [!] ERROR KONEKSI GEMINI: {e}")
            time.sleep(15)
            
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
        .hero-img { width: 100%; height: auto; border-radius: 8px; margin-bottom: 25px; object-fit: cover; aspect-ratio: 16/9; }
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
        if filename != "index.html" and filename != "sitemap.xml":
            slug = filename.replace('.html', '')
            html += f'<div class="card"><a href="/{slug}">{slug.replace("-", " ").title()}</a></div>\n'
            
    html += """</div></div></body></html>"""
    with open("content/index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("\n[OK] Index.html diperbarui.")

# === FUNGSI BARU UNTUK SITEMAP XML ===
def buat_sitemap_xml():
    base_url = "https://hotdealscpm.me"
    tanggal_sekarang = datetime.now().strftime("%Y-%m-%d")
    
    xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml_content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    
    # Halaman Utama (Homepage)
    xml_content += '  <url>\n'
    xml_content += f'    <loc>{base_url}/</loc>\n'
    xml_content += f'    <lastmod>{tanggal_sekarang}</lastmod>\n'
    xml_content += '    <changefreq>hourly</changefreq>\n'
    xml_content += '    <priority>1.0</priority>\n'
    xml_content += '  </url>\n'
    
    # Looping semua artikel untuk dimasukkan ke sitemap
    for filepath in glob.glob("content/*.html"):
        filename = os.path.basename(filepath)
        if filename != "index.html" and filename != "sitemap.xml":
            slug = filename.replace('.html', '')
            xml_content += '  <url>\n'
            # Di Github Pages, link menggunakan format /slug
            xml_content += f'    <loc>{base_url}/{slug}</loc>\n'
            xml_content += f'    <lastmod>{tanggal_sekarang}</lastmod>\n'
            xml_content += '    <changefreq>daily</changefreq>\n'
            xml_content += '    <priority>0.8</priority>\n'
            xml_content += '  </url>\n'
            
    xml_content += '</urlset>'
    
    # Simpan di folder content agar ikut di-upload ke GitHub Pages
    with open("content/sitemap.xml", "w", encoding="utf-8") as f:
        f.write(xml_content)
    print("[OK] Sitemap.xml berhasil dibuat dan diperbarui.")

def jalankan_bot():
    print(f"=== MEMULAI BOT PADA {datetime.now()} ===")
    random.shuffle(RSS_URLS)
    total_artikel_dibuat = 0
    batas_artikel = 4 
    
    for rss in RSS_URLS:
        if total_artikel_dibuat >= batas_artikel: break
        print(f"\n[+] Mengekstrak dari: {rss}")
        try:
            response = cffi_requests.get(rss, impersonate="chrome110", timeout=30.0)
            feed = feedparser.parse(response.content)
            print(f"    Ditemukan {len(feed.entries)} berita.")
            
            for entry in feed.entries[:3]:
                if total_artikel_dibuat >= batas_artikel: break
                
                print(f"  - Judul Asli: {entry.title}")
                teks_mentah = entry.get('description', '') or entry.get('summary', '') or entry.title
                teks_asli = re.sub(r'<[^>]+>', '', teks_mentah) 
                
                if len(teks_asli) > 10: 
                    judul_baru, konten_baru = rewrite_dengan_gemini(f"Judul: {entry.title}. Fakta: {teks_asli}")
                    
                    if judul_baru and konten_baru:
                        slug = bersihkan_judul(judul_baru)
                        buat_halaman_html(judul_baru, konten_baru, ekstrak_gambar(entry), slug)
                        total_artikel_dibuat += 1
                        print("    -> [JEDA AMAN] Istirahat 15 detik sebelum artikel berikutnya...")
                        time.sleep(15)
                else:
                    print("    -> [LEWAT] Teks kosong.")
        except Exception as e:
            print(f"[!] Error saat memproses {rss}: {e}")

    buat_index_html()
    buat_sitemap_xml() # <--- Memanggil fungsi sitemap di akhir

if __name__ == "__main__":
    os.makedirs('content', exist_ok=True)
    jalankan_bot()
    print("=== SELESAI ===")
