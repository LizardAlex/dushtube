import subprocess
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

def stream_video(video_url, duration):
    def generate():
        with requests.get(video_url, stream=True) as r:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:
                    yield chunk

    headers = {
        'Content-Type': 'video/mp4',
        'Accept-Ranges': 'bytes',
        'Content-Duration': str(duration),
    }
    
    return Response(stream_with_context(generate()), headers=headers)

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

    if range_header:
        range_match = re.match(r'bytes=(\d+)-(\d*)', range_header)
        if range_match:
            start = range_match.group(1)
            end = range_match.group(2)
            ffmpeg_cmd.extend(['-ss', start])
            if end:
                ffmpeg_cmd.extend(['-t', str(int(end) - int(start))])

    def generate():
        process = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        while True:
            data = process.stdout.read(1024)
            if not data:
                break
            yield data

        process.stdout.close()
        process.wait()

        # Добавляем вывод ошибок ffmpeg
        stderr = process.stderr.read().decode('utf-8')
        print(f"FFmpeg stderr: {stderr}")

    headers = {
        'Content-Type': 'video/mp4',
        'Accept-Ranges': 'bytes',
        'Content-Duration': str(duration),
    }

    return Response(stream_with_context(generate()), headers=headers)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
