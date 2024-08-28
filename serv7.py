import subprocess
from flask import Flask, request, render_template, Response, stream_with_context
import yt_dlp
import requests
import re

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
            
            # Найти видео и аудио потоки
            video_format = next(fmt for fmt in formats if fmt['format_id'] == quality and fmt['vcodec'] != 'none')
            audio_format = next(fmt for fmt in formats if fmt['acodec'] != 'none' and fmt['vcodec'] == 'none')

            video_stream_url = video_format['url']
            audio_stream_url = audio_format['url']

            # Использование ffmpeg для объединения потоков на лету
            ffmpeg_cmd = [
                'ffmpeg',
                '-i', video_stream_url,
                '-i', audio_stream_url,
                '-c', 'copy',
                '-f', 'mp4',
                '-movflags', 'frag_keyframe+empty_moov',
                'pipe:1'
            ]

            def generate():
                process = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                while True:
                    data = process.stdout.read(1024)
                    if not data:
                        break
                    yield data
                process.stdout.close()
                process.wait()

            return Response(stream_with_context(generate()), content_type='video/mp4')

    except Exception as e:
        print(f"Error during streaming: {str(e)}")
        return f"Error: {str(e)}", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
