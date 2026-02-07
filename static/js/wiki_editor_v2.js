(function () {
    "use strict";

    const cfg = window.wikiEditorV2Config || {};
    const form = document.getElementById("articleForm");
    if (!form) {
        return;
    }

    const categorySelect = document.getElementById("categorySelect");
    const subcategorySelect = document.getElementById("subcategorySelect");
    const titleInput = document.getElementById("titleInput");
    const iconInput = document.getElementById("iconInput");
    const tagsInput = document.getElementById("tagsInput");
    const statusSelect = document.getElementById("statusSelect");
    const changeDescriptionInput = document.getElementById("changeDescriptionInput");
    const toastEditorHost = document.getElementById("toastEditor");
    const fallbackEditor = document.getElementById("contentFallback");
    const contentInput = document.getElementById("contentInput");
    const autosaveStatus = document.getElementById("autosaveStatus");
    const uploadZone = document.getElementById("uploadZone");
    const fileInput = document.getElementById("fileInput");
    const uploadedImages = document.getElementById("uploadedImages");
    const emojiPicker = document.getElementById("emojiPicker");
    const emojiPickerToggle = document.getElementById("emojiPickerToggle");
    const editorLayout = document.getElementById("editorLayout");
    const editorViewButtons = Array.from(document.querySelectorAll("[data-editor-view]"));

    const cropModalEl = document.getElementById("imageCropModal");
    const cropperImage = document.getElementById("cropperImage");
    const cropperApplyBtn = document.getElementById("cropperApplyBtn");
    const cropperRotateLeft = document.getElementById("cropperRotateLeft");
    const cropperRotateRight = document.getElementById("cropperRotateRight");
    const cropperResetBtn = document.getElementById("cropperReset");
    const cropAspectButtons = Array.from(document.querySelectorAll("[data-crop-aspect]"));

    const subcategories = Array.isArray(cfg.subcategories) ? cfg.subcategories : [];
    const draftKey = cfg.draftKey || "wiki-editor-v2:new";

    let editor = null;
    let useToastEditor = false;
    let isSubmitting = false;
    let autosaveTimer = null;
    let initialSnapshot = "";

    let currentEditorView = "split";

    let cropModal = null;
    let cropper = null;
    let cropPendingResolve = null;
    let cropPendingFile = null;

    function isDarkTheme() {
        return (
            document.body.classList.contains("dark") ||
            document.documentElement.classList.contains("dark")
        );
    }

    function getCsrfToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        const hidden = form.querySelector('input[name="csrf_token"]');
        return (meta && meta.getAttribute("content")) || (hidden && hidden.value) || "";
    }

    function setAutosaveStatus(message, level) {
        if (!autosaveStatus) {
            return;
        }
        autosaveStatus.classList.remove("ok", "warn", "error");
        if (level) {
            autosaveStatus.classList.add(level);
        }
        autosaveStatus.textContent = message;
    }

    function getEditorContent() {
        if (useToastEditor && editor) {
            return editor.getMarkdown();
        }
        return fallbackEditor.value || "";
    }

    function setEditorContent(value) {
        const safeValue = value || "";
        if (useToastEditor && editor) {
            editor.setMarkdown(safeValue, false);
        }
        fallbackEditor.value = safeValue;
        contentInput.value = safeValue;
    }

    function syncContentField() {
        if (useToastEditor && editor) {
            contentInput.name = "content";
            contentInput.value = editor.getMarkdown();
            fallbackEditor.name = "";
            return;
        }
        fallbackEditor.name = "content";
        contentInput.name = "";
        contentInput.value = fallbackEditor.value || "";
    }

    function buildSnapshot() {
        syncContentField();
        return JSON.stringify({
            title: titleInput ? titleInput.value : "",
            icon: iconInput ? iconInput.value : "",
            tags: tagsInput ? tagsInput.value : "",
            status: statusSelect ? statusSelect.value : "",
            category: categorySelect ? categorySelect.value : "",
            subcategory: subcategorySelect ? subcategorySelect.value : "",
            changeDescription: changeDescriptionInput ? changeDescriptionInput.value : "",
            content: getEditorContent(),
        });
    }

    function scheduleAutosave() {
        if (autosaveTimer) {
            clearTimeout(autosaveTimer);
        }
        autosaveTimer = setTimeout(saveDraft, 1200);
    }

    function saveDraft() {
        try {
            const payload = {
                title: titleInput ? titleInput.value : "",
                icon: iconInput ? iconInput.value : "",
                tags: tagsInput ? tagsInput.value : "",
                status: statusSelect ? statusSelect.value : "",
                categoryId: categorySelect ? categorySelect.value : "",
                subcategoryId: subcategorySelect ? subcategorySelect.value : "",
                changeDescription: changeDescriptionInput ? changeDescriptionInput.value : "",
                content: getEditorContent(),
                savedAt: new Date().toISOString(),
            };

            const hasMeaningfulData =
                (payload.title && payload.title.trim().length > 0) ||
                (payload.content && payload.content.trim().length > 0);

            if (!hasMeaningfulData) {
                localStorage.removeItem(draftKey);
                setAutosaveStatus("Aucun brouillon local", "warn");
                return;
            }

            localStorage.setItem(draftKey, JSON.stringify(payload));
            setAutosaveStatus("Brouillon local sauvegardé", "ok");
        } catch (error) {
            console.error("Erreur autosave:", error);
            setAutosaveStatus("Erreur autosave local", "error");
        }
    }

    function getDraft() {
        const raw = localStorage.getItem(draftKey);
        if (!raw) {
            return null;
        }
        try {
            return JSON.parse(raw);
        } catch (error) {
            console.error("Draft JSON invalide:", error);
            localStorage.removeItem(draftKey);
            return null;
        }
    }

    function setCategoryAndSubcategory(categoryId, subcategoryId) {
        const normalizedCategory = categoryId != null ? String(categoryId) : "";
        const normalizedSubcategory = subcategoryId != null ? String(subcategoryId) : "";

        if (categorySelect) {
            categorySelect.value = normalizedCategory;
        }
        updateSubcategories(normalizedSubcategory);
    }

    function applyDraft(draft) {
        if (!draft) {
            return;
        }

        if (titleInput) {
            titleInput.value = draft.title || "";
        }
        if (iconInput) {
            iconInput.value = draft.icon || iconInput.value;
        }
        if (tagsInput) {
            tagsInput.value = draft.tags || "";
        }
        if (statusSelect && draft.status) {
            statusSelect.value = draft.status;
        }
        if (changeDescriptionInput) {
            changeDescriptionInput.value = draft.changeDescription || "";
        }

        if (draft.categoryId) {
            setCategoryAndSubcategory(draft.categoryId, draft.subcategoryId);
        } else if (draft.subcategoryId) {
            const relatedSubcat = subcategories.find(
                (subcat) => String(subcat.id) === String(draft.subcategoryId)
            );
            if (relatedSubcat) {
                setCategoryAndSubcategory(relatedSubcat.category_id, draft.subcategoryId);
            }
        }

        if (typeof draft.content === "string") {
            setEditorContent(draft.content);
            syncContentField();
        }

        setAutosaveStatus("Brouillon restauré depuis le local", "ok");
    }

    function maybeRestoreDraft() {
        const draft = getDraft();
        if (!draft) {
            return;
        }

        const savedAt = draft.savedAt ? ` (${draft.savedAt.replace("T", " ").slice(0, 19)})` : "";
        const shouldRestore = window.confirm(
            `Un brouillon local est disponible${savedAt}. Voulez-vous le restaurer ?`
        );
        if (shouldRestore) {
            applyDraft(draft);
        } else {
            setAutosaveStatus("Brouillon local conservé", "warn");
        }
    }

    function updateSubcategories(selectedSubcategoryId) {
        if (!subcategorySelect || !categorySelect) {
            return;
        }

        const categoryId = categorySelect.value ? String(categorySelect.value) : "";
        subcategorySelect.innerHTML = '<option value="">Sélectionnez une sous-catégorie</option>';

        const filtered = subcategories.filter(
            (subcat) => String(subcat.category_id) === categoryId
        );

        filtered.forEach((subcat) => {
            const option = document.createElement("option");
            option.value = subcat.id;
            option.textContent = `${subcat.icon || ""} ${subcat.name}`.trim();
            subcategorySelect.appendChild(option);
        });

        if (selectedSubcategoryId) {
            subcategorySelect.value = String(selectedSubcategoryId);
        }
    }

    function prefillCategoryFromArticle() {
        if (!cfg.articleSubcategoryId || !categorySelect) {
            return;
        }
        const current = subcategories.find(
            (subcat) => String(subcat.id) === String(cfg.articleSubcategoryId)
        );
        if (!current) {
            return;
        }

        categorySelect.value = String(current.category_id);
        updateSubcategories(cfg.articleSubcategoryId);
    }

    function initCategorySelectors() {
        if (!categorySelect) {
            return;
        }

        categorySelect.addEventListener("change", function () {
            updateSubcategories("");
            scheduleAutosave();
        });

        if (subcategorySelect) {
            subcategorySelect.addEventListener("change", scheduleAutosave);
        }
        prefillCategoryFromArticle();
        if (!cfg.articleSubcategoryId) {
            updateSubcategories("");
        }
    }

    function initEmojiPicker() {
        if (!emojiPicker || !emojiPickerToggle || !iconInput) {
            return;
        }

        const emojis = [
            "📝", "📚", "📌", "✅", "⚠️", "💡", "🛠️", "🔧",
            "🖥️", "🌐", "🔐", "📡", "📱", "🗂️", "📊", "🚀",
            "🧩", "🧪", "📷", "📎", "📦", "☎️", "🧭", "📍",
            "🧠", "🧰", "🔎", "🎯", "📈", "🔄", "👤", "🏷️"
        ];

        emojis.forEach((emoji) => {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "emoji-btn";
            button.textContent = emoji;
            button.addEventListener("click", function () {
                iconInput.value = emoji;
                emojiPicker.classList.remove("show");
                scheduleAutosave();
            });
            emojiPicker.appendChild(button);
        });

        emojiPickerToggle.addEventListener("click", function (event) {
            event.preventDefault();
            emojiPicker.classList.toggle("show");
        });

        document.addEventListener("click", function (event) {
            const clickedInPicker = event.target.closest("#emojiPicker");
            const clickedToggle = event.target.closest("#emojiPickerToggle");
            if (!clickedInPicker && !clickedToggle) {
                emojiPicker.classList.remove("show");
            }
        });
    }

    function setEditorView(view) {
        if (!editorLayout) {
            return;
        }

        const targetView = ["split", "edit", "preview"].includes(view) ? view : "split";
        currentEditorView = targetView;

        if (useToastEditor && editor && (targetView === "split" || targetView === "preview")) {
            try {
                editor.changeMode("markdown", true);
            } catch (error) {
                console.warn("Impossible de passer en mode markdown:", error);
            }
        }

        editorLayout.classList.remove("view-split", "view-edit", "view-preview");
        editorLayout.classList.add(`view-${targetView}`);

        editorViewButtons.forEach((button) => {
            const isActive = button.dataset.editorView === targetView;
            button.classList.toggle("active", isActive);
            button.classList.toggle("btn-secondary", isActive);
            button.classList.toggle("btn-outline-secondary", !isActive);
        });

        applyEditorSurfaceOverrides();

        if (useToastEditor && editor && targetView !== "preview") {
            window.setTimeout(function () {
                editor.focus();
            }, 0);
        }
    }

    function initViewControls() {
        if (!editorViewButtons.length) {
            return;
        }

        editorViewButtons.forEach((button) => {
            button.addEventListener("click", function () {
                setEditorView(button.dataset.editorView || "split");
            });
        });

        if (!useToastEditor) {
            editorViewButtons.forEach((button) => {
                if (button.dataset.editorView !== "edit") {
                    button.disabled = true;
                }
            });
            setEditorView("edit");
            return;
        }

        setEditorView(currentEditorView);
    }

    function parseAspectRatio(value) {
        if (!value || value === "free") {
            return NaN;
        }
        const [w, h] = String(value).split(":").map(Number);
        if (!w || !h) {
            return NaN;
        }
        return w / h;
    }

    function markActiveAspect(value) {
        cropAspectButtons.forEach((btn) => {
            const isActive = btn.getAttribute("data-crop-aspect") === value;
            btn.classList.toggle("btn-primary", isActive);
            btn.classList.toggle("btn-outline-secondary", !isActive);
        });
    }

    function destroyCropper() {
        if (cropper && typeof cropper.destroy === "function") {
            cropper.destroy();
        }
        cropper = null;
    }

    function ensureFileInstance(blobOrFile, fallbackName) {
        if (blobOrFile instanceof File) {
            return blobOrFile;
        }
        const safeType = blobOrFile.type || "image/png";
        const extension = safeType.split("/")[1] || "png";
        const filename = fallbackName || `image-${Date.now()}.${extension}`;
        return new File([blobOrFile], filename, { type: safeType, lastModified: Date.now() });
    }

    function readFileAsDataURL(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = function () {
                resolve(reader.result);
            };
            reader.onerror = function () {
                reject(new Error("Impossible de lire l'image pour recadrage"));
            };
            reader.readAsDataURL(file);
        });
    }

    function createCropperInstance() {
        if (!cropperImage || !(window.Cropper && typeof window.Cropper === "function")) {
            return;
        }
        destroyCropper();
        cropper = new window.Cropper(cropperImage, {
            viewMode: 1,
            dragMode: "move",
            autoCropArea: 0.92,
            background: false,
            responsive: true,
            zoomable: true,
            movable: true,
            rotatable: true,
            scalable: true,
            guides: true,
        });
        markActiveAspect("free");
    }

    function resolvePendingCrop(result) {
        if (!cropPendingResolve) {
            return;
        }
        const resolver = cropPendingResolve;
        cropPendingResolve = null;
        cropPendingFile = null;
        resolver(result);
    }

    function initCropperModal() {
        if (!cropModalEl || !window.bootstrap || !(window.Cropper && typeof window.Cropper === "function")) {
            return;
        }

        cropModal = new window.bootstrap.Modal(cropModalEl, {
            backdrop: "static",
            keyboard: true,
        });

        cropModalEl.addEventListener("hidden.bs.modal", function () {
            destroyCropper();
            if (cropPendingResolve) {
                resolvePendingCrop(null);
            }
        });

        cropAspectButtons.forEach((button) => {
            button.addEventListener("click", function () {
                if (!cropper) {
                    return;
                }
                const token = button.getAttribute("data-crop-aspect");
                cropper.setAspectRatio(parseAspectRatio(token));
                markActiveAspect(token);
            });
        });

        if (cropperRotateLeft) {
            cropperRotateLeft.addEventListener("click", function () {
                if (cropper) {
                    cropper.rotate(-90);
                }
            });
        }

        if (cropperRotateRight) {
            cropperRotateRight.addEventListener("click", function () {
                if (cropper) {
                    cropper.rotate(90);
                }
            });
        }

        if (cropperResetBtn) {
            cropperResetBtn.addEventListener("click", function () {
                if (cropper) {
                    cropper.reset();
                    cropper.setAspectRatio(NaN);
                    markActiveAspect("free");
                }
            });
        }

        if (cropperApplyBtn) {
            cropperApplyBtn.addEventListener("click", function () {
                if (!cropper || !cropPendingFile) {
                    resolvePendingCrop(null);
                    if (cropModal) {
                        cropModal.hide();
                    }
                    return;
                }

                const originalType = cropPendingFile.type || "image/png";
                const canvas = cropper.getCroppedCanvas({
                    maxWidth: 2600,
                    maxHeight: 2600,
                    imageSmoothingEnabled: true,
                    imageSmoothingQuality: "high",
                    fillColor: "#ffffff",
                });

                if (!canvas) {
                    resolvePendingCrop(cropPendingFile);
                    if (cropModal) {
                        cropModal.hide();
                    }
                    return;
                }

                canvas.toBlob(
                    function (blob) {
                        if (!blob) {
                            resolvePendingCrop(cropPendingFile);
                            if (cropModal) {
                                cropModal.hide();
                            }
                            return;
                        }

                        const croppedFile = ensureFileInstance(blob, cropPendingFile.name);
                        resolvePendingCrop(croppedFile);
                        if (cropModal) {
                            cropModal.hide();
                        }
                    },
                    originalType,
                    0.92
                );
            });
        }
    }

    async function maybeCropImage(fileOrBlob, fallbackName) {
        const file = ensureFileInstance(fileOrBlob, fallbackName);
        if (!cropModal || !cropperImage || !(window.Cropper && typeof window.Cropper === "function")) {
            return file;
        }

        const dataUrl = await readFileAsDataURL(file);
        return new Promise((resolve) => {
            cropPendingResolve = resolve;
            cropPendingFile = file;

            cropperImage.onload = function () {
                createCropperInstance();
            };
            cropperImage.src = dataUrl;
            cropModal.show();
        });
    }

    function escapeHtmlAttribute(value) {
        return String(value || "")
            .replace(/&/g, "&amp;")
            .replace(/\"/g, "&quot;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");
    }

    function widthBySize(size) {
        if (size === "small") {
            return "35%";
        }
        if (size === "large") {
            return "90%";
        }
        return "60%";
    }

    function buildImageSnippet(url, alt, align, size) {
        const safeUrl = escapeHtmlAttribute(url);
        const safeAlt = escapeHtmlAttribute(alt || "Image");
        const width = widthBySize(size);

        if (align === "left") {
            return (
                `\n<img src="${safeUrl}" alt="${safeAlt}" ` +
                `style="float:left;display:block;max-width:${width};width:100%;height:auto;margin:0.4rem 1rem 0.8rem 0;" />\n` +
                `<div style="clear:both;"></div>\n`
            );
        }

        if (align === "right") {
            return (
                `\n<img src="${safeUrl}" alt="${safeAlt}" ` +
                `style="float:right;display:block;max-width:${width};width:100%;height:auto;margin:0.4rem 0 0.8rem 1rem;" />\n` +
                `<div style="clear:both;"></div>\n`
            );
        }

        return (
            `\n<img src="${safeUrl}" alt="${safeAlt}" ` +
            `style="display:block;max-width:${width};width:100%;height:auto;margin:0.8rem auto;" />\n`
        );
    }

    function insertSnippetAtCursor(snippet) {
        if (useToastEditor && editor) {
            editor.insertText(snippet);
            editor.focus();
            scheduleAutosave();
            return;
        }

        const start = fallbackEditor.selectionStart || 0;
        const end = fallbackEditor.selectionEnd || 0;
        const current = fallbackEditor.value || "";
        fallbackEditor.value = current.slice(0, start) + snippet + current.slice(end);
        fallbackEditor.focus();
        fallbackEditor.setSelectionRange(start + snippet.length, start + snippet.length);
        scheduleAutosave();
    }

    function insertImageSnippet(url, options) {
        const snippet = buildImageSnippet(
            url,
            options && options.alt ? options.alt : "Image",
            options && options.align ? options.align : "center",
            options && options.size ? options.size : "medium"
        );
        insertSnippetAtCursor(snippet);
    }

    async function uploadImage(fileOrBlob) {
        const csrfToken = getCsrfToken();
        if (!csrfToken) {
            throw new Error("Token CSRF manquant");
        }

        const formData = new FormData();
        formData.append("file", fileOrBlob);
        formData.append("csrf_token", csrfToken);

        const response = await fetch(cfg.uploadUrl, {
            method: "POST",
            headers: {
                "X-CSRFToken": csrfToken,
                "X-Requested-With": "XMLHttpRequest",
            },
            body: formData,
        });

        const contentType = response.headers.get("content-type") || "";
        if (!contentType.includes("application/json")) {
            const bodyText = await response.text();
            throw new Error(`Réponse serveur invalide: ${bodyText.slice(0, 140)}`);
        }

        const payload = await response.json();
        if (!response.ok || !(payload.success || payload.status === "ok")) {
            throw new Error(payload.error || "Upload image refusé");
        }

        return payload;
    }

    function appendUploadResultCard(payload) {
        if (!uploadedImages) {
            return;
        }

        const wrapper = document.createElement("div");
        wrapper.className = "upload-result";

        const header = document.createElement("div");
        header.className = "upload-result-header";

        const preview = document.createElement("img");
        preview.className = "upload-preview-thumb";
        preview.src = payload.url;
        preview.alt = payload.filename || "Image";

        const details = document.createElement("div");
        details.className = "upload-meta";

        const title = document.createElement("strong");
        title.textContent = payload.filename || "Image uploadée";
        details.appendChild(title);

        const urlText = document.createElement("small");
        urlText.textContent = payload.url;
        details.appendChild(urlText);

        header.appendChild(preview);
        header.appendChild(details);

        const controls = document.createElement("div");
        controls.className = "upload-controls";

        const altInput = document.createElement("input");
        altInput.type = "text";
        altInput.className = "form-control form-control-sm";
        altInput.placeholder = "Texte alternatif (optionnel)";
        altInput.value = payload.filename || "Image";

        const sizeSelect = document.createElement("select");
        sizeSelect.className = "form-select form-select-sm";
        sizeSelect.innerHTML = [
            '<option value="small">Petit</option>',
            '<option value="medium" selected>Moyen</option>',
            '<option value="large">Grand</option>',
        ].join("");

        const actions = document.createElement("div");
        actions.className = "btn-group btn-group-sm";
        actions.setAttribute("role", "group");
        actions.setAttribute("aria-label", "Position image");

        [
            { label: "Gauche", align: "left" },
            { label: "Centre", align: "center" },
            { label: "Droite", align: "right" },
        ].forEach((action) => {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "btn btn-outline-primary";
            button.textContent = action.label;
            button.addEventListener("click", function () {
                insertImageSnippet(payload.url, {
                    align: action.align,
                    size: sizeSelect.value,
                    alt: altInput.value || payload.filename || "Image",
                });
            });
            actions.appendChild(button);
        });

        const copyUrlBtn = document.createElement("button");
        copyUrlBtn.type = "button";
        copyUrlBtn.className = "btn btn-outline-secondary btn-sm";
        copyUrlBtn.textContent = "Copier URL";
        copyUrlBtn.addEventListener("click", async function () {
            try {
                await navigator.clipboard.writeText(payload.url);
                copyUrlBtn.textContent = "URL copiée";
                window.setTimeout(function () {
                    copyUrlBtn.textContent = "Copier URL";
                }, 1200);
            } catch (error) {
                console.warn("Copie URL impossible:", error);
            }
        });

        controls.appendChild(altInput);
        controls.appendChild(sizeSelect);
        controls.appendChild(actions);
        controls.appendChild(copyUrlBtn);

        wrapper.appendChild(header);
        wrapper.appendChild(controls);
        uploadedImages.prepend(wrapper);
    }

    async function processUpload(fileOrBlob, options) {
        const safeName = (options && options.fallbackName) || `image-${Date.now()}.png`;
        const croppedFile = await maybeCropImage(fileOrBlob, safeName);
        if (!croppedFile) {
            setAutosaveStatus("Insertion d'image annulée", "warn");
            return null;
        }

        const payload = await uploadImage(croppedFile);
        appendUploadResultCard(payload);

        if (options && options.autoInsert) {
            insertImageSnippet(payload.url, {
                align: "center",
                size: "medium",
                alt: payload.filename || "Image",
            });
        }

        return payload;
    }

    async function handleFileUploads(fileList) {
        const files = Array.from(fileList || []);
        for (const file of files) {
            if (!file.type || !file.type.startsWith("image/")) {
                continue;
            }
            try {
                await processUpload(file, {
                    fallbackName: file.name,
                    autoInsert: false,
                });
            } catch (error) {
                console.error("Upload image error:", error);
                window.alert(`Erreur d'upload image: ${error.message}`);
            }
        }
    }

    function initUploadZone() {
        if (!uploadZone || !fileInput) {
            return;
        }

        uploadZone.addEventListener("click", function () {
            fileInput.click();
        });

        uploadZone.addEventListener("dragover", function (event) {
            event.preventDefault();
            uploadZone.classList.add("dragover");
        });

        uploadZone.addEventListener("dragleave", function () {
            uploadZone.classList.remove("dragover");
        });

        uploadZone.addEventListener("drop", function (event) {
            event.preventDefault();
            uploadZone.classList.remove("dragover");
            handleFileUploads(event.dataTransfer.files);
        });

        fileInput.addEventListener("change", function (event) {
            handleFileUploads(event.target.files);
            fileInput.value = "";
        });
    }

    function applyEditorSurfaceOverrides() {
        const caretColor = isDarkTheme() ? "#f9fafb" : "#111827";
        const textColor = isDarkTheme() ? "#f3f4f6" : "#111827";

        if (fallbackEditor) {
            fallbackEditor.style.setProperty("caret-color", caretColor, "important");
            fallbackEditor.style.setProperty("color", textColor, "important");
            fallbackEditor.style.setProperty("cursor", "text", "important");
        }

        if (!toastEditorHost) {
            return;
        }

        const editableSelectors = [
            ".toastui-editor-md-container textarea",
            ".toastui-editor-md-container .toastui-editor-md-textarea",
            ".toastui-editor-md-container [contenteditable='true']",
            ".toastui-editor-md-container [contenteditable='true'] *",
            ".toastui-editor-ww-container [contenteditable='true']",
            ".toastui-editor-ww-container [contenteditable='true'] *",
            ".toastui-editor-ww-container .ProseMirror",
            ".toastui-editor-ww-container .ProseMirror *",
        ];

        editableSelectors.forEach((selector) => {
            toastEditorHost.querySelectorAll(selector).forEach((el) => {
                el.style.setProperty("caret-color", caretColor, "important");
                el.style.setProperty("color", textColor, "important");
                el.style.setProperty("user-select", "text", "important");
                el.style.setProperty("-webkit-user-select", "text", "important");
                el.style.setProperty("-webkit-user-modify", "read-write", "important");
                el.style.setProperty("cursor", "text", "important");
            });
        });

        toastEditorHost
            .querySelectorAll(".toastui-editor-md-preview, .toastui-editor-md-preview *")
            .forEach((el) => {
                el.style.setProperty("color", textColor, "important");
            });
    }

    function enableToastEditor() {
        const hasToastLibrary =
            window.toastui &&
            window.toastui.Editor &&
            typeof window.toastui.Editor === "function";

        if (!hasToastLibrary) {
            useToastEditor = false;
            fallbackEditor.classList.remove("d-none");
            fallbackEditor.required = true;
            syncContentField();
            setAutosaveStatus("Mode secours actif (éditeur standard)", "warn");
            return;
        }

        try {
            editor = new window.toastui.Editor({
                el: toastEditorHost,
                height: "560px",
                initialEditType: "markdown",
                previewStyle: "vertical",
                usageStatistics: false,
                initialValue: fallbackEditor.value || "",
                hideModeSwitch: false,
                customHTMLSanitizer: function (html) {
                    if (window.DOMPurify) {
                        return window.DOMPurify.sanitize(html, {
                            USE_PROFILES: { html: true },
                        });
                    }
                    return html;
                },
                hooks: {
                    addImageBlobHook: function (blob, callback) {
                        processUpload(blob, {
                            fallbackName: `image-${Date.now()}.png`,
                            autoInsert: false,
                        })
                            .then((payload) => {
                                if (!payload) {
                                    return;
                                }
                                callback(payload.url, payload.filename || "Image");
                                scheduleAutosave();
                            })
                            .catch((error) => {
                                console.error("Editor image hook error:", error);
                                window.alert(`Erreur d'upload image: ${error.message}`);
                            });
                        return false;
                    },
                },
            });

            useToastEditor = true;
            toastEditorHost.classList.remove("d-none");
            fallbackEditor.classList.add("d-none");
            fallbackEditor.required = false;

            syncContentField();

            editor.on("change", function () {
                syncContentField();
                scheduleAutosave();
            });

            editor.on("focus", function () {
                applyEditorSurfaceOverrides();
            });

            applyEditorSurfaceOverrides();
            setAutosaveStatus("Éditeur moderne actif", "ok");
        } catch (error) {
            console.error("Toast UI init error:", error);
            useToastEditor = false;
            fallbackEditor.classList.remove("d-none");
            fallbackEditor.required = true;
            syncContentField();
            setAutosaveStatus("Mode secours actif (initialisation éditeur échouée)", "warn");
        }
    }

    function bindAutosaveOnInputs() {
        [titleInput, iconInput, tagsInput, statusSelect, changeDescriptionInput].forEach((element) => {
            if (!element) {
                return;
            }
            element.addEventListener("input", scheduleAutosave);
            element.addEventListener("change", scheduleAutosave);
        });

        fallbackEditor.addEventListener("input", function () {
            if (!useToastEditor) {
                scheduleAutosave();
            }
        });
    }

    function bindSubmitAndShortcuts() {
        form.addEventListener("submit", function () {
            isSubmitting = true;
            syncContentField();
            localStorage.removeItem(draftKey);
            setAutosaveStatus("Sauvegarde en cours...", "ok");
        });

        window.addEventListener("keydown", function (event) {
            const key = (event.key || "").toLowerCase();
            if ((event.ctrlKey || event.metaKey) && key === "s") {
                event.preventDefault();
                syncContentField();
                if (typeof form.requestSubmit === "function") {
                    form.requestSubmit();
                } else {
                    form.submit();
                }
            }
        });

        window.addEventListener("beforeunload", function (event) {
            if (isSubmitting) {
                return;
            }
            if (buildSnapshot() !== initialSnapshot) {
                event.preventDefault();
                event.returnValue = "";
            }
        });
    }

    function watchThemeChanges() {
        if (!window.MutationObserver) {
            return;
        }
        const observer = new MutationObserver(function () {
            applyEditorSurfaceOverrides();
        });
        observer.observe(document.body, {
            attributes: true,
            attributeFilter: ["class"],
        });
    }

    initCategorySelectors();
    initEmojiPicker();
    initCropperModal();
    initUploadZone();
    enableToastEditor();
    initViewControls();
    bindAutosaveOnInputs();
    bindSubmitAndShortcuts();
    watchThemeChanges();

    initialSnapshot = buildSnapshot();
    maybeRestoreDraft();
    syncContentField();
    applyEditorSurfaceOverrides();
})();
