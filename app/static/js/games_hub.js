/**
 * static/js/games_hub.js
 * Manages the Konami Hub arcade, Konami code detection,
 * routing to specific minigames, and sound toggle.
 */

class GamesHub {
    constructor() {
        this.container = document.getElementById('easterEggContainer');
        this.closeBtn = document.getElementById('closeHubBtn');

        this.konamiCode = [
            'ArrowUp', 'ArrowUp', 'ArrowDown', 'ArrowDown',
            'ArrowLeft', 'ArrowRight', 'ArrowLeft', 'ArrowRight',
            'b', 'a'
        ];
        this.konamiIndex = 0;
        this.activeGameInstance = null;

        this.init();
    }

    init() {
        if (!this.container) return;
        this.bindEvents();
        this.bindKonamiListeners();
    }

    bindEvents() {
        if (this.closeBtn) this.closeBtn.addEventListener('click', () => this.hideHub());

        // Sound toggle
        const soundBtn = document.getElementById('hubSoundToggle');
        if (soundBtn) {
            this.updateSoundBtn(soundBtn);
            soundBtn.addEventListener('click', () => {
                window.konamiSound?.toggleMute();
                this.updateSoundBtn(soundBtn);
            });
        }

        // Game Selection Buttons
        document.querySelectorAll('.hub-game-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const gameId = e.target.dataset.game;
                this.startGame(gameId);
            });
        });
    }

    updateSoundBtn(btn) {
        const muted = window.konamiSound?.isMuted();
        btn.textContent = muted ? '🔇 SON OFF' : '🔊 SON ON';
        btn.title = muted ? 'Activer le son' : 'Désactiver le son';
    }

    bindKonamiListeners() {
        const searchInput = document.getElementById('searchInput');
        const searchInputTech = document.getElementById('searchInputTech');

        const handleKeydown = (e) => {
            const key = e.key.toLowerCase();
            const expected = this.konamiCode[this.konamiIndex];
            if (e.key === expected || key === expected) {
                this.konamiIndex++;
                // Prevent ALL matching keys from typing into the field
                // (especially 'b' and 'a' which would appear as text)
                if (key.length === 1) {
                    e.preventDefault();
                }
                if (this.konamiIndex === this.konamiCode.length) {
                    this.konamiIndex = 0;
                    // Clear any leftover characters and reset filters
                    e.target.value = '';
                    e.target.dispatchEvent(new Event('input', { bubbles: true }));
                    this.showHub();
                }
            } else {
                this.konamiIndex = 0;
            }
        };

        if (searchInput) searchInput.addEventListener('keydown', handleKeydown);
        if (searchInputTech) searchInputTech.addEventListener('keydown', handleKeydown);
    }

    showHub() {
        this.container.classList.add('active');
        document.body.style.overflow = 'hidden';
        document.querySelectorAll('.minigame-canvas').forEach(c => c.style.display = 'none');
    }

    hideHub() {
        this.container.classList.remove('active');
        document.body.style.overflow = '';
        this.exitCurrentGame();
        if (typeof window.applyFilters === 'function') window.applyFilters();
        if (typeof window.applyTechFilters === 'function') window.applyTechFilters();
    }

    startGame(gameId) {
        // Stop whatever is running
        if (this.activeGameInstance && typeof this.activeGameInstance.stop === 'function') {
            this.activeGameInstance.stop();
        }
        this.activeGameInstance = null;
        document.querySelectorAll('.minigame-canvas').forEach(c => c.style.display = 'none');
        this.container.classList.add('game-active');

        const gameMap = {
            runner: { containerId: 'runnerGameContainer', cls: DispatchRunner },
            flappy: { containerId: 'flappyGameContainer', cls: FlappyDrone },
            invaders: { containerId: 'invadersGameContainer', cls: TicketInvaders },
            breakout: { containerId: 'breakoutGameContainer', cls: BreakoutNetwork },
            snake: { containerId: 'snakeGameContainer', cls: SnakeIT },
            memory: { containerId: 'memoryGameContainer', cls: MemoryErrors }
        };

        const game = gameMap[gameId];
        if (!game) return;

        const el = document.getElementById(game.containerId);
        if (el) el.style.display = 'flex';
        this.activeGameInstance = new game.cls();
    }

    exitCurrentGame() {
        this.container.classList.remove('game-active');
        if (this.activeGameInstance && typeof this.activeGameInstance.stop === 'function') {
            this.activeGameInstance.stop();
        }
        this.activeGameInstance = null;
        document.querySelectorAll('.minigame-canvas').forEach(c => c.style.display = 'none');
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => { window.gamesHub = new GamesHub(); });
} else {
    window.gamesHub = new GamesHub();
}

// ========== Shared Arcade Leaderboard Helpers ==========
window.arcadeLeaderboard = {
    makeIdempotencyKey(gameName) {
        const rand = (window.crypto && window.crypto.randomUUID)
            ? window.crypto.randomUUID()
            : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
        return `konami:${gameName}:${rand}`;
    },

    async submitScore(gameName, score, level) {
        try {
            const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
            return await fetch('/api/arcade/submit-score', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken || '',
                    'X-Idempotency-Key': this.makeIdempotencyKey(gameName)
                },
                body: JSON.stringify({ game: gameName, score, level })
            });
        } catch (e) { console.error(`Failed to submit ${gameName} score:`, e); }
    },

    async loadLeaderboard(gameName, containerId) {
        const el = document.getElementById(containerId);
        if (!el) return;
        el.innerHTML = '<div class="text-center py-2" style="color:#aaa; font-family:monospace;">Chargement...</div>';
        try {
            const res = await fetch(`/api/arcade/leaderboard/${gameName}`);
            const data = await res.json();
            if (!data || data.length === 0) {
                el.innerHTML = '<div class="text-center py-2" style="color:#666; font-family:monospace;">Aucun score</div>';
                return;
            }
            let html = '<table class="leaderboard-table w-100" style="font-family:monospace; color:#fff; font-size:0.8rem; border-collapse: collapse;"><tbody>';
            // Limit to Top 10
            const displayData = data.slice(0, 10);
            displayData.forEach((entry, i) => {
                const isMe = entry.username === (window.CURRENT_USER || '');
                const medal = i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : `#${i + 1}`;
                html += `<tr style="${isMe ? 'background:rgba(0,243,255,0.1); color:#00f3ff; font-weight:bold;' : ''} border-bottom: 1px solid rgba(255,255,255,0.05);">
                    <td style="padding:2px 4px; width: 30px;">${medal}</td>
                    <td style="padding:2px 4px; max-width: 100px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${entry.username}</td>
                    <td style="padding:2px 4px; text-align:right; font-weight: bold;">${entry.score}</td>
                    <td style="padding:2px 4px; text-align:right; color:#ff00ff; font-size: 0.75rem;">Nv.${entry.level || 1}</td>
                </tr>`;
            });
            html += '</tbody></table>';
            el.innerHTML = html;
        } catch (e) {
            el.innerHTML = '<div class="text-center py-2" style="color:#ff0000; font-family:monospace;">Erreur</div>';
        }
    }
};
