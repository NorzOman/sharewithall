       // Replace the existing text share form handler with this updated version:
       document.getElementById("textShareForm").addEventListener("submit", async function(event) {
        event.preventDefault();
        const uploadStatus = document.getElementById("uploadStatus");
        const submitButton = this.querySelector('button[type="submit"]');
        const content = this.elements.content.value.trim();

        // Check captcha first
        /* const captchaResponse = hcaptcha.getResponse();
        if (!captchaResponse) {
            uploadStatus.style.display = "block";
            uploadStatus.innerHTML = `
                <div class="share-form" style="background: #FFF2F2; border: 1px solid #FF4444;">
                    <p style="color: #FF4444; margin: 0; font-weight: 500; font-size: 0.95rem;">
                        Please complete the captcha verification.
                    </p>
                </div>`;
            return;
        } */

        // Check if content is empty
        if (!content) {
            uploadStatus.style.display = "block";
            uploadStatus.innerHTML = `
                <div class="share-form" style="background: #FFF2F2; border: 1px solid #FF4444;">
                    <p style="color: #FF4444; margin: 0; font-weight: 500; font-size: 0.95rem;">
                        Please enter some content to share.
                    </p>
                </div>`;
            return;
        }

        // Check word count
        const wordCount = content.split(/\s+/).filter(word => word.length > 0).length;
        if (wordCount > 1000) {
            uploadStatus.style.display = "block";
            uploadStatus.innerHTML = `
                <div class="share-form" style="background: #FFF2F2; border: 1px solid #FF4444;">
                    <p style="color: #FF4444; margin: 0; font-weight: 500; font-size: 0.95rem;">
                        Content exceeds 1000 words limit (current: ${wordCount} words)
                    </p>
                </div>`;
            // hcaptcha.reset();
            return;
        }

        // Disable submit button and show loading state
        submitButton.disabled = true;
        let timeLeft = 10;

        uploadStatus.style.display = "block";
        uploadStatus.innerHTML = `
            <div class="share-form" style="background: var(--background-color); border: 1px solid var(--border-color); box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
                <div style="display: flex; align-items: center; gap: 1rem;">
                    <div class="spinner-border" style="color: var(--secondary-color); width: 1.5rem; height: 1.5rem;" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <p style="color: var(--text-color); margin: 0; font-weight: 500; font-size: 0.95rem;">
                        Uploading your content... (${timeLeft}s cooldown)
                    </p>
                </div>
            </div>`;

        // Update countdown every second
        const countdownInterval = setInterval(() => {
            timeLeft--;
            if (timeLeft > 0) {
                const statusText = uploadStatus.querySelector('p');
                if (statusText) {
                    statusText.textContent = `Uploading your content... (${timeLeft}s cooldown)`;
                }
            }
        }, 1000);

        try {
            const file = new File([content], 'text.txt', {
                type: 'text/plain'
            });

            const formData = new FormData();
            formData.append('file', file);
            // formData.append('h-captcha-response', captchaResponse);

            const response = await fetch("/share-file", {
                method: "POST",
                body: formData
            });

            const data = await response.json();
            clearInterval(countdownInterval);

            if (data.error) {
                uploadStatus.innerHTML = `
                    <div class="share-form" style="background: #FFF2F2; border: 1px solid #FF4444;">
                        <p style="color: #FF4444; margin: 0; font-weight: 500; font-size: 0.95rem;">
                            ${data.error}
                        </p>
                    </div>`;
            } else {
                uploadStatus.innerHTML = `
                    <div class="share-form" style="background: #F5F5F7; border: 1px solid var(--border-color);">
                        <div style="text-align: center;">
                            <p style="color: var(--text-color); margin-bottom: 1rem; font-weight: 600; font-size: 1rem;">
                                Content uploaded successfully!
                            </p>
                            <div style="background: var(--background-color); padding: 1rem; border-radius: 12px; border: 1px solid var(--border-color); display: inline-block;">
                                <span style="font-size: 1.2rem; color: var(--text-color);">
                                    Access Code: <strong style="color: var(--secondary-color);">${data['File Code']}</strong>
                                </span>
                            </div>
                        </div>
                    </div>`;
                this.reset(); // Reset form
            }
        } catch (error) {
            clearInterval(countdownInterval);
            uploadStatus.innerHTML = `
                <div class="share-form" style="background: #FFF2F2; border: 1px solid #FF4444;">
                    <p style="color: #FF4444; margin: 0; font-weight: 500; font-size: 0.95rem;">
                        ${error.message || 'An error occurred during upload.'}
                    </p>
                </div>`;
        } finally {
            // Reset captcha and re-enable button after 10 seconds
            setTimeout(() => {
                submitButton.disabled = false;
                // hcaptcha.reset();
            }, 10000);
        }
    });

    // Replace the existing receive form handler with:
    document.getElementById("receiveForm").addEventListener("submit", async function(event) {
        event.preventDefault();

        const fileId = document.getElementById("fileId").value;
        const fileAccessResult = document.getElementById("fileAccessResult");
        const submitButton = this.querySelector('button[type="submit"]');

        // Disable submit button and show countdown
        submitButton.disabled = true;
        let timeLeft = 10;

        fileAccessResult.style.display = "block";
        fileAccessResult.innerHTML = `
            <div class="share-form" style="background: var(--background-color); border: 1px solid var(--border-color);">
                <div style="display: flex; align-items: center; gap: 1rem;">
                    <div class="spinner-border" style="color: var(--secondary-color); width: 1.5rem; height: 1.5rem;" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <p style="color: var(--text-color); margin: 0; font-weight: 500; font-size: 0.95rem;">
                        Fetching file... (${timeLeft}s cooldown)
                    </p>
                </div>
            </div>`;

        // Update countdown every second
        const countdownInterval = setInterval(() => {
            timeLeft--;
            if (timeLeft > 0) {
                const statusText = fileAccessResult.querySelector('p');
                if (statusText) {
                    statusText.textContent = `Fetching file... (${timeLeft}s cooldown)`;
                }
            }
        }, 1000);

        try {
            const response = await fetch("/receive-file", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ code: fileId })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || "Failed to fetch file info");
            }

            const fileInfo = await response.json();
            const filename = fileInfo.filename;
            const fileRoute = fileInfo.file_route; // Example: "/api/download/qewrwe"

            if (!fileRoute) {
                throw new Error("Invalid file route received.");
            }

            fileAccessResult.innerHTML = `<p>Downloading your file...</p>`;

            const fileResponse = await fetch(fileRoute);
            if (!fileResponse.ok) {
                throw new Error("Failed to fetch base64 file data.");
            }

            const fileData = await fileResponse.json();
            const base64String = fileData.file_base64;

            if (!base64String) {
                throw new Error("No file data received.");
            }

            const byteCharacters = atob(base64String);
            const byteNumbers = new Array(byteCharacters.length);
            for (let i = 0; i < byteCharacters.length; i++) {
                byteNumbers[i] = byteCharacters.charCodeAt(i);
            }
            const byteArray = new Uint8Array(byteNumbers);
            const blob = new Blob([byteArray], { type: "application/octet-stream" });

            const url = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.style.display = "none";
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

            fileAccessResult.innerHTML = `<p>Your file has been downloaded successfully.</p>`;

            clearInterval(countdownInterval);
            // Re-enable button after 10 seconds
            setTimeout(() => {
                submitButton.disabled = false;
            }, 10000);

        } catch (error) {
            clearInterval(countdownInterval);
            // Re-enable button after 10 seconds even on error
            setTimeout(() => {
                submitButton.disabled = false;
            }, 10000);
            fileAccessResult.innerHTML = `
                <div class="share-form" style="background: #FFF2F2; border: 1px solid #FF4444;">
                    <p style="color: #FF4444; margin: 0; font-weight: 500; font-size: 0.95rem;">
                        Error: ${error.message}
                    </p>
                </div>`;
        }
    });