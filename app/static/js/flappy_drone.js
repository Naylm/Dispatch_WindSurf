/**
 * static/js/flappy_drone.js
 * A simple Flappy Bird clone with an IT/synthwave aesthetic.
 */

class FlappyDrone {
    constructor() {
        this.container = document.getElementById('flappyGameContainer');
        this.canvas = document.getElementById('flappyCanvas');
        this.ctx = this.canvas.getContext('2d');

        // Game states
        this.isPlaying = false;
        this.isGameOver = false;
        this.score = 0;
        this.highScore = parseInt(localStorage.getItem('flappyHighScore')) || 0;

        // Settings
        this.gravity = 0.5;
        this.jumpForce = -8;
        this.pipeSpeed = 4;
        this.pipeWidth = 60;
        this.pipeGap = 160;
        this.level = 1;

        // Drone object
        this.drone = {
            x: 100,
            y: this.canvas.height / 2,
            width: 40,
            height: 30,
            velocity: 0,
            color: '#00f3ff'
        };

        this.pipes = [];
        this.frameCount = 0;
        this.animationId = null;

        // Binds
        this.handleInput = this.handleInput.bind(this);
        this.loop = this.loop.bind(this);

        this.init();
    }

    init() {
        this.resize();
        window.addEventListener('resize', () => this.resize());

        document.addEventListener('keydown', this.handleInput);
        document.addEventListener('touchstart', this.handleInput, { passive: false });
        this.canvas.addEventListener('mousedown', this.handleInput);

        // Bind restart button
        document.getElementById('restartFlappyBtn')?.addEventListener('click', () => {
            const overlay = document.getElementById('flappyGameOver');
            if (overlay) overlay.style.display = 'none';
            this.reset();
            this.start();
        });

        this.reset();
        this.drawInitialScreen();
    }

    resize() {
        this.canvas.width = Math.min(window.innerWidth - 40, 800);
        this.canvas.height = Math.min(window.innerHeight - 150, 600);
    }

    reset() {
        this.drone.y = this.canvas.height / 2;
        this.drone.velocity = 0;
        this.pipes = [];
        this.score = 0;
        this.level = 1;
        this.pipeSpeed = 4;
        this.pipeGap = 160;
        this.frameCount = 0;
        this.isGameOver = false;
        this.isPlaying = false;
        const overlay = document.getElementById('flappyGameOver');
        if (overlay) overlay.style.display = 'none';
    }

    handleInput(e) {
        if (!this.container || !this.container.offsetParent) return; // not visible

        if (e.type === 'touchstart') e.preventDefault();

        // Prevent accidental space restart
        if (this.isGameOver) return;

        if (e.code === 'Space' || e.type === 'mousedown' || e.type === 'touchstart') {
            if (!this.isPlaying) {
                this.start();
                this.jump();
            } else {
                this.jump();
            }
        }
    }

    jump() {
        this.drone.velocity = this.jumpForce;
        window.konamiSound?.play('jump');
    }

    start() {
        this.isPlaying = true;
        this.isGameOver = false;
        const overlay = document.getElementById('flappyGameOver');
        if (overlay) overlay.style.display = 'none';
        if (this.animationId) cancelAnimationFrame(this.animationId);
        this.loop();
    }

    stop() {
        this.isPlaying = false;
        if (this.animationId) cancelAnimationFrame(this.animationId);
    }

    async gameOver() {
        this.isGameOver = true;
        this.isPlaying = false;
        window.konamiSound?.play('die');

        if (this.score > this.highScore) {
            this.highScore = this.score;
            localStorage.setItem('flappyHighScore', this.highScore);
        }

        const overlay = document.getElementById('flappyGameOver');
        if (overlay) {
            overlay.querySelector('h2').textContent = `CRASHED — Nv.${this.level}`;
            overlay.style.display = 'flex';
        }

        await window.arcadeLeaderboard?.submitScore('flappy', this.score, this.level);
        window.arcadeLeaderboard?.loadLeaderboard('flappy', 'flappyLeaderboard');
    }

