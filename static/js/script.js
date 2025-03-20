// For Text Sharing:
document.getElementById("textShareForm").addEventListener("submit", async function(event) {
    event.preventDefault();
    const uploadStatus = document.getElementById("uploadStatus");
    uploadStatus.style.display = "block";

    // Check content size before showing loading state
    const content = this.elements.content.value;
    const contentSize = new Blob([content]).size;
    const MAX_FILE_SIZE = 3 * 1024 * 1024; // 3MB in bytes

    if (contentSize > MAX_FILE_SIZE) {
        uploadStatus.innerHTML = `
            <div class="share-form" style="background: #FFF2F2; border: 1px solid #FF4444;">
                <p style="color: #FF4444; margin: 0; font-weight: 500; font-size: 0.95rem;">Content size exceeds the 3MB limit.</p>
            </div>`;
        return;
    }

    // Show loading state only if size check passes
    uploadStatus.innerHTML = `
        <div class="share-form" style="background: var(--background-color); border: 1px solid var(--border-color); box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
            <div style="display: flex; align-items: center; gap: 1rem;">
                <div class="spinner-border" style="color: var(--secondary-color); width: 1.5rem; height: 1.5rem;" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p style="color: var(--text-color); margin: 0; font-weight: 500; font-size: 0.95rem;">Uploading your content...</p>
            </div>
        </div>`;

    try {
        const file = new File([content], 'text.txt', {
            type: 'text/plain'
        });

        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch("/share-file", {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (data.error) {
            uploadStatus.innerHTML = `
                <div class="share-form" style="background: #FFF2F2; border: 1px solid #FF4444;">
                    <p style="color: #FF4444; margin: 0; font-weight: 500; font-size: 0.95rem;">${data.error}</p>
                </div>`;
        } else {
            uploadStatus.innerHTML = `
                <div class="share-form" style="background: #F5F5F7; border: 1px solid var(--border-color);">
                    <div style="text-align: center;">
                        <p style="color: var(--text-color); margin-bottom: 1rem; font-weight: 600; font-size: 1rem;">Content uploaded successfully!</p>
                        <div style="background: var(--background-color); padding: 1rem; border-radius: 12px; border: 1px solid var(--border-color); display: inline-block;">
                            <span style="font-size: 1.2rem; color: var(--text-color);">Access Code: <strong style="color: var(--secondary-color);">${data['File Code']}</strong></span>
                        </div>
                    </div>
                </div>`;
        }
    } catch (error) {
        const errorResponse = await error.response?.json();
        uploadStatus.innerHTML = `
            <div class="share-form" style="background: #FFF2F2; border: 1px solid #FF4444;">
                <p style="color: #FF4444; margin: 0; font-weight: 500; font-size: 0.95rem;">${errorResponse?.error || error.message}</p>
            </div>`;
    }
});


// For File Sharing
document.getElementById("fileShareForm").addEventListener("submit", async function(event) {
    event.preventDefault();

    const uploadStatus = document.getElementById("uploadStatus");
    uploadStatus.style.display = "block";
    uploadStatus.innerHTML = `
        <div class="share-form" style="background: var(--background-color); border: 1px solid var(--border-color); box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
            <div style="display: flex; align-items: center; gap: 1rem;">
                <div class="spinner-border" style="color: var(--secondary-color); width: 1.5rem; height: 1.5rem;" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p style="color: var(--text-color); margin: 0; font-weight: 500; font-size: 0.95rem;">Uploading your file...</p>
            </div>
        </div>`;

    const fileInput = document.getElementById("fileInput"); // Assume your file input field has this ID.
    const file = fileInput.files[0];

    // Check if a file is selected and if it exceeds 3MB
    const MAX_FILE_SIZE = 3 * 1024 * 1024; // 3MB in bytes
    if (file && file.size > MAX_FILE_SIZE) {
        uploadStatus.innerHTML = `
            <div class="share-form" style="background: #FFF2F2; border: 1px solid #FF4444;">
                <p style="color: #FF4444; margin: 0; font-weight: 500; font-size: 0.95rem;">File size exceeds the 3MB limit.</p>
            </div>`;
        return; // Stop the form submission if the file is too large
    }

    try {
        const formData = new FormData(this);
        const response = await fetch("/share-file", {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (data.error) {
            uploadStatus.innerHTML = `
                <div class="share-form" style="background: #FFF2F2; border: 1px solid #FF4444;">
                    <p style="color: #FF4444; margin: 0; font-weight: 500; font-size: 0.95rem;">${data.error}</p>
                </div>`;
        } else {
            uploadStatus.innerHTML = `
                <div class="share-form" style="background: #F5F5F7; border: 1px solid var(--border-color);">
                    <div style="text-align: center;">
                        <p style="color: var(--text-color); margin-bottom: 1rem; font-weight: 600; font-size: 1rem;">File uploaded successfully!</p>
                        <div style="background: var(--background-color); padding: 1rem; border-radius: 12px; border: 1px solid var(--border-color); display: inline-block;">
                            <span style="font-size: 1.2rem; color: var(--text-color);">Access Code: <strong style="color: var(--secondary-color);">${data['File Code']}</strong></span>
                        </div>
                    </div>
                </div>`;
        }
    } catch (error) {
        const errorResponse = await error.response?.json();
        uploadStatus.innerHTML = `
            <div class="share-form" style="background: #FFF2F2; border: 1px solid #FF4444;">
                <p style="color: #FF4444; margin: 0; font-weight: 500; font-size: 0.95rem;">${errorResponse?.error || error.message}</p>
            </div>`;
    }
});


// For File Recieving
document.getElementById("receiveForm").addEventListener("submit", async function(event) {
    event.preventDefault();
    
    const fileId = document.getElementById("fileId").value;
    const fileAccessResult = document.getElementById("fileAccessResult");
    
    fileAccessResult.style.display = "block";
    fileAccessResult.innerHTML = `
        <div class="share-form" style="background: var(--background-color); border: 1px solid var(--border-color); box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
            <div style="display: flex; align-items: center; gap: 1rem;">
                <div class="spinner-border" style="color: var(--secondary-color); width: 1.5rem; height: 1.5rem;" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p style="color: var(--text-color); margin: 0; font-weight: 500; font-size: 0.95rem;">Searching for your file...</p>
            </div>
        </div>`;

    try {
        const response = await fetch("/receive-file", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            body: JSON.stringify({ code: fileId })
        });

        const data = await response.json();

        if (data.error) {
            fileAccessResult.innerHTML = `
                <div class="share-form" style="background: #FFF2F2; border: 1px solid #FF4444;">
                    <p style="color: #FF4444; margin: 0; font-weight: 500; font-size: 0.95rem;">${data.error}</p>
                </div>`;
        } else {
            window.location.href = data.file_url;
            fileAccessResult.innerHTML = `
                <div class="share-form" style="background: #F5F5F7; border: 1px solid var(--border-color);">
                    <div style="text-align: center;">
                        <p style="color: var(--text-color); margin: 0; font-weight: 500; font-size: 0.95rem;">Starting download...</p>
                        <p style="color: var(--accent-color); margin-top: 0.5rem; font-size: 0.9rem;">If download doesn't start, <a href="${data.file_url}" style="color: var(--secondary-color);">click here</a></p>
                    </div>
                </div>`;
        }
    } catch (error) {
        const errorResponse = await error.response?.json();
        fileAccessResult.innerHTML = `
            <div class="share-form" style="background: #FFF2F2; border: 1px solid #FF4444;">
                <p style="color: #FF4444; margin: 0; font-weight: 500; font-size: 0.95rem;">${errorResponse?.error || error.message}</p>
            </div>`;
    }
});



