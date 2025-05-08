        // File upload form handler
        document.getElementById("fileShareForm").addEventListener("submit", async function(event) {
            event.preventDefault();

            const uploadStatus = document.getElementById("uploadStatus");
            const fileInput = document.getElementById("fileInput");
            const submitButton = this.querySelector('button[type="submit"]');
            
            // Check if captcha is filled
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

            // Check if file is selected
            if (!fileInput.files[0]) {
                uploadStatus.style.display = "block";
                uploadStatus.innerHTML = `
                    <div class="share-form" style="background: #FFF2F2; border: 1px solid #FF4444;">
                        <p style="color: #FF4444; margin: 0; font-weight: 500; font-size: 0.95rem;">
                            Please select a file to upload.
                        </p>
                    </div>`;
                return;
            }

            // Disable submit button and start countdown
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
                            Uploading your file... (${timeLeft}s cooldown)
                        </p>
                    </div>
                </div>`;

            // Update countdown every second
            const countdownInterval = setInterval(() => {
                timeLeft--;
                if (timeLeft > 0) {
                    const statusText = uploadStatus.querySelector('p');
                    if (statusText) {
                        statusText.textContent = `Uploading your file... (${timeLeft}s cooldown)`;
                    }
                }
            }, 1000);

            const file = fileInput.files[0];

            // Check file size
            const MAX_REGULAR_SIZE = 2.5 * 1024 * 1024; // 2.5MB
            const MAX_FILE_SIZE = 5 * 1024 * 1024;      // 5MB

            if (file.size > MAX_FILE_SIZE) {
                clearInterval(countdownInterval);
                uploadStatus.innerHTML = `
                    <div class="share-form" style="background: #FFF2F2; border: 1px solid #FF4444;">
                        <p style="color: #FF4444; margin: 0; font-weight: 500; font-size: 0.95rem;">
                            File size exceeds the 5MB limit.
                        </p>
                    </div>`;
                submitButton.disabled = false;
                return;
            }

            // Show beta warning for large files
            if (file.size > MAX_REGULAR_SIZE) {
                uploadStatus.innerHTML = `
                    <div class="share-form" style="background: #FFF7E6; border: 1px solid #FFB800;">
                        <div style="text-align: left;">
                            <p style="color: #995500; margin: 0 0 8px 0; font-weight: 500; font-size: 0.95rem;">
                                ⚠️ Beta Phase: Large File Upload
                            </p>
                            <p style="color: #995500; margin: 0; font-size: 0.85rem;">
                                Files larger than 2.5MB are in beta testing. Upload might take longer and could occasionally fail.
                                Please try again if upload fails.
                            </p>
                        </div>
                    </div>`;
                
                // Wait 2 seconds before starting upload
                await new Promise(resolve => setTimeout(resolve, 2000));
            }

            try {
                const formData = new FormData(this);
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
                                Something failed. <a href="/fixes" style="color: #FF4444; text-decoration: underline;">Check fixes</a>
                            </p>
                        </div>`;
                } else {
                    uploadStatus.innerHTML = `
                        <div class="share-form" style="background: #F5F5F7; border: 1px solid var(--border-color);">
                            <div style="text-align: center;">
                                <p style="color: var(--text-color); margin-bottom: 1rem; font-weight: 600; font-size: 1rem;">
                                    File uploaded successfully!
                                </p>
                                <div style="background: var(--background-color); padding: 1rem; border-radius: 12px; border: 1px solid var(--border-color); display: inline-block;">
                                    <span style="font-size: 1.2rem; color: var(--text-color);">
                                        Access Code: <strong style="color: var(--secondary-color);">${data['File Code']}</strong>
                                    </span>
                                </div>
                            </div>
                        </div>`;
                    fileInput.value = '';
                }
            } catch (error) {
                clearInterval(countdownInterval);
                uploadStatus.innerHTML = `
                    <div class="share-form" style="background: #FFF2F2; border: 1px solid #FF4444;">
                        <p style="color: #FF4444; margin: 0; font-weight: 500; font-size: 0.95rem;">
                            Something failed. <a href="/fixes" style="color: #FF4444; text-decoration: underline;">Check fixes</a>
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

        // File access form handler
        document.getElementById("receiveForm").addEventListener("submit", async function(event) {
            event.preventDefault();

            const submitButton = this.querySelector('button[type="submit"]');
            const fileId = document.getElementById("fileId");
            const fileAccessResult = document.getElementById("fileAccessResult");

            // Disable the submit button and start countdown
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
                            Fetching file information... (${timeLeft}s cooldown)
                        </p>
                    </div>
                </div>`;

            // Update countdown every second
            const countdownInterval = setInterval(() => {
                timeLeft--;
                if (timeLeft > 0) {
                    fileAccessResult.querySelector('p').textContent = `Fetching file information... (${timeLeft}s cooldown)`;
                }
            }, 1000);

            try {
                const response = await fetch("/receive-file", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ code: fileId.value })
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.error || "Failed to fetch file info");
                }

                const fileInfo = await response.json();
                const filename = fileInfo.filename;
                const fileRoute = fileInfo.file_route;

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

                // Clear the countdown when done
                clearInterval(countdownInterval);
                
                // Re-enable the submit button after 10 seconds
                setTimeout(() => {
                    submitButton.disabled = false;
                }, 10000);

            } catch (error) {
                // Clear the countdown on error
                clearInterval(countdownInterval);
                
                // Re-enable the submit button after 10 seconds
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
