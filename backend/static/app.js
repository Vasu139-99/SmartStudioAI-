// ═══════════════════════════════════════
// SmartStudio AI — Main App JS
// ═══════════════════════════════════════

document.addEventListener('DOMContentLoaded', () => {

    // ── Auth Check ──
    checkAuth();

    // ── Elements ──
    const uploadGrid = document.getElementById('uploadGrid');
    const generateBtn = document.getElementById('generateBtn');
    const productName = document.getElementById('productName');

    const uploadSection = document.getElementById('uploadSection');
    const progressSection = document.getElementById('progressSection');
    const resultSection = document.getElementById('resultSection');
    const errorSection = document.getElementById('errorSection');

    const files = [null, null, null, null];

    // ── Nav Buttons ──
    document.getElementById('logoutBtn').addEventListener('click', handleLogout);
    document.getElementById('deleteAccountBtn').addEventListener('click', handleDeleteAccount);

    // ── File Upload Handling ──
    uploadGrid.querySelectorAll('.file-input').forEach((input, index) => {
        input.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (!file) return;

            files[index] = file;
            const slot = input.closest('.upload-slot');
            const preview = slot.querySelector('.preview-img');
            preview.src = URL.createObjectURL(file);
            slot.classList.add('has-image');
            checkReady();
        });
    });

    // Remove buttons
    uploadGrid.querySelectorAll('.remove-btn').forEach((btn, index) => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            files[index] = null;
            const slot = btn.closest('.upload-slot');
            slot.classList.remove('has-image');
            slot.querySelector('.preview-img').src = '';
            slot.querySelector('.file-input').value = '';
            checkReady();
        });
    });

    function checkReady() {
        const allFilled = files.filter(f => f !== null).length === 4;
        generateBtn.disabled = !allFilled;
    }

    // ── Custom Script Toggle ──
    const customScriptToggle = document.getElementById('customScriptToggle');
    const customScriptText = document.getElementById('customScriptText');
    if (customScriptToggle && customScriptText) {
        customScriptToggle.addEventListener('change', (e) => {
            customScriptText.style.display = e.target.checked ? 'block' : 'none';
        });
    }

    // ── Live Color Sync ──
    const captionColor = document.getElementById('captionColor');
    const captionColorResult = document.getElementById('captionColorResult');

    function updateLiveCaptionColor(color) {
        const captionsContainer = document.getElementById('customCaptionsContainer');
        if (captionsContainer) {
            const currentCaption = captionsContainer.querySelector('.custom-caption-text');
            if (currentCaption) {
                currentCaption.style.color = color;
            }
        }
    }

    if (captionColor) {
        captionColor.addEventListener('input', () => updateLiveCaptionColor(captionColor.value));
    }
    if (captionColorResult) {
        captionColorResult.addEventListener('input', () => updateLiveCaptionColor(captionColorResult.value));
    }

    // ── Generate Video ──
    generateBtn.addEventListener('click', async () => {
        if (files.filter(f => f !== null).length !== 4) return;

        const formData = new FormData();
        formData.append('product_name', productName.value || 'Product');
        formData.append('language', document.getElementById('languageSelect').value || 'English');

        if (customScriptToggle && customScriptToggle.checked) {
            const scriptText = customScriptText.value.trim();
            if (scriptText) {
                formData.append('custom_script', scriptText);
            }
        }

        const captionColor = document.getElementById('captionColor');
        if (captionColor) {
            formData.append('caption_color', captionColor.value);
        }

        const aspectRatio = document.getElementById('aspectRatioSelect');
        if (aspectRatio) {
            formData.append('aspect_ratio', aspectRatio.value);
        }

        files.forEach(f => formData.append('images', f));

        // Show progress
        uploadSection.style.display = 'none';
        progressSection.style.display = 'block';
        resultSection.style.display = 'none';
        errorSection.style.display = 'none';

        // Reset progress steps
        document.querySelectorAll('.progress-step').forEach(s => {
            s.classList.remove('active', 'completed');
        });

        try {
            const res = await fetch('/api/generate', {
                method: 'POST',
                body: formData
            });

            const data = await res.json();

            if (res.ok) {
                startPolling(data.project_id);
            } else {
                showError(data.error || 'Failed to start generation');
            }
        } catch (err) {
            showError('Network error. Please try again.');
        }
    });

    // ── Polling ──
    let pollInterval = null;

    function startPolling(projectId) {
        if (pollInterval) clearInterval(pollInterval);

        pollInterval = setInterval(async () => {
            try {
                const res = await fetch(`/api/project/${projectId}`);
                const data = await res.json();

                updateProgressSteps(data.current_step);
                document.getElementById('currentStatus').textContent = data.current_step || 'Processing...';

                if (data.status === 'completed') {
                    clearInterval(pollInterval);
                    showResult(data);
                } else if (data.status === 'failed') {
                    clearInterval(pollInterval);
                    showError(data.error_message || 'Generation failed');
                }
            } catch (err) {
                console.error('Poll error:', err);
            }
        }, 3000);
    }

    function updateProgressSteps(stepText) {
        if (!stepText) return;
        const steps = document.querySelectorAll('.progress-step');
        const lower = stepText.toLowerCase();

        if (lower.includes('analyz') || lower.includes('script')) {
            steps[0].classList.add('active');
        }
        if (lower.includes('3d') || lower.includes('generating') || lower.includes('video')) {
            steps[0].classList.remove('active');
            steps[0].classList.add('completed');
            steps[1].classList.add('active');
        }
        if (lower.includes('merg')) {
            steps[1].classList.remove('active');
            steps[1].classList.add('completed');
            steps[2].classList.add('active');
        }
        if (lower.includes('voice') || lower.includes('audio') || lower.includes('caption')) {
            steps[2].classList.remove('active');
            steps[2].classList.add('completed');
            steps[3].classList.add('active');
        }
        if (lower.includes('done') || lower.includes('complete')) {
            steps[3].classList.remove('active');
            steps[3].classList.add('completed');
            steps[4].classList.add('active');
            steps[4].classList.add('completed');
        }
    }

    function showResult(data) {
        progressSection.style.display = 'none';
        resultSection.style.display = 'block';

        const video = document.getElementById('videoPlayer');
        const captionsContainer = document.getElementById('customCaptionsContainer');
        const remixBtn = document.getElementById('remixBtn');
        const voiceLanguageChange = document.getElementById('voiceLanguageChange');
        const captionColorResult = document.getElementById('captionColorResult');

        // Sync result controls with current project state
        if (voiceLanguageChange) {
            const generateLang = document.getElementById('languageSelect').value || 'English';
            voiceLanguageChange.value = generateLang;
        }
        if (captionColorResult) {
            const initialColor = document.getElementById('captionColor')?.value || '#ffff00';
            captionColorResult.value = initialColor;
        }

        if (captionsContainer) {
            captionsContainer.innerHTML = '';
            captionsContainer.dataset.currentText = '';
        }

        video.src = data.video_path;

        // Clear existing tracks
        video.innerHTML = '';

        const highlightWord = (productName.value || '').trim();

        // Subtitle Color Result Live update listener
        if (captionColorResult) {
            captionColorResult.addEventListener('input', () => {
                const currentCaption = captionsContainer.querySelector('.custom-caption-text');
                if (currentCaption) {
                    currentCaption.style.color = captionColorResult.value;
                }
            });
        }

        // ── Custom JS Caption Rendering ──
        video.ontimeupdate = () => {
            if (!captionsContainer || !video.textTracks || video.textTracks.length === 0) return;

            let activeTrack = null;
            for (let i = 0; i < video.textTracks.length; i++) {
                if (video.textTracks[i].mode === 'showing' || video.textTracks[i].mode === 'hidden') {
                    video.textTracks[i].mode = 'hidden'; // Force native renderer to hide
                    activeTrack = video.textTracks[i];
                    break;
                }
            }

            if (activeTrack && activeTrack.activeCues && activeTrack.activeCues.length > 0) {
                const currentCue = activeTrack.activeCues[0];

                if (captionsContainer.dataset.currentText !== currentCue.text) {
                    captionsContainer.dataset.currentText = currentCue.text;

                    let formattedText = currentCue.text;
                    if (highlightWord && highlightWord.length >= 2) {
                        // Safe escape and regex setup to ensure case-insensitive highlighting
                        const safeWord = highlightWord.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
                        const regex = new RegExp(`(${safeWord})`, 'gi');
                        formattedText = formattedText.replace(regex, '<span class="caption-highlight">$1</span>');
                    }

                    // Forcing reflow to restart CSS animation:
                    captionsContainer.innerHTML = '';
                    const captionEl = document.createElement('div');
                    captionEl.className = 'custom-caption-text';

                    // Sync with our color picker
                    const resColor = document.getElementById('captionColorResult');
                    const topColor = document.getElementById('captionColor');
                    if (resColor) {
                        captionEl.style.color = resColor.value;
                    } else if (topColor) {
                        captionEl.style.color = topColor.value;
                    }

                    captionEl.innerHTML = formattedText;
                    captionsContainer.appendChild(captionEl);
                }
            } else {
                captionsContainer.innerHTML = '';
                captionsContainer.dataset.currentText = '';
            }
        };

        // Add CC tracks
        if (data.vtt_paths && data.vtt_paths !== '{}') {
            try {
                const tracks = typeof data.vtt_paths === 'string' ? JSON.parse(data.vtt_paths) : data.vtt_paths;

                // Determine which track should be default based on the generated language
                const generateLang = document.getElementById('languageSelect').value || 'English';
                const liveCaptionSelect = document.getElementById('liveCaptionSelect');
                let initialTrackName = generateLang;

                // Set initial dropdown value
                if (liveCaptionSelect) {
                    liveCaptionSelect.value = initialTrackName;
                }

                for (const [langName, filename] of Object.entries(tracks)) {
                    const track = document.createElement('track');
                    track.kind = 'captions';
                    track.label = langName;
                    track.srclang = getLangCode(langName);
                    track.src = `/static/output/${filename}`;
                    if (langName === initialTrackName) {
                        track.default = true;
                    }
                    video.appendChild(track);
                }

                // Initial setup to make sure only our selected language track is active 
                // and hide native tracks so we only see the custom JS rendering
                video.addEventListener('loadedmetadata', () => {
                    for (let i = 0; i < video.textTracks.length; i++) {
                        if (video.textTracks[i].label === initialTrackName) {
                            video.textTracks[i].mode = 'hidden'; // 'hidden' means actively loaded but don't show native UI
                        } else {
                            video.textTracks[i].mode = 'disabled';
                        }
                    }
                });

                // Add event listener to our live dropdown
                if (liveCaptionSelect) {
                    liveCaptionSelect.addEventListener('change', (e) => {
                        const selectedLang = e.target.value;

                        // Clear the current active caption text so it instantly refreshes
                        if (captionsContainer) {
                            captionsContainer.innerHTML = '';
                            captionsContainer.dataset.currentText = '';
                        }

                        for (let i = 0; i < video.textTracks.length; i++) {
                            const track = video.textTracks[i];
                            if (selectedLang === 'Off') {
                                track.mode = 'disabled';
                            } else if (track.label === selectedLang) {
                                track.mode = 'hidden'; // Make it active for our JS reader
                            } else {
                                track.mode = 'disabled';
                            }
                        }
                    });
                }
            } catch (e) {
                console.error('Failed to parse vtt paths:', e);
            }
        }

        const downloadBtn = document.getElementById('downloadBtn');
        const liveCaptionSelect = document.getElementById('liveCaptionSelect');
        const downloadLoader = document.getElementById('downloadLoader');

        if (downloadBtn) {
            downloadBtn.href = data.download_path || data.video_path;

            // Set up dynamic download behavior based on Live Caption choice
            // Remove old event listeners by cloning
            const newDownloadBtn = downloadBtn.cloneNode(true);
            downloadBtn.parentNode.replaceChild(newDownloadBtn, downloadBtn);

            newDownloadBtn.addEventListener('click', async (e) => {
                const selectedLang = liveCaptionSelect ? liveCaptionSelect.value : 'Off';

                if (selectedLang !== 'Off' && selectedLang) {
                    e.preventDefault();

                    // Disable buttons & show loading
                    newDownloadBtn.style.display = 'none';
                    if (downloadLoader) downloadLoader.style.display = 'inline-block';
                    if (liveCaptionSelect) liveCaptionSelect.disabled = true;

                    // Ask backend to burn subtitles on demand
                    try {
                        const res = await fetch(`/api/project/${data.id}/burn_captions`, {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify({
                                language: selectedLang,
                                captionColor: document.getElementById('captionColorResult')?.value || document.getElementById('captionColor')?.value || '#ffff00'
                            })
                        });

                        const result = await res.json();

                        if (result.success && result.download_url) {
                            // Trigger immediate download
                            const a = document.createElement('a');
                            a.href = result.download_url;
                            a.download = '';
                            document.body.appendChild(a);
                            a.click();
                            document.body.removeChild(a);
                        } else {
                            alert(result.error || "Failed to burn captions");
                        }
                    } catch (err) {
                        alert("Network error while generating captions");
                    } finally {
                        // Restore UI
                        newDownloadBtn.style.display = 'inline-block';
                        if (downloadLoader) downloadLoader.style.display = 'none';
                        if (liveCaptionSelect) liveCaptionSelect.disabled = false;
                    }
                } else {
                    // "Off" selected: download the raw unburned video 
                    // To ensure we get the clean original video without default burns:
                    e.preventDefault();
                    const a = document.createElement('a');
                    a.href = data.video_path; // Use the base unburned video path
                    a.download = '';
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                }
            });
        }

        loadProjects();
    }

    function getLangCode(langName) {
        const map = {
            "English": "en", "Spanish": "es", "French": "fr", "German": "de",
            "Italian": "it", "Portuguese": "pt", "Hindi": "hi", "Japanese": "ja", "Korean": "ko"
        };
        return map[langName] || "en";
    }

    function showError(message) {
        progressSection.style.display = 'none';
        uploadSection.style.display = 'none';
        errorSection.style.display = 'block';
        document.getElementById('errorText').textContent = message;
    }

    // ── Reset / Retry ──
    function resetUI() {
        uploadSection.style.display = 'block';
        progressSection.style.display = 'none';
        resultSection.style.display = 'none';
        errorSection.style.display = 'none';

        files.fill(null);
        uploadGrid.querySelectorAll('.upload-slot').forEach(slot => {
            slot.classList.remove('has-image');
            slot.querySelector('.preview-img').src = '';
            slot.querySelector('.file-input').value = '';
        });
        generateBtn.disabled = true;
        loadProjects();
    }

    document.getElementById('newVideoBtn')?.addEventListener('click', resetUI);
    document.getElementById('retryBtn')?.addEventListener('click', resetUI);

    // ── Load Projects ──
    async function loadProjects() {
        try {
            const res = await fetch('/api/projects');
            const data = await res.json();
            const list = document.getElementById('projectsList');

            if (!data.projects || data.projects.length === 0) {
                list.innerHTML = '<p class="empty-state">No projects yet. Create your first one above!</p>';
                return;
            }

            list.innerHTML = data.projects.map(p => {
                const date = new Date(p.created_at).toLocaleString();
                return `
                    <div class="project-card" data-id="${p.id}">
                        <button class="project-delete-btn" onclick="deleteProject('${p.id}', event)" title="Delete">×</button>
                        <div class="project-name">${p.product_name}</div>
                        <span class="project-status ${p.status}">${p.status.toUpperCase()}</span>
                        <div class="project-date">${date}</div>
                    </div>`;
            }).join('');
        } catch (err) {
            console.error('Failed to load projects:', err);
        }
    }

    // Load projects on page load
    loadProjects();
});


