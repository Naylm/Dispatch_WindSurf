(function () {
    "use strict";

    const cfg = window.wikiEditorV2Config || {};
    const form = document.getElementById("articleForm");
    if (!form) return;

    const categorySelect = document.getElementById("categorySelect");
    const subcategorySelect = document.getElementById("subcategorySelect");
    const titleInput = document.getElementById("titleInput");
    const iconInput = document.getElementById("iconInput");
    const tagsInput = document.getElementById("tagsInput");
    const statusSelect = document.getElementById("statusSelect");
    const changeDescriptionInput = document.getElementById("changeDescriptionInput");
    const contentInput = document.getElementById("contentInput");
    const autosaveStatus = document.getElementById("autosaveStatus");
    const emojiPicker = document.getElementById("emojiPicker");
    const emojiPickerToggle = document.getElementById("emojiPickerToggle");

    const subcategories = Array.isArray(cfg.subcategories) ? cfg.subcategories : [];
    const draftKey = cfg.draftKey || "wiki-editor-v2:new";

    let isSubmitting = false;
    let autosaveTimer = null;
    let initialSnapshot = "";
    let allEmojiData = null;

    function isDarkTheme() {
        return !document.documentElement.classList.contains("light-mode");
    }

    function getCsrfToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        const hidden = form.querySelector('input[name="csrf_token"]');
        return (meta && meta.getAttribute("content")) || (hidden && hidden.value) || "";
    }

    function setAutosaveStatus(message, level) {
        if (!autosaveStatus) return;
        autosaveStatus.className = 'status-indicator ms-auto small fw-medium';
        if (level) autosaveStatus.classList.add(level);
        autosaveStatus.textContent = message;
    }

    function getEditorContent() {
        if (window.tinymce && window.tinymce.get("tinymceEditor")) {
            return window.tinymce.get("tinymceEditor").getContent();
        }
        return contentInput ? contentInput.value || "" : "";
    }

    function syncContentField() {
        if (!contentInput) return;
        contentInput.name = "content";
        contentInput.value = getEditorContent();
    }

    function buildSnapshot() {
        return JSON.stringify({
            title: titleInput ? titleInput.value : "",
            icon: iconInput ? iconInput.value : "",
            categoryId: categorySelect ? categorySelect.value : "",
            subcategoryId: subcategorySelect ? subcategorySelect.value : "",
            tags: tagsInput ? tagsInput.value : "",
            status: statusSelect ? statusSelect.value : "",
            content: getEditorContent()
        });
    }

    function executeAutosave() {
        if (isSubmitting) return;
        try {
            const draft = {
                v: 2,
                title: titleInput ? titleInput.value : "",
                icon: iconInput ? iconInput.value : "",
                categoryId: categorySelect ? categorySelect.value : "",
                subcategoryId: subcategorySelect ? subcategorySelect.value : "",
                tags: tagsInput ? tagsInput.value : "",
                status: statusSelect ? statusSelect.value : "",
                content: getEditorContent(),
                savedAt: new Date().toISOString()
            };
            localStorage.setItem(draftKey, JSON.stringify(draft));
            setAutosaveStatus(`Brouillon local sauvé à ${new Date().toLocaleTimeString()}`, "ok");
        } catch (error) {
            console.error("Erreur de sauvegarde locale:", error);
            setAutosaveStatus("Sauvegarde locale échouée", "error");
        }
    }

    function scheduleAutosave() {
        if (autosaveTimer) clearTimeout(autosaveTimer);
        setAutosaveStatus("Sauvegarde en attente...", "warn");
        autosaveTimer = setTimeout(executeAutosave, 2500);
    }

    function getDraft() {
        try {
            const val = localStorage.getItem(draftKey);
            if (!val) return null;
            const draft = JSON.parse(val);
            if (!draft || draft.v !== 2) return null;
            return draft;
        } catch {
            return null;
        }
    }

    function applyDraft(draft) {
        if (titleInput && typeof draft.title === "string") titleInput.value = draft.title;
        if (iconInput && draft.icon) iconInput.value = draft.icon;
        if (tagsInput && typeof draft.tags === "string") tagsInput.value = draft.tags;
        if (statusSelect && draft.status) statusSelect.value = draft.status;
        if (draft.categoryId && categorySelect) {
            categorySelect.value = draft.categoryId;
            updateSubcategories(draft.subcategoryId);
        }
        if (typeof draft.content === "string") {
            if (window.tinymce && window.tinymce.get("tinymceEditor")) {
                window.tinymce.get("tinymceEditor").setContent(draft.content);
            }
            if (contentInput) contentInput.value = draft.content;
        }
        setAutosaveStatus("Brouillon restauré", "ok");
    }

    function updateSubcategories(selectedSubcategoryId) {
        if (!subcategorySelect || !categorySelect) return;
        const categoryId = String(categorySelect.value || "");
        subcategorySelect.innerHTML = '<option value="">Sélectionnez une sous-catégorie</option>';
        const filtered = subcategories.filter(s => String(s.category_id) === categoryId);
        filtered.forEach(s => {
            const option = document.createElement("option");
            option.value = s.id;
            option.textContent = `${s.icon || ""} ${s.name}`.trim();
            subcategorySelect.appendChild(option);
        });
        if (selectedSubcategoryId) subcategorySelect.value = String(selectedSubcategoryId);
    }

    function prefillCategoryFromArticle() {
        if (!cfg.articleSubcategoryId || !categorySelect) return;
        const current = subcategories.find(s => String(s.id) === String(cfg.articleSubcategoryId));
        if (!current) return;
        categorySelect.value = String(current.category_id);
        // Ensure subcategories are loaded before setting value
        updateSubcategories(cfg.articleSubcategoryId);
    }

    function initCategorySelectors() {
        if (!categorySelect) return;
        categorySelect.addEventListener("change", () => {
            updateSubcategories("");
            scheduleAutosave();
        });
        if (subcategorySelect) subcategorySelect.addEventListener("change", scheduleAutosave);
        prefillCategoryFromArticle();
        if (!cfg.articleSubcategoryId) updateSubcategories("");
    }

    async function initEmojiPicker() {
        const emojiPicker = document.getElementById("emojiPicker");
        const emojiGrid = document.getElementById("emojiGrid");
        const emojiSearch = document.getElementById("emojiSearch");
        const categoryBtns = document.querySelectorAll(".category-btn");

        if (!emojiPicker || !emojiPickerToggle || !iconInput || !emojiGrid) return;

        const categoryMap = {
            smileys: ["Smileys & Emotion"],
            gestures: ["People & Body"],
            nature: ["Animals & Nature"],
            it: ["Objects"],
            objects: ["Objects", "Food & Drink", "Travel & Places"],
            symbols: ["Symbols", "Activities", "Flags"]
        };

        let recentEmojis = JSON.parse(localStorage.getItem("wiki_recent_emojis") || "[]");

        async function fetchEmojiData() {
            if (allEmojiData) return allEmojiData;
            try {
                emojiGrid.innerHTML = '<div class="text-muted p-4 text-center w-100">Chargement...</div>';
                const resp = await fetch("https://unpkg.com/emoji.json/emoji.json");
                allEmojiData = await resp.json();
                return allEmojiData;
            } catch (e) {
                console.error("Emoji fetch error:", e);
                return [];
            }
        }

        async function renderEmojis(category, filter = "") {
            const data = await fetchEmojiData();
            if (!data || data.length === 0) {
                emojiGrid.innerHTML = '<div class="text-danger p-4 text-center w-100">Erreur de chargement des émojis.</div>';
                return;
            }

            emojiGrid.innerHTML = "";
            let list = [];

            if (filter) {
                const searchLower = filter.toLowerCase();
                list = data.filter(e =>
                    e.name.toLowerCase().includes(searchLower) ||
                    (e.codes && e.codes.toLowerCase().includes(searchLower)) ||
                    e.char.includes(filter)
                );
            } else if (category === "recent") {
                list = recentEmojis.map(char => data.find(e => e.char === char)).filter(Boolean);
                if (list.length === 0) {
                    emojiGrid.innerHTML = '<div class="text-muted small p-4 text-center w-100" style="grid-column: span 8;">Aucun émoji récent</div>';
                    return;
                }
            } else {
                const targetCategories = categoryMap[category] || [];
                list = data.filter(e => targetCategories.some(tc => e.category.startsWith(tc)));
            }

            const displayLimit = 250;
            const items = list.slice(0, displayLimit);

            items.forEach(item => {
                const btn = document.createElement("button");
                btn.type = "button";
                btn.className = "emoji-btn";
                btn.textContent = item.char;
                btn.title = item.name;
                btn.addEventListener("click", (e) => {
                    e.stopPropagation();
                    selectEmoji(item.char);
                });
                emojiGrid.appendChild(btn);
            });

            if (list.length > displayLimit) {
                const more = document.createElement("div");
                more.className = "text-muted small text-center w-100 p-2 text-primary";
                more.style.gridColumn = "span 8";
                more.textContent = `+ ${list.length - displayLimit} autres... (affinez la recherche)`;
                emojiGrid.appendChild(more);
            }
        }

        function selectEmoji(emoji) {
            iconInput.value = emoji;
            emojiPicker.classList.remove("show");

            recentEmojis = [emoji, ...recentEmojis.filter(e => e !== emoji)].slice(0, 32);
            localStorage.setItem("wiki_recent_emojis", JSON.stringify(recentEmojis));

            scheduleAutosave();
        }

        categoryBtns.forEach(btn => {
            btn.addEventListener("click", (e) => {
                e.stopPropagation();
                categoryBtns.forEach(b => b.classList.remove("active"));
                btn.classList.add("active");
                emojiSearch.value = "";
                renderEmojis(btn.dataset.category);
            });
        });

        let searchDebounce = null;
        emojiSearch.addEventListener("input", (e) => {
            clearTimeout(searchDebounce);
            searchDebounce = setTimeout(() => {
                const val = e.target.value.trim();
                const activeBtn = document.querySelector(".category-btn.active");
                const activeCat = activeBtn ? activeBtn.dataset.category : "smileys";
                renderEmojis(val ? null : activeCat, val);
            }, 200);
        });

        emojiPickerToggle.addEventListener("click", async e => {
            e.preventDefault();
            e.stopPropagation();
            const isShowing = emojiPicker.classList.contains("show");
            if (!isShowing) {
                emojiPicker.classList.add("show");
                emojiSearch.focus();
                const activeBtn = document.querySelector(".category-btn.active");
                const activeCat = activeBtn ? activeBtn.dataset.category : "smileys";
                await renderEmojis(activeCat);
            } else {
                emojiPicker.classList.remove("show");
            }
        });

        document.addEventListener("click", e => {
            if (!e.target.closest("#emojiPicker") && !e.target.closest("#emojiPickerToggle")) {
                emojiPicker.classList.remove("show");
            }
        });
    }

    function enableTinyMCE() {
        let initialContent = contentInput ? (contentInput.value || "") : "";

        if (window.marked && initialContent && !initialContent.trim().startsWith("<")) {
            try {
                initialContent = marked.parse(initialContent);
                if (window.DOMPurify) {
                    initialContent = window.DOMPurify.sanitize(initialContent, { USE_PROFILES: { html: true } });
                }
            } catch (err) {
                console.warn("Markdown parse fallback error:", err);
            }
        }

        const darkTheme = isDarkTheme();

        tinymce.init({
            selector: '#tinymceEditor',
            base_url: '/static/js/vendor/tinymce',
            suffix: '.min',
            plugins: 'preview importcss searchreplace autolink autosave save directionality code visualblocks visualchars fullscreen image link media codesample table charmap pagebreak nonbreaking anchor insertdatetime advlist lists wordcount help charmap emoticons accordion',
            menubar: 'file edit view insert format tools table help',
            toolbar: "undo redo | blocks fontfamily fontsize | bold italic underline strikethrough | align numlist bullist | link image | table media | lineheight outdent indent | forecolor backcolor removeformat | charmap emoticons | code fullscreen preview",
            autosave_ask_before_unload: false,
            skin: darkTheme ? "oxide-dark" : "oxide",
            content_css: darkTheme ? "dark" : "default",
            content_style: `
                body {
                    max-width: 850px;
                    margin: 20px auto;
                    padding: 40px 50px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                    min-height: 1000px;
                }
                
                /* Dark mode overrides */
                body.tox-content-dark {
                    color: #e5e7eb;
                    background-color: #1f2937;
                }
                html.tox-content-dark, .tox-tinymce { 
                    background-color: #111827 !important; 
                }
            `,
            height: 650,
            image_title: true,
            automatic_uploads: true,
            file_picker_types: 'image',
            paste_data_images: true,
            images_upload_handler: function (blobInfo, progress) {
                return new Promise((resolve, reject) => {
                    const formData = new FormData();
                    formData.append('file', blobInfo.blob(), blobInfo.filename());
                    formData.append('csrf_token', getCsrfToken());

                    fetch(cfg.uploadUrl, {
                        method: 'POST',
                        body: formData
                    })
                        .then(response => {
                            if (!response.ok) throw new Error("Erreur HTTP " + response.status);
                            return response.json();
                        })
                        .then(result => {
                            if (result && result.url) {
                                resolve(result.url);
                            } else {
                                reject("Upload refusé");
                            }
                        })
                        .catch(error => reject(error.message));
                });
            },
            setup: function (ed) {
                ed.on('init', function () {
                    ed.setContent(initialContent);
                    initialSnapshot = buildSnapshot();
                    const draft = getDraft();
                    if (draft && draft.v === 2) {
                        const savedAt = draft.savedAt ? ` (${draft.savedAt.replace("T", " ").slice(0, 19)})` : "";
                        setTimeout(() => {
                            if (window.confirm(`Un brouillon local est disponible${savedAt}. Voulez-vous le restaurer ?`)) {
                                applyDraft(draft);
                            }
                        }, 500);
                    }
                });
                ed.on('change', scheduleAutosave);
                ed.on('keyup', scheduleAutosave);
            }
        });
    }

    function initThemeObserver() {
        const toggle = document.getElementById("themeToggle");
        if (toggle) {
            toggle.addEventListener("click", () => {
                if (window.tinymce && initialSnapshot !== buildSnapshot()) {
                    syncContentField();
                    setTimeout(() => window.location.reload(), 300);
                } else if (window.tinymce) {
                    setTimeout(() => window.location.reload(), 300);
                }
            });
        }
    }

    function bindSubmitAndShortcuts() {
        form.addEventListener("submit", () => {
            isSubmitting = true;
            syncContentField();
            localStorage.removeItem(draftKey);
        });

        window.addEventListener("keydown", (e) => {
            const key = (e.key || "").toLowerCase();
            // Removed CTRL+S shortcut as it crashes the page or submits improperly
            /*
            if ((e.ctrlKey || e.metaKey) && key === "s") {
                e.preventDefault();
                syncContentField();
                if (typeof form.requestSubmit === "function") form.requestSubmit();
                else form.submit();
            }
            */
        });

        window.addEventListener("beforeunload", (e) => {
            if (isSubmitting) return;
            if (buildSnapshot() !== initialSnapshot) {
                e.preventDefault();
                e.returnValue = "Modifications non sauvegardées. Quitter ?";
            }
        });
    }

    function bindCategoryModals() {
        const addCategoryBtn = document.getElementById("addCategoryBtn");
        const addSubcategoryBtn = document.getElementById("addSubcategoryBtn");
        const categoryModal = new bootstrap.Modal(document.getElementById("categoryModal"));
        const subcategoryModal = new bootstrap.Modal(document.getElementById("subcategoryModal"));
        const categoryModalForm = document.getElementById("categoryModalForm");
        const subcategoryModalForm = document.getElementById("subcategoryModalForm");
        const saveCategoryModalBtn = document.getElementById("saveCategoryModalBtn");
        const saveSubcategoryModalBtn = document.getElementById("saveSubcategoryModalBtn");

        if (addCategoryBtn) {
            addCategoryBtn.addEventListener("click", () => categoryModal.show());
        }

        if (addSubcategoryBtn) {
            addSubcategoryBtn.addEventListener("click", () => {
                const categoryId = categorySelect.value;
                if (!categoryId) return;

                const catOption = categorySelect.options[categorySelect.selectedIndex];
                document.getElementById("subcategoryModalCatName").textContent = `Catégorie : ${catOption.textContent}`;
                subcategoryModalForm.querySelector('[name="category_id"]').value = categoryId;
                subcategoryModal.show();
            });
        }

        if (saveCategoryModalBtn) {
            saveCategoryModalBtn.addEventListener("click", async () => {
                const formData = new FormData(categoryModalForm);
                const data = Object.fromEntries(formData.entries());

                if (!data.name) {
                    alert("Le nom est requis");
                    return;
                }

                saveCategoryModalBtn.disabled = true;
                saveCategoryModalBtn.textContent = "Création...";

                try {
                    const response = await fetch("/wiki/wiki/category/create", {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json",
                            "X-CSRFToken": getCsrfToken()
                        },
                        body: JSON.stringify(data)
                    });

                    const result = await response.json();
                    if (result.success) {
                        // We need to refresh the categories list. 
                        // Since we don't have a simple "get all categories" API here, 
                        // we'll reload the page but keep the draft, OR simpler: 
                        // warn the user that a reload is needed to see the new category.
                        // Better: Just reload and let the auto-restore handle the rest.
                        window.location.reload();
                    } else {
                        alert("Erreur: " + (result.error || "Inconnue"));
                    }
                } catch (e) {
                    console.error(e);
                    alert("Erreur réseau");
                } finally {
                    saveCategoryModalBtn.disabled = false;
                    saveCategoryModalBtn.textContent = "Créer";
                }
            });
        }

        if (saveSubcategoryModalBtn) {
            saveSubcategoryModalBtn.addEventListener("click", async () => {
                const formData = new FormData(subcategoryModalForm);
                if (!formData.get("name")) {
                    alert("Le nom est requis");
                    return;
                }

                saveSubcategoryModalBtn.disabled = true;
                saveSubcategoryModalBtn.textContent = "Création...";

                try {
                    const data = Object.fromEntries(formData.entries());
                    const response = await fetch("/wiki/wiki/subcategory/create", {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json",
                            "X-CSRFToken": getCsrfToken(),
                            "X-Requested-With": "XMLHttpRequest"
                        },
                        body: JSON.stringify(data)
                    });

                    const result = await response.json();
                    if (result.success) {
                        // Unlike categories, we can easily inject a subcategory into the local array
                        // but it's safer to reload to get the real ID and consistency.
                        window.location.reload();
                    } else {
                        alert("Erreur: " + (result.error || "Inconnue"));
                    }
                } catch (e) {
                    console.error(e);
                    alert("Erreur réseau");
                } finally {
                    saveSubcategoryModalBtn.disabled = false;
                    saveSubcategoryModalBtn.textContent = "Créer";
                }
            });
        }

        // Enable/disable subcategory button based on category selection
        if (categorySelect && addSubcategoryBtn) {
            categorySelect.addEventListener("change", () => {
                addSubcategoryBtn.disabled = !categorySelect.value;
            });
            addSubcategoryBtn.disabled = !categorySelect.value;
        }
    }

    initCategorySelectors();
    initEmojiPicker();
    bindSubmitAndShortcuts();
    initThemeObserver();
    bindCategoryModals();

    [titleInput, iconInput, tagsInput, statusSelect, changeDescriptionInput].forEach(el => {
        if (el) {
            el.addEventListener("input", scheduleAutosave);
            el.addEventListener("change", scheduleAutosave);
        }
    });

    if (window.tinymce) {
        enableTinyMCE();
    } else {
        setAutosaveStatus("Erreur chargement TinyMCE", "error");
    }
})();
