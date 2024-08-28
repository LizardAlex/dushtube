import subprocess
import re
from flask import Flask, request, render_template, Response, stream_with_context
import yt_dlp
import requests

app = Flask(__name__)

@app.route('/watch', methods=['GET'])
def watch():
    video_id = request.args.get('v')

    if not video_id:
        return "No video ID provided.", 400

    video_url = f"https://www.youtube.com/watch?v={video_id}"

    try:
        print(f"Requesting video: {video_url}")
        
        ydl_opts = {
            'noplaylist': True,
            'quiet': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(video_url, download=False)
            formats = result.get('formats', [])
            available_formats = {fmt['format_id']: fmt for fmt in formats}

            return render_template('video.html', video_id=video_id, available_formats=available_formats)

    except Exception as e:
        print(f"Error during fetching video info: {str(e)}")
        return f"Error: {str(e)}", 500

@app.route('/stream', methods=['GET'])
def stream():
    video_id = request.args.get('v')
    quality = request.args.get('quality', 'best')

    if not video_id:
        return "No video ID provided.", 400

    video_url = f"https://www.youtube.com/watch?v={video_id}"

    try:
        print(f"Requesting video stream for quality: {quality}")

        ydl_opts = {
            'noplaylist': True,
            'quiet': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(video_url, download=False)
            formats = result.get('formats', [])
            
            video_format = next((fmt for fmt in formats if fmt['format_id'] == quality and fmt.get('vcodec') != 'none'), None)
            audio_format = next((fmt for fmt in formats if fmt.get('acodec') != 'none' and fmt.get('vcodec') == 'none'), None)

            if not video_format:
                return "Requested video format not available.", 404

            if not audio_format:
                # Если нет отдельного аудио потока, возвращаем только видео
                video_stream_url = video_format['url']
                return stream_video(video_stream_url, result['duration'])

            video_stream_url = video_format['url']
            audio_stream_url = audio_format['url']

            return stream_video_with_audio(video_stream_url, audio_stream_url, result['duration'])

    except Exception as e:
        print(f"Error during streaming: {str(e)}")
        return f"Error: {str(e)}", 500

def stream_video(url, duration):
    range_header = request.headers.get('Range', None)

    headers = {
        'Content-Type': 'video/mp4',
        'Accept-Ranges': 'bytes',
    }

    if range_header:
        match = re.match(r'bytes=(\d+)-(\d*)', range_header)
        if match:
            start = int(match.group(1))
            end = int(match.group(2)) if match.group(2) else None
            headers['Content-Range'] = f'bytes {start}-{end}/{duration}'
            headers['Content-Length'] = str(end - start + 1 if end else duration - start)
            status_code = 206
        else:
            return "Invalid Range Header", 416
    else:
        start = 0
        status_code = 200

    def generate():
        with requests.get(url, headers={'Range': f'bytes={start}-'}, stream=True) as r:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:
                    yield chunk

    return Response(stream_with_context(generate()), headers=headers, status=status_code)

def stream_video_with_audio(video_url, audio_url, duration):
    range_header = request.headers.get('Range', None)

    ffmpeg_cmd = [
        'ffmpeg',
        '-i', video_url,
        '-i', audio_url,
        '-c:v', 'copy',
        '-c:a', 'aac',
        '-strict', 'experimental',
        '-bsf:a', 'aac_adtstoasc',
        '-f', 'mp4',
        '-movflags', 'frag_keyframe+empty_moov+faststart',
        'pipe:1'
    ]

    headers = {
        'Content-Type': 'video/mp4',
        'Accept-Ranges': 'bytes',
    }

    if range_header:
        range_match = re.match(r'bytes=(\d+)-(\d*)', range_header)
        if range_match:
            start = int(range_match.group(1))
            ffmpeg_cmd.extend(['-ss', str(start / 1000)])  # перемотка на указанное время
            headers['Content-Range'] = f'bytes {start}-{duration}'
            headers['Content-Length'] = str(duration - start)
            status_code = 206
        else:
            return "Invalid Range Header", 416
    else:
        status_code = 200

    def generate():
        process = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        while True:
            data = process.stdout.read(1024)
            if not data:
                break
            yield data

        process.stdout.close()
        process.wait()

        stderr = process.stderr.read().decode('utf-8')
        print(f"FFmpeg stderr: {stderr}")

    headers['Content-Duration'] = str(duration)

    return Response(stream_with_context(generate()), headers=headers, status=status_code)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
