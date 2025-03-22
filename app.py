

'''Necessary imports for the projects'''
from flask import Flask, render_template, request, jsonify , redirect, url_for, session , Response , send_file
from supabase import create_client
from urllib.parse import urlparse
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
import uuid
import dropbox
import random
import string
import time
import requests
import re
import io
import base64

'''Initialize environment variables'''
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SERVICE_ROLE_SECRET")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
APP_KEY = os.getenv("APP_KEY")
APP_SECRET = os.getenv("APP_SECRET")
REFRESH_TOKEN = os.getenv("DROPBOX_REFRESH_TOKEN")
HCAPTCHA_SECRET_KEY = os.getenv("HCAPTCHA_SECRET_KEY")


'''Initialize Flask app and databases'''
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


'''Initialize rate limiter'''
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["20 per minute"],
)


BASE64_STORAGE = {}

# --------------------------------------------------------------------
# -------------------START OF CRITICAL FUNCS--------------------------
# --------------------------------------------------------------------


'''Function to get a fresh Dropbox token'''
def get_fresh_dropbox_token():
    """Fetch a fresh Dropbox access token using refresh token."""
    try:
        url = "https://api.dropbox.com/oauth2/token"
        data = {
            "grant_type": "refresh_token",
            "refresh_token": REFRESH_TOKEN,
            "client_id": APP_KEY,
            "client_secret": APP_SECRET
        }

        response = requests.post(url, data=data)
        response.raise_for_status()

        access_token = response.json().get("access_token")
        if not access_token:
            raise ValueError("Failed to retrieve access token")

        return access_token  

    except requests.exceptions.RequestException as req_err:
        print(f"[ERROR] Request failed while refreshing Dropbox token: {req_err}")
        return None


"""Fetch direct file URL from Supabase using a 4-digit code."""
def get_url_from_supabase(access_code):
    try:
        if not isinstance(access_code, str) or len(access_code) != 4 or not access_code.isdigit():
            return "Error: Invalid access code"
        response = supabase.table("Files").select("url").eq("code", access_code).execute()
    except Exception as e:
        return "Error fetching file from Supabase, Make sure correct code, or report to dev (Error Code: GET-FAIL-SUPA-01)"

    if response.data and len(response.data) > 0:
        file_url = response.data[0]["url"]
        direct_url = file_url.replace("dl=0", "dl=1")
        return direct_url

    return "Error: File not found"


"""Uploads a file to Dropbox and returns an access code for the shared link."""
def upload_files(file):
    latest_token = get_fresh_dropbox_token()
    if not latest_token:
        return {"error": "Failed to fetch token. Please try again later, or report to dev (Error Code: TOKEN-FAIL-DROP-01)"}

    dbx = dropbox.Dropbox(latest_token)
    
    filename, file_ext = os.path.splitext(file.filename)

    filename = re.sub(r'[<>:"/\\|?*\'`]', ' ', filename).strip()
    file_ext = re.sub(r'[<>:"/\\|?*\'`]', ' ', file_ext).strip()

    file_id = f"{filename}_{random.randint(1000, 9999)}{file_ext}"  

    file_path = f"/{file_id}"
    
    try:
        dbx.files_upload(file.read(), file_path, mute=True)
    except Exception as e:
        return {"error": "Error uploading file to file storage client, Please try again later, or report to dev (Error Code: UP-FAIL-DROP-02)"}

    try:
        shared_link = dbx.sharing_create_shared_link_with_settings(file_path)
    except Exception as e:
        return {"error": "Error generating shareable link for the code, Please try again later, or report to dev (Error Code: SHARE-FAIL-DROP-03)"}

    access_code = random.randint(1000, 9999)

    try:
        file_url = shared_link.url if hasattr(shared_link, "url") else str(shared_link)
        file_url = file_url.replace('dl=0', 'dl=1')
    except Exception as e:
        return {"error": "Error extracting file URL, Please try again later, or report to dev (Error Code: UP-FAIL-URL-04)"}
        
    data = {"code": access_code, "url": file_url}

    try:
        response = supabase.table("Files").insert(data).execute()
    except Exception as e:
        return {"error": "Error inserting data into Supabase, Please try again later, or report to dev (Error Code: POST-FAIL-SUPA-05)"}

    if not response.data:
        return {"error": "Error saving file, Please try again later, or report to dev (Error Code: NORESP-FAIL-SUPA-06)"}

    if "code" not in response.data[0]:
        return {"error": "Error saving file, Please try again later, or report to dev (Error Code: NOCODE-FAIL-SUPA-07)"}

    return {"success": True, "code": access_code}

