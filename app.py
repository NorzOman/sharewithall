from flask import Flask, request, render_template, jsonify, send_file
import base64
import os
import time
import threading
import random
from io import BytesIO
from threading import Lock


app = Flask(__name__)
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')


# Store uploaded files in memory (key = random ID, value = { filename, filedata, mime_type })
global_files = {}
files_lock = Lock()


def cleanup_expired_files():
    """Cleanup expired files every 5 minutes"""
    while True:
        time.sleep(300)  # Sleep for 5 minutes
        current_time = time.time()
        
        with files_lock:
            # Create list of expired keys to avoid modifying dict during iteration
            expired_keys = [
                key for key, info in global_files.items()
                if current_time - info['created_at'] > 900  # 15 minutes
            ]
            
            # Remove expired files
            for key in expired_keys:
                global_files.pop(key, None)


# Start cleanup thread
cleanup_thread = threading.Thread(target=cleanup_expired_files, daemon=True)
cleanup_thread.start()


@app.route('/')
def base():
    try:
        all_files = []
        current_time = time.time()
        
        with files_lock:
            for route_id, file_info in global_files.items():
                is_expired = current_time - file_info['created_at'] > 900  # 15 minutes
                if not is_expired:  # Only show non-expired files
                    all_files.append({
                        'route_id': route_id,
                        'filename': file_info['filename'],
                        'created_at': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(file_info['created_at'])),
                        'expires_at': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(file_info['created_at'] + 900))
                    })

        return render_template('base.html', active_files=all_files)
    except Exception as e:
        return jsonify({'error': 'Failed to render template: ' + str(e)}), 500


@app.route('/upload', methods=['POST'])
def upload():
    try:
        data = request.get_json()
        filename = data.get('filename')
        filedata = data.get('filedata')  # Base64 encoded
        mime_type = data.get('mime_type')

        if not filename or not filedata:
            return jsonify({'error': 'Missing file data'}), 400

        try:
            # Validate file size (10MB limit)
            file_size = len(base64.b64decode(filedata))
            if file_size > 10 * 1024 * 1024:  # 10MB in bytes
                return jsonify({'error': 'File size must be less than 10MB'}), 400
        except Exception as e:
            return jsonify({'error': 'Invalid base64 data: ' + str(e)}), 400

        # Generate a 4 digit route ID
        with files_lock:
            while True:
                route_id = str(random.randint(1000, 9999))
                if route_id not in global_files:
                    # Store file data in memory
                    global_files[route_id] = {
                        'filename': filename,
                        'filedata': filedata,
                        'mime_type': mime_type,
                        'created_at': time.time()
                    }
                    break

        return jsonify({'code': route_id})

    except Exception as e:
        return jsonify({'error': 'Upload failed: ' + str(e)}), 500


@app.route('/download/<route_id>')
def download(route_id):
    try:
        with files_lock:
            if route_id not in global_files:
                return jsonify({'error': 'File not found or expired'}), 404

            file_info = global_files[route_id].copy()  # Make a copy to avoid race conditions
            
            # Check if file has expired (15 minutes)
            if time.time() - file_info['created_at'] > 900:
                global_files.pop(route_id, None)
                return jsonify({'error': 'File has expired'}), 404

        try:
            file_bytes = base64.b64decode(file_info['filedata'])
        except Exception as e:
            return jsonify({'error': 'Invalid file data: ' + str(e)}), 500

        try:
            # Create BytesIO object instead of raw bytes
            file_stream = BytesIO(file_bytes)
            file_stream.seek(0)  # Ensure stream is at start
            
            return send_file(
                path_or_file=file_stream,
                mimetype=file_info['mime_type'],
                as_attachment=True,
                download_name=file_info['filename']
            )
        except Exception as e:
            return jsonify({'error': 'Failed to send file: ' + str(e)}), 500

    except Exception as e:
        return jsonify({'error': 'Download failed: ' + str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
