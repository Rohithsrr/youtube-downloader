import os
import traceback
from flask import Flask, render_template, request, jsonify
import yt_dlp

try:
    from yt_dlp.networking.impersonate import ImpersonateTarget
    IMPERSONATE_CHROME = ImpersonateTarget('chrome')
except Exception:
    IMPERSONATE_CHROME = 'chrome'

app = Flask(__name__)

def get_yt_dlp_options(extra_opts=None):
    opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'impersonate': IMPERSONATE_CHROME,
    }
    if extra_opts:
        opts.update(extra_opts)
    return opts

def format_filesize_mb(bytes_size, tbr=None, duration=None):
    try:
        if bytes_size and float(bytes_size) > 0:
            return round(float(bytes_size) / (1024 * 1024), 2)
        if tbr and duration and float(tbr) > 0 and float(duration) > 0:
            estimated_bytes = (float(tbr) * 1000 * float(duration)) / 8
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
        ydl_opts = get_yt_dlp_options()
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
        title = info.get('title', 'Unknown Title')
        thumbnail = info.get('thumbnail', '')
        duration = info.get('duration', 0)
        formats = info.get('formats', [])
        
        quality_options = []
        seen_keys = set()

        for fmt in formats:
            format_id = fmt.get('format_id')
            vcodec = fmt.get('vcodec')
            acodec = fmt.get('acodec')
            height = fmt.get('height')
            ext = fmt.get('ext', 'mp4')
            fps = fmt.get('fps')
            filesize = fmt.get('filesize') or fmt.get('filesize_approx')
            
            tbr = fmt.get('tbr')
            if not tbr:
                vbr = fmt.get('vbr') or 0
                abr = fmt.get('abr') or 0
                tbr = vbr + abr if (vbr or abr) else None

            size_mb = format_filesize_mb(filesize, tbr, duration)
            size_str = f"~{size_mb} MB" if size_mb else "Unknown size"

            has_video = vcodec and vcodec != 'none'
            has_audio = acodec and acodec != 'none'

            # Check if format has video
            if has_video and height:
                try:
                    fps_val = int(fps) if fps else 0
                except Exception:
                    fps_val = 0
                
                fps_text = f" {fps_val}fps" if fps_val > 30 else ""
                label = f"{height}p{fps_text} ({ext.upper()})"
                sort_val = int(height) * 100 + fps_val
                type_name = "Video"
                key = (height, ext, fps_val)
            elif has_audio and not has_video:
                abr_val = fmt.get('abr')
                try:
                    abr_text = f" ({int(abr_val)} kbps)" if abr_val else ""
                except Exception:
                    abr_text = ""

                label = f"Audio Only{abr_text} ({ext.upper()})"
                sort_val = 0
                type_name = "Audio"
                key = ('audio', format_id)
            else:
                continue

            if key not in seen_keys:
                seen_keys.add(key)
                quality_options.append({
                    'format_id': str(format_id),
                    'height': height or 0,
                    'label': label,
                    'ext': ext,
                    'size_mb': size_mb,
                    'size_str': size_str,
                    'type': type_name,
                    'sort_val': sort_val
                })

        # Sort options from highest quality to lowest
        quality_options.sort(key=lambda x: x['sort_val'], reverse=True)

        return jsonify({
            'title': title,
            'thumbnail': thumbnail,
            'duration': duration,
            'options': quality_options
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
        format_rule = f"{format_id}+bestaudio/best" if format_id != 'best' else 'best'
        ydl_opts = get_yt_dlp_options({'format': format_rule})

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        direct_url = None

        # Check standard url
        if info.get('url'):
            direct_url = info.get('url')
        # Check requested_formats array if merged format rule was requested
        elif info.get('requested_formats'):
            req_formats = info.get('requested_formats', [])
            for req in req_formats:
                req_vcodec = req.get('vcodec')
                if req_vcodec and req_vcodec != 'none' and req.get('url'):
                    direct_url = req.get('url')
                    break
            if not direct_url and req_formats and req_formats[0].get('url'):
                direct_url = req_formats[0].get('url')

        if not direct_url:
            return jsonify({'error': 'Could not extract direct stream URL.'}), 500

        return jsonify({'download_url': direct_url})

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)