"""Fetch file from Dropbox and return base64-encoded content & filename."""
def get_file_from_dropbox(file_url):
    try:
        response = requests.get(file_url, stream=True)
        response.raise_for_status()

        file_data = response.content
        base64_data = base64.b64encode(file_data).decode('utf-8')

        # Extract file name from URL
        match = re.search(r'/scl/fi/[^/]+/([^/?]+)', file_url)
        filename = match.group(1) if match else "downloaded_file.ext"

        return base64_data, filename
    except Exception as e:
        return None, str(e)

def verify_hcaptcha(token):
    """Verify hCaptcha response with the hCaptcha API."""
    try:
        response = requests.post("https://api.hcaptcha.com/siteverify", data={
            "secret": HCAPTCHA_SECRET_KEY,
            "response": token
        })
        result = response.json()

        if result.get("success"):
            return True
        error_codes = result.get("error-codes", [])
        if "missing-input-response" in error_codes or "invalid-input-response" in error_codes:
            return False 

        print(f"[WARNING] hCaptcha API issue: {error_codes}. Allowing upload.")
        return True

    except Exception as e:
        print(f"[ERROR] hCaptcha verification request failed: {str(e)}. Allowing upload.")
        return True

# --------------------------------------------------------------------
# -------------------END OF CRITICAL FUNCS----------------------------
# --------------------------------------------------------------------



# --------------------------------------------------------------------
# -------------------START OF FLASK ROUTES----------------------------
# --------------------------------------------------------------------

@app.before_request
def block_bad_agents():
    """Block requests from bad user-agents and redirect to rate_limit page"""
    if "rate_limit" not in request.path:  # Prevent infinite redirect loop
        blocked_agents = [
            "curl", "python-requests", "wget", "httpie", "go-http-client",
            "postmanruntime", "sqlmap", "burp", "nmap", "hydra", "fuzz", "dirbuster",
            "zap", "nikto", "arachni", "masscan"
        ]

        user_agent = request.headers.get("User-Agent", "").lower()

        if any(agent in user_agent for agent in blocked_agents):
            return redirect(url_for('rate_limit'))  # Redirect to rate limit page

    if request.method == 'POST' and request.endpoint in ["share_file", "receive_file"]:
            limiter.check()

@app.errorhandler(429)
def rate_limit_exceeded(e):
    return redirect(url_for('rate_limit'))  # Redirect to custom page


'''Base route'''
@app.route('/')
def base():
    return render_template('base.html')


'''Share file route'''
@app.route('/share-file', methods=['GET','POST'])
def share_file():
    if request.method == "POST":
        if "file" not in request.files:
            return jsonify({"error": "No file uploaded"}), 400
        
        if "h-captcha-response" not in request.form:
            return redirect(url_for('rate_limit'))
        
        file = request.files["file"]
        
        if file.filename == "":
            return jsonify({"error": "No selected file"}), 400

        hcaptcha_token = request.form.get("h-captcha-response")
        hcaptcha_result = verify_hcaptcha(hcaptcha_token)

        if hcaptcha_result is False:
            return redirect(url_for('rate_limit'))

        MAX_FILE_SIZE = 3 * 1024 * 1024
        if file.content_length > MAX_FILE_SIZE:
            return jsonify({"error": "File size exceeds 3MB limit"}), 400

        result = upload_files(file)

        if "error" in result:
            return jsonify({"error": result["error"]}), 500

        return jsonify({
            "success": True,
            "message": "File uploaded successfully!",
            "File Code": result["code"]
        })

    return render_template('share-file.html')

