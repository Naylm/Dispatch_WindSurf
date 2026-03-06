/**
 * DISPATCH RUNNER - MINI GAME
 * Synthwave infinite runner - launched from Konami Hub
 */

class DispatchRunner {
    constructor() {
        this.canvas = document.getElementById('gameCanvas');
        this.ctx = this.canvas.getContext('2d');
        this.scoreElement = document.getElementById('gameScore');
        this.highScoreElement = document.getElementById('gameHighScore');
        this.gameOverOverlay = document.querySelector('#runnerGameContainer .game-over-overlay');

        // Game specs
        this.width = 800;
        this.height = 400;
        this.canvas.width = this.width;
        this.canvas.height = this.height;

        // Game state
        this.active = false;
        this.waitStart = true;
        this.score = 0;
        this.level = 1;
        this.highScore = parseInt(localStorage.getItem('dispatch_runner_highscore')) || 0;
        this.speed = 5;
        this.gravity = 0.6;
        this.gameLoopId = null;

        // Entities
        this.player = {
            x: 100, y: 0, width: 40, height: 60,
            dy: 0, jumpForce: 12, grounded: false, crouching: false, color: '#00ffff'
        };

        this.obstacles = [];
        this.particles = [];
        this.keys = {};

        this.boundKeyDown = (e) => this._onKeyDown(e);
        this.boundKeyUp = (e) => this._onKeyUp(e);
        this.boundClick = () => {
            if (this.waitStart) {
                this.waitStart = false;
                this.active = true;
            } else if (this.active) {
                this.jump();
            }
        };

        this.init();
    }

    init() {
        if (this.highScoreElement) this.highScoreElement.textContent = this.highScore;
        this.setupListeners();
        this.reset();
    }

    setupListeners() {
        window.addEventListener('keydown', this.boundKeyDown);
        window.addEventListener('keyup', this.boundKeyUp);
        this.canvas.addEventListener('mousedown', this.boundClick);

        document.getElementById('restartGameBtn')?.addEventListener('click', () => {
            this.reset();
            this.active = true;
        });
    }

    _onKeyDown(e) {
        if (this.waitStart && (e.code === 'Space' || e.code === 'ArrowUp')) {
            this.waitStart = false;
            this.active = true;
            e.preventDefault();
            return;
        }
        if (!this.active) return;
        this.keys[e.code] = true;
        if (e.code === 'Space' || e.code === 'ArrowUp') { this.jump(); e.preventDefault(); }
        if (e.code === 'ArrowDown' || e.code === 'KeyS') { if (this.player.grounded) this.crouch(true); e.preventDefault(); }
    }

    _onKeyUp(e) {
        if (!this.active) return;
        this.keys[e.code] = false;
        if (e.code === 'ArrowDown' || e.code === 'KeyS') this.crouch(false);
    }

    start() {
        this.reset();
        this.waitStart = true;
        this.active = false;
    }

    stop() {
        this.active = false;
        this.waitStart = true;
        cancelAnimationFrame(this.gameLoopId);
    }

    reset() {
        this.active = false;
        this.waitStart = true;
        this.score = 0;
        this.level = 1;
        this.speed = 5;
        this.player.y = this.height - 110;
        this.player.dy = 0;
        this.player.grounded = false;
        this.player.crouching = false;
        this.player.height = 60;
        this.obstacles = [];
        this.particles = [];
        if (this.gameOverOverlay) this.gameOverOverlay.classList.remove('visible');
        if (this.scoreElement) this.scoreElement.textContent = '0';

        if (this.gameLoopId) cancelAnimationFrame(this.gameLoopId);
        this.gameLoop();
    }

    jump() {
        if (this.player.grounded && !this.player.crouching) {
            this.player.dy = -this.player.jumpForce;
            this.player.grounded = false;
            this.createJumpParticles();
            window.konamiSound?.play('jump');
        }
    }

    crouch(isCrouching) {
        if (!this.player.grounded && isCrouching) return;
        if (isCrouching && !this.player.crouching) {
            this.player.crouching = true;
            this.player.height = 35;
            this.player.y += 25;
        } else if (!isCrouching && this.player.crouching) {
            this.player.crouching = false;
            this.player.height = 60;
            this.player.y -= 25;
        }
    }

    createJumpParticles() {
        for (let i = 0; i < 8; i++) {
            this.particles.push({
                x: this.player.x + this.player.width / 2,
                y: this.player.y + this.player.height,
                vx: (Math.random() - 0.5) * 4, vy: Math.random() * -2,
                size: Math.random() * 4 + 2, color: '#ff00ff', life: 1.0
            });
        }
    }

    spawnObstacle() {
        if (this.obstacles.length === 0 ||
            (this.width - this.obstacles[this.obstacles.length - 1].x > (200 + Math.random() * 300))) {
            const type = Math.random() > 0.4 ? 'ground' : 'air';
            const h = type === 'ground' ? 30 + Math.random() * 40 : 40;
            this.obstacles.push({
                x: this.width,
                y: type === 'ground' ? this.height - 50 - h : this.height - 130,
                width: 30, height: h, type: type,
                color: type === 'ground' ? '#ff00ff' : '#ffff00'
            });
        }
    }

