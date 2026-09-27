import os
import random
import re
import glob
import time
import json
import feedparser
import httpx
import xml.etree.ElementTree as ET
from datetime import datetime
from curl_cffi import requests as cffi_requests

# === SUMBER RSS GOSIP/HIBURAN ===
RSS_URLS = [
    "https://www.kapanlagi.com/feed/",
    "https://www.antaranews.com/rss/hiburan",
    "https://daerah.sindonews.com/rss"
]

def ekstrak_gambar(entry):
    if 'media_content' in entry and len(entry.media_content) > 0:
        return entry.media_content[0]['url']
    if 'media_thumbnail' in entry and len(entry.media_thumbnail) > 0:
        return entry.media_thumbnail[0]['url']
    if 'links' in entry:
        for link in entry.links:
            if link.get('type', '').startswith('image/') or link.get('rel') == 'enclosure':
                return link.href
                
    konten_mentah = ''
    if 'content' in entry:
        konten_mentah = entry.content[0].value
    elif 'description' in entry:
        konten_mentah = entry.description
        
    img_match = re.search(r'<img[^>]+src=["\'](https?://[^"\']+)["\']', konten_mentah)
    if img_match:
        return img_match.group(1)
        
    return "https://images.unsplash.com/photo-1495020689067-958852a7765e?auto=format&fit=crop&w=800&q=80"

def dapatkan_google_trends():
    try:
        url = "https://trends.google.com/trends/trendingsearches/daily/rss?geo=ID"
        response = cffi_requests.get(url, impersonate="chrome110", timeout=10.0)
        root = ET.fromstring(response.content)
        trends = [item.find('title').text for item in root.findall('.//item')[:5]]
        return ", ".join(trends)
    except Exception:
        return "gosip selebriti, artis viral, berita hiburan"

