import os
import random
import re
import glob
import feedparser
import httpx
import xml.etree.ElementTree as ET
from datetime import datetime
import google.generativeai as genai

# Konfigurasi Gemini API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

# Daftar RSS Feed Gosip/Hiburan
RSS_URLS = [
    "https://www.insertlive.com/rss",
    "https://www.detik.com/hot/rss",
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
        
        trends = []
        for item in root.findall('.//item')[:5]:
            title = item.find('title').text
            trends.append(title)
            
        return ", ".join(trends)
    except Exception as e:
        print(f"Gagal mengambil tren: {e}")
        return "gosip viral, artis indonesia terkini, berita selebritis"

def rewrite_dengan_gemini(teks_asli):
    kata_kunci_trending = dapatkan_google_trends()
    
    try:
        prompt = f"""
        Tulis ulang artikel/berita hiburan berikut ini.
        
        ATURAN SANGAT PENTING:
        1. DILARANG KERAS menggunakan emoji apapun.
        2. Gaya bahasa natural, profesional, ala portal berita DetikHot atau InsertLive.
        3. Langsung ke isi berita, tanpa kata pengantar AI.
        4. Baris PERTAMA wajib berisi Judul clickbait.
        5. Baris KEDUA dan seterusnya adalah isi paragraf berita.
        6. ATURAN SEO: Sisipkan kata kunci trending berikut ini secara natural ke dalam berita: {kata_kunci_trending}.
        
        Artikel asli:
        {teks_asli}
        """
        
        response = model.generate_content(prompt)
        teks_hasil = response.text.strip()

# Matikan sensor keamanan AI agar berita gosip/skandal tidak diblokir
        pengaturan_sensor = {
            'HARM_CATEGORY_HARASSMENT': 'BLOCK_NONE',
            'HARM_CATEGORY_HATE_SPEECH': 'BLOCK_NONE',
            'HARM_CATEGORY_SEXUALLY_EXPLICIT': 'BLOCK_NONE',
            'HARM_CATEGORY_DANGEROUS_CONTENT': 'BLOCK_NONE'
        }
        
        response = model.generate_content(prompt, safety_settings=pengaturan_sensor)
        teks_hasil = response.text.strip()
        
        # Mengambil baris pertama sebagai Judul, sisanya sebagai Konten
        baris_teks = [b.strip() for b in teks_hasil.split('\n') if b.strip()]
        
        if len(baris_teks) > 1:
            judul = baris_teks[0].replace('"', '').replace('*', '').replace('Judul:', '').strip()
            konten = '\n'.join(baris_teks[1:])
            
            konten_html = ""
            for paragraf in konten.split('\n'):
                if paragraf.strip():
                    konten_html += f"<p>{paragraf.strip()}</p>\n"
                    
            return judul, konten_html
        return None, None
    except Exception as e:
        print(f"Error Gemini: {e}")
        return None, None


def bersihkan_judul(judul):
    judul_bersih = re.sub(r'[^a-zA-Z0-9\s-]', '', judul)
    return re.sub(r'\s+', '-', judul_bersih.strip()).lower()

def buat_halaman_html(judul, konten, image_url, slug):
    # Menggunakan string biasa (bukan f-string) agar script iklan JS tidak error
    html_template = """<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>[JUDUL]</title>
    <meta name="description" content="[JUDUL] - Berita artis terhangat hari ini.">
    <style>
        :root { --primary: #e63946; --bg: #f3f4f6; --text: #374151; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background-color: var(--bg); color: var(--text); line-height: 1.7; margin: 0; padding: 0; }
        header { background: #fff; border-bottom: 3px solid var(--primary); padding: 15px 20px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        header a { text-decoration: none; color: var(--primary); font-size: 24px; font-weight: 800; letter-spacing: -0.5px; text-transform: uppercase; }
        .container { max-width: 680px; margin: 25px auto; background: #fff; padding: 30px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.03); }
        h1 { font-size: 28px; line-height: 1.35; margin-top: 0; margin-bottom: 15px; color: #111; letter-spacing: -0.5px; }
        .meta { font-size: 14px; color: #6b7280; border-bottom: 1px solid #e5e7eb; padding-bottom: 15px; margin-bottom: 25px; }
        .hero-img { width: 100%; height: auto; border-radius: 8px; margin-bottom: 25px; object-fit: cover; aspect-ratio: 16/9; background-color: #eee; }
        .content { font-size: 17px; color: #4b5563; }
        .content p { margin-bottom: 20px; }
        footer { text-align: center; padding: 20px; font-size: 13px; color: #9ca3af; margin-top: 20px; }
        @media (max-width: 600px) { .container { margin: 15px; padding: 20px; } h1 { font-size: 24px; } }
    </style>
</head>
<body>
    <header>
        <a href="/">HotDeals Gosip</a>
    </header>
    
    <main class="container">
        
        <!-- IKLAN BANNER ATAS -->
        <div style="text-align: center; margin-bottom: 20px;">
            <script>
              atOptions = {
                'key' : '34e8a8453e65d906ec3b64040798743a',
                'format' : 'iframe',
                'height' : 50,
                'width' : 320,
                'params' : {}
              };
            </script>
            <script src="https://www.highrevenueformat.com/34e8a8453e65d906ec3b64040798743a/invoke.js"></script>
        </div>

        <h1>[JUDUL]</h1>
        <div class="meta">Dipublikasikan otomatis | Redaksi HotDeals</div>
        
        <img src="[IMAGE_URL]" alt="Gambar Berita" class="hero-img">
        
        <div class="content">
            [KONTEN]
        </div>
        
        <!-- IKLAN BANNER BAWAH -->
        <div style="text-align: center; margin-top: 20px;">
            <script>
              atOptions = {
                'key' : '34e8a8453e65d906ec3b64040798743a',
                'format' : 'iframe',
                'height' : 50,
                'width' : 320,
                'params' : {}
              };
            </script>
            <script src="https://www.highrevenueformat.com/34e8a8453e65d906ec3b64040798743a/invoke.js"></script>
        </div>

    </main>
    
    <footer>
        &copy; 2026 HotDealsCPM.me - Portal Berita Hiburan Terkini.
    </footer>
    
    <!-- IKLAN POPUNDER BAWAH -->
    <script src="https://pl31470708.profitableratecpmnetwork.com/6f/e7/76/6fe776724aa6c362b50373f1a2c3d422.js"></script>
</body>
</html>"""
    
    html_final = html_template.replace("[JUDUL]", judul).replace("[IMAGE_URL]", image_url).replace("[KONTEN]", konten)
    
    filepath = f"content/{slug}.html"
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_final)

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
        header h2 { margin: 0; font-size: 24px; color: var(--primary); font-weight: 800; letter-spacing: -0.5px; text-transform: uppercase; }
        .container { max-width: 800px; margin: 30px auto; padding: 0 20px; }
        .section-title { font-size: 20px; font-weight: 700; margin-bottom: 20px; color: #111; display: flex; align-items: center; gap: 8px; }
        .grid { display: flex; flex-direction: column; gap: 12px; }
        .card { background: #fff; padding: 18px 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.04); border-left: 4px solid var(--primary); transition: transform 0.2s, box-shadow 0.2s; }
        .card:hover { transform: translateY(-2px); box-shadow: 0 6px 12px rgba(0,0,0,0.08); }
        .card a { text-decoration: none; color: #1f2937; font-size: 17px; font-weight: 600; line-height: 1.4; display: block; }
        .card a:hover { color: var(--primary); }
        footer { text-align: center; padding: 30px 20px; font-size: 13px; color: #6b7280; }
    </style>
</head>
<body>
    <header>
        <h2>HotDeals Gosip</h2>
    </header>
    <div class="container">
        <div class="section-title">Berita Terkini</div>
        <div class="grid">
"""
    
    for filepath in glob.glob("content/*.html"):
        filename = os.path.basename(filepath)
        if filename == "index.html":
            continue
        slug = filename.replace('.html', '')
        judul_tampil = slug.replace('-', ' ').title()
        html += f'            <div class="card"><a href="/{slug}">{judul_tampil}</a></div>\n'
        
    html += """        </div>
    </div>
    <footer>&copy; 2026 HotDealsCPM.me - Portal Berita Hiburan.</footer>
</body>
</html>
"""
    with open("content/index.html", "w", encoding="utf-8") as f:
        f.write(html)

def jalankan_bot():
    print(f"Memulai bot AGC pada {datetime.now()}")
    
    random.shuffle(RSS_URLS)
    total_artikel_dibuat = 0
    batas_artikel = 4 
    
    for rss in RSS_URLS:
        if total_artikel_dibuat >= batas_artikel:
            break
            
        print(f"Mengekstrak RSS: {rss}")
        try:
            feed = feedparser.parse(rss)
            
            for entry in feed.entries[:2]:
                if total_artikel_dibuat >= batas_artikel:
                    break
                    
                image_url = ekstrak_gambar(entry)
                
                teks_mentah = entry.get('description', '') or entry.get('summary', '') or entry.title
                teks_asli = re.sub(r'<[^>]+>', '', teks_mentah) 
                
                if len(teks_asli) > 40: 
                    print(f"Memproses judul: {entry.title}")
                    judul_baru, konten_baru = rewrite_dengan_gemini(teks_asli)
                    
                    if judul_baru and konten_baru:
                        slug = bersihkan_judul(judul_baru)
                        buat_halaman_html(judul_baru, konten_baru, image_url, slug)
                        total_artikel_dibuat += 1
        except Exception as e:
            print(f"Error memproses {rss}: {e}")

    buat_index_html()

if __name__ == "__main__":
    os.makedirs('content', exist_ok=True)
    jalankan_bot()
    print("Selesai mengeksekusi bot AGC.")
