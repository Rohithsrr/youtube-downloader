import os
import shutil
import tempfile
import traceback
from flask import Flask, render_template, request as flask_request, jsonify, send_file, after_this_request
import yt_dlp

# Add local ./bin directory to PATH if present (for static ffmpeg on Render)
local_bin = os.path.join(os.path.dirname(__file__), 'bin')
if os.path.exists(local_bin) and local_bin not in os.environ.get('PATH', ''):
    os.environ['PATH'] = local_bin + os.path.pathsep + os.environ.get('PATH', '')

app = Flask(__name__)

# Single Primary Fast Webshare Residential Proxy
PRIMARY_PROXY = 'http://jufzjzml:5ibfzrazhgap@31.59.20.176:6754'

DEFAULT_COOKIES = """# Netscape HTTP Cookie File
.youtube.com	TRUE	/	TRUE	1798089081	VISITOR_PRIVACY_METADATA	CgJJThIEGgAgRg%3D%3D
.youtube.com	TRUE	/	TRUE	1798089081	VISITOR_INFO1_LIVE	u7nb7Mcu6ls
.youtube.com	TRUE	/	TRUE	1819181304	PREF	f7=4100&tz=Asia.Calcutta&f4=4000000&f5=20000
.youtube.com	TRUE	/	TRUE	1791204351	__Secure-BUCKET	CIAG
.youtube.com	TRUE	/	TRUE	1813162597	LOGIN_INFO	AFmmF2swRQIhAIgOEd1a2XI4zwkOub1ppm-drTLxAyAg2EQZ9k2QL7mMAiBkE8nkwU1zSijERylGoJWW3jBeEYRPkINbsklMP4kYuA:QUQ3MjNmenc5TWdYVW9sV1piM3lQZHlhTGFLdnZQTEt2STUwZ0d0ZFVrQmZsZ0E1d1owM2xuanBRTjFEaHJHUWpPTXU4LU83MTJyeE9YcUFTX21rbE85MFZCMGZCMXZyZUYxb196QTZ0Nk5rc0dma3FrMS1DQWs1cDBGMGZOcUNDM05pbGZFNUlMOXBndm1zcnpRT1B5M0Noak5nT0FvSTRR
.youtube.com	TRUE	/	FALSE	1819123809	HSID	AvN5juLVPxa-G5K_n
.youtube.com	TRUE	/	TRUE	1819123809	SSID	ActLeCD2kFJK5T6XM
.youtube.com	TRUE	/	FALSE	1819123809	APISID	v_GrH6QJtJqkqcSF/AoGyXJVnf2P5zYmBO
.youtube.com	TRUE	/	TRUE	1819123809	SAPISID	lGNUPf
.youtube.com	TRUE	/	TRUE	1819123809	__Secure-1PAPISID	lGNUPf
.youtube.com	TRUE	/	TRUE	1819123809	__Secure-3PAPISID	lGNUPf
.youtube.com	TRUE	/	FALSE	1819123809	SID	g.a000AgkHpeb17C4y8tSrGGXzjvsB3j3xFdi2nHPyvEAa32mTH4WNv0U4hMqDT84Zo-n8ufoxfwACgYKASQSARYSFQHGX2MiSaVkzCKrw--CFQNNF6V7-xoVAUF8yKqphNsj4dKMDTnJyRnUsrX80076
.youtube.com	TRUE	/	TRUE	1819123809	__Secure-1PSID	g.a000AgkHpeb17C4y8tSrGGXzjvsB3j3xFdi2nHPyvEAa32mTH4WNv0U4hMqDT84Zo-n8ufoxfwACgYKASQSARYSFQHGX2MiSaVkzCKrw--CFQNNF6V7-xoVAUF8yKqphNsj4dKMDTnJyRnUsrX80076
.youtube.com	TRUE	/	TRUE	1819123809	__Secure-3PSID	g.a000AgkHpeb17C4y8tSrGGXzjvsB3j3xFdi2nHPyvEAa32mTH4WNv0U4hMqDT84Zo-n8ufoxfwACgYKASQSARYSFQHGX2MiSaVkzCKrw--CFQNNF6V7-xoVAUF8yKqphNsj4dKMDTnJyRnUsrX80076"""

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
    return response

def format_as_netscape_cookiefile(text):
    if not text:
        return None
    clean = text.strip().strip('\'"').replace('\\n', '\n').replace('\\r', '').replace('\\t', '\t')
    out_lines = [
        '# Netscape HTTP Cookie File',
        '# https://curl.haxx.se/rfc/cookie_spec.html',
        '# This is a generated file! Do not edit.'
    ]
    
    for line in clean.splitlines():
        line = line.strip().strip('\'"')
        if not line or line.startswith('#'):
            continue
            
        parts = line.split('\t')
        if len(parts) < 7:
            parts = [p for p in line.split(' ') if p]
            
        if len(parts) >= 7:
            domain = parts[0]
            flag1 = parts[1]
            path = parts[2]
            flag2 = parts[3]
            expiration = parts[4]
            name = parts[5]
            value = ' '.join(parts[6:])
            out_lines.append(f"{domain}\t{flag1}\t{path}\t{flag2}\t{expiration}\t{name}\t{value}")

    if len(out_lines) > 3:
        return '\n'.join(out_lines)
    return None

