import os
import re
import json
import time
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
import subprocess
import requests

PORT = int(os.environ.get("PORT", 7860))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="bn">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>BlinkNote & Jotted Video Studio Pro</title>
  <script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', system-ui, sans-serif; }
    body { background-color: #0b1120; color: #f8fafc; min-height: 100vh; padding: 20px; }
    .header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; border-bottom: 1px solid #1e293b; padding-bottom: 12px; }
    .title { font-size: 20px; font-weight: 700; color: #38bdf8; }
    .badge { background: #065f46; color: #34d399; font-size: 11px; font-weight: 600; padding: 4px 10px; border-radius: 20px; }
    .container { display: grid; grid-template-columns: 380px 1fr; gap: 20px; }
    @media (max-width: 850px) { .container { grid-template-columns: 1fr; } }
    .panel { background: #111827; border: 1px solid #1f2937; border-radius: 12px; padding: 16px; display: flex; flex-direction: column; gap: 14px; }
    .input-box { display: flex; flex-direction: column; gap: 6px; }
    label { font-size: 13px; color: #94a3b8; font-weight: 600; }
    input[type="text"] { width: 100%; padding: 11px; background: #0b1120; border: 1px solid #374151; border-radius: 8px; color: #fff; font-size: 14px; outline: none; }
    input[type="text"]:focus { border-color: #38bdf8; }
    button.btn-primary { background: #0284c7; color: white; padding: 11px; font-size: 14px; font-weight: 600; border: none; border-radius: 8px; cursor: pointer; }
    button.btn-primary:hover { background: #0369a1; }
    .video-list { max-height: 480px; overflow-y: auto; display: flex; flex-direction: column; gap: 8px; margin-top: 8px; }
    .video-card { background: #1e293b; border: 1px solid #334155; padding: 8px; border-radius: 8px; cursor: pointer; display: flex; gap: 10px; align-items: center; }
    .video-card:hover { border-color: #38bdf8; }
    .video-card.active { border-color: #38bdf8; background: #1e3a5f; }
    .thumb { width: 68px; height: 42px; background: #000; border-radius: 4px; object-fit: cover; }
    .meta { flex: 1; overflow: hidden; }
    .meta-title { font-size: 12px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: #f1f5f9; }
    .meta-sub { font-size: 11px; color: #94a3b8; }
    .player-box { background: #000; border-radius: 10px; overflow: hidden; width: 100%; aspect-ratio: 16/9; display: flex; justify-content: center; align-items: center; }
    video { width: 100%; height: 100%; }
    .btn-download-main { width: 100%; background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; padding: 12px; font-size: 14px; font-weight: 700; border: none; border-radius: 8px; cursor: pointer; margin-top: 8px; }
    .btn-download-main:disabled { background: #374151; color: #9ca3af; cursor: not-allowed; }
    .actions { display: flex; gap: 8px; margin-top: 8px; }
    .btn-action { flex: 1; padding: 9px; background: #1f2937; border: 1px solid #374151; color: #e2e8f0; font-size: 12px; border-radius: 6px; cursor: pointer; text-align: center; }
    .status-msg { font-size: 12px; padding: 10px; border-radius: 6px; display: none; }
    .status-loading { background: #1e3a5f; color: #7dd3fc; display: block; }
    .status-error { background: #451a1a; color: #fca5a5; display: block; }
    .download-status { font-size: 12px; padding: 10px; border-radius: 8px; text-align: center; display: none; margin-top: 8px; }
  </style>
</head>
<body>
  <div class="header">
    <div class="title">BlinkNote & Jotted Video Studio Pro</div>
    <div class="badge">● Render Cloud Online</div>
  </div>

  <div class="container">
    <div class="panel">
      <div class="input-box">
        <label>শেয়ার লিংক বা আইডি দিন:</label>
        <input type="text" id="shareUrl" placeholder="https://jottedlgkq.com/s/... বা আইডি">
      </div>
      <button class="btn-primary" onclick="resolveVideo()">ভিডিও বের করুন</button>
      <div id="statusBox" class="status-msg"></div>

      <label style="margin-top: 8px;">ভিডিও তালিকা:</label>
      <div class="video-list" id="videoList">
        <div style="color: #64748b; font-size: 12px; text-align: center; padding: 20px;">কোনো লিংক দেওয়া হয়নি</div>
      </div>
    </div>

    <div class="panel">
      <div class="player-box">
        <video id="player" controls autoplay></video>
      </div>

      <button id="downloadBtn" class="btn-download-main" onclick="downloadCurrentVideo()">
        📥 সরাসরি MP4 ডাউনলোড করুন
      </button>

      <div id="downloadNotice" class="download-status"></div>
      
      <div class="actions">
        <button class="btn-action" onclick="copyM3u8()">🔗 m3u8 লিংক কপি</button>
        <button class="btn-action" onclick="copyFfmpeg()">📋 FFmpeg কমান্ড কপি</button>
      </div>
    </div>
  </div>

  <script>
    let currentM3u8 = "", currentTitle = "", hls = null;

    async function resolveVideo() {
      const input = document.getElementById('shareUrl').value.trim();
      const statusBox = document.getElementById('statusBox');
      const listContainer = document.getElementById('videoList');
      if (!input) return alert('অনুগ্রহ করে লিংক দিন!');

      statusBox.className = 'status-msg status-loading';
      statusBox.innerText = 'সার্ভার থেকে ভিডিও ডাটা সংগ্রহ হচ্ছে...';

      try {
        const res = await fetch('/api/extract', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url: input })
        });
        const data = await res.json();
        if (!data.success) throw new Error(data.error);

        statusBox.style.display = 'none';
        listContainer.innerHTML = '';

        data.videos.forEach((vid, index) => {
          const card = document.createElement('div');
          card.className = 'video-card' + (index === 0 ? ' active' : '');
          card.innerHTML = `
            <img class="thumb" src="${vid.thumbnail || 'https://via.placeholder.com/68x42'}" alt="thumb">
            <div class="meta">
              <div class="meta-title">${vid.title}</div>
              <div class="meta-sub">${vid.size ? (vid.size / (1024*1024)).toFixed(1) + ' MB' : 'Stream Ready'}</div>
            </div>
          `;
          card.onclick = () => {
            document.querySelectorAll('.video-card').forEach(c => c.classList.remove('active'));
            card.classList.add('active');
            playStream(vid.m3u8, vid.title);
          };
          listContainer.appendChild(card);
        });

        if (data.videos.length > 0) playStream(data.videos[0].m3u8, data.videos[0].title);
      } catch (err) {
        statusBox.className = 'status-msg status-error';
        statusBox.innerText = 'ব্যর্থ: ' + err.message;
      }
    }

    function playStream(url, title) {
      currentM3u8 = url; currentTitle = title;
      const video = document.getElementById('player');
      document.getElementById('downloadNotice').style.display = 'none';

      if (Hls.isSupported()) {
        if (hls) hls.destroy();
        hls = new Hls();
        hls.loadSource(url);
        hls.attachMedia(video);
        hls.on(Hls.Events.MANIFEST_PARSED, () => video.play());
      } else { video.src = url; }
    }

    async function downloadCurrentVideo() {
      if (!currentM3u8) return alert('আগে একটি ভিডিও সিলেক্ট করুন!');
      const btn = document.getElementById('downloadBtn');
      const notice = document.getElementById('downloadNotice');
      
      btn.disabled = true;
      btn.innerText = '⏳ ক্লাউডে MP4 তৈরি হচ্ছে...';
      notice.style.display = 'block';
      notice.style.background = '#1e3a5f';
      notice.style.color = '#7dd3fc';
      notice.innerText = 'সার্ভারে ভিডিও জোড়া লাগানো হচ্ছে, কয়েক সেকেন্ড অপেক্ষা করুন...';

      try {
        const res = await fetch('/api/download', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ m3u8: currentM3u8, title: currentTitle })
        });
        const data = await res.json();
        if (!data.success) throw new Error(data.error);

        const a = document.createElement('a');
        a.href = data.download_url;
        a.download = data.filename;
        document.body.appendChild(a);
        a.click();
        a.remove();

        notice.style.background = '#064e3b';
        notice.style.color = '#34d399';
        notice.innerText = `✅ ডাউনলোড শুরু হয়েছে: ${data.filename}`;
        btn.innerText = '📥 পুনরায় ডাউনলোড করুন';
      } catch (err) {
        notice.style.background = '#451a1a';
        notice.style.color = '#fca5a5';
        notice.innerText = 'ডাউনলোড এরর: ' + err.message;
        btn.innerText = '📥 আবার চেষ্টা করুন';
      } finally { btn.disabled = false; }
    }

    function copyM3u8() {
      if (!currentM3u8) return alert('আগে ভিডিও সিলেক্ট করুন!');
      navigator.clipboard.writeText(currentM3u8);
      alert('m3u8 লিংক কপি হয়েছে!');
    }

    function copyFfmpeg() {
      if (!currentM3u8) return alert('আগে ভিডিও সিলেক্ট করুন!');
      navigator.clipboard.writeText(`ffmpeg -i "${currentM3u8}" -c copy output.mp4`);
      alert('FFmpeg কমান্ড কপি হয়েছে!');
    }
  </script>
</body>
</html>
"""

class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == '/api/get-download':
            params = urllib.parse.parse_qs(parsed.query)
            filename = params.get('file', [''])[0]
            filepath = os.path.join(DOWNLOAD_DIR, filename)

            if os.path.exists(filepath):
                file_size = os.path.getsize(filepath)
                self.send_response(200)
                self.send_header('Content-Type', 'video/mp4')
                self.send_header('Content-Length', str(file_size))
                quoted = urllib.parse.quote(filename)
                self.send_header('Content-Disposition', f'attachment; filename="{filename}"; filename*=UTF-8\'\'{quoted}')
                self.end_headers()
                with open(filepath, 'rb') as f:
                    while True:
                        buf = f.read(128 * 1024)
                        if not buf:
                            break
                        self.wfile.write(buf)
                return
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b'File not found')
                return

        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(HTML_PAGE.encode('utf-8'))

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)

        if self.path == '/api/extract':
            try:
                body = json.loads(post_data.decode('utf-8'))
                input_url = body.get('url', '')
                match = re.search(r'(\d{15,})', input_url)
                if not match:
                    raise Exception("সঠিক লিংক বা Link ID পাওয়া যায়নি!")

                link_id = match.group(1)
                api_url = "https://api.cshsnpcwio.com/v1/h5_open_data"
                headers = {
                    "accept": "application/json, text/plain, */*",
                    "content-type": "application/json",
                    "origin": "https://www.jottedctbb.com",
                    "referer": "https://www.jottedctbb.com/",
                    "user-agent": "Mozilla/5.0 (Linux; Android 16; Pixel 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Mobile Safari/537.36"
                }
                payload = {
                    "uid": "",
                    "dir_id": "",
                    "link_id": link_id,
                    "open_link": True,
                    "page_size": 50,
                    "current_page": 1
                }

                res = requests.post(api_url, json=payload, headers=headers, timeout=12)
                raw_json = res.json()
                videos_data = raw_json.get('files') or raw_json.get('top100_view_count_videos') or raw_json.get('recent_videos') or []
                if not videos_data:
                    raise Exception("সার্ভার থেকে কোনো ভিডিও পাওয়া যায়নি।")

                results = []
                for item in videos_data:
                    meta = item.get('file_meta', {})
                    thumb = meta.get('thumbnail', '')
                    cat_match = re.search(r'xbox/(\d+)/', thumb)
                    cat_id = cat_match.group(1) if cat_match else ''
                    storage_id = meta.get('storage_id', '')

                    if cat_id and storage_id:
                        m3u8_url = f"https://www.pbcshsnp.com/xbox/{cat_id}/{storage_id}/{storage_id}.m3u8"
                        results.append({
                            "title": meta.get('display_name', 'Unnamed Video'),
                            "thumbnail": thumb,
                            "size": meta.get('size', 0),
                            "m3u8": m3u8_url
                        })

                response_payload = {"success": True, "videos": results}
            except Exception as e:
                response_payload = {"success": False, "error": str(e)}

            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(response_payload).encode('utf-8'))
            return

        if self.path == '/api/download':
            try:
                body = json.loads(post_data.decode('utf-8'))
                m3u8_url = body.get('m3u8', '')
                title = body.get('title', 'video')

                safe_title = re.sub(r'[\\/*?:"<>|]', '', title).replace('.mp4', '').strip()
                if not safe_title:
                    safe_title = f"video_{int(time.time())}"

                output_filename = f"{safe_title}.mp4"
                output_path = os.path.join(DOWNLOAD_DIR, output_filename)

                if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                    cmd = ['ffmpeg', '-y', '-i', m3u8_url, '-c', 'copy', output_path]
                    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    if proc.returncode != 0:
                        raise Exception("FFmpeg এরর: " + proc.stderr.decode('utf-8', errors='ignore')[-200:])

                file_size = os.path.getsize(output_path)
                encoded_name = urllib.parse.quote(output_filename)
                response_payload = {
                    "success": True,
                    "filename": output_filename,
                    "size": file_size,
                    "download_url": f"/api/get-download?file={encoded_name}"
                }
            except Exception as e:
                response_payload = {"success": False, "error": str(e)}

            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(response_payload).encode('utf-8'))
            return

    def log_message(self, format, *args):
        return

def main():
    print(f"Server listening on 0.0.0.0:{PORT}...")
    server = HTTPServer(('0.0.0.0', PORT), RequestHandler)
    server.serve_forever()

if __name__ == '__main__':
    main()