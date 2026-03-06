/**
 * static/js/snake_it.js
 * Snake clone – RJ45 cable collecting data packets.
 * Features: level progression (faster speed), global sound.
 */

class SnakeIT {
    constructor() {
        this.container = document.getElementById('snakeGameContainer');
        this.canvas = document.getElementById('snakeCanvas');
        this.ctx = this.canvas.getContext('2d');
        this.scoreElement = document.getElementById('snakeScore');
        this.highScoreElement = document.getElementById('snakeHighScore');
        this.gameOverOverlay = document.getElementById('snakeGameOver');

        this.isPlaying = false;
        this.isGameOver = false;
        this.score = 0;
        this.level = 1;
        this.highScore = parseInt(localStorage.getItem('snakeHighScore')) || 0;
        this.animationId = null;

        this.gridSize = 20;
        this.tileCountX = 0;
        this.tileCountY = 0;

        this.snake = [];
        this.headX = 10;
        this.headY = 10;
        this.velX = 0;
        this.velY = 0;
        this.tailLength = 5;
        this.food = { x: 15, y: 15 };
        this.speed = 8;
        this.lastRenderTime = 0;
        this.waitReady = false;
        this.inputQueue = [];

        this.handleKeyDown = this.handleKeyDown.bind(this);
        this.loop = this.loop.bind(this);
        this.init();
    }

    init() {
        this.resize();
        window.addEventListener('resize', () => this.resize());
        document.addEventListener('keydown', this.handleKeyDown);
        if (this.highScoreElement) this.highScoreElement.textContent = this.highScore;
        document.getElementById('restartSnakeBtn')?.addEventListener('click', () => {
            if (this.gameOverOverlay) this.gameOverOverlay.style.display = 'none';
            this.fullReset(); this.start();
        });
        this.fullReset();
        this.drawInitialScreen();
    }

    resize() {
        let maxW = Math.min(window.innerWidth - 40, 600);
        let maxH = Math.min(window.innerHeight - 150, 600);
        this.canvas.width = Math.floor(maxW / this.gridSize) * this.gridSize;
        this.canvas.height = Math.floor(maxH / this.gridSize) * this.gridSize;
        this.tileCountX = this.canvas.width / this.gridSize;
        this.tileCountY = this.canvas.height / this.gridSize;
    }

    fullReset() {
        this.score = 0;
        this.level = 1;
        this.speed = 8;
        this.waitReady = false;
        this.inputQueue = [];
        this.reset();
    }

    reset() {
        this.headX = Math.floor(this.tileCountX / 2);
        this.headY = Math.floor(this.tileCountY / 2);
        this.velX = 0; this.velY = 0;
        this.snake = [];
        this.tailLength = 5;
        if (this.scoreElement) this.scoreElement.textContent = this.score;
        this.isGameOver = false; this.isPlaying = false;
        this.placeFood();
    }

    placeFood() {
        this.food.x = Math.floor(Math.random() * this.tileCountX);
        this.food.y = Math.floor(Math.random() * this.tileCountY);
        for (let s of this.snake) { if (s.x === this.food.x && s.y === this.food.y) { this.placeFood(); break; } }
    }

