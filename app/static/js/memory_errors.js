/**
 * static/js/memory_errors.js
 * Memory card matching game – HTTP error codes.
 * Features: multiple levels (more cards), global sound.
 */

class MemoryErrors {
    constructor() {
        this.container = document.getElementById('memoryGameContainer');
        this.gridContainer = document.getElementById('memoryGrid');
        this.scoreElement = document.getElementById('memoryScore');
        this.highScoreElement = document.getElementById('memoryHighScore');
        this.gameOverOverlay = document.getElementById('memoryGameOver');

        this.attempts = 0;
        this.matches = 0;
        this.level = 1;
        this.totalPairs = 0;
        this.highScore = parseInt(localStorage.getItem('memoryHighScore')) || 0;

        this.flippedCards = [];
        this.isLocked = false;

        this.allSymbols = [
            '🔥 500', '🕵️ 404', '🚫 403', '🫖 418',
            '🚧 503', '🔀 301', '✅ 200', '🔐 401',
            '⏳ 408', '💾 507', '🔧 502', '⚡ 429'
        ];
        this.init();
    }

    init() {
        if (this.highScoreElement) this.highScoreElement.textContent = this.highScore === 0 ? '-' : this.highScore;
        document.getElementById('restartMemoryBtn')?.addEventListener('click', () => { this.level = 1; this.start(); });
        this.start();
    }

    start() {
        if (this.gameOverOverlay) this.gameOverOverlay.style.display = 'none';
        this.gridContainer.innerHTML = '';
        this.attempts = 0;
        this.matches = 0;
        if (this.scoreElement) this.scoreElement.textContent = '0';
        this.flippedCards = [];
        this.isLocked = false;

        // Level determines how many pairs (level 1 = 6 pairs = 12 cards, level 2 = 8 = 16, etc)
        const pairCount = Math.min(6 + (this.level - 1) * 2, this.allSymbols.length);
        const selected = this.allSymbols.slice(0, pairCount);
        const deck = [...selected, ...selected];
        this.totalPairs = pairCount;
        this.shuffle(deck);
        this.createBoard(deck, pairCount);
    }

    shuffle(a) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1));[a[i], a[j]] = [a[j], a[i]]; } }

    createBoard(deck, pairCount) {
        const cols = pairCount <= 6 ? 4 : pairCount <= 8 ? 4 : 6;
        this.gridContainer.style.cssText = `display:grid; grid-template-columns:repeat(${cols},1fr); gap:10px; width:100%; max-width:${cols * 90}px; margin:0 auto;`;

        deck.forEach((symbol) => {
            const card = document.createElement('div');
            card.dataset.name = symbol;
            card.style.cssText = 'position:relative; width:100%; aspect-ratio:1/1.2; cursor:pointer; transform-style:preserve-3d; transition:transform 0.4s; box-shadow:0 0 10px rgba(0,243,255,0.4); border:2px solid #00f3ff; border-radius:8px;';

            const front = document.createElement('div');
            front.textContent = symbol;
            front.style.cssText = 'position:absolute; width:100%; height:100%; backface-visibility:hidden; display:flex; justify-content:center; align-items:center; font-size:1.3rem; font-weight:bold; background:#00f3ff; color:#000; border-radius:6px; transform:rotateY(180deg);';

            const back = document.createElement('div');
            back.textContent = '</>';
            back.style.cssText = 'position:absolute; width:100%; height:100%; backface-visibility:hidden; display:flex; justify-content:center; align-items:center; font-size:2rem; font-weight:bold; background:#0f0f19; color:#ff00ff; border-radius:6px;';

            card.appendChild(front);
            card.appendChild(back);
            card.addEventListener('click', () => this.flipCard(card));
            this.gridContainer.appendChild(card);
        });
    }

    flipCard(card) {
        if (this.isLocked) return;
        if (card === this.flippedCards[0]) return;
        if (card.classList.contains('matched')) return;

        card.style.transform = 'rotateY(180deg)';
        card.classList.add('flipped');
        window.konamiSound?.play('flip');

        this.flippedCards.push(card);
        if (this.flippedCards.length === 2) {
            this.attempts++;
            if (this.scoreElement) this.scoreElement.textContent = this.attempts;
            this.checkForMatch();
        }
    }

    checkForMatch() {
        if (this.flippedCards[0].dataset.name === this.flippedCards[1].dataset.name) {
            this.disableCards();
            window.konamiSound?.play('match');
            this.matches++;
            if (this.matches === this.totalPairs) setTimeout(() => this.levelComplete(), 500);
        } else {
            this.unflipCards();
        }
    }

    disableCards() {
        for (let c of this.flippedCards) {
            c.classList.add('matched');
            c.style.boxShadow = '0 0 15px #00ff00';
            c.style.borderColor = '#00ff00';
            c.querySelector('div').style.background = '#00ff00';
        }
        this.flippedCards = [];
    }

    unflipCards() {
        this.isLocked = true;
        window.konamiSound?.play('error');
        setTimeout(() => {
            for (let c of this.flippedCards) { c.style.transform = 'rotateY(0deg)'; c.classList.remove('flipped'); }
            this.flippedCards = [];
            this.isLocked = false;
        }, 800);
    }

    levelComplete() {
        window.konamiSound?.play('levelup');
        // Check if there are more levels
        if (this.totalPairs < this.allSymbols.length) {
            if (this.gameOverOverlay) {
                this.gameOverOverlay.querySelector('h2').textContent = `NIVEAU ${this.level} RÉUSSI !`;
                const sc = this.gameOverOverlay.querySelector('.memory-current-score');
                if (sc) sc.textContent = `Paires trouvées en ${this.attempts} tentatives.`;
                const btn = document.getElementById('restartMemoryBtn');
                if (btn) btn.textContent = "NIVEAU SUIVANT";
                this.gameOverOverlay.style.display = 'flex';
                // Temporal change to button behavior
                const nextLevelHandler = () => {
                    this.level++;
                    btn.textContent = "NOUVELLE PARTIE";
                    btn.removeEventListener('click', nextLevelHandler);
                    this.start();
                };
                btn.addEventListener('click', nextLevelHandler);
            }
        } else {
            this.gameOver();
        }
    }

    async gameOver() {
        window.konamiSound?.play('win');
        if (this.highScore === 0 || this.attempts < this.highScore) {
            this.highScore = this.attempts;
            localStorage.setItem('memoryHighScore', this.highScore);
            if (this.highScoreElement) this.highScoreElement.textContent = this.highScore;
        }
        if (this.gameOverOverlay) {
            this.gameOverOverlay.querySelector('h2').textContent = "TOUS NIVEAUX TERMINÉS !";
            const sc = this.gameOverOverlay.querySelector('.memory-current-score');
            if (sc) sc.textContent = `Tentatives totales: ${this.attempts}`;
            this.gameOverOverlay.style.display = 'flex';
        }
        await window.arcadeLeaderboard?.submitScore('memory', this.attempts, this.level);
        window.arcadeLeaderboard?.loadLeaderboard('memory', 'memoryLeaderboard');
    }

    stop() { /* nothing to stop for Memory */ }
}