def rewrite_dengan_gemini(teks_asli):
    kata_kunci_trending = dapatkan_google_trends()
    api_key = os.getenv("GEMINI_API_KEY")
    
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
            print(f"    -> Meminta AI meracik artikel (Percobaan {percobaan + 1}/3)...")
            response = httpx.post(url, json=payload, headers={'Content-Type': 'application/json'}, timeout=40.0)
            data = response.json()
            
            if "candidates" in data:
                teks_hasil = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                baris_teks = [b.strip() for b in teks_hasil.split('\n') if b.strip()]
                
                if len(baris_teks) > 1:
                    judul = baris_teks[0].replace('"', '').replace('*', '').replace('Judul:', '').strip()
                    konten = '\n'.join(baris_teks[1:])
                    konten_html = "".join([f"<p>{p.strip()}</p>\n" for p in konten.split('\n') if p.strip()])
                    return judul, konten_html
            
            error_msg = data.get('error', {}).get('message', '')
            if "high demand" in error_msg.lower() or "exceeded" in error_msg.lower() or "503" in str(data):
                print("    -> [SABAR] Server/Quota padat. Menunggu 30 detik...")
                time.sleep(30)
                continue
            else:
                return None, None
        except Exception as e:
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
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .content p { margin-bottom: 1.25rem; font-size: 1.125rem; line-height: 1.75; color: #374151; }
    </style>
</head>
<body class="bg-gray-50 font-sans antialiased">
    <nav class="bg-white shadow-md border-b-4 border-red-600 sticky top-0 z-50">
        <div class="max-w-5xl mx-auto px-4 py-4 flex flex-col sm:flex-row justify-between items-center gap-4">
            <a href="/" class="text-2xl font-extrabold text-red-600 tracking-tighter">LENSA<span class="text-gray-800">TERKINI</span></a>
            <form action="/search.html" method="GET" class="flex w-full sm:w-auto">
                <input type="text" name="q" placeholder="Cari gosip..." class="w-full sm:w-64 px-4 py-2 border border-gray-300 rounded-l-md focus:outline-none focus:border-red-500" required>
                <button type="submit" class="bg-red-600 text-white px-4 py-2 rounded-r-md hover:bg-red-700">Cari</button>
            </form>
        </div>
    </nav>

    <main class="max-w-3xl mx-auto px-4 py-8">
        <h1 class="text-3xl md:text-4xl font-bold text-gray-900 mb-4 leading-tight">[JUDUL]</h1>
        
        <div class="flex justify-center mb-6 bg-gray-100 p-2 rounded">
            <script>
              atOptions = { 'key' : '34e8a8453e65d906ec3b64040798743a', 'format' : 'iframe', 'height' : 50, 'width' : 320, 'params' : {} };
            </script>
            <script src="https://www.highrevenueformat.com/34e8a8453e65d906ec3b64040798743a/invoke.js"></script>
        </div>

        <div class="flex items-center text-sm text-gray-500 mb-6">
            <span class="bg-red-100 text-red-600 px-2 py-1 rounded font-bold mr-3">Gosip Viral</span>
            <span>Redaksi LensaTerkini</span>
        </div>

        <img src="[IMAGE_URL]" alt="Thumbnail Berita" class="w-full h-auto object-cover rounded-xl shadow-lg mb-8 aspect-video">
        
        <div class="content bg-white p-6 md:p-8 rounded-xl shadow-sm border border-gray-100">
            [KONTEN]
        </div>
        
        <div class="flex justify-center mt-8 bg-gray-100 p-2 rounded">
            <script>
              atOptions = { 'key' : '34e8a8453e65d906ec3b64040798743a', 'format' : 'iframe', 'height' : 50, 'width' : 320, 'params' : {} };
            </script>
            <script src="https://www.highrevenueformat.com/34e8a8453e65d906ec3b64040798743a/invoke.js"></script>
        </div>
    </main>

    <footer class="bg-gray-800 text-white text-center py-6 mt-12">
        <p class="text-sm text-gray-400">&copy; 2026 LensaTerkini Network.</p>
        <div style="display:none;">
            <!-- SILAKAN PASTE SCRIPT HISTATS ANDA DI BAWAH BARIS INI -->
            
            <!-- BATAS BAWAH HISTATS -->
        </div>
    </footer>
    <script src="https://pl31470708.profitableratecpmnetwork.com/6f/e7/76/6fe776724aa6c362b50373f1a2c3d422.js"></script>
</body>
</html>"""
    html_final = html_template.replace("[JUDUL]", judul).replace("[IMAGE_URL]", image_url).replace("[KONTEN]", konten)
    filepath = f"content/{slug}.html"
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_final)
    print(f"    -> [SUKSES] {slug}.html disimpan!")

def buat_index_html(semua_artikel):
    html = """<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LensaTerkini - Portal Gosip & Berita Viral Hari Ini</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 font-sans antialiased">
    <nav class="bg-white shadow-md border-b-4 border-red-600 sticky top-0 z-50">
        <div class="max-w-5xl mx-auto px-4 py-4 flex flex-col sm:flex-row justify-between items-center gap-4">
            <a href="/" class="text-2xl font-extrabold text-red-600 tracking-tighter">LENSA<span class="text-gray-800">TERKINI</span></a>
            <form action="/search.html" method="GET" class="flex w-full sm:w-auto">
                <input type="text" name="q" placeholder="Cari gosip..." class="w-full sm:w-64 px-4 py-2 border border-gray-300 rounded-l-md focus:outline-none focus:border-red-500" required>
                <button type="submit" class="bg-red-600 text-white px-4 py-2 rounded-r-md hover:bg-red-700">Cari</button>
            </form>
        </div>
    </nav>

    <div class="bg-gray-800 text-white text-center py-10 px-4 mb-8">
        <h1 class="text-3xl md:text-5xl font-bold mb-3">Kabar Sensasional Hari Ini</h1>
        <p class="text-gray-300 md:text-lg">Berita paling viral dan terpanas dari dunia hiburan tanah air.</p>
    </div>

    <div class="max-w-5xl mx-auto px-4 pb-12">
        <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-6">"""
    
    for item in semua_artikel:
        slug = item["slug"]
        judul = item["judul"]
        gambar = item["gambar"]
        
        html += f"""
            <div class="bg-white rounded-xl overflow-hidden shadow-md hover:shadow-xl transition-shadow duration-300 flex flex-col">
                <a href="/{slug}">
                    <img src="{gambar}" alt="Thumbnail" class="w-full h-48 object-cover">
                </a>
                <div class="p-5 flex flex-col flex-grow">
                    <span class="text-xs font-bold text-red-600 mb-2 uppercase">Viral</span>
                    <a href="/{slug}" class="text-lg font-bold text-gray-800 hover:text-red-600 line-clamp-3 leading-snug mb-4">
                        {judul}
                    </a>
                    <div class="mt-auto">
                        <a href="/{slug}" class="inline-block bg-red-50 text-red-600 text-sm font-semibold px-4 py-2 rounded-full hover:bg-red-600 hover:text-white transition-colors">Baca &rarr;</a>
                    </div>
                </div>
            </div>"""
            
    html += """
        </div>
    </div>
    
    <footer class="bg-gray-800 text-white text-center py-6">
        <p class="text-sm text-gray-400">&copy; 2026 LensaTerkini Network.</p>
        <div style="display:none;">
            <!-- SILAKAN PASTE SCRIPT HISTATS ANDA DI BAWAH BARIS INI -->
            
            <!-- BATAS BAWAH HISTATS -->
        </div>
    </footer>
    <script src="https://pl31470708.profitableratecpmnetwork.com/6f/e7/76/6fe776724aa6c362b50373f1a2c3d422.js"></script>
</body>
</html>"""
    
    with open("content/index.html", "w", encoding="utf-8") as f:
        f.write(html)

def buat_sitemap_xml(semua_artikel):
    base_url = "https://hotdealscpm.me" 
    tanggal_sekarang = datetime.now().strftime("%Y-%m-%d")
    
    xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    xml_content += f'  <url>\n    <loc>{base_url}/</loc>\n    <lastmod>{tanggal_sekarang}</lastmod>\n    <changefreq>hourly</changefreq>\n    <priority>1.0</priority>\n  </url>\n'
    
    for item in semua_artikel:
        slug = item["slug"]
        xml_content += f'  <url>\n    <loc>{base_url}/{slug}</loc>\n    <lastmod>{tanggal_sekarang}</lastmod>\n    <changefreq>daily</changefreq>\n    <priority>0.8</priority>\n  </url>\n'
            
    xml_content += '</urlset>'
    with open("content/sitemap.xml", "w", encoding="utf-8") as f:
        f.write(xml_content)

def buat_sistem_pencarian(semua_artikel):
    with open("content/search.json", "w", encoding="utf-8") as f:
        json.dump(semua_artikel, f)
        
    html_search = """<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pencarian - LensaTerkini</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 font-sans antialiased">
    <nav class="bg-white shadow-md border-b-4 border-red-600 sticky top-0 z-50">
        <div class="max-w-5xl mx-auto px-4 py-4 flex flex-col sm:flex-row justify-between items-center gap-4">
            <a href="/" class="text-2xl font-extrabold text-red-600 tracking-tighter">LENSA<span class="text-gray-800">TERKINI</span></a>
            <form action="/search.html" method="GET" class="flex w-full sm:w-auto">
                <input type="text" name="q" id="searchInputTop" placeholder="Cari gosip..." class="w-full sm:w-64 px-4 py-2 border border-gray-300 rounded-l-md focus:outline-none focus:border-red-500">
                <button type="submit" class="bg-red-600 text-white px-4 py-2 rounded-r-md hover:bg-red-700">Cari</button>
            </form>
        </div>
    </nav>

    <div class="max-w-5xl mx-auto px-4 py-8 min-h-screen">
        <h1 class="text-2xl font-bold mb-6">Hasil Pencarian: <span id="keywordDisplay" class="text-red-600">...</span></h1>
        <div id="searchResults" class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-6">
            <p class="text-gray-500 col-span-full">Memuat hasil pencarian...</p>
        </div>
    </div>
    
    <footer class="bg-gray-800 text-white text-center py-6">
        <p class="text-sm text-gray-400">&copy; 2026 LensaTerkini Network.</p>
        <div style="display:none;">
            <!-- SILAKAN PASTE SCRIPT HISTATS ANDA DI BAWAH BARIS INI -->
            
            <!-- BATAS BAWAH HISTATS -->
        </div>
    </footer>

    <script>
        const urlParams = new URLSearchParams(window.location.search);
        const query = urlParams.get('q');
        
        if(query) {
            document.getElementById('keywordDisplay').innerText = '"' + query + '"';
            document.getElementById('searchInputTop').value = query;
            
            fetch('/search.json')
                .then(response => response.json())
                .then(data => {
                    const results = data.filter(item => item.judul.toLowerCase().includes(query.toLowerCase()));
                    const resultsContainer = document.getElementById('searchResults');
                    resultsContainer.innerHTML = '';
                    
                    if(results.length > 0) {
                        results.forEach(item => {
                            resultsContainer.innerHTML += `
                            <div class="bg-white rounded-xl overflow-hidden shadow-md hover:shadow-xl flex flex-col">
                                <a href="/${item.slug}">
                                    <img src="${item.gambar}" class="w-full h-48 object-cover">
                                </a>
                                <div class="p-5 flex flex-col flex-grow">
                                    <a href="/${item.slug}" class="text-lg font-bold text-gray-800 hover:text-red-600 mb-4">${item.judul}</a>
                                    <div class="mt-auto">
                                        <a href="/${item.slug}" class="inline-block bg-red-50 text-red-600 text-sm font-semibold px-4 py-2 rounded-full">Baca &rarr;</a>
                                    </div>
                                </div>
                            </div>`;
                        });
                    } else {
                        resultsContainer.innerHTML = '<p class="text-gray-500 col-span-full font-semibold">Maaf, berita tidak ditemukan.</p>';
                    }
                });
        }
    </script>
</body>
</html>"""
    with open("content/search.html", "w", encoding="utf-8") as f:
        f.write(html_search)

def jalankan_bot():
    print(f"=== MEMULAI BOT PADA {datetime.now()} ===")
    
    artikel_lama = []
    if os.path.exists("content/search.json"):
        try:
            with open("content/search.json", "r", encoding="utf-8") as f:
                artikel_lama = json.load(f)
                for item in artikel_lama:
                    if "timestamp" not in item:
                        item["timestamp"] = 0 
        except: pass
            
    if not artikel_lama:
        file_html_lama = [f for f in glob.glob("content/*.html")]
        for filepath in file_html_lama:
            filename = os.path.basename(filepath)
            
            if filename in ["index.html", "sitemap.xml", "search.html"] or filename.startswith("google"):
                continue
                
            slug = filename.replace('.html', '')
            try:
                with open(filepath, "r", encoding="utf-8") as f_html:
                    isi = f_html.read()
                    jdl = re.search(r'<title>(.*?)</title>', isi)
                    gmb = re.search(r'<img src="(.*?)"', isi)
                    artikel_lama.append({
                        "judul": jdl.group(1) if jdl else slug.replace("-", " "),
                        "slug": slug,
                        "gambar": gmb.group(1) if gmb else "",
                        "timestamp": os.path.getmtime(filepath)
                    })
            except: pass

    artikel_baru = []
    random.shuffle(RSS_URLS)
    total_artikel_dibuat = 0
    batas_artikel = 4 
    
    for rss in RSS_URLS:
        if total_artikel_dibuat >= batas_artikel: break
        print(f"\n[+] Mengekstrak: {rss}")
        try:
            response = cffi_requests.get(rss, impersonate="chrome110", timeout=30.0)
            feed = feedparser.parse(response.content)
            
            for entry in feed.entries[:3]:
                if total_artikel_dibuat >= batas_artikel: break
                
                teks_mentah = entry.get('description', '') or entry.get('summary', '') or entry.title
                teks_asli = re.sub(r'<[^>]+>', '', teks_mentah) 
                
                if len(teks_asli) > 10: 
                    judul_baru, konten_baru = rewrite_dengan_gemini(f"Judul: {entry.title}. Fakta: {teks_asli}")
                    
                    if judul_baru and konten_baru:
                        slug = bersihkan_judul(judul_baru)
                        gambar = ekstrak_gambar(entry)
                        buat_halaman_html(judul_baru, konten_baru, gambar, slug)
                        
                        artikel_baru.append({
                            "judul": judul_baru,
                            "slug": slug,
                            "gambar": gambar,
                            "timestamp": int(time.time())
                        })
                        
                        total_artikel_dibuat += 1
                        time.sleep(15)
        except Exception:
            pass

    slug_baru = [item["slug"] for item in artikel_baru]
    artikel_lama_bersih = [item for item in artikel_lama if item["slug"] not in slug_baru] 
    
    semua_artikel = artikel_baru + artikel_lama_bersih 
    semua_artikel = sorted(semua_artikel, key=lambda x: x.get("timestamp", 0), reverse=True)

    print("\n=== MEMBANGUN WEB ===")
    buat_index_html(semua_artikel)
    buat_sitemap_xml(semua_artikel) 
    buat_sistem_pencarian(semua_artikel)

if __name__ == "__main__":
    os.makedirs('content', exist_ok=True)
    jalankan_bot()
    print("=== SELESAI ===")