    update() {
        if (!this.isPlaying) return;

        // Physics
        this.drone.velocity += this.gravity;
        this.drone.y += this.drone.velocity;

        // Ground / Ceiling collision
        if (this.drone.y + this.drone.height > this.canvas.height) {
            this.gameOver();
        }
        if (this.drone.y < 0) {
            this.drone.y = 0;
            this.drone.velocity = 0;
        }

        // Generate Pipes
        if (this.frameCount % 90 === 0) {
            let spaceLeft = this.canvas.height - this.pipeGap;
            let topPipeHeight = Math.max(50, Math.random() * (spaceLeft - 50));

            this.pipes.push({
                x: this.canvas.width,
                topHeight: topPipeHeight,
                bottomY: topPipeHeight + this.pipeGap,
                passed: false
            });
        }

        // Move Pipes & Check Collisions
        for (let i = 0; i < this.pipes.length; i++) {
            let p = this.pipes[i];
            p.x -= this.pipeSpeed;

            // Collision
            // Top pipe
            if (this.drone.x < p.x + this.pipeWidth &&
                this.drone.x + this.drone.width > p.x &&
                this.drone.y < p.topHeight) {
                this.gameOver();
            }
            // Bottom pipe
            if (this.drone.x < p.x + this.pipeWidth &&
                this.drone.x + this.drone.width > p.x &&
                this.drone.y + this.drone.height > p.bottomY) {
                this.gameOver();
            }

            // Score check
            if (p.x + this.pipeWidth < this.drone.x && !p.passed) {
                this.score++;
                p.passed = true;
                // Level up every 5 passed pipes
                const newLevel = Math.floor(this.score / 5) + 1;
                if (newLevel > this.level) {
                    this.level = newLevel;
                    this.pipeSpeed = Math.min(10, 4 + (this.level - 1) * 0.5);
                    this.pipeGap = Math.max(100, 160 - (this.level - 1) * 8);
                    window.konamiSound?.play('levelup');
                } else {
                    window.konamiSound?.play('eat');
                }
            }
        }

        // Filter offscreen pipes
        this.pipes = this.pipes.filter(p => p.x + this.pipeWidth > 0);
        this.frameCount++;
    }