def get_base_ydl_options(extra_opts=None):
    opts = {
        'quiet': True,
        'no_warnings': True,
        'socket_timeout': 4,
    }
    
    cookies_content = (
        os.environ.get("YOUTUBE_COOKIES") or 
        os.environ.get("COOKIES_TEXT") or 
        os.environ.get("COOKIES") or 
        os.environ.get("YT_COOKIES") or
        DEFAULT_COOKIES
    )
    clean_cookies = format_as_netscape_cookiefile(cookies_content)
    if clean_cookies:
        cookie_file_path = os.path.join(tempfile.gettempdir(), 'yt_cookies.txt')
        with open(cookie_file_path, 'w', encoding='utf-8') as f:
            f.write(clean_cookies)
        opts['cookiefile'] = cookie_file_path

    if extra_opts:
        opts.update(extra_opts)
    return opts

def extract_info_with_fallback(url, extra_opts=None):
    download_flag = extra_opts.get('download', False) if extra_opts else False
    errors = []

    # Strategy 1: Primary Residential Proxy + Session Cookies
    try:
        opts = get_base_ydl_options(extra_opts)
        opts['proxy'] = PRIMARY_PROXY
        with yt_dlp.YoutubeDL(opts) as ydl:
            res = ydl.extract_info(url, download=download_flag)
            if res and res.get('formats'):
                return res
            else:
                errors.append("Proxy: No formats")
    except Exception as e:
        errors.append(f"Proxy: {str(e)}")

    # Strategy 2: Direct connection fallback
    try:
        opts = get_base_ydl_options(extra_opts)
        with yt_dlp.YoutubeDL(opts) as ydl:
            res = ydl.extract_info(url, download=download_flag)
            if res and res.get('formats'):
                return res
            else:
                errors.append("Direct: No formats")
    except Exception as e:
        errors.append(f"Direct: {str(e)}")

    raise Exception(" | ".join(errors) if errors else "Extraction failed")

def estimate_size_mb(fmt, duration):
    try:
        filesize = fmt.get('filesize') or fmt.get('filesize_approx')
        if filesize and float(filesize) > 0:
            return round(float(filesize) / (1024 * 1024), 1)
        
        tbr = fmt.get('tbr')
        if not tbr:
            vbr = fmt.get('vbr') or 0
            abr = fmt.get('abr') or 0
            tbr = (vbr + abr) if (vbr or abr) else None

        if tbr and duration and float(tbr) > 0 and float(duration) > 0:
            estimated_bytes = (float(tbr) * 1000.0 * float(duration)) / 8.0
            return round(estimated_bytes / (1024 * 1024), 1)
    except Exception:
        pass
    return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/fetch-info', methods=['POST', 'OPTIONS'])
def fetch_info():
    if flask_request.method == 'OPTIONS':
        return jsonify({}), 200

    data = flask_request.get_json() or {}
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
        seen_format_ids = set()
        
        for fmt in formats:
            fmt_id = str(fmt.get('format_id'))
            if fmt_id in seen_format_ids:
                continue

            ext = fmt.get('ext', '')
            if ext == 'mhtml' or ext == 'storyboard':
                continue

            vcodec = fmt.get('vcodec', '')
            if not vcodec or vcodec == 'none':
                continue

            height = fmt.get('height') or 0
            fps = fmt.get('fps', 0) or 0
            size_mb = estimate_size_mb(fmt, duration)

            h_text = f"{height}p" if height > 0 else "Video"
            fps_text = f" {int(fps)}fps" if fps > 30 else ""
            label = f"{h_text}{fps_text} ({ext.upper()})"
            size_str = f"~{size_mb} MB" if size_mb and size_mb > 0 else "Direct Stream"

            seen_format_ids.add(fmt_id)
            quality_options.append({
                'format_id': fmt_id,
                'height': int(height),
                'label': label,
                'size': size_str
            })

        if not quality_options:
            for fmt in formats:
                ext = fmt.get('ext', '')
                if ext == 'mhtml' or ext == 'storyboard':
                    continue
                fmt_id = str(fmt.get('format_id'))
                if fmt_id in seen_format_ids:
                    continue
                height = fmt.get('height', 0) or 0
                size_mb = estimate_size_mb(fmt, duration)
                h_text = f"{height}p" if height > 0 else "Download"
                label = f"{h_text} ({ext.upper() if ext else 'MP4'})"
                size_str = f"~{size_mb} MB" if size_mb and size_mb > 0 else "Direct Stream"
                seen_format_ids.add(fmt_id)
                quality_options.append({
                    'format_id': fmt_id,
                    'height': int(height),
                    'label': label,
                    'size': size_str
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
        clean_err = str(e).encode('ascii', 'ignore').decode('ascii')
        return jsonify({'error': clean_err or 'Failed to extract video details.'}), 400

@app.route('/get-download-link', methods=['POST', 'OPTIONS'])
def get_download_link():
    if flask_request.method == 'OPTIONS':
        return jsonify({}), 200

    data = flask_request.get_json() or {}
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
        clean_err = str(e).encode('ascii', 'ignore').decode('ascii')
        return jsonify({'error': clean_err or 'Failed to get stream URL.'}), 400

@app.route('/download')
def download_stream():
    url = flask_request.args.get('url', '').strip()
    format_id = flask_request.args.get('format_id', '').strip()

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
        clean_err = str(e).encode('ascii', 'ignore').decode('ascii')
        return jsonify({'error': clean_err or 'Failed to download video.'}), 400

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)