    update() {
        if (!this.active) return;
        const isJumping = this.keys['Space'] || this.keys['ArrowUp'];
        const isFalling = this.keys['ArrowDown'] || this.keys['KeyS'];
        let currentGravity = this.gravity;
        if (!this.player.grounded && isFalling) currentGravity *= 3;
        if (!this.player.grounded && !isJumping && this.player.dy < 0) this.player.dy += 1;

        if (!this.player.crouching) {
            this.player.dy += currentGravity;
            this.player.y += this.player.dy;
        }

        const groundY = this.height - 50;
        if (this.player.y + this.player.height > groundY) {
            this.player.y = groundY - this.player.height;
            this.player.dy = 0;
            this.player.grounded = true;
        }

        this.spawnObstacle();
        for (let i = this.obstacles.length - 1; i >= 0; i--) {
            const obs = this.obstacles[i];
            obs.x -= this.speed;
            if (this.player.x < obs.x + obs.width && this.player.x + this.player.width > obs.x &&
                this.player.y < obs.y + obs.height && this.player.y + this.player.height > obs.y) {
                this.gameOver();
            }
            if (obs.x + obs.width < 0) {
                this.obstacles.splice(i, 1);
                this.score++;
                // Level up every 10 obstacles
                const newLevel = Math.floor(this.score / 10) + 1;
                if (newLevel > this.level) {
                    this.level = newLevel;
                    this.speed = Math.min(15, 5 + (this.level - 1) * 0.8);
                    window.konamiSound?.play('levelup');
                }
            }
        }

        for (let i = this.particles.length - 1; i >= 0; i--) {
            const p = this.particles[i];
            p.x += p.vx; p.y += p.vy; p.life -= 0.02;
            if (p.life <= 0) this.particles.splice(i, 1);
        }

        if (this.scoreElement) this.scoreElement.textContent = this.score;
    }

    draw() {
        this.ctx.clearRect(0, 0, this.width, this.height);
        this.drawGrid();
        this.drawPlayer();
        for (const obs of this.obstacles) this.drawObstacle(obs);
        for (const p of this.particles) {
            this.ctx.fillStyle = `rgba(255, 0, 255, ${p.life})`;
            this.ctx.shadowBlur = 0;
            this.ctx.fillRect(p.x, p.y, p.size, p.size);
        }
        this.ctx.shadowBlur = 0;

        // Level indicator
        this.ctx.fillStyle = '#00f3ff';
        this.ctx.font = 'bold 14px Courier New';
        this.ctx.textAlign = 'right';
        this.ctx.fillText(`LEVEL ${this.level}`, this.width - 15, 25);
        this.ctx.textAlign = 'left';

        // Start screen
        if (this.waitStart && !this.gameOverOverlay.classList.contains('visible')) {
            this.ctx.fillStyle = 'rgba(0,0,0,0.6)';
            this.ctx.fillRect(0, 0, this.width, this.height);
            this.ctx.fillStyle = '#00f3ff';
            this.ctx.font = 'bold 40px Courier New';
            this.ctx.textAlign = 'center';
            this.ctx.fillText('DISPATCH RUNNER', this.width / 2, this.height / 2 - 20);
            this.ctx.fillStyle = '#fff';
            this.ctx.font = '20px Courier New';
            this.ctx.fillText('ESPACE pour commencer la livraison', this.width / 2, this.height / 2 + 30);
            this.ctx.textAlign = 'left';
        }
    }

    drawPlayer() {
        const p = this.player;
        this.ctx.save();
        this.ctx.translate(p.x, p.y);
        this.ctx.shadowBlur = 15;
        this.ctx.shadowColor = p.color;
        if (p.crouching) {
            this.ctx.fillStyle = p.color;
            this.ctx.fillRect(0, 10, 40, 25);
            this.ctx.fillStyle = '#fff';
            this.ctx.fillRect(25, 5, 15, 15);
            this.ctx.fillStyle = '#000';
            this.ctx.fillRect(32, 10, 8, 4);
            this.ctx.fillStyle = '#ff00ff';
            this.ctx.fillRect(-5, 20, 5, 5);
        } else {
            this.ctx.fillStyle = p.color;
            this.ctx.fillRect(5, 15, 30, 35);
            this.ctx.fillStyle = '#fff';
            this.ctx.fillRect(10, 0, 20, 18);
            this.ctx.fillStyle = '#000';
            this.ctx.fillRect(12, 5, 16, 5);
            const legOffset = Math.sin(Date.now() / 100) * 8;
            this.ctx.fillStyle = p.color;
            if (p.grounded) {
                this.ctx.fillRect(8, 50, 10, 10 + legOffset);
                this.ctx.fillRect(22, 50, 10, 10 - legOffset);
            } else {
                this.ctx.fillRect(8, 50, 10, 5);
                this.ctx.fillRect(22, 50, 10, 5);
            }
        }
        this.ctx.restore();
    }

