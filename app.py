import os
import shutil
import tempfile
import traceback
from flask import Flask, render_template, request, jsonify, send_file, after_this_request
import yt_dlp

# Add local ./bin directory to PATH if present (for static ffmpeg on Render)
local_bin = os.path.join(os.path.dirname(__file__), 'bin')
if os.path.exists(local_bin) and local_bin not in os.environ.get('PATH', ''):
    os.environ['PATH'] = local_bin + os.path.pathsep + os.environ.get('PATH', '')

try:
    from yt_dlp.networking.impersonate import ImpersonateTarget
    IMPERSONATE_CHROME = ImpersonateTarget('chrome')
except Exception:
    IMPERSONATE_CHROME = 'chrome'

app = Flask(__name__)

def get_clean_cookies_text(text):
    if not text:
        return None
    # Unescape literal \n, \r, and \t from environment variables
    fixed = text.replace('\\n', '\n').replace('\\r', '').replace('\\t', '\t')
    if len(fixed.strip()) < 50:
        return None
    lines = [line.strip() for line in fixed.splitlines() if line.strip() and not line.strip().startswith('#')]
    if any('youtube' in line.lower() for line in lines):
        return fixed
    return None

def get_base_ydl_options(extra_opts=None):
    opts = {
        'quiet': True,
        'no_warnings': True,
        'impersonate': IMPERSONATE_CHROME,
    }
    
    cookies_content = os.environ.get("YOUTUBE_COOKIES") or os.environ.get("COOKIES_TEXT")
    clean_cookies = get_clean_cookies_text(cookies_content)
    if clean_cookies:
        cookie_file_path = os.path.join(tempfile.gettempdir(), 'yt_cookies.txt')
        with open(cookie_file_path, 'w', encoding='utf-8') as f:
            f.write(clean_cookies)
        opts['cookiefile'] = cookie_file_path

    if extra_opts:
        opts.update(extra_opts)
    return opts

def has_playable_video_formats(info):
    if not info or not info.get('formats'):
        return False
    for fmt in info.get('formats', []):
        vcodec = fmt.get('vcodec')
        ext = fmt.get('ext')
        if vcodec and vcodec != 'none' and ext != 'mhtml':
            return True
    return False

def extract_info_with_fallback(url, extra_opts=None):
    strategies = [
        # Strategy 1: Standard with impersonation & cookies
        get_base_ydl_options(extra_opts),
        
        # Strategy 2: Without impersonate flag
        {**get_base_ydl_options(extra_opts), 'impersonate': None},
        
        # Strategy 3: Local browser cookies fallback (Chrome, Firefox, Edge)
        {**get_base_ydl_options(extra_opts), 'cookiesfrombrowser': ('chrome',)},
        {**get_base_ydl_options(extra_opts), 'cookiesfrombrowser': ('firefox',)},
        {**get_base_ydl_options(extra_opts), 'cookiesfrombrowser': ('edge',)},

        # Strategy 4: Android/iOS player clients (guarantees playable video format on cloud hosting)
        {**get_base_ydl_options(extra_opts), 'extractor_args': {'youtube': {'player_client': ['android', 'ios']}}},
        
        # Strategy 5: Android/iOS without impersonate
        {**get_base_ydl_options(extra_opts), 'impersonate': None, 'extractor_args': {'youtube': {'player_client': ['android', 'ios']}}}
    ]

    last_error = None
    best_res = None
    download_flag = extra_opts.get('download', False) if extra_opts else False

    for opts in strategies:
        try:
            opts_clean = {k: v for k, v in opts.items() if v is not None}
            with yt_dlp.YoutubeDL(opts_clean) as ydl:
                res = ydl.extract_info(url, download=download_flag)
                if has_playable_video_formats(res):
                    return res
                if res and not best_res:
                    best_res = res
        except Exception as e:
            last_error = e

    if best_res:
        return best_res

    raise last_error

def estimate_size_mb(fmt, duration):
    try:
        filesize = fmt.get('filesize') or fmt.get('filesize_approx')
        if filesize and float(filesize) > 0:
            return round(float(filesize) / (1024 * 1024), 2)
        
        tbr = fmt.get('tbr')
        if not tbr:
            vbr = fmt.get('vbr') or 0
            abr = fmt.get('abr') or 0
            tbr = (vbr + abr) if (vbr or abr) else None

        if tbr and duration and float(tbr) > 0 and float(duration) > 0:
            estimated_bytes = (float(tbr) * 1000.0 * float(duration)) / 8.0
            return round(estimated_bytes / (1024 * 1024), 2)
    except Exception:
        pass
    return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/fetch-info', methods=['POST'])
