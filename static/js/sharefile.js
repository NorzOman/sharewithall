document.addEventListener('DOMContentLoaded', () => { // Ensure DOM is loaded

    const fileShareForm = document.getElementById("fileShareForm");
    const receiveForm = document.getElementById("receiveForm");

    // File upload form handler
    if (fileShareForm) {
        fileShareForm.addEventListener("submit", async function(event) {
            event.preventDefault();

            const uploadStatus = document.getElementById("uploadStatus");
            const fileInput = document.getElementById("fileInput");
            const submitButton = this.querySelector('button[type="submit"]');

            if (!uploadStatus || !fileInput || !submitButton) {
                console.error("Share form: One or more required elements not found.");
                alert("Page setup error. Please contact support.");
                return;
            }

            if (!fileInput.files[0]) {
                uploadStatus.style.display = "block";
                uploadStatus.className = 'status-box error mt-medium';
                uploadStatus.innerHTML = `<p>Please select a file to upload.</p>`;
                return;
            }

            submitButton.disabled = true;
            let timeLeft = 10; // Cooldown in seconds

            uploadStatus.style.display = "block";
            uploadStatus.className = 'status-box mt-medium';
            uploadStatus.innerHTML = `
                <div style="display: flex; align-items: center; gap: 0.75rem;">
                    <span style="font-size: 1.2rem; line-height: 1;">⏳</span>
                    <p style="margin: 0;">Uploading your file... (Submit again in ${timeLeft}s)</p>
                </div>`;

            let countdownInterval = setInterval(() => {
                timeLeft--;
                if (timeLeft > 0) {
                    const statusTextP = uploadStatus.querySelector('p');
                    if (statusTextP) {
                        statusTextP.textContent = `Uploading your file... (Submit again in ${timeLeft}s)`;
                    }
                } else {
                    clearInterval(countdownInterval); // Stop when time is up
                    const statusTextP = uploadStatus.querySelector('p');
                     if (statusTextP && statusTextP.textContent.includes("Submit again in")) { // Check if message needs clearing
                        statusTextP.textContent = `Uploading your file...`;
                    }
                }
            }, 1000);

            const file = fileInput.files[0];
            const MAX_FILE_SIZE_JS = 3 * 1024 * 1024; // Match Python for primary limit
            const MAX_REGULAR_SIZE_JS = 2.5 * 1024 * 1024;


            if (file.size > MAX_FILE_SIZE_JS) {
                clearInterval(countdownInterval);
                uploadStatus.className = 'status-box error mt-medium';
                uploadStatus.innerHTML = `<p>File size exceeds the ${MAX_FILE_SIZE_JS / (1024 * 1024)}MB limit.</p>`;
                // finally block will re-enable button after cooldown
                return;
            }

            if (file.size > MAX_REGULAR_SIZE_JS && file.size <= MAX_FILE_SIZE_JS) {
                uploadStatus.className = 'status-box warning mt-medium';
                uploadStatus.innerHTML = `
                    <div style="text-align: left;">
                        <p style="margin: 0 0 0.5rem 0; font-weight: 700;">
                            ⚠️ Beta Phase: Large File Upload
                        </p>
                        <p style="margin: 0; font-size: 0.85rem;">
                            Files larger than ${MAX_REGULAR_SIZE_JS / (1024*1024)}MB are in beta. Upload might take longer.
                        </p>
                    </div>`;
            }

            try {
                const formData = new FormData(this);
                const response = await fetch("/share-file", {
                    method: "POST",
                    body: formData
                });

                clearInterval(countdownInterval); // Stop countdown on receiving response
                const data = await response.json();

                if (!response.ok || data.error) {
                    const errorMessage = data.error || `Server error (${response.status}). Please try again.`;
                    uploadStatus.className = 'status-box error mt-medium';
                    uploadStatus.innerHTML = `<p>${errorMessage} <a href="/fixes">Check fixes</a></p>`;
                } else if (data.success && data.FileCode) {
                    uploadStatus.className = 'status-box success mt-medium';
                    uploadStatus.innerHTML = `
                        <div style="text-align: center;">
                            <p style="margin-bottom: 1rem; font-weight: 700; font-size: 1rem;">
                                File uploaded successfully!
                            </p>
                            <div style="background: var(--background); padding: 0.75rem 1rem; border-radius: var(--radius); border: 1px solid var(--border); display: inline-block; box-shadow: var(--shadow-sm);">
                                <span style="font-size: 1.1rem; color: var(--foreground);">
                                    Access Code: <strong style="color: var(--primary); font-size: 1.2rem;">${data.FileCode}</strong>
                                </span>
                            </div>
                        </div>`;
                    fileInput.value = '';
                } else {
                    uploadStatus.className = 'status-box error mt-medium';
                    uploadStatus.innerHTML = `<p>Received an unexpected response from the server. <a href="/fixes">Check fixes</a></p>`;
                }
            } catch (error) {
                clearInterval(countdownInterval);
                console.error("Upload error:", error);
                uploadStatus.className = 'status-box error mt-medium';
                uploadStatus.innerHTML = `<p>A network or client-side error occurred. Please try again. <a href="/fixes">Check fixes</a></p>`;
            } finally {
                setTimeout(() => {
                    submitButton.disabled = false;
                    // Ensure interval is cleared if it was running
                    if (countdownInterval) clearInterval(countdownInterval);

                    // Optionally reset status message if it's still showing cooldown text
                    const statusTextP = uploadStatus.querySelector('p');
                    if (statusTextP && statusTextP.textContent.includes("Submit again in")) {
                         uploadStatus.innerHTML = `<p>Ready for next upload.</p>`;
                         setTimeout(()=> { if(uploadStatus) uploadStatus.style.display = "none"; }, 3000);
                    }
                }, 10000); // Cooldown duration
            }
        });
    } else {
        console.warn("fileShareForm not found in the DOM.");
    }

    // File access form handler
    if (receiveForm) {
        receiveForm.addEventListener("submit", async function(event) {
            event.preventDefault();

            const submitButton = this.querySelector('button[type="submit"]');
            const fileIdInput = document.getElementById("fileId");
            const fileAccessResult = document.getElementById("fileAccessResult");

            if (!submitButton || !fileIdInput || !fileAccessResult) {
                console.error("Receive form: One or more required elements not found.");
                alert("Page setup error. Please contact support.");
                return;
            }

            submitButton.disabled = true;
            let timeLeft = 10;

            fileAccessResult.style.display = "block";
            fileAccessResult.className = 'status-box mt-medium';
            fileAccessResult.innerHTML = `
                <div style="display: flex; align-items: center; gap: 0.75rem;">
                    <span style="font-size: 1.2rem; line-height: 1;">⏳</span>
                    <p style="margin: 0;">Fetching file information... (Submit again in ${timeLeft}s)</p>
                </div>`;

            let countdownInterval = setInterval(() => {
                timeLeft--;
                if (timeLeft > 0) {
                    const statusTextP = fileAccessResult.querySelector('p');
                    if (statusTextP) {
                        statusTextP.textContent = `Fetching file information... (Submit again in ${timeLeft}s)`;
                    }
                } else {
                    clearInterval(countdownInterval);
                    const statusTextP = fileAccessResult.querySelector('p');
                    if (statusTextP && statusTextP.textContent.includes("Submit again in")) {
                         statusTextP.textContent = `Fetching file information...`;
                    }
                }
            }, 1000);

            try {
                const accessCode = fileIdInput.value.trim();
                if (!/^\d{4}$/.test(accessCode)) {
                    throw new Error("Invalid Access Code. Please enter a 4-digit code.");
                }

                const response = await fetch("/receive-file", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ code: accessCode })
                });

                const fileInfo = await response.json();
                // console.log("Received from /receive-file:", fileInfo); // For debugging

                if (!response.ok || fileInfo.error) {
                    const errorMessage = fileInfo.error || `Server error (${response.status}). Please try again.`;
                    throw new Error(errorMessage);
                }

                if (fileInfo.success && fileInfo.download_url && fileInfo.filename) {
                    const downloadUrl = fileInfo.download_url;
                    const filename = fileInfo.filename;

                    fileAccessResult.className = 'status-box mt-medium';
                    const statusTextP = fileAccessResult.querySelector('p');
                    if (statusTextP) {
                        statusTextP.textContent = `Initiating download for: ${filename}...`;
                    } else { // Fallback if p element somehow got removed
                        fileAccessResult.innerHTML = `
                            <div style="display: flex; align-items: center; gap: 0.75rem;">
                                <span style="font-size: 1.2rem; line-height: 1;">⏳</span>
                                <p style="margin: 0;">Initiating download for: ${filename}...</p>
                            </div>`;
                    }

                    const a = document.createElement("a");
                    a.style.display = "none";
                    a.href = downloadUrl;
                    a.download = filename;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    // No need to revokeObjectURL for direct URLs from Dropbox

                    clearInterval(countdownInterval);
                    fileAccessResult.className = 'status-box success mt-medium';
                    fileAccessResult.innerHTML = `<p>"${filename}" download has started. Check your browser's downloads.</p>`;
                    fileIdInput.value = '';
                } else {
                    // This will catch cases where success is true but download_url or filename is missing
                    // OR if success is false and there was no explicit fileInfo.error
                    throw new Error(fileInfo.error || "Invalid response from server: Missing download details or success flag.");
                }

            } catch (error) {
                clearInterval(countdownInterval);
                console.error("Receive error:", error);
                fileAccessResult.className = 'status-box error mt-medium';
                fileAccessResult.innerHTML = `<p>Error: ${error.message}</p>`;
            } finally {
                setTimeout(() => {
                    submitButton.disabled = false;
                    if (countdownInterval) clearInterval(countdownInterval);

                    const statusTextP = fileAccessResult.querySelector('p');
                     if (statusTextP && statusTextP.textContent.includes("Submit again in")) {
                         fileAccessResult.innerHTML = `<p>Ready to fetch another file.</p>`;
                         setTimeout(()=> { if(fileAccessResult) fileAccessResult.style.display = "none"; }, 3000);
                    }
                }, 10000);
            }
        });
    } else {
        console.warn("receiveForm not found in the DOM.");
    }
});