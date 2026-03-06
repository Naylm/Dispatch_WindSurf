/**
 * static/js/breakout_network.js
 * Breakout clone – Piercing a Firewall with a Ping.
 * Features: multi-level waves, proper circle-vs-rect collision, global sound, server leaderboard.
 */

class BreakoutNetwork {
    constructor() {
        this.container = document.getElementById('breakoutGameContainer');
        this.canvas = document.getElementById('breakoutCanvas');
        this.ctx = this.canvas.getContext('2d');
        this.scoreElement = document.getElementById('breakoutScore');
        this.highScoreElement = document.getElementById('breakoutHighScore');
        this.gameOverOverlay = document.getElementById('breakoutGameOver');

        this.isPlaying = false;
        this.isGameOver = false;
        this.score = 0;
        this.level = 1;
        this.highScore = parseInt(localStorage.getItem('breakoutHighScore')) || 0;
        this.animationId = null;
        this.lives = 3;

        // Base settings
        this.baseSpeed = 4;
        this.basePaddleWidth = 120;

        this.paddle = { width: this.basePaddleWidth, height: 15, x: 0, y: 0, speed: 7, color: '#00f3ff' };
        this.balls = [];
        this.bullets = [];
        this.powerups = [];

        this.stickyActive = false;
        this.laserActive = false;
        this.pierceActive = false;
        this.fireActive = false;
        this.shieldActive = false;
        this.speedMultiplier = 1;
        this.waitReady = true;
        this.stickyWait = false;

        // Brick settings
        this.brickCols = 10;
        this.brickHeight = 20;
        this.brickPadding = 5;
        this.brickOffsetLeft = 30;
        this.brickOffsetTop = 50;

        this.keys = { ArrowLeft: false, ArrowRight: false, Space: false };
        this.handleKeyDown = this.handleKeyDown.bind(this);
        this.handleKeyUp = this.handleKeyUp.bind(this);
        this.loop = this.loop.bind(this);
        this.init();
    }

    init() {
        this.resize();
        window.addEventListener('resize', () => this.resize());
        document.addEventListener('keydown', this.handleKeyDown);
        document.addEventListener('keyup', this.handleKeyUp);
        if (this.highScoreElement) this.highScoreElement.textContent = this.highScore;
        document.getElementById('restartBreakoutBtn')?.addEventListener('click', () => {
            if (this.gameOverOverlay) this.gameOverOverlay.style.display = 'none';
            this.fullReset(); this.start();
        });
        this.fullReset();
        this.drawInitialScreen();
    }

    resize() {
        this.canvas.width = Math.min(window.innerWidth - 40, 800);
        this.canvas.height = Math.min(window.innerHeight - 150, 600);
        this.paddle.y = this.canvas.height - 30;
        this.brickWidth = (this.canvas.width - (this.brickOffsetLeft * 2) - (this.brickPadding * (this.brickCols - 1))) / this.brickCols;
    }

    fullReset() {
        this.score = 0;
        this.level = 1;
        this.lives = 3;
        this.paddle.width = this.basePaddleWidth;
        this.speedMultiplier = 1;
        this.fullResetState();
        this.resetBall();
        this.createBricks();
        if (this.scoreElement) this.scoreElement.textContent = '0';
        this.isGameOver = false;
        this.isPlaying = false;
    }

    fullResetState() {
        this.stickyActive = false;
        this.laserActive = false;
        this.pierceActive = false;
        this.fireActive = false;
        this.shieldActive = false;
        this.bullets = [];
        this.powerups = [];
    }

    resetBall() {
        this.paddle.x = this.canvas.width / 2 - this.paddle.width / 2;
        this.balls = [{
            x: this.canvas.width / 2,
            y: this.paddle.y - 8,
            radius: 8,
            speed: this.baseSpeed + (this.level - 1) * 0.3,
            dx: 0,
            dy: 0,
            color: '#ff00ff'
        }];
        this.waitReady = true;
    }

