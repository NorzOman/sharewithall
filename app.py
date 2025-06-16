from flask import Flask, render_template, request, jsonify , redirect, url_for, send_file
from supabase import create_client, Client
from urllib.parse import urlparse
import os
import dropbox
import random
import time
import requests
import re

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SERVICE_ROLE_SECRET")
APP_KEY = os.getenv("APP_KEY")
APP_SECRET = os.getenv("APP_SECRET")
REFRESH_TOKEN = os.getenv("DROPBOX_REFRESH_TOKEN")

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

if SUPABASE_URL and SUPABASE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    print("[ERROR] SUPABASE_URL or SUPABASE_KEY not set. Supabase functionality will fail.")
    supabase = None

DROPBOX_ACCESS_TOKEN = None
DROPBOX_TOKEN_EXPIRY_TIME = 0

def get_fresh_dropbox_token():
    global DROPBOX_ACCESS_TOKEN, DROPBOX_TOKEN_EXPIRY_TIME

    if DROPBOX_ACCESS_TOKEN and time.time() < (DROPBOX_TOKEN_EXPIRY_TIME - 60):
        print("[INFO] Using cached Dropbox token.")
        return DROPBOX_ACCESS_TOKEN

    print("[INFO] Refreshing Dropbox token.")
    try:
        url = "https://api.dropbox.com/oauth2/token"
        data = {
            "grant_type": "refresh_token",
            "refresh_token": REFRESH_TOKEN,
            "client_id": APP_KEY,
            "client_secret": APP_SECRET
        }
        response = requests.post(url, data=data, timeout=7)
        response.raise_for_status()
        token_data = response.json()
        access_token = token_data.get("access_token")
        expires_in = token_data.get("expires_in")

        if not access_token:
            raise ValueError("Failed to retrieve access token from Dropbox response.")

        DROPBOX_ACCESS_TOKEN = access_token
        if expires_in:
            DROPBOX_TOKEN_EXPIRY_TIME = time.time() + int(expires_in)
        else:
            DROPBOX_TOKEN_EXPIRY_TIME = time.time() + 3600
        return access_token
    except requests.exceptions.Timeout:
        print(f"[ERROR] Timeout while refreshing Dropbox token.")
        return None
    except requests.exceptions.RequestException as req_err:
        print(f"[ERROR] Request failed while refreshing Dropbox token: {req_err}")
        return None
    except ValueError as val_err:
        print(f"[ERROR] Dropbox token processing error: {val_err}")
        return None
    except Exception as e:
        print(f"[ERROR] Unexpected error in get_fresh_dropbox_token: {e}")
        return None

def get_url_and_filename_from_supabase(access_code_str):
    if not supabase:
        return "Error: Supabase client not initialized.", None
    try:
        if not (isinstance(access_code_str, str) and len(access_code_str) == 4 and access_code_str.isdigit()):
            return "Error: Invalid access code format.", None
        
        # Use .single() if 'code' is unique for potentially better performance/error handling
        # response = supabase.table("Files").select("url, filename").eq("code", access_code_str).single().execute()
        response = supabase.table("Files").select("url, filename").eq("code", access_code_str).limit(1).execute()


    except Exception as e:
        print(f"[ERROR] Supabase query error for code '{access_code_str}': {e}")
        return "Error fetching file from Supabase. (Error Code: GET-FAIL-SUPA-01)", None

    if response.data and len(response.data) > 0: # Adjusted for .limit(1).execute()
        file_info = response.data[0]
    # elif response.data: # If using .single().execute() and it found data
    #     file_info = response.data
    else:
        return "Error: File not found for the given code.", None

    file_url = file_info.get("url")
    original_filename = file_info.get("filename", "downloaded_file")

    if not file_url:
        return "Error: File URL not found in Supabase record.", None

    direct_url = file_url.replace("dl=0", "dl=1")
    if "www.dropbox.com" in direct_url:
        direct_url = direct_url.replace("www.dropbox.com", "dl.dropboxusercontent.com", 1)
    return direct_url, original_filename

