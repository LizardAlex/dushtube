from flask import Flask, request, Response, stream_with_context
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
            'format': 'best',
            'noplaylist': True,
            'quiet': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(video_url, download=False)
            video_stream_url = result['url']
            print(f"Video stream URL retrieved: {video_stream_url}")

        # Получаем видеопоток в режиме стриминга
        video_stream = requests.get(video_stream_url, stream=True)

        def generate():
            for chunk in video_stream.iter_content(chunk_size=1024):
                if chunk:
                    yield chunk

        # Отправляем поток данных клиенту напрямую
        return Response(stream_with_context(generate()), content_type='video/mp4')

    except Exception as e:
        print(f"Error during streaming: {str(e)}")
        return f"Error: {str(e)}", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
