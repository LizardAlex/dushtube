from flask import Flask, request, send_file
import yt_dlp
import io

app = Flask(__name__)

@app.route('/watch', methods=['GET'])
def watch():
    video_id = request.args.get('v')
    if not video_id:
        return "No video ID provided.", 400

    video_url = f"https://www.youtube.com/watch?v={video_id}"

    try:
        ydl_opts = {
            'format': 'best',
            'noplaylist': True,
            'quiet': True,
        }

        # Загружаем видео в буфер
        buffer = io.BytesIO()
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(video_url, download=False)
            video_stream_url = result['url']

        return send_file(io.BytesIO(requests.get(video_stream_url).content),
                         as_attachment=False,
                         mimetype='video/mp4',
                         download_name='video.mp4')

    except Exception as e:
        return f"Error: {str(e)}", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
