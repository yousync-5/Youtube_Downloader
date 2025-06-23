from flask import Flask, request, jsonify
from downloader.youtube_downloader import download_audio

app = Flask(__name__)

@app.route('/download', methods=['POST'])
def download():
    data = request.json
    url = data.get('url')
    mp3_path = download_audio(url)
    return jsonify({'status': 'ok', 'path': mp3_path})

if __name__ == '__main__':
    app.run(debug=True)