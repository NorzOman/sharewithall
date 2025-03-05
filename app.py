from flask import Flask, request, render_template, jsonify, send_file
import base64
import os
import time
import threading
import random
from io import BytesIO


app = Flask(__name__)

# Store uploaded files in memory (key = random ID, value = { filename, filedata, mime_type })
global_files = {}

@app.route('/')
def base():
    try:
        return render_template('base.html')
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
        while True:
            route_id = str(random.randint(1000, 9999))
            if route_id not in global_files:
                break
        
        try:
            # Store file data in memory
            global_files[route_id] = {
                'filename': filename,
                'filedata': filedata,
                'mime_type': mime_type,
                'created_at': time.time()
            }

            # Schedule deletion after 1 hour
            threading.Timer(3600, lambda: global_files.pop(route_id, None)).start()
        except Exception as e:
            return jsonify({'error': 'Failed to store file: ' + str(e)}), 500

        return jsonify({'code': route_id})

    except Exception as e:
        return jsonify({'error': 'Upload failed: ' + str(e)}), 500

@app.route('/download/<route_id>')
def download(route_id):
    try:
        if route_id not in global_files:
            return jsonify({'error': 'File not found or expired'}), 404

        file_info = global_files[route_id]
        
        # Check if file has expired (1 hour)
        if time.time() - file_info['created_at'] > 3600:
            try:
                global_files.pop(route_id, None)
            except Exception:
                pass  # Ignore error if key was already removed
            return jsonify({'error': 'File has expired'}), 404

        try:
            file_bytes = base64.b64decode(file_info['filedata'])
        except Exception as e:
            return jsonify({'error': 'Invalid file data: ' + str(e)}), 500

        try:
            # Create BytesIO object instead of raw bytes
            file_stream = BytesIO(file_bytes)
            
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