    handleKeyDown(e) {
        if (!this.container || !this.container.offsetParent) return;
        if (this.waitReady) {
            this.waitReady = false;
            e.preventDefault();
            return;
        }
        if (!this.isPlaying && !this.isGameOver && ['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'Space'].includes(e.code)) {
            if (e.code === 'Space' || e.code === 'ArrowRight') { this.velX = 1; this.velY = 0; }
            else if (e.code === 'ArrowUp') { this.velX = 0; this.velY = -1; }
            else if (e.code === 'ArrowDown') { this.velX = 0; this.velY = 1; }
            else if (e.code === 'ArrowLeft') { this.velX = -1; this.velY = 0; }
            this.start();
            e.preventDefault();
            return;
        }
        if (e.code === 'ArrowUp') this.inputQueue.push('UP');
        if (e.code === 'ArrowDown') this.inputQueue.push('DOWN');
        if (e.code === 'ArrowLeft') this.inputQueue.push('LEFT');
        if (e.code === 'ArrowRight') this.inputQueue.push('RIGHT');
    }

    start() {
        this.isPlaying = true; this.isGameOver = false;
        if (this.gameOverOverlay) this.gameOverOverlay.style.display = 'none';
        if (this.animationId) cancelAnimationFrame(this.animationId);
        this.lastRenderTime = 0;
        this.animationId = requestAnimationFrame(this.loop);
    }

    stop() {
        this.isPlaying = false;
        if (this.animationId) cancelAnimationFrame(this.animationId);
    }

    async gameOver() {
        this.isGameOver = true; this.isPlaying = false;
        window.konamiSound?.play('die');
        if (this.score > this.highScore) { this.highScore = this.score; localStorage.setItem('snakeHighScore', this.highScore); if (this.highScoreElement) this.highScoreElement.textContent = this.highScore; }
        if (this.gameOverOverlay) {
            this.gameOverOverlay.querySelector('h2').textContent = `CÂBLE DÉCONNECTÉ — Niveau ${this.level}`;
            this.gameOverOverlay.style.display = 'flex';
        }
        await window.arcadeLeaderboard?.submitScore('snake', this.score, this.level);
        window.arcadeLeaderboard?.loadLeaderboard('snake', 'snakeLeaderboard');
    }

    update() {
        if (this.waitReady) return;

        // Process input queue
        if (this.inputQueue.length > 0) {
            const nextDir = this.inputQueue.shift();
            if (nextDir === 'UP' && this.velY !== 1) { this.velX = 0; this.velY = -1; }
            else if (nextDir === 'DOWN' && this.velY !== -1) { this.velX = 0; this.velY = 1; }
            else if (nextDir === 'LEFT' && this.velX !== 1) { this.velX = -1; this.velY = 0; }
            else if (nextDir === 'RIGHT' && this.velX !== -1) { this.velX = 1; this.velY = 0; }
        }

        this.headX += this.velX; this.headY += this.velY;
        if (this.headX < 0 || this.headX >= this.tileCountX || this.headY < 0 || this.headY >= this.tileCountY) { this.gameOver(); return; }
        for (let s of this.snake) { if (this.headX === s.x && this.headY === s.y && (this.velX !== 0 || this.velY !== 0)) { this.gameOver(); return; } }

        this.snake.push({ x: this.headX, y: this.headY });
        while (this.snake.length > this.tailLength) this.snake.shift();

        if (this.headX === this.food.x && this.headY === this.food.y) {
            this.score += 10;
            this.tailLength++;
            // Level up every 5 food
            const newLevel = Math.floor(this.score / 50) + 1;
            if (newLevel > this.level) {
                this.level = newLevel;
                this.speed = Math.min(20, 8 + (this.level - 1) * 1.5);
                window.konamiSound?.play('levelup');
                this.waitReady = true;
            } else {
                window.konamiSound?.play('eat');
            }
            if (this.scoreElement) this.scoreElement.textContent = this.score;
            this.placeFood();
        }
    }

    draw() {
        const ctx = this.ctx;
        ctx.fillStyle = '#0f0f19';
        ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

        // Grid
        ctx.strokeStyle = 'rgba(0,243,255,0.05)';
        for (let i = 0; i <= this.tileCountX; i++) {
            ctx.beginPath();
            ctx.moveTo(i * this.gridSize, 0);
            ctx.lineTo(i * this.gridSize, this.canvas.height);
            ctx.stroke();
        }
        for (let i = 0; i <= this.tileCountY; i++) {
            ctx.beginPath();
            ctx.moveTo(0, i * this.gridSize);
            ctx.lineTo(this.canvas.width, i * this.gridSize);
            ctx.stroke();
        }

        // Food (Data Packet)
        const fx = this.food.x * this.gridSize;
        const fy = this.food.y * this.gridSize;
        ctx.fillStyle = '#ff00ff';
        ctx.shadowColor = '#ff00ff';
        ctx.shadowBlur = 15;
        // Central core
        ctx.fillRect(fx + 6, fy + 6, this.gridSize - 12, this.gridSize - 12);
        // Inner detail
        ctx.fillStyle = '#fff';
        ctx.fillRect(fx + 8, fy + 8, 4, 4);
        // Outer glowing corners
        ctx.strokeStyle = '#ff00ff';
        ctx.lineWidth = 1;
        ctx.strokeRect(fx + 2, fy + 2, this.gridSize - 4, this.gridSize - 4);
        ctx.shadowBlur = 0;

        // Snake (RJ45 Cable)
        for (let i = 0; i < this.snake.length; i++) {
            const p = this.snake[i];
            const px = p.x * this.gridSize;
            const py = p.y * this.gridSize;
            const isHead = (i === this.snake.length - 1);

            if (isHead) {
                // RJ45 Connector Head
                ctx.fillStyle = '#00f3ff';
                ctx.shadowColor = '#00f3ff';
                ctx.shadowBlur = 10;
                // Main body
                ctx.fillRect(px + 2, py + 2, this.gridSize - 4, this.gridSize - 4);
                // Connector tip
                ctx.fillStyle = '#fff';
                if (this.velX === 1) ctx.fillRect(px + this.gridSize - 4, py + 6, 4, 8);
                else if (this.velX === -1) ctx.fillRect(px, py + 6, 4, 8);
                else if (this.velY === 1) ctx.fillRect(px + 6, py + this.gridSize - 4, 8, 4);
                else if (this.velY === -1) ctx.fillRect(px + 6, py, 8, 4);
                else ctx.fillRect(px + this.gridSize - 4, py + 6, 4, 8); // default right

                // Pins
                ctx.fillStyle = '#ff9900';
                for (let j = 4; j < this.gridSize - 4; j += 4) {
                    if (this.velX !== 0) ctx.fillRect(px + this.gridSize / 2, py + j, 3, 1);
                    else ctx.fillRect(px + j, py + this.gridSize / 2, 1, 3);
                }
                ctx.shadowBlur = 0;
            } else {
                // Cable segment
                ctx.fillStyle = '#0066cc';
                ctx.fillRect(px + 4, py + 4, this.gridSize - 8, this.gridSize - 8);
                // Internal wires detail
                ctx.fillStyle = 'rgba(255,255,255,0.2)';
                ctx.fillRect(px + 6, py + 6, this.gridSize - 12, 2);
                ctx.fillRect(px + 6, py + 10, this.gridSize - 12, 2);
            }
        }

        // Level
        ctx.fillStyle = '#00f3ff';
        ctx.font = 'bold 14px Courier New';
        ctx.textAlign = 'right';
        ctx.fillText(`NIVEAU ${this.level}`, this.canvas.width - 10, 20);
        ctx.textAlign = 'left';

        // Intermission
        if (this.waitReady) {
            ctx.fillStyle = 'rgba(0,0,0,0.6)';
            ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
            ctx.fillStyle = '#00f3ff';
            ctx.font = 'bold 30px Courier New';
            ctx.textAlign = 'center';
            ctx.fillText(`NIVEAU ${this.level - 1} RÉUSSI`, this.canvas.width / 2, this.canvas.height / 2 - 20);
            ctx.fillStyle = '#fff';
            ctx.font = '20px Courier New';
            ctx.fillText(`BANDE PASSANTE AUGMENTÉE (Nv.${this.level})`, this.canvas.width / 2, this.canvas.height / 2 + 20);
            ctx.font = '14px Courier New';
            ctx.fillText('APPUYEZ SUR UNE TOUCHE POUR REPRENDRE', this.canvas.width / 2, this.canvas.height / 2 + 60);
            ctx.textAlign = 'left';
        }
    }

    drawInitialScreen() {
        this.ctx.fillStyle = '#0f0f19'; this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
        this.ctx.fillStyle = '#00f3ff'; this.ctx.font = '40px Courier New'; this.ctx.textAlign = 'center';
        this.ctx.fillText('SNAKE IT', this.canvas.width / 2, this.canvas.height / 2 - 20);
        this.ctx.fillStyle = '#fff'; this.ctx.font = '20px Courier New';
        this.ctx.fillText('Flèches pour commencer', this.canvas.width / 2, this.canvas.height / 2 + 30);
        this.ctx.textAlign = 'left';
    }

    loop(t) {
        if (!this.isPlaying && !this.isGameOver) { this.drawInitialScreen(); return; }
        if (this.isPlaying) {
            this.animationId = requestAnimationFrame(this.loop);
            if ((t - this.lastRenderTime) / 1000 < 1 / this.speed) return;
            this.lastRenderTime = t;
            this.update(); this.draw();
        }
    }
}