// ═══════════════════════════════════════
// Auth Functions (global scope)
// ═══════════════════════════════════════

async function checkAuth() {
    try {
        const res = await fetch('/api/me');
        if (res.ok) {
            const data = await res.json();
            document.getElementById('navUsername').textContent = `👤 ${data.user.username}`;
        } else {
            window.location.href = '/login';
        }
    } catch (err) {
        window.location.href = '/login';
    }
}

async function handleLogout() {
    try {
        await fetch('/api/logout', { method: 'POST' });
        window.location.href = '/login';
    } catch (err) {
        window.location.href = '/login';
    }
}

async function handleDeleteAccount() {
    const confirmed = confirm(
        '⚠️ DELETE ACCOUNT\n\n' +
        'This will permanently delete your account and ALL your projects.\n\n' +
        'Are you sure? This cannot be undone.'
    );

    if (!confirmed) return;

    try {
        const res = await fetch('/api/account', { method: 'DELETE' });
        if (res.ok) {
            alert('Account deleted successfully.');
            window.location.href = '/login';
        } else {
            const data = await res.json();
            alert(data.error || 'Failed to delete account');
        }
    } catch (err) {
        alert('Network error. Please try again.');
    }
}

async function deleteProject(projectId, event) {
    event.stopPropagation();

    const confirmed = confirm('Delete this project? This cannot be undone.');
    if (!confirmed) return;

    try {
        const res = await fetch(`/api/project/${projectId}`, { method: 'DELETE' });
        if (res.ok) {
            // Remove card from UI
            const card = document.querySelector(`.project-card[data-id="${projectId}"]`);
            if (card) {
                card.style.transition = 'all 0.3s';
                card.style.opacity = '0';
                card.style.transform = 'scale(0.9)';
                setTimeout(() => card.remove(), 300);
            }
        } else {
            const data = await res.json();
            alert(data.error || 'Failed to delete project');
        }
    } catch (err) {
        alert('Network error. Please try again.');
    }
}