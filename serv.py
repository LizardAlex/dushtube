from flask import Flask, request, send_file, Response
from pytube import YouTube
import io

app = Flask(__name__)

@app.route('/watch', methods=['GET'])
def watch():
    video_id = request.args.get('v')
    if not video_id:
        return "No video ID provided.", 400

    video_url = f"https://www.youtube.com/watch?v={video_id}"

    try:
        # Загружаем информацию о видео с YouTube
        yt = YouTube(video_url)
        stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()

        # Создаём поток данных в памяти для передачи
        video_buffer = io.BytesIO()
        stream.stream_to_buffer(video_buffer)
        video_buffer.seek(0)

        # Отправляем видео пользователю
        return send_file(video_buffer, as_attachment=False, mimetype='video/mp4', download_name='video.mp4')

    except Exception as e:
        return f"Error: {str(e)}", 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