"""Receives access code, fetches file info, and returns download route."""
@app.route('/receive-file', methods=['POST'])
def receive_file():
    """Receives access code, fetches file info, and returns download route."""
    try:
        data = request.get_json()
        access_code = data.get("code")

        if not access_code:
            return jsonify({"error": "No access code provided"}), 400

        if not str(access_code).isdigit() or len(str(access_code)) != 4:
            return jsonify({"error": "Invalid access code format"}), 400

        file_url = get_url_from_supabase(access_code)

        if "Error" in file_url:
            return jsonify({"error": file_url}), 404

        base64_data, filename = get_file_from_dropbox(file_url)

        if base64_data is None:
            return jsonify({"error": f"Failed to fetch file: {filename}"}), 500

        file_key = f"file_{access_code}"
        BASE64_STORAGE[file_key] = base64_data

        print(f"[INFO] File received: {filename}")

        return jsonify({
            "filename": filename,
            "file_route": f"/api/download/{file_key}"
        })

    except Exception as e:
        return jsonify({"error": f"Server error (Code 108): {str(e)}"}), 500


@app.route('/api/download/<file_key>', methods=['GET'])
def download_file(file_key):
    if not re.fullmatch(r"file_\d{4}", file_key):
        return jsonify({"error": "Invalid file key format"}), 400
    
    if file_key not in BASE64_STORAGE:
        return jsonify({"error": "File not found"}), 404

    file_data = BASE64_STORAGE.pop(file_key)

    return jsonify({"file_base64": file_data})



'''Admin login route'''
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            return jsonify({"error": "Invalid username or password"}), 401

    return render_template('admin_login.html')


'''Admin dashboard route'''
@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    # Get all the tables from the database
    tables = supabase.table("Files").select("*").execute()
    return render_template('admin_dashboard.html', tables=tables)


'''Admin logout route'''
@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))


'''Admin clear dropbox route'''
@app.route('/clear-dropbox', methods=['POST'])
def clear_dropbox():
    if not session.get('admin_logged_in'):
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        response = supabase.table("Files").select("url").execute()
        if not response.data:
            return jsonify({"error": "No URLs found in the database."}), 404
        
        urls = [record['url'] for record in response.data]

        # Process URLs in batches of 5
        batch_size = 5
        for i in range(0, len(urls), batch_size):
            batch = urls[i:i+batch_size]
            
            # Send delete requests for current batch
            for url in batch:
                file_path = None
                latest_token = get_fresh_dropbox_token()
                if not latest_token:
                    return jsonify({"error": "Failed to fetch"}),404

                dbx = dropbox.Dropbox(latest_token)
                try:
                    parsed_url = urlparse(url)
                    filename = os.path.basename(parsed_url.path)
                    file_path = f"/{filename}"
                    
                    dbx.files_delete_v2(file_path)
                except dropbox.exceptions.ApiError as delete_error:
                    if 'not_found' in str(delete_error):
                        print(f"[INFO] File not found, possibly already deleted: {file_path}")
                    else:
                        print(f"[ERROR] Failed to delete file {file_path}: {str(delete_error)}")
                except Exception as general_error:
                    print(f"[ERROR] Unexpected error deleting {file_path}: {str(general_error)}")
                    continue
            
            # Wait 3 seconds between batches to avoid rate limiting
            if i + batch_size < len(urls):
                time.sleep(3)
                
        # Clear the database table after deleting files
        supabase.table("Files").delete().neq("id", 0).execute()
        return jsonify({"success": True})
        
    except Exception as e:
        return jsonify({"error": f"Failed to clear files: {str(e)}"}), 500


'''About page route'''
@app.route('/about')
def about():
    return render_template('about.html')


'''VDP page route'''
@app.route('/vdp')
def vdp():
    return render_template('vdp.html')


'''Support page route'''
@app.route('/support')
def support():
    return render_template('support.html')


@app.route('/rate-limit')
def rate_limit():
    return render_template('rate_limit.html')


'''Error Fallback page route'''
@app.route('/<path:path>')
def error_404(path):
    return render_template('error.html')

# --------------------------------------------------------------------
# -------------------END OF FLASK ROUTES------------------------------
# --------------------------------------------------------------------


if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0',port=5000)
