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
            available_formats = {fmt['format_id']: fmt for fmt in result.get('formats', [])}

            if quality not in available_formats:
                print(f"Requested format '{quality}' is not available. Falling back to 'best'.")
                quality = 'best'

            video_stream_url = available_formats[quality]['url']
            print(f"Video stream URL retrieved: {video_stream_url}")

        video_stream = requests.get(video_stream_url, stream=True)
        video_length = int(video_stream.headers.get('Content-Length', 0))

        def generate(start, end):
            headers = {'Range': f'bytes={start}-{end}'}
            with requests.get(video_stream_url, headers=headers, stream=True) as r:
                for chunk in r.iter_content(chunk_size=1024):
                    if chunk:
                        yield chunk

        range_header = request.headers.get('Range', None)
        if range_header:
            match = re.search(r'bytes=(\d+)-(\d*)', range_header)
            if match:
                start = int(match.group(1))
                end = int(match.group(2)) if match.group(2) else video_length - 1

                if start > end or end >= video_length:
                    return "Requested range not satisfiable.", 416

                response = Response(stream_with_context(generate(start, end)), status=206, content_type='video/mp4')
                response.headers.add('Content-Range', f'bytes {start}-{end}/{video_length}')
                return response

        return Response(stream_with_context(generate(0, video_length - 1)), content_type='video/mp4')

    except Exception as e:
        print(f"Error during streaming: {str(e)}")
        return f"Error: {str(e)}", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)