    draw() {
        const ctx = this.ctx;
        const w = this.canvas.width;
        const h = this.canvas.height;

        // Background
        ctx.fillStyle = '#0a0a14';
        ctx.fillRect(0, 0, w, h);

        // Starfield
        ctx.fillStyle = 'rgba(255, 255, 255, 0.3)';
        for (let i = 0; i < 30; i++) {
            const sx = ((i * 137) % w + this.frameCount * 0.3 * ((i % 3) + 1)) % w;
            const sy = (i * 97) % h;
            ctx.fillRect(w - sx, sy, 1.5, 1.5);
        }

        // Scanlines
        ctx.strokeStyle = 'rgba(255, 0, 255, 0.05)';
        ctx.lineWidth = 1;
        for (let i = 0; i < w; i += 40) {
            ctx.beginPath();
            ctx.moveTo(i - (this.frameCount % 40), 0);
            ctx.lineTo(i - (this.frameCount % 40), h);
            ctx.stroke();
        }

        // ===== PIPES (Server Racks) =====
        for (let p of this.pipes) {
            // Top pipe body
            ctx.fillStyle = '#1a1a2e';
            ctx.fillRect(p.x, 0, this.pipeWidth, p.topHeight);
            ctx.strokeStyle = '#ff00ff';
            ctx.lineWidth = 2;
            ctx.strokeRect(p.x, 0, this.pipeWidth, p.topHeight);
            // Top pipe LEDs
            for (let ly = p.topHeight - 15; ly > 5; ly -= 18) {
                ctx.fillStyle = Math.random() > 0.2 ? '#00ff00' : '#ff0000';
                ctx.fillRect(p.x + 8, ly, 5, 5);
                ctx.fillStyle = '#333';
                ctx.fillRect(p.x + 18, ly + 1, this.pipeWidth - 30, 3);
            }
            // Top pipe neon cap
            ctx.fillStyle = '#ff00ff';
            ctx.shadowColor = '#ff00ff';
            ctx.shadowBlur = 12;
            ctx.fillRect(p.x - 5, p.topHeight - 5, this.pipeWidth + 10, 8);
            ctx.shadowBlur = 0;

            // Bottom pipe body
            ctx.fillStyle = '#1a1a2e';
            ctx.fillRect(p.x, p.bottomY, this.pipeWidth, h - p.bottomY);
            ctx.strokeStyle = '#ff00ff';
            ctx.strokeRect(p.x, p.bottomY, this.pipeWidth, h - p.bottomY);
            // Bottom pipe LEDs
            for (let ly = p.bottomY + 10; ly < h - 10; ly += 18) {
                ctx.fillStyle = Math.random() > 0.2 ? '#00ff00' : '#ff0000';
                ctx.fillRect(p.x + 8, ly, 5, 5);
                ctx.fillStyle = '#333';
                ctx.fillRect(p.x + 18, ly + 1, this.pipeWidth - 30, 3);
            }
            // Bottom pipe neon cap
            ctx.fillStyle = '#ff00ff';
            ctx.shadowColor = '#ff00ff';
            ctx.shadowBlur = 12;
            ctx.fillRect(p.x - 5, p.bottomY - 3, this.pipeWidth + 10, 8);
            ctx.shadowBlur = 0;
        }

        // ===== DRONE =====
        const d = this.drone;
        const cx = d.x + d.width / 2;
        const cy = d.y + d.height / 2;
        const tilt = Math.min(8, d.velocity * 1.5);

        ctx.save();
        ctx.translate(cx, cy);
        ctx.rotate(tilt * Math.PI / 180);

        // Thruster glow
        ctx.fillStyle = 'rgba(0, 243, 255, 0.15)';
        ctx.beginPath();
        ctx.arc(0, d.height / 2 + 5, 15 + Math.sin(this.frameCount * 0.3) * 3, 0, Math.PI * 2);
        ctx.fill();

        // Body (rounded rectangle)
        ctx.fillStyle = '#1a1a2e';
        ctx.shadowColor = d.color;
        ctx.shadowBlur = 15;
        const bw = d.width, bh = d.height * 0.6;
        ctx.beginPath();
        ctx.roundRect(-bw / 2, -bh / 2, bw, bh, 6);
        ctx.fill();

        // Body accent line
        ctx.strokeStyle = d.color;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.roundRect(-bw / 2, -bh / 2, bw, bh, 6);
        ctx.stroke();
        ctx.shadowBlur = 0;

        // Eye / lens
        ctx.fillStyle = d.color;
        ctx.shadowColor = d.color;
        ctx.shadowBlur = 8;
        ctx.beginPath();
        ctx.arc(bw / 4, 0, 5, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = '#fff';
        ctx.beginPath();
        ctx.arc(bw / 4 + 1.5, -1.5, 2, 0, Math.PI * 2);
        ctx.fill();
        ctx.shadowBlur = 0;

        // Rotor arms
        ctx.strokeStyle = '#555';
        ctx.lineWidth = 3;
        ctx.beginPath(); ctx.moveTo(-bw / 2, -bh / 2); ctx.lineTo(-bw / 2 - 10, -bh / 2 - 12); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(bw / 2, -bh / 2); ctx.lineTo(bw / 2 + 10, -bh / 2 - 12); ctx.stroke();

        // Spinning rotors
        const rotorPhase = this.frameCount * 0.4;
        ctx.strokeStyle = 'rgba(0, 243, 255, 0.6)';
        ctx.lineWidth = 2;
        const rw = Math.cos(rotorPhase) * 14;
        // Left rotor
        ctx.beginPath(); ctx.moveTo(-bw / 2 - 10 - rw, -bh / 2 - 12); ctx.lineTo(-bw / 2 - 10 + rw, -bh / 2 - 12); ctx.stroke();
        // Right rotor
        const rw2 = Math.cos(rotorPhase + 1) * 14;
        ctx.beginPath(); ctx.moveTo(bw / 2 + 10 - rw2, -bh / 2 - 12); ctx.lineTo(bw / 2 + 10 + rw2, -bh / 2 - 12); ctx.stroke();

        // Antenna
        ctx.strokeStyle = '#888';
        ctx.lineWidth = 1;
        ctx.beginPath(); ctx.moveTo(-5, -bh / 2); ctx.lineTo(-5, -bh / 2 - 8); ctx.stroke();
        ctx.fillStyle = '#ff0000';
        ctx.fillRect(-6.5, -bh / 2 - 10, 3, 3);

        ctx.restore();

        // ===== HUD =====
        ctx.fillStyle = '#fff';
        ctx.font = '20px Courier New';
        ctx.textAlign = 'left';
        ctx.fillText(`Score: ${this.score}`, 15, 30);
        ctx.fillText(`Record: ${this.highScore}`, 15, 55);

        if (this.isGameOver) {
            ctx.fillStyle = 'rgba(0,0,0,0.75)';
            ctx.fillRect(0, 0, w, h);

            ctx.fillStyle = '#ff00ff';
            ctx.font = '36px Courier New';
            ctx.textAlign = 'center';
            ctx.fillText(`CRASHED — Nv.${this.level}`, w / 2, h / 2 - 20);
            ctx.textAlign = 'left';
        } else {
            ctx.fillStyle = '#00f3ff';
            ctx.font = '14px Courier New';
            ctx.textAlign = 'right';
            ctx.fillText(`NIVEAU ${this.level}`, w - 15, 30);
            ctx.textAlign = 'left';
        }
    }

    drawInitialScreen() {
        this.ctx.fillStyle = '#0f0f19';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

        this.ctx.fillStyle = '#00f3ff';
        this.ctx.font = '40px Courier New';
        this.ctx.textAlign = 'center';
        this.ctx.fillText('FLAPPY DRONE', this.canvas.width / 2, this.canvas.height / 2 - 20);

        this.ctx.fillStyle = '#fff';
        this.ctx.font = '20px Courier New';
        this.ctx.fillText('Tap or Space to Start', this.canvas.width / 2, this.canvas.height / 2 + 30);
        this.ctx.textAlign = 'left';
    }

    loop() {
        if (!this.isPlaying && !this.isGameOver) return;
        this.update();
        this.draw();

        if (!this.isGameOver) {
            this.animationId = requestAnimationFrame(this.loop);
        }
    }

}
