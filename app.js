const express = require('express');
const ytdl = require('ytdl-core');

const app = express();
const port = 3000;

app.get('/watch', async (req, res) => {
    const videoId = req.query.v;

    if (!videoId) {
        return res.status(400).send('No video ID provided.');
    }

    const videoUrl = `https://www.youtube.com/watch?v=${videoId}`;

    // Проверка валидности ссылки
    if (!ytdl.validateURL(videoUrl)) {
        return res.status(400).send('Invalid YouTube URL.');
    }

    try {
        console.log(`Requesting video: ${videoUrl}`);
        
        // Запрашиваем видео с YouTube и передаем его клиенту
        const stream = ytdl(videoUrl, {
            quality: 'highest',
            filter: 'audioandvideo',
        });

        // Настройка заголовков для корректного воспроизведения
        res.setHeader('Content-Type', 'video/mp4');
        res.setHeader('Content-Disposition', 'inline; filename="video.mp4"');

        // Передача видео потока клиенту
        stream.pipe(res);

        stream.on('end', () => {
            console.log('Video streaming ended successfully.');
        });

        stream.on('error', (error) => {
            console.error('Error during streaming:', error);
            res.status(500).send('Error during video streaming.');
        });

    } catch (error) {
        console.error('Error retrieving video or streaming:', error);
        res.status(500).send('Error retrieving video or streaming.');
    }
});

app.listen(port, () => {
    console.log(`Server is running on http://localhost:${port}`);
});
