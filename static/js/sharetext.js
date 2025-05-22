document.addEventListener("DOMContentLoaded", function() {
    // Text share form handler
    const textShareForm = document.getElementById("textShareForm");
    if (textShareForm) {
        textShareForm.addEventListener("submit", async function(event) {
            event.preventDefault();

            const uploadStatus = document.getElementById("uploadStatus"); // Ensure this ID is unique or scoped if you have multiple status elements
            const submitButton = this.querySelector('button[type="submit"]');
            const contentTextArea = this.elements.content; // Assuming textarea has name="content"
            let countdownInterval;

            if (!uploadStatus || !submitButton || !contentTextArea) {
                console.error("Text share form: One or more required elements not found.");
                alert("Page setup error (text share). Please contact support.");
                return;
            }

            const content = contentTextArea.value.trim();

            if (!content) {
                uploadStatus.style.display = "block";
                uploadStatus.className = 'status-box error mt-medium';
                uploadStatus.innerHTML = `<p>Please enter some content to share.</p>`;
                return;
            }

            const wordCount = content.split(/\s+/).filter(word => word.length > 0).length;
            if (wordCount > 1000) { // Keep your word count limit
                uploadStatus.style.display = "block";
                uploadStatus.className = 'status-box error mt-medium';
                uploadStatus.innerHTML = `<p>Content exceeds 1000 words limit (current: ${wordCount} words)</p>`;
                return;
            }

            submitButton.disabled = true;
            let timeLeft = 10; // Cooldown

            uploadStatus.style.display = "block";
            uploadStatus.className = 'status-box mt-medium';
            uploadStatus.innerHTML = `
                <div style="display: flex; align-items: center; gap: 0.75rem;">
                    <span style="font-size: 1.2rem; line-height: 1;">⏳</span>
                    <p style="margin: 0;">Sharing your content... (Submit again in ${timeLeft}s)</p>
                </div>`;

            countdownInterval = setInterval(() => {
                timeLeft--;
                const statusTextP = uploadStatus.querySelector('p');
                if (timeLeft > 0) {
                    if (statusTextP) {
                        statusTextP.textContent = `Sharing your content... (Submit again in ${timeLeft}s)`;
                    }
                } else {
                    clearInterval(countdownInterval);
                    if (statusTextP && statusTextP.textContent.includes("Submit again in")) {
                        statusTextP.textContent = `Sharing your content...`;
                    }
                }
            }, 1000);

            try {
                const file = new File([content], 'shared_text.txt', {
                    type: 'text/plain'
                });

                const formData = new FormData();
                formData.append('file', file); // Backend /share-file expects 'file'

                const response = await fetch("/share-file", { // Uses the same endpoint as file sharing
                    method: "POST",
                    body: formData
                });

                clearInterval(countdownInterval); // Stop countdown on response
                const data = await response.json();

                if (!response.ok || data.error) {
                    const errorMessage = data.error || `Server error (${response.status}). Please try again.`;
                    uploadStatus.className = 'status-box error mt-medium';
                    uploadStatus.innerHTML = `<p>${errorMessage} <a href="/fixes">Check fixes</a></p>`;
                } else if (data.success && data.FileCode) { // Check for FileCode from backend
                    uploadStatus.className = 'status-box success mt-medium';
                    uploadStatus.innerHTML = `
                        <div style="text-align: center;">
                            <p style="margin-bottom: 1rem; font-weight: 700; font-size: 1rem;">
                                Content shared successfully!
                            </p>
                            <div style="background: var(--background); padding: 0.75rem 1rem; border-radius: var(--radius); border: 1px solid var(--border); display: inline-block; box-shadow: var(--shadow-sm);">
                                <span style="font-size: 1.1rem; color: var(--foreground);">
                                    Access Code: <strong style="color: var(--primary); font-size: 1.2rem;">${data.FileCode}</strong>
                                </span>
                            </div>
                        </div>`;
                    contentTextArea.value = ''; // Clear textarea
                } else {
                    uploadStatus.className = 'status-box error mt-medium';
                    uploadStatus.innerHTML = `<p>Received an unexpected response from the server. <a href="/fixes">Check fixes</a></p>`;
                }
            } catch (error) {
                clearInterval(countdownInterval);
                console.error("Text share error:", error);
                uploadStatus.className = 'status-box error mt-medium';
                uploadStatus.innerHTML = `<p>A network or client-side error occurred. Please try again. <a href="/fixes">Check fixes</a></p>`;
            } finally {
                setTimeout(() => {
                    submitButton.disabled = false;
                    if(countdownInterval) clearInterval(countdownInterval);

                    const statusTextP = uploadStatus.querySelector('p');
                    if (statusTextP && statusTextP.textContent.includes("Submit again in")) {
                         uploadStatus.innerHTML = `<p>Ready for next share.</p>`;
                         setTimeout(()=> { if(uploadStatus) uploadStatus.style.display = "none"; }, 3000);
                    }
                }, 10000); // Cooldown duration
            }
        });
    } else {
        console.warn("textShareForm not found in the DOM.");
    }

    // --- Receive form handler (SHOULD BE IDENTICAL TO THE ONE IN sharefile.js) ---
    const receiveForm = document.getElementById("receiveForm");
    if (receiveForm) {
        receiveForm.addEventListener("submit", async function(event) {
            event.preventDefault();

            const submitButton = this.querySelector('button[type="submit"]');
            const fileIdInput = document.getElementById("fileId");
            const fileAccessResult = document.getElementById("fileAccessResult"); // Ensure this ID is unique or scoped

            if (!submitButton || !fileIdInput || !fileAccessResult) {
                console.error("Receive form (text page): One or more required elements not found.");
                alert("Page setup error (receive form). Please contact support.");
                return;
            }

            submitButton.disabled = true;
            let timeLeft = 10;
            let countdownInterval;

            fileAccessResult.style.display = "block";
            fileAccessResult.className = 'status-box mt-medium';
            fileAccessResult.innerHTML = `
                <div style="display: flex; align-items: center; gap: 0.75rem;">
                    <span style="font-size: 1.2rem; line-height: 1;">⏳</span>
                    <p style="margin: 0;">Fetching content... (Submit again in ${timeLeft}s)</p>
                </div>`;

            countdownInterval = setInterval(() => {
                timeLeft--;
                const statusTextP = fileAccessResult.querySelector('p');
                if (timeLeft > 0) {
                    if (statusTextP) {
                        statusTextP.textContent = `Fetching content... (Submit again in ${timeLeft}s)`;
                    }
                } else {
                    clearInterval(countdownInterval);
                    if (statusTextP && statusTextP.textContent.includes("Submit again in")) {
                        statusTextP.textContent = `Fetching content...`;
                    }
                }
            }, 1000);

            try {
                const accessCode = fileIdInput.value.trim();
                if (!/^\d{4}$/.test(accessCode)) { // Basic 4-digit validation
                    throw new Error("Invalid Access Code. Please enter a 4-digit code.");
                }

                const response = await fetch("/receive-file", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ code: accessCode })
                });

                const fileInfo = await response.json();
                // console.log("Received from /receive-file (text page):", fileInfo);

                if (!response.ok || fileInfo.error) {
                    const errorMessage = fileInfo.error || `Server error (${response.status}). Please try again.`;
                    throw new Error(errorMessage);
                }

                if (fileInfo.success && fileInfo.download_url && fileInfo.filename) {
                    const downloadUrl = fileInfo.download_url;
                    const filename = fileInfo.filename; // This will be 'shared_text.txt' or similar

                    fileAccessResult.className = 'status-box mt-medium';
                    const statusTextP = fileAccessResult.querySelector('p');
                    if (statusTextP) {
                        statusTextP.textContent = `Initiating download for: ${filename}...`;
                    } else {
                         fileAccessResult.innerHTML = `
                            <div style="display: flex; align-items: center; gap: 0.75rem;">
                                <span style="font-size: 1.2rem; line-height: 1;">⏳</span>
                                <p style="margin: 0;">Initiating download for: ${filename}...</p>
                            </div>`;
                    }

                    // Download the text file
                    const a = document.createElement("a");
                    a.style.display = "none";
                    a.href = downloadUrl;
                    a.download = filename;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);

                    clearInterval(countdownInterval);
                    fileAccessResult.className = 'status-box success mt-medium';
                    fileAccessResult.innerHTML = `<p>Content "${filename}" download has started. Check your browser's downloads.</p>`;
                    fileIdInput.value = '';
                } else {
                    throw new Error(fileInfo.error || "Invalid response from server: Missing download details or success flag.");
                }

            } catch (error) {
                clearInterval(countdownInterval);
                console.error("Receive content error:", error);
                fileAccessResult.className = 'status-box error mt-medium';
                fileAccessResult.innerHTML = `<p>Error: ${error.message}</p>`;
            } finally {
                setTimeout(() => {
                    submitButton.disabled = false;
                    if(countdownInterval) clearInterval(countdownInterval);

                    const statusTextP = fileAccessResult.querySelector('p');
                    if (statusTextP && statusTextP.textContent.includes("Submit again in")) {
                         fileAccessResult.innerHTML = `<p>Ready to fetch more content.</p>`;
                         setTimeout(()=> { if(fileAccessResult) fileAccessResult.style.display = "none"; }, 3000);
                    }
                }, 10000); // Cooldown duration
            }
        });
    } else {
        console.warn("receiveForm not found in the DOM (text page).");
    }
});