def upload_files(file_storage_object):
    if not supabase:
        return {"error": "Supabase client not initialized. (Error Code: SUPA-INIT-FAIL)"}

    latest_token = get_fresh_dropbox_token()
    if not latest_token:
        return {"error": "Failed to fetch token. Please try again later. (Error Code: TOKEN-FAIL-DROP-01)"}

    dbx = dropbox.Dropbox(latest_token, timeout=10)
    original_filename = file_storage_object.filename
    filename_base, file_ext = os.path.splitext(original_filename)

    sanitized_filename_base = re.sub(r'[<>:"/\\|?*\'`\s]', '_', filename_base).strip('_')
    sanitized_file_ext = re.sub(r'[<>:"/\\|?*\'`\s]', '_', file_ext).strip('_')
    
    if not sanitized_filename_base:
        sanitized_filename_base = "file_" + str(random.randint(100,999))
    if not sanitized_file_ext and original_filename:
        sanitized_file_ext = ".bin"
    elif not sanitized_file_ext and not original_filename:
         sanitized_file_ext = ".bin"


    unique_suffix = random.randint(1000, 9999)
    dropbox_file_name = f"{sanitized_filename_base}_{unique_suffix}{sanitized_file_ext}"
    file_path_dropbox = f"/{dropbox_file_name}"

    try:
        file_storage_object.seek(0)
        dbx.files_upload(file_storage_object.read(), file_path_dropbox, mute=True)
    except dropbox.exceptions.ApiError as api_err:
        print(f"[ERROR] Dropbox API error during upload: {api_err}")
        return {"error": "Error uploading file to storage. (Error Code: UP-FAIL-DROP-02a)"}
    except Exception as e:
        print(f"[ERROR] General error during upload: {e}")
        return {"error": "Error uploading file to storage. (Error Code: UP-FAIL-DROP-02b)"}

    shared_url = None
    try:
        shared_link_metadata = dbx.sharing_create_shared_link_with_settings(file_path_dropbox)
        shared_url = shared_link_metadata.url
    except dropbox.exceptions.ApiError as api_err:
        if api_err.error.is_shared_link_already_exists():
            print(f"[INFO] Shared link already exists for {file_path_dropbox}, attempting to retrieve it.")
            try:
                links = dbx.sharing_list_shared_links(path=file_path_dropbox, direct_only=True).links
                if links:
                    shared_url = links[0].url
                else:
                    print(f"[ERROR] Dropbox: Link existed but could not be retrieved for {file_path_dropbox}: {api_err}")
                    return {"error": "Error generating shareable link (retrieval failed). (Error Code: SHARE-FAIL-DROP-03a)"}
            except Exception as e_retrieve:
                print(f"[ERROR] Dropbox: Error retrieving existing link for {file_path_dropbox}: {e_retrieve}")
                return {"error": "Error generating shareable link (retrieval failed). (Error Code: SHARE-FAIL-DROP-03a2)"}
        else:
            print(f"[ERROR] Dropbox API error generating shareable link for {file_path_dropbox}: {api_err}")
            return {"error": "Error generating shareable link. (Error Code: SHARE-FAIL-DROP-03b)"}
    except Exception as e:
        print(f"[ERROR] General error generating shareable link for {file_path_dropbox}: {e}")
        return {"error": "Error generating shareable link. (Error Code: SHARE-FAIL-DROP-03c)"}

    if not shared_url:
         print(f"[ERROR] Failed to obtain a shared URL for {file_path_dropbox}")
         return {"error": "Critical error: Failed to obtain a shareable URL. (Error Code: SHARE-FAIL-DROP-03d)"}

    access_code_str = None
    for _ in range(10):
        temp_code = str(random.randint(1000, 9999)).zfill(4)
        try:
            check_response = supabase.table("Files").select("code", count="exact").eq("code", temp_code).execute()
            if check_response.count == 0:
                access_code_str = temp_code
                break
        except Exception as e_check:
            print(f"[WARN] Supabase check error for code '{temp_code}': {e_check}. Will retry.")
            time.sleep(0.1) 
    
    if not access_code_str:
        return {"error": "Failed to generate a unique access code after multiple attempts. (Error Code: CODEGEN-FAIL-01)"}

    direct_shared_url = shared_url.replace("dl=0", "dl=1")
    if "www.dropbox.com" in direct_shared_url:
         direct_shared_url = direct_shared_url.replace("www.dropbox.com", "dl.dropboxusercontent.com", 1)

    data_to_insert = {
        "code": access_code_str,
        "url": direct_shared_url,
        "filename": original_filename
    }

    try:
        response = supabase.table("Files").insert(data_to_insert).execute()
        if not (response.data and len(response.data) > 0 and response.data[0].get("code") == access_code_str):
            print(f"[ERROR] Supabase insert issue or unexpected response for code {access_code_str}: {response}")
            return {"error": "Error saving file data to Supabase. (Error Code: POST-FAIL-SUPA-05a)"}
    except Exception as e:
        print(f"[ERROR] Supabase insert error for code {access_code_str}: {e}")
        return {"error": "Error saving file data to Supabase. (Error Code: POST-FAIL-SUPA-05b)"}

    return {"success": True, "code": access_code_str}