    getLevelConfig() {
        const patterns = [
            // Level 1: Full block (Basic)
            { type: 'full', rows: 4 },
            // Level 2: Hollow Box
            {
                type: 'pattern', data: [
                    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
                    [1, 0, 0, 0, 0, 0, 0, 0, 0, 1],
                    [1, 0, 0, 0, 0, 0, 0, 0, 0, 1],
                    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
                ]
            },
            // Level 3: Stripes
            {
                type: 'pattern', data: [
                    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
                    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
                    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
                ]
            },
            // Level 4: Diamond
            {
                type: 'pattern', data: [
                    [0, 0, 0, 0, 1, 1, 0, 0, 0, 0],
                    [0, 0, 0, 1, 1, 1, 1, 0, 0, 0],
                    [0, 0, 1, 1, 1, 1, 1, 1, 0, 0],
                    [0, 1, 1, 1, 1, 1, 1, 1, 1, 0],
                    [0, 0, 1, 1, 1, 1, 1, 1, 0, 0],
                    [0, 0, 0, 1, 1, 1, 1, 0, 0, 0],
                    [0, 0, 0, 0, 1, 1, 0, 0, 0, 0]
                ]
            },
            // Level 5: X-Shape
            {
                type: 'pattern', data: [
                    [1, 1, 0, 0, 0, 0, 0, 0, 1, 1],
                    [0, 1, 1, 0, 0, 0, 0, 1, 1, 0],
                    [0, 0, 1, 1, 0, 0, 1, 1, 0, 0],
                    [0, 0, 0, 1, 1, 1, 1, 0, 0, 0],
                    [0, 0, 1, 1, 0, 0, 1, 1, 0, 0],
                    [0, 1, 1, 0, 0, 0, 0, 1, 1, 0],
                    [1, 1, 0, 0, 0, 0, 0, 0, 1, 1]
                ]
            },
            // Level 6: Checkerboard
            {
                type: 'pattern', data: [
                    [1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
                    [0, 1, 0, 1, 0, 1, 0, 1, 0, 1],
                    [1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
                    [0, 1, 0, 1, 0, 1, 0, 1, 0, 1]
                ]
            },
            // Level 7: Pyramids
            {
                type: 'pattern', data: [
                    [0, 0, 1, 1, 0, 0, 0, 0, 1, 1],
                    [0, 1, 1, 1, 1, 0, 0, 1, 1, 1],
                    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
                    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
                ]
            },
            // Level 8: Columns
            {
                type: 'pattern', data: [
                    [1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
                    [1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
                    [1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
                    [1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
                    [1, 0, 1, 0, 1, 0, 1, 0, 1, 0]
                ]
            },
            // Level 9: The Heart
            {
                type: 'pattern', data: [
                    [0, 1, 1, 0, 0, 0, 0, 1, 1, 0],
                    [1, 1, 1, 1, 0, 0, 1, 1, 1, 1],
                    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
                    [0, 1, 1, 1, 1, 1, 1, 1, 1, 0],
                    [0, 0, 1, 1, 1, 1, 1, 1, 0, 0],
                    [0, 0, 0, 1, 1, 1, 1, 0, 0, 0],
                    [0, 0, 0, 0, 1, 1, 0, 0, 0, 0]
                ]
            },
            // Level 10: Space Invader pixel art
            {
                type: 'pattern', data: [
                    [0, 0, 1, 0, 0, 0, 0, 1, 0, 0],
                    [0, 0, 0, 1, 1, 1, 1, 0, 0, 0],
                    [0, 1, 1, 1, 1, 1, 1, 1, 1, 0],
                    [1, 1, 0, 1, 1, 1, 1, 0, 1, 1],
                    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
                ]
            }
        ];
        return patterns[(this.level - 1) % patterns.length];
    }

    createBricks() {
        const config = this.getLevelConfig();
        const colors = ['#ff0000', '#ff9900', '#ffff00', '#00ff00', '#00f3ff', '#ff00ff', '#9900ff', '#ffffff'];
        this.bricks = [];

        if (config.type === 'pattern') {
            const data = config.data;
            const rows = data.length;
            const cols = data[0].length;
            // Center the pattern if it's smaller than current brickCols
            const startCol = Math.max(0, Math.floor((this.brickCols - cols) / 2));

            for (let c = 0; c < this.brickCols; c++) {
                this.bricks[c] = [];
                for (let r = 0; r < rows; r++) {
                    const patternCol = c - startCol;
                    const status = (patternCol >= 0 && patternCol < cols) ? data[r][patternCol] : 0;
                    this.bricks[c][r] = { x: 0, y: 0, status: status, color: colors[r % colors.length] };
                }
            }
        } else {
            const rows = Math.min(3 + this.level, 8);
            for (let c = 0; c < this.brickCols; c++) {
                this.bricks[c] = [];
                for (let r = 0; r < rows; r++) {
                    this.bricks[c][r] = { x: 0, y: 0, status: 1, color: colors[r % colors.length] };
                }
            }
        }
    }

    handleKeyDown(e) {
        if (!this.container || !this.container.offsetParent) return;
        if (e.code === 'ArrowLeft') this.keys.ArrowLeft = true;
        if (e.code === 'ArrowRight') this.keys.ArrowRight = true;
        if (e.code === 'Space') {
            this.keys.Space = true;
            if (!this.isPlaying && !this.isGameOver) {
                this.start();
            } else if (this.waitReady && this.isPlaying) {
                this.waitReady = false;
                this.stickyWait = false;
                const b = this.balls[0];
                if (b) {
                    b.dx = (b.speed || this.baseSpeed) * (Math.random() > 0.5 ? 1 : -1);
                    b.dy = -(b.speed || this.baseSpeed);
                }
            } else if (this.laserActive && this.isPlaying && !this.waitReady) {
                this.fireLaser();
            }
            e.preventDefault();
        }
    }

    handleKeyUp(e) {
        if (e.code === 'ArrowLeft') this.keys.ArrowLeft = false;
        if (e.code === 'ArrowRight') this.keys.ArrowRight = false;
        if (e.code === 'Space') this.keys.Space = false;
    }

    start() {
        this.isPlaying = true;
        this.isGameOver = false;
        this.waitReady = true;
        this.stickyWait = false;
        this.resetBall();
        if (this.gameOverOverlay) this.gameOverOverlay.style.display = 'none';
        if (this.animationId) cancelAnimationFrame(this.animationId);
        this.loop();
    }

    stop() {
        this.isPlaying = false;
        if (this.animationId) cancelAnimationFrame(this.animationId);
        this.keys = { ArrowLeft: false, ArrowRight: false, Space: false };
    }

    async gameOver() {
        this.isGameOver = true;
        this.isPlaying = false;
        window.konamiSound?.play('die');
        if (this.score > this.highScore) {
            this.highScore = this.score;
            localStorage.setItem('breakoutHighScore', this.highScore);
            if (this.highScoreElement) this.highScoreElement.textContent = this.highScore;
        }
        if (this.gameOverOverlay) {
            this.gameOverOverlay.querySelector('h2').textContent = `CONNEXION PERDUE — Nv.${this.level}`;
            this.gameOverOverlay.style.display = 'flex';
        }
        await window.arcadeLeaderboard?.submitScore('breakout', this.score, this.level);
        window.arcadeLeaderboard?.loadLeaderboard('breakout', 'breakoutLeaderboard');
    }

    nextLevel() {
        this.level++;
        this.balls = [];
        this.resetBall();
        this.createBricks();
        if (this.scoreElement) this.scoreElement.textContent = this.score;
        this.bullets = [];
        this.powerups = [];
        this.laserActive = false;
        this.pierceActive = false;
        this.fireActive = false;
        this.shieldActive = false;
        this.speedMultiplier = 1;
    }

    loseLife() {
        this.lives--;
        window.konamiSound?.play('hit');
        if (this.lives <= 0) {
            this.gameOver();
        } else {
            this.waitReady = true;
            this.stickyWait = false;
            this.resetBall();
            this.fullResetState();
        }
    }

    spawnPowerup(bx, by) {
        if (Math.random() > 0.15) return;
        const types = [
            { id: 'WIDE', color: '#00ff00', label: '↔️' },
            { id: 'LIFE', color: '#ff00ff', label: '❤️' },
            { id: 'SLOW', color: '#ffff00', label: '🐢' },
            { id: 'STICKY', color: '#00f3ff', label: '🧲' },
            { id: 'LASER', color: '#ff0000', label: '🔫' },
            { id: 'MULTI', color: '#ff9900', label: '🌐' },
            { id: 'PIERCE', color: '#00ffff', label: '💎' },
            { id: 'SHIELD', color: '#777777', label: '🛡️' },
            { id: 'MEGA', color: '#ff0055', label: '🎾' },
            { id: 'FIRE', color: '#ffcc00', label: '🔥' },
            { id: 'SPEED', color: '#ffffff', label: '⚡' }
        ];
        const t = types[Math.floor(Math.random() * types.length)];
        this.powerups.push({ x: bx + this.brickWidth / 2 - 10, y: by, width: 25, height: 25, type: t.id, color: t.color, label: t.label });
    }

    activatePowerup(p) {
        window.konamiSound?.play('levelup');
        if (p.type === 'WIDE') {
            const oldW = this.paddle.width;
            this.paddle.width = Math.min(this.canvas.width * 0.6, this.paddle.width + 40);
            setTimeout(() => { if (this.isPlaying) this.paddle.width = Math.max(this.basePaddleWidth - (this.level - 1) * 5, 60); }, 10000);
        } else if (p.type === 'LIFE') {
            this.lives = Math.min(5, this.lives + 1);
        } else if (p.type === 'SLOW') {
            for (let b of this.balls) { b.dx *= 0.6; b.dy *= 0.6; }
            setTimeout(() => {
                if (this.isPlaying) {
                    for (let b of this.balls) { b.dx /= 0.6; b.dy /= 0.6; }
                }
            }, 8000);
        } else if (p.type === 'STICKY') {
            this.stickyActive = true;
            this.laserActive = false;
            setTimeout(() => { if (this.isPlaying) this.stickyActive = false; }, 15000);
        } else if (p.type === 'LASER') {
            this.laserActive = true;
            this.stickyActive = false;
            setTimeout(() => { if (this.isPlaying) this.laserActive = false; }, 15000);
        } else if (p.type === 'MULTI') {
            this.splitBalls();
        } else if (p.type === 'PIERCE') {
            this.pierceActive = true;
            setTimeout(() => { if (this.isPlaying) this.pierceActive = false; }, 10000);
        } else if (p.type === 'SHIELD') {
            this.shieldActive = true;
        } else if (p.type === 'MEGA') {
            for (let b of this.balls) b.radius = 16;
            setTimeout(() => { if (this.isPlaying) for (let b of this.balls) b.radius = 8; }, 12000);
        } else if (p.type === 'FIRE') {
            this.fireActive = true;
            setTimeout(() => { if (this.isPlaying) this.fireActive = false; }, 10000);
        } else if (p.type === 'SPEED') {
            this.speedMultiplier = 2;
            for (let b of this.balls) { b.dx *= 1.5; b.dy *= 1.5; }
            setTimeout(() => {
                if (this.isPlaying) {
                    this.speedMultiplier = 1;
                    for (let b of this.balls) { b.dx /= 1.5; b.dy /= 1.5; }
                }
            }, 8000);
        }
    }

    splitBalls() {
        const newBalls = [];
        for (let b of this.balls) {
            // Ball 2
            newBalls.push({ ...b, dx: b.dx * Math.cos(0.2) - b.dy * Math.sin(0.2), dy: b.dx * Math.sin(0.2) + b.dy * Math.cos(0.2) });
            // Ball 3
            newBalls.push({ ...b, dx: b.dx * Math.cos(-0.2) - b.dy * Math.sin(-0.2), dy: b.dx * Math.sin(-0.2) + b.dy * Math.cos(-0.2) });
        }
        this.balls.push(...newBalls);
    }

    explode(bx, by) {
        // Find adjacent bricks
        for (let c = 0; c < this.brickCols; c++) {
            for (let r = 0; r < this.bricks[c].length; r++) {
                let b = this.bricks[c][r];
                if (b.status === 1) {
                    const dx = b.x + this.brickWidth / 2 - bx;
                    const dy = b.y + this.brickHeight / 2 - by;
                    const dist = Math.sqrt(dx * dx + dy * dy);
                    if (dist < 80) { // Explosion radius
                        b.status = 0;
                        this.score += 10 * this.level * this.speedMultiplier;
                        if (this.scoreElement) this.scoreElement.textContent = this.score;
                    }
                }
            }
        }
    }

    fireLaser() {
        window.konamiSound?.play('hit');
        this.bullets.push({ x: this.paddle.x + 10, y: this.paddle.y, width: 4, height: 10 });
        this.bullets.push({ x: this.paddle.x + this.paddle.width - 14, y: this.paddle.y, width: 4, height: 10 });
    }

    update() {
        if (!this.isPlaying) return;

        // Paddle movement
        if (this.keys.ArrowLeft && this.paddle.x > 0) this.paddle.x -= this.paddle.speed;
        if (this.keys.ArrowRight && this.paddle.x < this.canvas.width - this.paddle.width) this.paddle.x += this.paddle.speed;

        if (this.waitReady) {
            if (this.balls.length > 0) {
                this.balls[0].x = this.paddle.x + this.paddle.width / 2;
                this.balls[0].y = this.paddle.y - this.balls[0].radius;
            }
            return;
        }

        // Bullets update
        for (let i = this.bullets.length - 1; i >= 0; i--) {
            let b = this.bullets[i];
            b.y -= 7;
            if (b.y < 0) { this.bullets.splice(i, 1); continue; }
            let hit = false;
            for (let rc = 0; rc < this.brickCols; rc++) {
                for (let rr = 0; rr < this.bricks[rc].length; rr++) {
                    let br = this.bricks[rc][rr];
                    if (br.status === 1 && b.x < br.x + this.brickWidth && b.x + b.width > br.x &&
                        b.y < br.y + this.brickHeight && b.y + b.height > br.y) {
                        br.status = 0;
                        this.score += 10 * this.level * this.speedMultiplier;
                        if (this.scoreElement) this.scoreElement.textContent = this.score;
                        window.konamiSound?.play('hit');
                        this.spawnPowerup(br.x, br.y);
                        hit = true; break;
                    }
                }
                if (hit) break;
            }
            if (hit) this.bullets.splice(i, 1);
        }

        // Powerups update
        for (let i = this.powerups.length - 1; i >= 0; i--) {
            let p = this.powerups[i]; p.y += 3;
            if (p.y > this.canvas.height) { this.powerups.splice(i, 1); continue; }
            if (p.x + p.width > this.paddle.x && p.x < this.paddle.x + this.paddle.width &&
                p.y + p.height > this.paddle.y && p.y < this.paddle.y + this.paddle.height) {
                this.activatePowerup(p);
                this.powerups.splice(i, 1);
            }
        }

        // Balls update
        for (let i = this.balls.length - 1; i >= 0; i--) {
            let b = this.balls[i];
            b.x += b.dx;
            b.y += b.dy;

            // Wall bounces
            if (b.x - b.radius <= 0) { b.x = b.radius; b.dx = Math.abs(b.dx); window.konamiSound?.play('bounce'); }
            else if (b.x + b.radius >= this.canvas.width) { b.x = this.canvas.width - b.radius; b.dx = -Math.abs(b.dx); window.konamiSound?.play('bounce'); }
            if (b.y - b.radius <= 0) { b.y = b.radius; b.dy = Math.abs(b.dy); window.konamiSound?.play('bounce'); }

            // Shield bounce
            if (this.shieldActive && b.y + b.radius >= this.canvas.height - 5) {
                b.y = this.canvas.height - 5 - b.radius;
                b.dy = -Math.abs(b.dy);
                this.shieldActive = false; // Shield is one-time use or until next level? Let's say one hit
                window.konamiSound?.play('bounce');
            }

            // Paddle collision
            if (b.dy > 0 && b.y + b.radius >= this.paddle.y && b.y - b.radius < this.paddle.y + this.paddle.height &&
                b.x + b.radius > this.paddle.x && b.x - b.radius < this.paddle.x + this.paddle.width) {
                if (this.stickyActive) {
                    this.waitReady = true; this.stickyWait = true;
                    b.y = this.paddle.y - b.radius;
                } else {
                    b.y = this.paddle.y - b.radius;
                    const hitPos = (b.x - this.paddle.x) / this.paddle.width;
                    const angle = (hitPos - 0.5) * Math.PI * 0.7;
                    const speed = Math.sqrt(b.dx * b.dx + b.dy * b.dy);
                    b.dx = speed * Math.sin(angle); b.dy = -speed * Math.cos(angle);
                }
                window.konamiSound?.play('bounce');
            }

            // Brick collision
            for (let c = 0; c < this.brickCols; c++) {
                for (let r = 0; r < this.bricks[c].length; r++) {
                    let br = this.bricks[c][r];
                    if (br.status === 1) {
                        const closestX = Math.max(br.x, Math.min(b.x, br.x + this.brickWidth));
                        const closestY = Math.max(br.y, Math.min(b.y, br.y + this.brickHeight));
                        const distX = b.x - closestX;
                        const distY = b.y - closestY;
                        if (distX * distX + distY * distY <= b.radius * b.radius) {
                            if (!this.pierceActive) {
                                const ol = (b.x + b.radius) - br.x;
                                const or_ = (br.x + this.brickWidth) - (b.x - b.radius);
                                const ot = (b.y + b.radius) - br.y;
                                const ob = (br.y + this.brickHeight) - (b.y - b.radius);
                                if (Math.min(ol, or_) < Math.min(ot, ob)) b.dx = -b.dx;
                                else b.dy = -b.dy;
                            }
                            br.status = 0;
                            this.score += 10 * this.level * this.speedMultiplier;
                            if (this.scoreElement) this.scoreElement.textContent = this.score;
                            window.konamiSound?.play('hit');
                            this.spawnPowerup(br.x, br.y);
                            if (this.fireActive) this.explode(br.x + this.brickWidth / 2, br.y + this.brickHeight / 2);
                        }
                    }
                }
            }

            // Lose ball
            if (b.y - b.radius > this.canvas.height) {
                this.balls.splice(i, 1);
            }
        }

        if (this.balls.length === 0) {
            this.loseLife();
            return;
        }

        // Win check
        let totalActive = 0;
        for (let c = 0; c < this.brickCols; c++) {
            for (let r = 0; r < this.bricks[c].length; r++) {
                if (this.bricks[c][r].status === 1) totalActive++;
            }
        }
        if (totalActive === 0 && this.isPlaying) this.nextLevel();
    }

    draw() {
        const ctx = this.ctx;

        // Dynamic background based on level
        const bgColors = ['#0f0f19', '#1a0f1a', '#0f1a1a', '#1a1a0f', '#0a0a14'];
        ctx.fillStyle = bgColors[(this.level - 1) % bgColors.length];
        ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

        // Bricks
        const glowIntensity = 4 + (this.level % 5);
        for (let c = 0; c < this.brickCols; c++) {
            for (let r = 0; r < this.bricks[c].length; r++) {
                if (this.bricks[c][r].status === 1) {
                    let bx = c * (this.brickWidth + this.brickPadding) + this.brickOffsetLeft;
                    let by = r * (this.brickHeight + this.brickPadding) + this.brickOffsetTop;
                    this.bricks[c][r].x = bx; this.bricks[c][r].y = by;
                    ctx.fillStyle = this.bricks[c][r].color;
                    ctx.shadowColor = this.bricks[c][r].color;
                    ctx.shadowBlur = glowIntensity;
                    ctx.fillRect(bx, by, this.brickWidth, this.brickHeight);
                    ctx.shadowBlur = 0;
                }
            }
        }

        // Powerups draw
        for (let p of this.powerups) {
            ctx.fillStyle = p.color; ctx.shadowColor = p.color; ctx.shadowBlur = 10;
            ctx.fillRect(p.x, p.y, p.width, p.height);
            ctx.fillStyle = '#fff'; ctx.font = '16px serif'; ctx.textAlign = 'center';
            ctx.fillText(p.label, p.x + p.width / 2, p.y + p.height - 6);
            ctx.shadowBlur = 0;
        }

        // Bullets
        ctx.fillStyle = '#ff0000';
        for (let b of this.bullets) { ctx.fillRect(b.x, b.y, b.width, b.height); }

        // Shield
        if (this.shieldActive) {
            ctx.fillStyle = '#777'; ctx.shadowColor = '#fff'; ctx.shadowBlur = 10;
            ctx.fillRect(0, this.canvas.height - 5, this.canvas.width, 5);
            ctx.shadowBlur = 0;
        }

        // Paddle
        ctx.fillStyle = this.paddle.color; ctx.shadowColor = this.paddle.color; ctx.shadowBlur = 12;
        ctx.fillRect(this.paddle.x, this.paddle.y, this.paddle.width, this.paddle.height);

        // Sticky/Pierce/Fire indicators on paddle
        if (this.stickyActive) {
            ctx.strokeStyle = '#00ffff'; ctx.lineWidth = 2;
            ctx.strokeRect(this.paddle.x - 2, this.paddle.y - 2, this.paddle.width + 4, this.paddle.height + 4);
        }
        if (this.pierceActive) { ctx.fillStyle = '#00ffff'; ctx.fillRect(this.paddle.x, this.paddle.y + this.paddle.height - 2, this.paddle.width, 2); }
        if (this.fireActive) { ctx.fillStyle = '#ffcc00'; ctx.fillRect(this.paddle.x, this.paddle.y, 10, 2); ctx.fillRect(this.paddle.x + this.paddle.width - 10, this.paddle.y, 10, 2); }
        ctx.shadowBlur = 0;

        // Balls
        for (let b of this.balls) {
            ctx.beginPath(); ctx.arc(b.x, b.y, b.radius, 0, Math.PI * 2);
            ctx.fillStyle = this.pierceActive ? '#00ffff' : b.color;
            ctx.shadowColor = b.color; ctx.shadowBlur = b.radius;
            ctx.fill(); ctx.closePath();
        }
        ctx.shadowBlur = 0;

        // HUD
        ctx.fillStyle = '#00f3ff'; ctx.font = 'bold 14px Courier New'; ctx.textAlign = 'right';
        ctx.fillText(`NIVEAU ${this.level} x${this.speedMultiplier}`, this.canvas.width - 15, 25);
        ctx.textAlign = 'left'; ctx.fillStyle = '#ff00ff'; ctx.font = 'bold 16px Courier New';
        ctx.fillText('❤️'.repeat(this.lives), 15, 30);

        // Intermission
        let totalActiveInDraw = 0;
        for (let c = 0; c < this.brickCols; c++) {
            for (let r = 0; r < this.bricks[c].length; r++) {
                if (this.bricks[c][r].status === 1) totalActiveInDraw++;
            }
        }

        if (this.waitReady && this.isPlaying && !this.stickyWait) {
            ctx.fillStyle = 'rgba(0,0,0,0.8)';
            ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
            ctx.textAlign = 'center';

            if (this.level > 1 && totalActiveInDraw === 0) {
                ctx.fillStyle = '#00f3ff';
                ctx.font = 'bold 28px Courier New';
                ctx.fillText(`FIREWALL NIVEAU ${this.level - 1} DÉTRUIT`, this.canvas.width / 2, this.canvas.height / 2 - 40);
            }

            ctx.fillStyle = '#00f3ff';
            ctx.font = 'bold 32px Courier New';
            ctx.fillText(`PRÊT POUR LE NIVEAU ${this.level} ?`, this.canvas.width / 2, this.canvas.height / 2 + 10);

            ctx.fillStyle = '#fff';
            ctx.font = '18px Courier New';
            ctx.fillText('APPUYEZ SUR ESPACE POUR LANCER LE PING', this.canvas.width / 2, this.canvas.height / 2 + 60);
            ctx.textAlign = 'left';
        }
    }

    drawInitialScreen() {
        this.ctx.fillStyle = '#0f0f19';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
        this.ctx.fillStyle = '#00f3ff';
        this.ctx.font = '40px Courier New';
        this.ctx.textAlign = 'center';
        this.ctx.fillText('BREAKOUT NETWORK', this.canvas.width / 2, this.canvas.height / 2 - 20);
        this.ctx.fillStyle = '#fff';
        this.ctx.font = '20px Courier New';
        this.ctx.fillText('ESPACE pour commencer', this.canvas.width / 2, this.canvas.height / 2 + 30);
        this.ctx.textAlign = 'left';
    }

    loop() {
        if (!this.isPlaying && !this.isGameOver) { this.drawInitialScreen(); return; }
        if (this.isPlaying) {
            this.update();
            this.draw();
            this.animationId = requestAnimationFrame(this.loop);
        }
    }
}
