import os
import base64
from datetime import datetime
from flask import Flask, render_template
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'cambia-esta-key-en-produccion')
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, 'static', 'images')
CATEGORIES = ['tarima', 'carpa', 'hangar', 'varios']

for cat in CATEGORIES:
    os.makedirs(os.path.join(UPLOAD_DIR, cat), exist_ok=True)

def get_catalog():
    catalog = {cat: [] for cat in CATEGORIES}
    for cat in CATEGORIES:
        cat_path = os.path.join(UPLOAD_DIR, cat)
        if os.path.exists(cat_path):
            files = sorted(os.listdir(cat_path), reverse=True)
            for f in files:
                if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                    catalog[cat].append({
                        'filename': f,
                        'url': f'/static/images/{cat}/{f}',
                        'date': datetime.fromtimestamp(
                            os.path.getctime(os.path.join(cat_path, f))
                        ).strftime('%d/%m/%Y %H:%M')
                    })
    return catalog

@app.route('/')
def index():
    return render_template('index.html', catalog=get_catalog())

@socketio.on('connect')
def handle_connect():
    emit('catalog_update', get_catalog())

@socketio.on('upload_image')
def handle_upload(data):
    category = data.get('category', 'varios')
    if category not in CATEGORIES:
        category = 'varios'

    image_data = base64.b64decode(data['image'])
    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}_{data.get('name', 'photo.png')}"
    filepath = os.path.join(UPLOAD_DIR, category, filename)

    with open(filepath, 'wb') as f:
        f.write(image_data)

    emit('catalog_update', get_catalog(), broadcast=True)

@socketio.on('delete_image')
def handle_delete(data):
    category = data.get('category')
    filename = data.get('filename')
    if category in CATEGORIES:
        filepath = os.path.join(UPLOAD_DIR, category, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            emit('catalog_update', get_catalog(), broadcast=True)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False)
