import os
import yt_dlp
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

YDL_OPTS_BASE = {
    'impersonate': 'chrome',
    'player_client': ['web', 'android'],
    'quiet': True,
    'no_warnings': True,
    'skip_download': True,
}

def format_size(size_bytes):
    if size_bytes is None:
        return "Unknown"
    return f"{size_bytes / (1024 * 1024):.1f} MB"

def extract_formats(info):
    formats = info.get('formats', [])
    video_formats = {}
    
    for f in formats:
        height = f.get('height')
        if not height or not f.get('vcodec') or f.get('vcodec') == 'none':
            continue
        if f.get('acodec') != 'none':
            continue
        
        format_id = f.get('format_id')
        filesize = f.get('filesize') or f.get('filesize_approx')
        
        if height not in video_formats or (filesize and (not video_formats[height].get('filesize') or filesize > video_formats[height]['filesize'])):
            video_formats[height] = {
                'format_id': format_id,
                'height': height,
                'filesize': filesize,
                'ext': f.get('ext', 'mp4'),
                'fps': f.get('fps'),
                'vcodec': f.get('vcodec'),
            }
    
    sorted_formats = sorted(video_formats.values(), key=lambda x: x['height'], reverse=True)
    return [
        {
            'format_id': f['format_id'],
            'label': f"{f['height']}p{f' @ {f[\"fps\"]}fps' if f.get('fps') else ''}",
            'size': format_size(f['filesize']),
            'height': f['height'],
        }
        for f in sorted_formats
    ]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/fetch-info', methods=['POST'])
def fetch_info():
    data = request.get_json()
    url = data.get('url', '').strip()
    
    if not url:
        return jsonify({'error': 'No URL provided'}), 400
    
    if 'youtube.com' not in url and 'youtu.be' not in url:
        return jsonify({'error': 'Please provide a valid YouTube URL'}), 400
    
    ydl_opts = {**YDL_OPTS_BASE}
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            formats = extract_formats(info)
            
            return jsonify({
                'title': info.get('title', 'Unknown Title'),
                'thumbnail': info.get('thumbnail', ''),
                'duration': info.get('duration'),
                'formats': formats,
            })
    except yt_dlp.utils.DownloadError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'Error fetching video info: {str(e)}'}), 500

@app.route('/get-download-link', methods=['POST'])
def get_download_link():
    data = request.get_json()
    url = data.get('url', '').strip()
    format_id = data.get('format_id', '').strip()
    
    if not url or not format_id:
        return jsonify({'error': 'URL and format_id are required'}), 400
    
    ydl_opts = {
        **YDL_OPTS_BASE,
        'format': f"{format_id}+bestaudio/best",
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            url = info.get('url')
            if not url and 'requested_formats' in info:
                for f in info['requested_formats']:
                    if f.get('vcodec') != 'none':
                        url = f.get('url')
                        break
            
            if not url:
                return jsonify({'error': 'Could not extract direct stream URL'}), 500
            
            return jsonify({'url': url})
    except yt_dlp.utils.DownloadError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'Error extracting download link: {str(e)}'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)