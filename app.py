from flask import Flask, request, render_template, jsonify, send_file, redirect, session
import base64
import os
import time
import threading
import random
from io import BytesIO
from threading import Lock
import jwt
from datetime import datetime, timedelta


app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')
JWT_SECRET = os.getenv('JWT_SECRET')  # Secret key for JWT

# Global maintenance mode flag
MAINTENANCE_MODE = False

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


def generate_token():
    """Generate JWT token for admin authentication"""
    expiration = datetime.utcnow() + timedelta(hours=1)
    token = jwt.encode(
        {'admin': True, 'exp': expiration},
        JWT_SECRET,
        algorithm='HS256'
    )
    return token


def verify_token(token):
    """Verify JWT token"""
    try:
        jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return True
    except:
        return False


@app.before_request
def check_maintenance():
    if MAINTENANCE_MODE and not request.path.startswith('/admin') and not request.path.startswith('/static'):
        if request.method == 'GET':
            return render_template('error.html', message="Oops! Seems like the website is down for maintenance or has been taken down by the admin for now. Please try again later."), 503
        return jsonify({'error': 'Site is under maintenance'}), 503


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


@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == ADMIN_PASSWORD:
            token = generate_token()
            session['admin_token'] = token  # Store JWT token in session
            return redirect('/admin/control_panel')
        else:
            return render_template('admin_login.html', error='Invalid password')
    return render_template('admin_login.html')


@app.route('/admin/control_panel', methods=['GET', 'POST'])
def control_panel():
    global MAINTENANCE_MODE
    token = session.get('admin_token')
    if not token or not verify_token(token):
        return redirect('/admin')
        
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'clear_memory':
            with files_lock:
                global_files.clear()
            return jsonify({'success': True})
        elif action == 'take_down':
            MAINTENANCE_MODE = True
            return jsonify({'success': True})
        elif action == 'bring_up':
            MAINTENANCE_MODE = False
            return jsonify({'success': True})
        return jsonify({'error': 'Invalid action'}), 400
        
    return render_template('admin_control_panel.html', status=MAINTENANCE_MODE)

if __name__ == '__main__':
    app.run(debug=True)
