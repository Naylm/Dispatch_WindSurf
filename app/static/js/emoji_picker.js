// Sélecteur d'émojis réutilisable
const EMOJI_CATEGORIES = {
    'Smileys': ['😀', '😃', '😄', '😁', '🤣', '😂', '😅', '😊', '☺️', '😌', '😉', '😏', '😍', '🥰', '😘', '😗', '😙', '😚', '🤗', '🤩', '🤔', '🤨', '😐', '😑', '😶', '🙄', '😮', '😯', '😲', '😳', '🥺', '😢', '😭', '😤', '😠', '😡', '🤬'],
    'Mains & Corps': ['💪', '👍', '👎', '👏', '🙌', '🤝', '🙏', '✍️', '💅', '👂', '👃', '👁️', '👀', '🧠', '👋', '🤚', '✋', '🖐️', '👌', '🤏', '✌️', '🤞', '🤟', '🤘', '👊', '✊', '🤛', '🤜'],
    'Cœurs & Émotions': ['❤️', '🧡', '💛', '💚', '💙', '💜', '🖤', '🤍', '🤎', '💔', '❣️', '💕', '💞', '💓', '💗', '💖', '💝', '💟', '💌'],
    'Nature & Météo': ['⭐', '🌟', '✨', '💫', '☀️', '🌙', '⚡', '🔥', '💥', '❄️', '🌈', '☁️', '🌊', '💧', '☔', '🌸', '🌺', '🌻', '🌷', '🌹', '🌲', '🌳', '🍀'],
    'Activités': ['🎯', '🎲', '🎮', '🎨', '🎬', '🎵', '🎶', '🎤', '🎧', '📻', '📺', '📷', '📹', '⚽', '🏀', '🏈', '⚾', '🎾', '🏐', '🏉', '🎱'],
    'Technologie': ['📱', '💻', '⌨️', '🖥️', '🖨️', '💾', '💿', '📀', '🔌', '💡', '🔦', '🔋', '⚙️', '🔧', '🔨', '🛠️'],
    'Travail & Docs': ['📚', '📖', '📝', '📄', '📃', '📋', '📊', '📈', '📉', '🗂️', '📁', '📂', '🗃️', '🗄️', '📦', '📮', '📬', '📭', '📪', '📫', '✉️', '📩', '📨', '💼', '📎', '🖊️', '✏️', '📏', '📐'],
    'Symboles': ['✅', '❌', '⚠️', '❗', '❓', '💯', '🔴', '🟡', '🟢', '🔵', '🟣', '⚫', '⚪', '🟤', '🔶', '🔷', '▶️', '⏸️', '⏹️', '⏺️', '⏭️', '⏮️', '⏩', '⏪', '➕', '➖', '✖️', '➗', '💲', '💵', '💴', '💶', '💷'],
    'Transports': ['🚗', '🚕', '🚙', '🚌', '🚎', '🏎️', '🚓', '🚑', '🚒', '🚐', '🚚', '🚛', '🚜', '🚲', '🛴', '🛵', '🏍️', '✈️', '🚁', '🚂', '🚃', '🚄', '🚅', '🚆', '🚇', '🚊', '🚝', '🚞', '🚋'],
    'Nourriture': ['🍕', '🍔', '🍟', '🌭', '🥪', '🌮', '🌯', '🍿', '🧂', '🥓', '🍳', '🥞', '🧇', '🧀', '🍖', '🍗', '🥩', '🍞', '🥐', '🥖', '🥨', '🥯', '🎂', '🍰', '🧁', '🍪', '🍩', '🍫', '🍬', '🍭', '🍮', '☕', '🍵', '🍷', '🍺', '🍻']
};

// Initialiser un sélecteur d'émojis
function initEmojiPicker(pickerId, inputId) {
    const picker = document.getElementById(pickerId);
    const input = document.getElementById(inputId);
    
    if (!picker || !input) {
        console.error(`Emoji picker ou input non trouvé: ${pickerId}, ${inputId}`);
        return;
    }
    
    // Vider le picker au cas où
    picker.innerHTML = '';
    
    // Remplir avec les catégories d'émojis
    Object.entries(EMOJI_CATEGORIES).forEach(([categoryName, emojis]) => {
        // Titre de catégorie
        const categoryTitle = document.createElement('div');
        categoryTitle.className = 'emoji-category';
        categoryTitle.textContent = categoryName;
        picker.appendChild(categoryTitle);
        
        // Émojis
        emojis.forEach(emoji => {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'emoji-btn';
            btn.textContent = emoji;
            btn.onclick = () => {
                input.value = emoji;
                picker.classList.remove('show');
            };
            picker.appendChild(btn);
        });
    });
    
    return {
        toggle: () => picker.classList.toggle('show'),
        hide: () => picker.classList.remove('show'),
        show: () => picker.classList.add('show')
    };
}

// Fermer tous les pickers en cliquant en dehors
document.addEventListener('click', function(e) {
    if (!e.target.closest('.emoji-picker-container') && !e.target.closest('.emoji-btn')) {
        document.querySelectorAll('.emoji-picker.show').forEach(picker => {
            picker.classList.remove('show');
        });
    }
});
