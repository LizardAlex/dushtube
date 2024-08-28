from flask import Flask, request, render_template, Response, stream_with_context
import yt_dlp
import subprocess

app = Flask(__name__)

# Глобальный словарь для хранения длительности видео
video_durations = {}

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
            
            # Получаем длительность видео
            duration = result.get('duration', 0)
            video_durations[video_id] = duration  # Сохраняем длительность в глобальном словаре

            return render_template('video.html', video_id=video_id, available_formats=available_formats, duration=duration)

    except Exception as e:
        print(f"Error during fetching video info: {str(e)}")
        return f"Error: {str(e)}", 500

@app.route('/stream', methods=['GET'])
def stream():
    video_id = request.args.get('v')
    quality = request.args.get('quality', 'best')

    if not video_id:
        return "No video ID provided.", 400

    try:
        print(f"Requesting video stream for quality: {quality}")

        # Получаем сохраненную длительность
        duration = video_durations.get(video_id, 0)

        # Если длительность не найдена, возвращаем ошибку
        if duration == 0:
            return "Video duration not available.", 404

        # Получаем информацию о формате
        ydl_opts = {
            'noplaylist': True,
            'quiet': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
            formats = result.get('formats', [])
            
            video_format = next((fmt for fmt in formats if fmt['format_id'] == quality and fmt.get('vcodec') != 'none'), None)
            audio_format = next((fmt for fmt in formats if fmt.get('acodec') != 'none' and fmt.get('vcodec') == 'none'), None)

            if not video_format:
                return "Requested video format not available.", 404

            video_stream_url = video_format['url']
            audio_stream_url = audio_format['url'] if audio_format else None

            return stream_video_with_audio_range(video_stream_url, audio_stream_url, duration)

    except Exception as e:
        print(f"Error during streaming: {str(e)}")
        return f"Error: {str(e)}", 500

def stream_video_with_audio_range(video_url, audio_url, duration):
    ffmpeg_cmd = [
        'ffmpeg',
        '-i', video_url,
        '-i', audio_url if audio_url else 'anullsrc=r=44100:cl=stereo',
        '-c:v', 'copy',
        '-c:a', 'aac',
        '-strict', 'experimental',
        '-bsf:a', 'aac_adtstoasc',
        '-f', 'mp4',
        '-movflags', 'frag_keyframe+empty_moov+faststart',
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

    response = Response(stream_with_context(generate()), content_type='video/mp4')
    
    # Передаем длительность в заголовке
    response.headers['X-Video-Duration'] = str(duration)  
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)