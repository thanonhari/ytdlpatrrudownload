document.addEventListener("DOMContentLoaded", () => {
    // State
    let selectedPresetId = "video_best_subs";
    let presetsById = new Map();
    let tasksMap = new Map();
    let currentAnalyzeInfo = null;
    let activeCaptionType = "short";

    // DOM Elements
    const navButtons = document.querySelectorAll(".nav-btn");
    const tabContents = document.querySelectorAll(".tab-content");
    const urlInput = document.getElementById("url-input");
    const btnAnalyze = document.getElementById("btn-analyze");
    const previewCard = document.getElementById("video-preview-card");
    const duplicateAlertBox = document.getElementById("duplicate-alert-box");
    const btnOpenDupFolder = document.getElementById("btn-open-dup-folder");
    const btnOpenTitleFolder = document.getElementById("btn-open-title-folder");
    const presetsContainer = document.getElementById("presets-container");
    const customOptsHeader = document.getElementById("toggle-custom-opts");
    const customOptsBody = document.getElementById("custom-opts-body");
    const btnStartDownload = document.getElementById("btn-start-download");
    const btnUpdateYtDlp = document.getElementById("btn-update-ytdlp");
    const tasksContainer = document.getElementById("tasks-container");
    const filesTbody = document.getElementById("files-tbody");
    const queueCountBadge = document.getElementById("queue-count");

    // Caption Studio Elements
    const hashtagsCloud = document.getElementById("hashtags-cloud");
    const captionTextarea = document.getElementById("caption-textarea");
    const btnCopyHashtags = document.getElementById("btn-copy-hashtags");
    const btnCopyCaption = document.getElementById("btn-copy-caption");
    const capTabBtns = document.querySelectorAll(".cap-tab-btn");

    // Controls
    const chkAudioOnly = document.getElementById("chk-audio-only");
    const chkWriteSubs = document.getElementById("chk-write-subs");
    const chkUseWhisper = document.getElementById("chk-use-whisper");
    const optFormat = document.getElementById("opt-format");
    const optAudioFormat = document.getElementById("opt-audio-format");
    const optWhisperLang = document.getElementById("opt-whisper-lang");
    const optCookieType = document.getElementById("opt-cookie-type");
    const optCookieVal = document.getElementById("opt-cookie-val");
    const btnOpenExplorer = document.getElementById("btn-open-explorer");
    const btnRefreshFiles = document.getElementById("btn-refresh-files");
    const cookieFileInput = document.getElementById("cookie-file-input");
    const btnUploadCookie = document.getElementById("btn-upload-cookie");
    const uploadedCookiesList = document.getElementById("uploaded-cookies-list");

    // 1. Tab Switching
    navButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            navButtons.forEach(b => b.classList.remove("active"));
            tabContents.forEach(t => t.classList.remove("active"));

            btn.classList.add("active");
            const targetTab = btn.getAttribute("data-tab");
            document.getElementById(targetTab).classList.add("active");

            if (targetTab === "tab-queue") loadTasks();
            if (targetTab === "tab-files") loadFiles();
            if (targetTab === "tab-settings") loadSystemStatus();
        });
    });

    // 2. Load Tasks via REST API
    async function loadTasks() {
        try {
            const res = await fetch("/api/tasks");
            const data = await res.json();
            if (data.tasks) {
                data.tasks.forEach(t => tasksMap.set(t.task_id, t));
                renderTasksList();
            }
        } catch (e) {
            console.error("Failed to load tasks:", e);
        }
    }

    // 3. Load Presets & Initial Status
    async function loadPresets() {
        try {
            const res = await fetch("/api/presets");
            const data = await res.json();
            presetsById = new Map((data.presets || []).map(p => [p.id, p]));
            renderPresets(data.presets || []);
        } catch (e) {
            console.error("Failed to load presets:", e);
        }
    }

    function applyPresetToForm(preset) {
        if (!preset) return;

        const formatInput = document.getElementById("opt-format");
        if (formatInput && preset.format) {
            formatInput.value = preset.format;
        }

        const resolutionSelect = document.getElementById("opt-resolution");
        if (resolutionSelect && preset.resolution) {
            resolutionSelect.value = preset.resolution;
        }

        const checkboxMap = {
            "chk-audio-only": preset.extract_audio,
            "chk-write-subs": preset.write_subs,
            "chk-embed-subs": preset.embed_subs,
            "chk-embed-metadata": preset.embed_metadata,
            "chk-embed-thumb": preset.embed_thumbnail,
            "chk-sponsorblock": preset.sponsorblock,
        };

        Object.entries(checkboxMap).forEach(([id, value]) => {
            const el = document.getElementById(id);
            if (el && typeof value === "boolean") {
                el.checked = value;
            }
        });

        const audioFormat = document.getElementById("opt-audio-format");
        if (audioFormat && preset.audio_format) {
            audioFormat.value = preset.audio_format;
        }

        if (audioFormat) {
            audioFormat.disabled = !document.getElementById("chk-audio-only")?.checked;
        }
    }

    function renderPresets(presets) {
        presetsContainer.innerHTML = "";
        presets.forEach(p => {
            const div = document.createElement("div");
            const formatValue = p.format || "default";
            const shortFormat = formatValue.length > 44 ? `${formatValue.slice(0, 41)}...` : formatValue;
            const isCustomFormat = Boolean(p.format);
            const formatHelp = isCustomFormat
                ? "?????????? format ??? yt-dlp ?????????????????????? --format ??????"
                : "???????? format ?????????????? preset ???";
            const fullFormatHelp = isCustomFormat
                ? `Format ????: ${p.format}`
                : "Format ????: default logic ??? preset";
            const formatBadgeClass = isCustomFormat ? "preset-format-badge custom" : "preset-format-badge default";
            const formatBadgeIcon = isCustomFormat ? "?" : "?";
            const formatBadgeText = isCustomFormat ? `Format: ${shortFormat}` : "Format: default";

            div.className = `preset-btn ${p.id === selectedPresetId ? "selected" : ""}`;
            div.setAttribute("data-id", p.id);
            div.title = `${p.name}
${formatHelp}`;
            div.innerHTML = `
                <div class="preset-title">${p.name}</div>
                <div class="preset-desc">${p.description}</div>
                <div class="${formatBadgeClass}" title="${escapeHtml(fullFormatHelp)}">
                    <span aria-hidden="true">${formatBadgeIcon}</span>
                    <span>${escapeHtml(formatBadgeText)}</span>
                </div>
            `;
            div.addEventListener("click", () => {
                document.querySelectorAll(".preset-btn").forEach(b => b.classList.remove("selected"));
                div.classList.add("selected");
                selectedPresetId = p.id;
                applyPresetToForm(p);
            });
            presetsContainer.appendChild(div);
        });

        applyPresetToForm(presetsById.get(selectedPresetId));
    }

    function renderCookieValueOptions(mode, selectedValue = "") {
        const fileOptions = JSON.parse(optCookieVal.getAttribute("data-files") || "[]");
        const browserOptions = JSON.parse(optCookieVal.getAttribute("data-browsers") || "[]");

        optCookieVal.innerHTML = "";

        const sourceOptions = mode === "browser" ? browserOptions : fileOptions;
        sourceOptions.forEach(item => {
            const opt = document.createElement("option");
            opt.value = item.name || item;
            opt.innerText = item.label || item;
            optCookieVal.appendChild(opt);
        });

        if (selectedValue) {
            optCookieVal.value = selectedValue;
        }
    }

    async function loadSystemStatus() {
        try {
            const res = await fetch("/api/status");
            const data = await res.json();

            document.getElementById("ytdlp-ver").innerText = `v${data.yt_dlp_version}`;

            // Sidebar GPU status
            const gpuText = document.getElementById("sidebar-gpu-text");
            if (data.gpu.gpu_accelerated) {
                const gpuName = data.gpu.nvidia?.gpus?.[0]?.name || "Hardware Accelerated";
                gpuText.innerText = `GPU: ${gpuName}`;
            } else {
                gpuText.innerText = "GPU: Standard (CPU Mode)";
            }

            optCookieVal.setAttribute("data-files", JSON.stringify(data.uploaded_cookies || []));
            optCookieVal.setAttribute("data-browsers", JSON.stringify(data.browsers || []));

            if (uploadedCookiesList) {
                const uploadedCookies = data.uploaded_cookies || [];
                uploadedCookiesList.innerHTML = "";
                if (uploadedCookies.length > 0) {
                    const wrap = document.createElement("div");
                    wrap.className = "cookie-uploaded-items";
                    uploadedCookies.forEach(name => {
                        const item = document.createElement("div");
                        item.className = "p-tag";
                        item.textContent = name;
                        wrap.appendChild(item);
                    });
                    uploadedCookiesList.appendChild(wrap);
                } else {
                    uploadedCookiesList.innerHTML = `<div class="empty-state"><div class="empty-icon">🍪</div><p>ยังไม่มีไฟล์ cookies.txt ที่อัปโหลด</p></div>`;
                }
            }

            const cookieType = optCookieType.value;
            if (cookieType === "browser" || cookieType === "file") {
                renderCookieValueOptions(cookieType, optCookieVal.value);
            }

            // Render Settings Tab
            const container = document.getElementById("gpu-details-container");
            if (container) {
                container.innerHTML = `<pre style="color: #a5b4fc; background: rgba(0,0,0,0.4); padding: 14px; border-radius: 8px;">${JSON.stringify(data, null, 2)}</pre>`;
            }
        } catch (e) {
            console.error("Failed to fetch system status:", e);
        }
    }

    // 4. Custom Options Accordion & Controls Toggle
    customOptsHeader.addEventListener("click", () => {
        customOptsBody.classList.toggle("hidden");
    });

    chkAudioOnly.addEventListener("change", () => {
        optAudioFormat.disabled = !chkAudioOnly.checked;
    });

    optCookieType.addEventListener("change", () => {
        const val = optCookieType.value;
        if (val === "none") {
            optCookieVal.classList.add("hidden");
            optCookieVal.innerHTML = "";
        } else {
            optCookieVal.classList.remove("hidden");
            renderCookieValueOptions(val, optCookieVal.value);
        }
    });

    btnUploadCookie.addEventListener("click", async () => {
        const file = cookieFileInput.files && cookieFileInput.files[0];
        if (!file) {
            showToast("?????????????? cookies.txt ????", "error");
            return;
        }

        const originalText = btnUploadCookie.innerText;
        btnUploadCookie.disabled = true;
        btnUploadCookie.innerText = "Uploading...";

        try {
            const formData = new FormData();
            formData.append("file", file);
            const res = await fetch("/api/upload-cookies", {
                method: "POST",
                body: formData
            });
            const data = await res.json();

            if (!res.ok || !data.success) {
                throw new Error(data.detail || "Upload failed");
            }

            cookieFileInput.value = "";
            showToast(`??????? ${data.filename} ?????????`, "success");
            await loadSystemStatus();
        } catch (e) {
            showToast(`??????? cookies.txt ?????????: ${e.message}`, "error");
        } finally {
            btnUploadCookie.disabled = false;
            btnUploadCookie.innerText = originalText || "Upload cookies.txt";
        }
    });

    if (chkUseWhisper && optWhisperLang) {
        const syncWhisperLangState = () => {
            optWhisperLang.disabled = !chkUseWhisper.checked;
        };
        chkUseWhisper.addEventListener("change", syncWhisperLangState);
        syncWhisperLangState();
    }

    if (btnUpdateYtDlp) {
        btnUpdateYtDlp.addEventListener("click", async () => {
            const originalText = btnUpdateYtDlp.innerText;
            btnUpdateYtDlp.disabled = true;
            btnUpdateYtDlp.innerText = "Updating...";
            try {
                const res = await fetch("/api/update-ytdlp", { method: "POST" });
                const data = await res.json();
                if (!res.ok || !data.success) {
                    throw new Error(data.detail || "Update failed");
                }
                showToast(`yt-dlp updated: v${data.yt_dlp_version || "unknown"}`, "success");
                await loadSystemStatus();
            } catch (e) {
                showToast(`yt-dlp update failed: ${e.message}`, "error");
            } finally {
                btnUpdateYtDlp.disabled = false;
                btnUpdateYtDlp.innerText = originalText || "Update yt-dlp";
            }
        });
    }

    // 5. Analyze URL Metadata & Render Caption Studio & Duplicate Check
    btnAnalyze.addEventListener("click", async () => {
        const url = urlInput.value.trim();
        if (!url) return showToast("กรุณากรอก URL วิดีโอ", "error");

        btnAnalyze.disabled = true;
        btnAnalyze.innerText = "⏳ กำลังวิเคราะห์...";
        duplicateAlertBox.classList.add("hidden");

        try {
            const cookieType = optCookieType.value !== "none" ? optCookieType.value : null;
            const cookieVal = cookieType ? optCookieVal.value : null;
            const query = new URLSearchParams({ url });
            if (cookieType && cookieVal) {
                query.set("cookie_type", cookieType);
                query.set("cookie_val", cookieVal);
            }
            const res = await fetch(`/api/info?${query.toString()}`);
            const data = await res.json();

            if (data.success && data.info) {
                currentAnalyzeInfo = data.info;
                renderPreview(data.info);

                if (data.info.duplicate_info && data.info.duplicate_info.exists) {
                    showToast("⚠️ ตรวจพบไฟล์วิดีโอนี้เคยดาวน์โหลดไว้แล้ว!", "info");
                    duplicateAlertBox.classList.remove("hidden");
                    btnOpenDupFolder.setAttribute("data-path", data.info.duplicate_info.folder_path);
                    btnOpenTitleFolder.setAttribute("data-path", data.info.duplicate_info.folder_path);
                } else {
                    showToast("วิเคราะห์ลิงก์และสร้างแฮชแท็กเรียบร้อย!", "success");
                }
            } else {
                showToast(`วิเคราะห์ล้มเหลว: ${data.detail || 'ไม่ทราบสาเหตุ'}`, "error");
            }
        } catch (e) {
            showToast(`เกิดข้อผิดพลาด: ${e.message}`, "error");
        } finally {
            btnAnalyze.disabled = false;
            btnAnalyze.innerText = "🔍 วิเคราะห์ลิงก์";
        }
    });

    function renderPreview(info) {
        document.getElementById("prev-thumb").src = info.thumbnail || "";
        document.getElementById("prev-title").innerText = info.title || "Unknown Title";
        document.getElementById("prev-uploader").innerText = `ช่อง/ผู้สร้าง: ${info.uploader || '-'}`;
        document.getElementById("prev-duration").innerText = info.duration_string || "";

        const subsBox = document.getElementById("prev-subs-tags");
        subsBox.innerHTML = "";
        if (info.subtitles && info.subtitles.length > 0) {
            info.subtitles.forEach(s => {
                subsBox.innerHTML += `<span class="p-tag" style="background: rgba(16, 185, 129, 0.2); color: #6ee7b7;">ซับ: ${s}</span>`;
            });
        } else {
            subsBox.innerHTML = `<span class="p-tag" style="background: rgba(245, 158, 11, 0.2); color: #fcd34d;">ไม่มีซับต้นทาง (ใช้ AI Whisper ได้)</span>`;
        }

        // Populate resolution options
        if (info.formats && info.formats.length > 0) {
            const select = document.getElementById("opt-resolution");
            select.innerHTML = '<option value="best" selected>สูงสุด (Best Available)</option>';
            info.formats.forEach(f => {
                select.innerHTML += `<option value="${f.height}">${f.resolution} (${f.ext}) - approx ${f.filesize_approx_mb} MB</option>`;
            });
        }

        // Populate Caption Studio
        if (info.caption_studio) {
            renderCaptionStudio(info.caption_studio);
        }

        previewCard.classList.remove("hidden");
    }

    // Open Folder Handlers from Preview
    btnOpenDupFolder.addEventListener("click", () => {
        const path = btnOpenDupFolder.getAttribute("data-path");
        fetch("/api/open-folder", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ path: path })
        });
    });

    btnOpenTitleFolder.addEventListener("click", () => {
        const path = btnOpenTitleFolder.getAttribute("data-path");
        fetch("/api/open-folder", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ path: path })
        });
    });

    function renderCaptionStudio(studio) {
        hashtagsCloud.innerHTML = "";
        if (studio.hashtags) {
            studio.hashtags.forEach(tag => {
                const pill = document.createElement("span");
                pill.className = "tag-pill";
                pill.innerText = tag;
                pill.addEventListener("click", () => {
                    navigator.clipboard.writeText(tag);
                    showToast(`คัดลอก ${tag} เรียบร้อย!`, "success");
                });
                hashtagsCloud.appendChild(pill);
            });
        }

        updateCaptionTextarea(studio);
    }

    function updateCaptionTextarea(studio) {
        if (!studio) return;
        if (activeCaptionType === "short") {
            captionTextarea.value = studio.caption_short || "";
        } else if (activeCaptionType === "full") {
            captionTextarea.value = studio.caption_full || "";
        } else if (activeCaptionType === "editor") {
            captionTextarea.value = studio.caption_editor || "";
        }
    }

    capTabBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            capTabBtns.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            activeCaptionType = btn.getAttribute("data-cap");
            if (currentAnalyzeInfo && currentAnalyzeInfo.caption_studio) {
                updateCaptionTextarea(currentAnalyzeInfo.caption_studio);
            }
        });
    });

    btnCopyHashtags.addEventListener("click", () => {
        if (currentAnalyzeInfo && currentAnalyzeInfo.caption_studio) {
            navigator.clipboard.writeText(currentAnalyzeInfo.caption_studio.hashtags_text || "");
            showToast("คัดลอกแฮชแท็กทั้งหมดเรียบร้อย!", "success");
        }
    });

    btnCopyCaption.addEventListener("click", () => {
        if (captionTextarea.value) {
            navigator.clipboard.writeText(captionTextarea.value);
            showToast("คัดลอกแคปชันเรียบร้อย!", "success");
        }
    });

    // 6. Start Download & Submit Task
    btnStartDownload.addEventListener("click", async () => {
        const url = urlInput.value.trim();
        if (!url) return showToast("กรุณากรอก URL วิดีโอ", "error");

        btnStartDownload.disabled = true;
        btnStartDownload.innerText = "⏳ กำลังส่งคำสั่ง...";

        const payload = {
            url: url,
            preset_id: selectedPresetId,
            format: optFormat.value.trim() || null,
            resolution: document.getElementById("opt-resolution") ? document.getElementById("opt-resolution").value : "best",
            extract_audio: chkAudioOnly ? chkAudioOnly.checked : false,
            audio_format: optAudioFormat ? optAudioFormat.value : "mp3",
            write_subs: chkWriteSubs ? chkWriteSubs.checked : true,
            embed_subs: document.getElementById("chk-embed-subs") ? document.getElementById("chk-embed-subs").checked : true,
            embed_metadata: document.getElementById("chk-embed-metadata") ? document.getElementById("chk-embed-metadata").checked : true,
            embed_thumbnail: document.getElementById("chk-embed-thumb") ? document.getElementById("chk-embed-thumb").checked : true,
            use_whisper: chkUseWhisper ? chkUseWhisper.checked : false,
            whisper_lang: optWhisperLang ? optWhisperLang.value : "auto",
            sponsorblock: document.getElementById("chk-sponsorblock") ? document.getElementById("chk-sponsorblock").checked : true,
            time_section: document.getElementById("opt-time-section") ? document.getElementById("opt-time-section").value.trim() || null : null,
            cookie_type: optCookieType && optCookieType.value !== "none" ? optCookieType.value : null,
            cookie_val: optCookieType && optCookieType.value !== "none" ? optCookieVal.value : null
        };

        try {
            const res = await fetch("/api/download", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            const data = await res.json();

            if (data.success && data.task) {
                showToast("ส่งคิวดาวน์โหลดเรียบร้อย!", "success");
                tasksMap.set(data.task.task_id, data.task);
                renderTasksList();

                urlInput.value = "";
                previewCard.classList.add("hidden");
                duplicateAlertBox.classList.add("hidden");

                // Switch to Queue tab so user immediately sees live progress!
                document.querySelector('.nav-btn[data-tab="tab-queue"]').click();
            } else {
                showToast("ส่งคิวล้มเหลว", "error");
            }
        } catch (e) {
            showToast(`เกิดข้อผิดพลาด: ${e.message}`, "error");
        } finally {
            btnStartDownload.disabled = false;
            btnStartDownload.innerText = "🚀 เริ่มดาวน์โหลดทันที";
        }
    });

    // 7. WebSocket & Task List Progress Handling
    function handleWebSocketTasksInit(tasks) {
        if (tasks && tasks.length > 0) {
            tasks.forEach(t => tasksMap.set(t.task_id, t));
            renderTasksList();
        }
    }

    function handleWebSocketProgressUpdate(task) {
        if (task && task.task_id) {
            tasksMap.set(task.task_id, task);
            renderTasksList();
        }
    }

    function renderTasksList() {
        const tasks = Array.from(tasksMap.values());
        queueCountBadge.innerText = tasks.filter(t => t.status === "downloading" || t.status === "queued" || t.status === "fetching_info" || t.status === "transcribing_whisper" || t.status === "processing").length;

        if (tasks.length === 0) {
            tasksContainer.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">📥</div>
                    <p>ยังไม่มีรายการดาวน์โหลดขณะนี้</p>
                </div>`;
            return;
        }

        tasksContainer.innerHTML = "";
        // Sort newest first
        tasks.slice().reverse().forEach(t => {
            const div = document.createElement("div");
            div.className = "task-item";
            
            let statusClass = `status-${t.status}`;
            let statusText = t.status.toUpperCase();
            if (t.status === "transcribing_whisper") statusText = "🤖 AI WHISPER TRANSCRIBING";
            if (t.status === "completed") statusText = "✅ สำเร็จ (COMPLETED)";
            if (t.status === "error") statusText = "❌ ผิดพลาด (FAILED)";

            div.innerHTML = `
                <div class="task-header">
                    <div style="display: flex; align-items: center; gap: 12px; flex: 1;">
                        <div class="task-title" style="flex: 1;">${t.title || t.filename || t.url}</div>
                        ${t.filepath ? `<button class="btn btn-sm btn-secondary btn-open-card-folder" data-path="${encodeURIComponent(t.filepath)}">📂 เปิดโฟลเดอร์คลิปนี้</button>` : ''}
                    </div>
                    <span class="task-status-tag ${statusClass}">${statusText}</span>
                </div>
                <div class="task-stage-text">${t.stage || 'กำลังดำเนินการ...'}</div>
                <div class="progress-bar-track">
                    <div class="progress-bar-fill" style="width: ${t.percent}%;"></div>
                </div>
                <div class="task-meta">
                    <span>${t.percent}% | สปีด: ${t.speed}</span>
                    <span>ETA: ${t.eta}</span>
                </div>
                ${t.caption_studio && t.caption_studio.hashtags_text ? `
                    <div style="margin-top: 12px; padding-top: 10px; border-top: 1px dashed rgba(255,255,255,0.15); display: flex; flex-wrap: wrap; gap: 8px; align-items: center;">
                        <span style="font-size: 12px; color: #a5b4fc; font-weight: 600;">🏷️ สำหรับนำไปตัดต่อ:</span>
                        <button class="btn btn-sm btn-secondary btn-copy-task-tags" data-tags="${encodeURIComponent(t.caption_studio.hashtags_text)}">📋 คัดลอกแฮชแท็ก</button>
                        <button class="btn btn-sm btn-secondary btn-copy-task-cap" data-cap="${encodeURIComponent(t.caption_studio.caption_short)}">📋 คัดลอกแคปชัน</button>
                    </div>
                ` : ''}
                ${t.error_msg ? `<div style="background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.3); padding: 10px; border-radius: 8px; color: #fca5a5; font-size: 12px; margin-top: 10px;"><strong>รายละเอียดข้อผิดพลาด:</strong> ${t.error_msg}</div>` : ''}
            `;
            tasksContainer.appendChild(div);
        });

        // Add task copy and open folder handlers
        document.querySelectorAll(".btn-open-card-folder").forEach(btn => {
            btn.addEventListener("click", () => {
                const path = decodeURIComponent(btn.getAttribute("data-path"));
                fetch("/api/open-folder", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ path: path })
                });
            });
        });
        document.querySelectorAll(".btn-copy-task-tags").forEach(btn => {
            btn.addEventListener("click", () => {
                navigator.clipboard.writeText(decodeURIComponent(btn.getAttribute("data-tags")));
                showToast("คัดลอกแฮชแท็กเรียบร้อย!", "success");
            });
        });
        document.querySelectorAll(".btn-copy-task-cap").forEach(btn => {
            btn.addEventListener("click", () => {
                navigator.clipboard.writeText(decodeURIComponent(btn.getAttribute("data-cap")));
                showToast("คัดลอกแคปชันเรียบร้อย!", "success");
            });
        });
    }

    // Clear completed tasks handler
    const btnClearCompleted = document.getElementById("btn-clear-completed");
    if (btnClearCompleted) {
        btnClearCompleted.addEventListener("click", async () => {
            try {
                btnClearCompleted.disabled = true;
                btnClearCompleted.innerText = "?????????...";
                const res = await fetch("/api/tasks/clear-completed", { method: "POST" });
                const data = await res.json();
                if (data.success) {
                    tasksMap.clear();
                    (data.tasks || []).forEach(t => tasksMap.set(t.task_id, t));
                    renderTasksList();
                    showToast(`?????????????????????? ${data.removed_count || 0} ??????`, "success");
                } else {
                    showToast("???????????????????", "error");
                }
            } catch (e) {
                showToast(`??????????????: ${e.message}`, "error");
            } finally {
                btnClearCompleted.disabled = false;
                btnClearCompleted.innerText = "??????????????????????";
            }
        });
    }

    // Initialize WebSocket Connection
    window.downloadWebSocket = new DownloadWebSocket(handleWebSocketProgressUpdate, handleWebSocketTasksInit);

    // 8. File Manager
    async function loadFiles() {
        try {
            const res = await fetch("/api/files");
            const data = await res.json();
            renderFilesTable(data.files);
        } catch (e) {
            console.error("Failed to load files:", e);
        }
    }

    function renderFilesTable(files) {
        if (!files || files.length === 0) {
            filesTbody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: var(--text-muted); padding: 32px;">ยังไม่มีไฟล์ที่ดาวน์โหลด</td></tr>`;
            return;
        }

        filesTbody.innerHTML = "";
        files.forEach(f => {
            const tr = document.createElement("tr");

            const tdName = document.createElement("td");
            tdName.innerHTML = `<strong>${escapeHtml(f.name)}</strong><br><small style="color: var(--text-muted);">${escapeHtml(f.relative_path)}</small>`;

            const tdType = document.createElement("td");
            tdType.innerHTML = `<span class="p-tag">${f.type.toUpperCase()}</span>`;

            const tdSize = document.createElement("td");
            tdSize.innerText = `${f.size_mb} MB`;

            const tdActions = document.createElement("td");
            tdActions.style.display = "flex";
            tdActions.style.gap = "6px";

            const btnPlay = document.createElement("button");
            btnPlay.className = "btn btn-sm btn-secondary";
            btnPlay.innerText = "▶ เล่น/พรีวิว";
            btnPlay.addEventListener("click", () => playMedia(f.relative_path, f.type));

            const btnFolder = document.createElement("button");
            btnFolder.className = "btn btn-sm btn-secondary";
            btnFolder.innerText = "📂 เปิดโฟลเดอร์คลิปนี้";
            btnFolder.addEventListener("click", () => {
                fetch("/api/open-folder", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ path: f.absolute_path })
                });
            });

            const btnDel = document.createElement("button");
            btnDel.className = "btn btn-sm btn-secondary";
            btnDel.innerText = "🗑️ ลบ";
            btnDel.addEventListener("click", async () => {
                if (confirm(`คุณแน่ใจหรือไม่ว่าต้องการลบไฟล์ '${f.name}'?`)) {
                    await fetch(`/api/files?path=${encodeURIComponent(f.relative_path)}`, { method: "DELETE" });
                    loadFiles();
                }
            });

            tdActions.appendChild(btnPlay);
            tdActions.appendChild(btnFolder);
            tdActions.appendChild(btnDel);

            tr.appendChild(tdName);
            tr.appendChild(tdType);
            tr.appendChild(tdSize);
            tr.appendChild(tdActions);

            filesTbody.appendChild(tr);
        });
    }

    function escapeHtml(str) {
        if (!str) return '';
        return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
    }

    function playMedia(relPath, type) {
        // Encode each path segment to handle '#' and special unicode characters in filenames
        const encodedSegments = relPath.split('/').map(seg => encodeURIComponent(seg));
        const mediaUrl = `/downloads-media/${encodedSegments.join('/')}`;
        const playerBox = document.getElementById("player-box");
        const playerContainer = document.getElementById("player-container");
        document.getElementById("player-title").innerText = relPath;

        if (type === "video") {
            playerContainer.innerHTML = `<video controls autoplay src="${mediaUrl}"></video>`;
        } else if (type === "audio") {
            playerContainer.innerHTML = `<audio controls autoplay src="${mediaUrl}"></audio>`;
        } else {
            playerContainer.innerHTML = `<p style="color: var(--text-muted);">ไม่สามารถเล่นไฟล์ประเภทนี้ในเบราว์เซอร์ได้</p>`;
        }
        playerBox.classList.remove("hidden");
        playerBox.scrollIntoView({ behavior: 'smooth' });
    }

    document.getElementById("btn-close-player").addEventListener("click", () => {
        document.getElementById("player-box").classList.add("hidden");
        document.getElementById("player-container").innerHTML = "";
    });

    btnRefreshFiles.addEventListener("click", loadFiles);

    // 9. Open Windows Explorer
    btnOpenExplorer.addEventListener("click", async () => {
        await fetch("/api/open-folder", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({})
        });
    });


    // Helper: Toast Notifications
    function showToast(msg, type = "info") {
        const container = document.getElementById("toast-container");
        const toast = document.createElement("div");
        toast.className = `toast toast-${type}`;
        toast.innerText = msg;
        container.appendChild(toast);
        setTimeout(() => toast.remove(), 4000);
    }

    // Initializations
    loadPresets();
    loadSystemStatus();
    loadTasks();
});