@app.route('/')
def base():
    return render_template('hack.html')
    #return render_template('base.html')

@app.route('/share-file', methods=['GET','POST'])
def share_file_route():
    if request.method == "POST":
        if "file" not in request.files:
            return jsonify({"error": "No file part in the request"}), 400

        file = request.files["file"]
        if not file or file.filename == "":
            return jsonify({"error": "No selected file or filename is empty"}), 400

        file.seek(0, os.SEEK_END)
        file_length = file.tell()
        file.seek(0)

        MAX_FILE_SIZE_BYTES = 3 * 1024 * 1024 
        if file_length == 0:
            return jsonify({"error": "Uploaded file is empty."}), 400
        if file_length > MAX_FILE_SIZE_BYTES:
            return jsonify({"error": f"File size ({file_length / (1024*1024):.2f}MB) exceeds {MAX_FILE_SIZE_BYTES // (1024*1024)}MB limit"}), 413

        result = upload_files(file)
        if "error" in result:
            print(f"[SERVER_ERROR] /share-file: {result['error']}")
            return jsonify({"error": result["error"]}), 500 

        return jsonify({
            "success": True,
            "message": "File uploaded successfully!",
            "FileCode": result["code"]
        })
    return render_template('share-file.html')

@app.route('/receive-file', methods=['POST'])
def receive_file_route():
    try:
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 415

        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        access_code = data.get("code")
        if access_code is None:
            return jsonify({"error": "No access code provided in JSON payload (key 'code' missing)"}), 400

        access_code_str = str(access_code).strip()
        if not (len(access_code_str) == 4 and access_code_str.isdigit()):
            return jsonify({"error": "Invalid access code format. Must be 4 digits."}), 400

        direct_url, original_filename = get_url_and_filename_from_supabase(access_code_str)

        if original_filename is None and "Error" in direct_url:
            status_code = 404 if "not found" in direct_url.lower() else 500
            return jsonify({"error": direct_url}), status_code
        elif not direct_url or not original_filename :
             return jsonify({"error": "Failed to retrieve file details."}), 500

        print(f"[INFO] File URL retrieved for code {access_code_str}: {original_filename}")
        return jsonify({
            "success": True,
            "download_url": direct_url,
            "filename": original_filename
        })
    except Exception as e:
        print(f"[ERROR] Server error in /receive-file: {str(e)}")
        return jsonify({"error": f"Server error processing request. (Code 108)"}), 500

@app.route('/fixes') 
def fixes_redirect():
    return redirect("https://online-clipboard.online/online-clipboard/", code=302)

@app.route('/sitemap.xml')
def sitemap():
    try:
        return send_file('static/sitemap.xml', mimetype='application/xml')
    except FileNotFoundError:
        return "sitemap.xml not found", 404

@app.route('/robots.txt')
def robots_txt():
    try:
        return send_file('static/robots.txt', mimetype='text/plain')
    except FileNotFoundError:
        return "robots.txt not found", 404

@app.route('/<path:path>')
def error_404(path):
    return f"404 Not Found: The requested path '/{path}' was not found on this server.", 404

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)