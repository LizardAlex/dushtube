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

            video_stream_url = video_format['url']
            audio_stream_url = audio_format['url'] if audio_format else None

            return stream_video_with_audio(video_stream_url, audio_stream_url)

    except Exception as e:
        print(f"Error during streaming: {str(e)}")
        return f"Error: {str(e)}", 500

def stream_video_with_audio(video_url, audio_url):
    ffmpeg_cmd = [
        'ffmpeg',
        '-i', video_url,
        '-c:v', 'copy',
    ]

    if audio_url:
        ffmpeg_cmd.extend(['-i', audio_url, '-c:a', 'aac', '-strict', 'experimental', '-bsf:a', 'aac_adtstoasc'])

    ffmpeg_cmd.extend([
        '-f', 'mp4',
        '-movflags', 'frag_keyframe+empty_moov+faststart',
        'pipe:1'
    ])

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

    headers = {
        'Content-Type': 'video/mp4',
        'Accept-Ranges': 'bytes'
    }

    return Response(stream_with_context(generate()), headers=headers)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
