import subprocess
import os
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

            video_url = video_format['url']
            audio_url = audio_format['url']

            # Временные файлы
            video_file = f"/tmp/{video_id}_video.mp4"
            audio_file = f"/tmp/{video_id}_audio.mp4"
            output_file = f"/tmp/{video_id}_output.mp4"

            # Загрузка видео и аудио
            with open(video_file, 'wb') as vf, open(audio_file, 'wb') as af:
                vf.write(requests.get(video_url).content)
                af.write(requests.get(audio_url).content)

            # Объединение видео и аудио с помощью ffmpeg
            ffmpeg_cmd = [
                'ffmpeg', '-i', video_file, '-i', audio_file, '-c', 'copy', output_file
            ]
            subprocess.run(ffmpeg_cmd, check=True)

            # Стриминг объединенного файла
            def generate():
                with open(output_file, 'rb') as f:
                    while chunk := f.read(1024):
                        yield chunk

            response = Response(stream_with_context(generate()), content_type='video/mp4')

            # Удаление временных файлов
            os.remove(video_file)
            os.remove(audio_file)
            os.remove(output_file)

            return response

    except Exception as e:
        print(f"Error during streaming: {str(e)}")
        return f"Error: {str(e)}", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