    drawObstacle(obs) {
        this.ctx.save();
        this.ctx.translate(obs.x, obs.y);
        this.ctx.shadowBlur = 10;
        this.ctx.shadowColor = obs.color;
        if (obs.type === 'ground') {
            this.ctx.fillStyle = '#333';
            this.ctx.fillRect(0, 0, obs.width, obs.height);
            this.ctx.strokeStyle = obs.color;
            this.ctx.lineWidth = 1;
            this.ctx.strokeRect(0, 0, obs.width, obs.height);
            for (let y = 5; y < obs.height - 5; y += 12) {
                this.ctx.fillStyle = Math.random() > 0.1 ? '#00ff00' : '#ff0000';
                this.ctx.fillRect(5, y, 4, 4);
                this.ctx.fillStyle = '#555';
                this.ctx.fillRect(12, y, obs.width - 18, 4);
            }
        } else {
            const droneTime = Date.now() / 50;
            const floatY = Math.sin(droneTime) * 8;
            this.ctx.translate(0, floatY);
            this.ctx.fillStyle = '#222';
            this.ctx.fillRect(0, 10, obs.width, 15);
            this.ctx.fillStyle = '#555';
            const rotorW = Math.cos(droneTime * 0.5) * obs.width;
            this.ctx.fillRect((obs.width / 2) - (rotorW / 2), 5, rotorW, 2);
            this.ctx.fillStyle = obs.color;
            this.ctx.beginPath();
            this.ctx.arc(obs.width / 2, 17, 5, 0, Math.PI * 2);
            this.ctx.fill();
        }
        this.ctx.restore();
    }

    drawGrid() {
        const groundY = this.height - 50;
        this.ctx.strokeStyle = '#2d0a4e';
        this.ctx.lineWidth = 1;
        this.ctx.beginPath();
        this.ctx.moveTo(0, groundY);
        this.ctx.lineTo(this.width, groundY);
        this.ctx.stroke();
        const offset = (Date.now() / 10 % 50);
        for (let x = -50; x < this.width + 50; x += 50) {
            this.ctx.beginPath();
            this.ctx.moveTo(x + (offset * -1), groundY);
            this.ctx.lineTo(x + (offset * -1) - 100, this.height);
            this.ctx.stroke();
        }
        for (let y = groundY; y < this.height; y += 15) {
            this.ctx.beginPath();
            this.ctx.moveTo(0, y);
            this.ctx.lineTo(this.width, y);
            this.ctx.stroke();
        }
    }

    async gameOver() {
        this.active = false;
        window.konamiSound?.play('die');
        if (this.gameOverOverlay) this.gameOverOverlay.classList.add('visible');

        try {
            const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
            await fetch('/api/runner/submit-score', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
                body: JSON.stringify({ score: this.score })
            });
        } catch (e) { console.error("Failed to submit score:", e); }

        if (this.score > this.highScore) {
            this.highScore = this.score;
            localStorage.setItem('dispatch_runner_highscore', this.highScore);
            if (this.highScoreElement) this.highScoreElement.textContent = this.highScore;
        }
        cancelAnimationFrame(this.gameLoopId);

        // Submit to generic leaderboard too
        await window.arcadeLeaderboard?.submitScore('runner', this.score, this.level);
        this.loadLeaderboard();
    }

    async loadLeaderboard() {
        // Load original runner leaderboard
        const lbContainer = document.getElementById('gameLeaderboard');
        if (lbContainer) {
            lbContainer.innerHTML = '<div class="text-center py-2">Chargement...</div>';
            try {
                const response = await fetch('/api/runner/leaderboard');
                const data = await response.json();
                if (!data || data.length === 0) {
                    lbContainer.innerHTML = '<div class="text-center py-2 opacity-50">Aucun score</div>';
                } else {
                    let html = '<table class="leaderboard-table w-100"><tbody>';
                    data.forEach((entry, index) => {
                        const isMe = entry.username === window.CURRENT_USER;
                        html += `<tr class="${isMe ? 'me' : ''}"><td class="rank">#${index + 1}</td><td class="user">${entry.username}</td><td class="score">${entry.score}</td></tr>`;
                    });
                    html += '</tbody></table>';
                    lbContainer.innerHTML = html;
                }
            } catch (e) { lbContainer.innerHTML = '<div class="text-center py-2 text-danger">Erreur</div>'; }
        }

        // Load generic hub leaderboard into the new runnerLeaderboard container
        window.arcadeLeaderboard?.loadLeaderboard('runner', 'runnerLeaderboard');
    }

    gameLoop() {
        if (!this.active && !this.waitStart) return;
        this.update();
        this.draw();
        this.gameLoopId = requestAnimationFrame(() => this.gameLoop());
    }
}