def fetch_info():
    data = request.get_json() or {}
    url = data.get('url', '').strip()
    
    if not url:
        return jsonify({'error': 'Please provide a valid YouTube URL.'}), 400

    try:
        info = extract_info_with_fallback(url, {'format': 'all'})
            
        title = info.get('title', 'Unknown Title')
        thumbnail = info.get('thumbnail', '')
        duration = info.get('duration', 0)
        formats = info.get('formats', [])
        
        quality_options = []
        seen_heights = set()
        
        # Pass 1: Extract video formats with vcodec != 'none'
        for fmt in formats:
            vcodec = fmt.get('vcodec')
            if vcodec == 'none' or not vcodec:
                continue

            height = fmt.get('height') or 0
            fmt_id = fmt.get('format_id')
            fps = fmt.get('fps', 0) or 0
            ext = fmt.get('ext', 'mp4')
            size_mb = estimate_size_mb(fmt, duration)

            h_text = f"{height}p" if height > 0 else "Video"
            fps_text = f" {int(fps)}fps" if fps > 30 else ""
            label = f"{h_text}{fps_text} ({ext.upper()})"
            size_str = f"~{size_mb} MB" if size_mb else "Unknown size"
            
            key = (height, ext)
            if key not in seen_heights:
                seen_heights.add(key)
                quality_options.append({
                    'format_id': str(fmt_id),
                    'height': int(height),
                    'label': label,
                    'size': size_str,
                    'size_mb': size_mb
                })

        # Pass 2: Fallback if no vcodec != 'none' formats found
        if not quality_options:
            for fmt in formats:
                ext = fmt.get('ext', '')
                if ext == 'mhtml' or ext == 'storyboard':
                    continue
                fmt_id = fmt.get('format_id')
                height = fmt.get('height', 0) or 0
                size_mb = estimate_size_mb(fmt, duration)
                h_text = f"{height}p" if height > 0 else "Download"
                label = f"{h_text} ({ext.upper() if ext else 'MP4'})"
                size_str = f"~{size_mb} MB" if size_mb else "Unknown size"
                quality_options.append({
                    'format_id': str(fmt_id),
                    'height': int(height),
                    'label': label,
                    'size': size_str,
                    'size_mb': size_mb
                })

        quality_options.sort(key=lambda x: x['height'], reverse=True)

        return jsonify({
            'title': title,
            'thumbnail': thumbnail,
            'duration': duration,
            'formats': quality_options
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/get-download-link', methods=['POST'])
def get_download_link():
    data = request.get_json() or {}
    url = data.get('url', '').strip()
    format_id = data.get('format_id', '').strip()

    if not url or not format_id:
        return jsonify({'error': 'URL and format_id are required.'}), 400

    try:
        format_rule = f"{format_id}+bestaudio/bestvideo+bestaudio/best/worst" if format_id != 'best' else 'best'
        info = extract_info_with_fallback(url, {'format': format_rule})

        direct_url = None

        if info.get('url'):
            direct_url = info.get('url')
        elif info.get('requested_formats'):
            req_formats = info.get('requested_formats', [])
            for req in req_formats:
                vcodec = req.get('vcodec')
                if vcodec and vcodec != 'none' and req.get('url'):
                    direct_url = req.get('url')
                    break
            if not direct_url and req_formats and req_formats[0].get('url'):
                direct_url = req_formats[0].get('url')

        if not direct_url:
            return jsonify({'error': 'Could not extract direct stream URL.'}), 500

        return jsonify({
            'download_url': direct_url,
            'url': direct_url
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/download')
def download_stream():
    url = request.args.get('url', '').strip()
    format_id = request.args.get('format_id', '').strip()

    if not url or not format_id:
        return jsonify({'error': 'URL and format_id query parameters are required.'}), 400

    temp_dir = tempfile.mkdtemp()
    try:
        outtmpl = os.path.join(temp_dir, 'video.%(ext)s')
        format_rule = f"{format_id}+bestaudio/bestvideo+bestaudio/best/worst" if format_id != 'best' else 'best'
        
        extra_opts = {
            'format': format_rule,
            'merge_output_format': 'mp4',
            'outtmpl': outtmpl,
            'download': True
        }
        
        info = extract_info_with_fallback(url, extra_opts)
        
        mp4_path = os.path.join(temp_dir, 'video.mp4')
        final_path = mp4_path if os.path.exists(mp4_path) else None
        
        if not final_path:
            files = [os.path.join(temp_dir, f) for f in os.listdir(temp_dir)]
            if files:
                final_path = files[0]

        if not final_path or not os.path.exists(final_path):
            return jsonify({'error': 'Failed to process merged video file.'}), 500

        title = info.get('title', 'video')
        safe_title = "".join([c for c in title if c.isalnum() or c in (' ', '-', '_')]).strip() or 'youtube_video'
        height = info.get('height') or ''
        height_str = f"_{height}p" if height else ''
        download_name = f"{safe_title}{height_str}.mp4"

        @after_this_request
        def cleanup(response):
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass
            return response

        return send_file(
            final_path,
            as_attachment=True,
            download_name=download_name,
            mimetype='video/mp4'
        )

    except Exception as e:
        traceback.print_exc()
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)