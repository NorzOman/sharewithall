'''Necessary imports for the projects'''
from flask import Flask, render_template, request, jsonify , redirect, url_for, session
from supabase import create_client
from urllib.parse import urlparse
import os
import uuid
import dropbox
import random
import string
import time

'''Initialize environment variables'''
ACCESS_TOKEN = os.getenv("DROPBOX_ACCESS_TOKEN") 
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SERVICE_ROLE_SECRET")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

'''Initialize Flask app and databases'''
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
dbx = dropbox.Dropbox(ACCESS_TOKEN)

def get_file_from_supabase(access_code):
    """Fetch direct file URL from Supabase using a 4-digit code."""

    # Search for the file in Supabase
    try:
        response = supabase.table("Files").select("url").eq("code", access_code).execute()
    except Exception as e:
        print(f"[DEBUG] Error fetching file from Supabase: {e}")
        return "Error fetching file from Supabase, Please try again later, or report to dev (Error Code: 107)"

    print(f"[DEBUG] Supabase search response: {response}")

    if response.data and len(response.data) > 0:
        file_url = response.data[0]["url"]
        # Convert to direct download URL
        direct_url = file_url.replace("dl=0", "dl=1")
        return direct_url

    print(f"[DEBUG] File not found in Supabase")
    return "Error: File not found"

def upload_files(file):
    """Uploads a file to Dropbox and returns an access code for the shared link."""
    # Generate unique filename
    file_ext = file.filename.split(".")[-1]
    file_id = f"{uuid.uuid4().hex}.{file_ext}"

    # Create a path for the file in Dropbox
    file_path = f"/{file_id}"  # Stored at root of Dropbox
    print(f"[DEBUG] Uploading file to Dropbox: {file_path}")
    
    # Upload file to Dropbox
    try:
        dbx.files_upload(file.read(), file_path, mute=True)
    except Exception as e:
        print(f"[DEBUG] Error uploading file to Dropbox: {e}")
        return {"error": "Error uploading file to file storage client, Please try again later, or report to dev (Error Code: 101)"}

    # Generate shareable link
    try:
        shared_link = dbx.sharing_create_shared_link_with_settings(file_path)
    except Exception as e:
        print(f"[DEBUG] Error generating shareable link: {e}")
        return {"error": "Error generating shareable link for the code, Please try again later, or report to dev (Error Code: 102)"}

    print(f"[DEBUG] Shared link: {shared_link}")

    access_code = random.randint(1000, 9999)

    # Extract direct download URL by replacing dl=0 with dl=1
    try:
        file_url = shared_link.url if hasattr(shared_link, "url") else str(shared_link)
        file_url = file_url.replace('dl=0', 'dl=1')
    except Exception as e:
        print(f"[DEBUG] Error extracting file URL: {e}")
        return {"error": "Error extracting file URL, Please try again later, or report to dev (Error Code: 103)"}
    
    print(f"[DEBUG] Extracted file URL: {file_url}")
    
    data = {"code": access_code, "url": file_url}

    try:
        print(f"[DEBUG] Now inserting data into Supabase")
        response = supabase.table("Files").insert(data).execute()
        print(f"[DEBUG] Supabase response: {response}")
    except Exception as e:
        print(f"[DEBUG] Error inserting data into Supabase: {e}")
        return {"error": "Error inserting data into Supabase, Please try again later, or report to dev (Error Code: 104)"}

    if not response.data:
        print(f"Error saving file: {response}")
        return {"error": "Error saving file, Please try again later, or report to dev (Error Code: 105)"}

    if "code" not in response.data[0]:
        print(f"Error saving file: {response}")
        return {"error": "Error saving file, Please try again later, or report to dev (Error Code: 106)"}

    return {"success": True, "code": access_code}




'''Start of routes'''

@app.route('/')
def base():
    return render_template('base.html')

@app.route('/share-file', methods=['GET','POST']) 
def share_file():
    if request.method == 'POST':
        if "file" not in request.files:
            return jsonify({"error": "No file uploaded"}), 400
        
        file = request.files["file"]
        
        if file.filename == "":
            return jsonify({"error": "No selected file"}), 400

        # Check if the file size exceeds 3MB
        MAX_FILE_SIZE = 3 * 1024 * 1024  # 3MB in bytes
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

@app.route('/receive-file', methods=['POST'])
def receive_file():
    try:
        data = request.get_json()
        access_code = data.get("code")

        if not access_code:
            return jsonify({"error": "No access code provided"}), 400

        if not str(access_code).isdigit() or len(str(access_code)) != 4:
            return jsonify({"error": "Invalid access code format"}), 400

        file_url = get_file_from_supabase(access_code)

        if "Error" in file_url:
            return jsonify({"error": file_url}), 404

        return jsonify({
            "success": True,
            "file_url": file_url
        })

    except Exception as e:
        return jsonify({"error": "Server error occurred , Report to dev (Error Code: 108)"}), 500


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

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    # Get all the tables from the database
    tables = supabase.table("Files").select("*").execute()
    print(f"[DEBUG] Tables: {tables}")
    return render_template('admin_dashboard.html', tables=tables)


@app.route('/clear-dropbox', methods=['POST'])
def clear_dropbox():
    if not session.get('admin_logged_in'):
        return jsonify({"error": "Unauthorized"}), 401
        
    try:
        # Get all URLs from the Files table
        response = supabase.table("Files").select("url").execute()
        if not response.data:
            print("[ERROR] No URLs found in the database.")
            return jsonify({"error": "No URLs found in the database."}), 404
        
        urls = [record['url'] for record in response.data]
        print(f"[DEBUG] URLs to delete: {urls}")

        # Process URLs in batches of 5
        batch_size = 5
        for i in range(0, len(urls), batch_size):
            batch = urls[i:i+batch_size]
            
            # Send delete requests for current batch
            for url in batch:
                file_path = None  # Initialize to avoid reference errors
                try:
                    # Extract filename from URL and create file path
                    parsed_url = urlparse(url)
                    filename = os.path.basename(parsed_url.path)
                    file_path = f"/{filename}"
                    
                    print(f"[DEBUG] Attempting to delete file: {file_path}")
                    dbx.files_delete_v2(file_path)
                    print(f"[DEBUG] Successfully deleted: {file_path}")
                except dropbox.exceptions.ApiError as delete_error:
                    # Handle specific Dropbox errors
                    if 'not_found' in str(delete_error):
                        print(f"[INFO] File not found, possibly already deleted: {file_path}")
                    else:
                        print(f"[ERROR] Failed to delete file {file_path}: {str(delete_error)}")
                except Exception as general_error:
                    # Catch any other exceptions
                    print(f"[ERROR] Unexpected error deleting {file_path}: {str(general_error)}")
                    continue
            
            # Wait 3 seconds between batches to avoid rate limiting
            if i + batch_size < len(urls):
                time.sleep(3)
                
        # Clear the database table after deleting files
        #supabase.table("Files").delete().neq("id", 0).execute()
        #print("[DEBUG] Files cleared successfully from database.")
        return jsonify({"success": True})
        
    except Exception as e:
        print(f"[ERROR] Failed to clear files: {str(e)}")
        return jsonify({"error": f"Failed to clear files: {str(e)}"}), 500



@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/vdp')
def vdp():
    return render_template('vdp.html')

@app.route('/support')
def support():
    return render_template('support.html')

@app.route('/<path:path>')
def error_404(path):
    return render_template('error.html')

@app.route('/share-text', methods=['POST'])
def share_text():
    return render_template('base.html')

        


if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0',port=5000)
