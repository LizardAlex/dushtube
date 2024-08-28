import subprocess
from flask import Flask, request, render_template, Response
import yt_dlp
import os

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

            # Сначала объединяем видео и аудио в один файл
            output_file = f"/tmp/{video_id}_{quality}.mp4"
            if not os.path.exists(output_file):
                combine_video_audio(video_stream_url, audio_stream_url, output_file)

            # Теперь стримим объединенный файл
            return stream_combined_file(output_file, result['duration'])

    except Exception as e:
        print(f"Error during streaming: {str(e)}")
        return f"Error: {str(e)}", 500

def combine_video_audio(video_url, audio_url, output_file):
    ffmpeg_cmd = [
        'ffmpeg',
        '-i', video_url,
        '-i', audio_url,
        '-c:v', 'copy',
        '-c:a', 'aac',
        '-strict', 'experimental',
        '-bsf:a', 'aac_adtstoasc',
        '-f', 'mp4',
        '-movflags', 'faststart',
        output_file
    ]
    
    subprocess.run(ffmpeg_cmd, check=True)

def stream_combined_file(file_path, duration):
    def generate():
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(1024)
                if not chunk:
                    break
                yield chunk

    file_size = os.path.getsize(file_path)
    headers = {
        'Content-Length': str(file_size),
        'Content-Duration': str(duration),
        'Content-Type': 'video/mp4',
        'Accept-Ranges': 'bytes'
    }
    
    return Response(stream_with_context(generate()), headers=headers)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
