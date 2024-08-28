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

            return stream_video_with_audio_range(video_stream_url, audio_stream_url)

    except Exception as e:
        print(f"Error during streaming: {str(e)}")
        return f"Error: {str(e)}", 500