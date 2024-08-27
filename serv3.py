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

        # Получаем длину видео
        video_length = int(video_stream.headers.get('Content-Length', 0))

        def generate(start, end):
            headers = {'Range': f'bytes={start}-{end}'}
            with requests.get(video_stream_url, headers=headers, stream=True) as r:
                for chunk in r.iter_content(chunk_size=1024):
                    if chunk:
                        yield chunk

        # Обработка диапазонов
        range_header = request.headers.get('Range', None)
        if range_header:
            # Обработка диапазона
            match = re.search(r'bytes=(\d+)-(\d*)', range_header)
            if match:
                start = int(match.group(1))
                end = int(match.group(2)) if match.group(2) else video_length - 1

                # Убедитесь, что диапазон корректен
                if start > end or end >= video_length:
                    return "Requested range not satisfiable.", 416

                # Устанавливаем заголовки для частичного ответа
                response = Response(stream_with_context(generate(start, end)), status=206, content_type='video/mp4')
                response.headers.add('Content-Range', f'bytes {start}-{end}/{video_length}')
                return response

        # Если диапазон не указан, отправляем весь поток
        return Response(stream_with_context(generate(0, video_length - 1)), content_type='video/mp4')

    except Exception as e:
        print(f"Error during streaming: {str(e)}")
        return f"Error: {str(e)}", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)