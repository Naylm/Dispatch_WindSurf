/**
 * static/js/ticket_invaders.js
 * Space Invaders clone – IT/synthwave aesthetic.
 * Features: varied enemy types per level, formations, boss waves, global sound, server leaderboard.
 */

class TicketInvaders {
    constructor() {
        this.container = document.getElementById('invadersGameContainer');
        this.canvas = document.getElementById('invadersCanvas');
        this.ctx = this.canvas.getContext('2d');
        this.scoreElement = document.getElementById('invadersScore');
        this.highScoreElement = document.getElementById('invadersHighScore');
        this.gameOverOverlay = document.getElementById('invadersGameOver');

        this.isPlaying = false;
        this.isGameOver = false;
        this.score = 0;
        this.level = 1;
        this.highScore = parseInt(localStorage.getItem('invadersHighScore')) || 0;
        this.animationId = null;
        this.waitReady = false;
        this.keys = { ArrowLeft: false, ArrowRight: false, Space: false };

        this.player = { width: 50, height: 30, x: 0, y: 0, speed: 6, color: '#00f3ff', cooldown: 0, lives: 3 };
        this.bullets = [];
        this.enemyBullets = [];
        this.enemies = [];
        this.powerups = [];
        this.enemyDirection = 1;
        this.moveInterval = 60;
        this.frameCount = 0;

        // Visual FX
        this.particles = [];
        this.stars = [];
        this.screenShake = 0;
        this.initStarfield();

        // Weapon system
        this.weapon = 'basic';  // basic, spread, rapid, laser
        this.weaponTimer = 0;
        this.shieldActive = false;
        this.shieldTimer = 0;

        // Weapon definitions
        this.weaponDefs = {
            basic: { label: 'PATCH', color: '#fff', cooldown: 15, bulletSpeed: 8, spread: 0 },
            spread: { label: 'SPREAD', color: '#00ff00', cooldown: 15, bulletSpeed: 7, spread: 3 },
            rapid: { label: 'RAPID', color: '#ffff00', cooldown: 5, bulletSpeed: 10, spread: 0 },
            laser: { label: 'LASER', color: '#ff0000', cooldown: 2, bulletSpeed: 15, spread: 0, width: 6, height: 25 },
        };

        // Powerup types that can drop
        this.powerupTypes = [
            { type: 'spread', label: '⊕ SPREAD', color: '#00ff00' },
            { type: 'rapid', label: '⚡ RAPID', color: '#ffff00' },
            { type: 'laser', label: '🔴 LASER', color: '#ff0000' },
            { type: 'shield', label: '🛡️ SHIELD', color: '#00f3ff' },
            { type: 'life', label: '❤️ +1 VIE', color: '#ff00ff' },
        ];

        // Enemy type definitions (Redesigned for vector aesthetic)
        this.enemyTypes = {
            ticket: { hp: 1, points: 10, color: '#ffff00', width: 35, height: 25, shootChance: 0.02, bulletSpeed: 3 },
            bug: { hp: 2, points: 20, color: '#ff9900', width: 40, height: 25, shootChance: 0.03, bulletSpeed: 4 },
            virus: { hp: 3, points: 30, color: '#00f3ff', width: 45, height: 30, shootChance: 0.04, bulletSpeed: 5 },
            trojan: { hp: 2, points: 25, color: '#ff00ff', width: 40, height: 25, shootChance: 0.05, bulletSpeed: 4, zigzag: true },
            firewall: { hp: 8, points: 100, color: '#ff3333', width: 70, height: 50, shootChance: 0.08, bulletSpeed: 6, isBoss: true },
            ddos: { hp: 1, points: 5, color: '#ffffff', width: 25, height: 15, shootChance: 0.01, bulletSpeed: 4, fast: true },
            ransom: { hp: 4, points: 40, color: '#9900ff', width: 50, height: 30, shootChance: 0.04, bulletSpeed: 5, shield: true },
        };

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
        document.getElementById('restartInvadersBtn')?.addEventListener('click', () => {
            if (this.gameOverOverlay) this.gameOverOverlay.style.display = 'none';
            this.fullReset();
            this.start();
        });
        this.fullReset();
        this.drawInitialScreen();
    }

    resize() {
        this.canvas.width = Math.min(window.innerWidth - 40, 800);
        this.canvas.height = Math.min(window.innerHeight - 150, 600);
        this.player.y = this.canvas.height - 50;
    }

    fullReset() {
        this.score = 0;
        this.level = 1;
        this.player.lives = 3;
        this.moveInterval = 60;
        this.weapon = 'basic';
        this.weaponTimer = 0;
        this.shieldActive = false;
        this.shieldTimer = 0;
        this.particles = [];
        this.reset();
    }

    reset() {
        this.player.x = this.canvas.width / 2 - this.player.width / 2;
        this.bullets = [];
        this.enemyBullets = [];
        this.powerups = [];
        if (this.scoreElement) this.scoreElement.textContent = this.score;
        this.frameCount = 0;
        this.isGameOver = false;
        this.isPlaying = false;
        this.enemyDirection = 1;
        this.createWave();
    }

    // Level design — each level has a different wave composition
    getLevelConfig() {
        const configs = [
            // Level 1: Simple tickets
            { rows: [['ticket', 'ticket', 'ticket', 'ticket', 'ticket', 'ticket']] },
            // Level 2: Tickets + bugs
            { rows: [['bug', 'bug', 'bug', 'bug', 'bug'], ['ticket', 'ticket', 'ticket', 'ticket', 'ticket', 'ticket']] },
            // Level 3: Mixed with virus
            { rows: [['virus', 'virus', 'virus', 'virus'], ['bug', 'bug', 'bug', 'bug', 'bug'], ['ticket', 'ticket', 'ticket', 'ticket', 'ticket', 'ticket']] },
            // Level 4: Trojans (zigzag movement)
            { rows: [['trojan', 'trojan', 'trojan', 'trojan', 'trojan'], ['bug', 'bug', 'bug', 'bug', 'bug'], ['ticket', 'ticket', 'ticket', 'ticket', 'ticket', 'ticket', 'ticket']] },
            // Level 5: BOSS WAVE — Firewall + minions
            { rows: [['firewall', 'firewall'], ['virus', 'virus', 'virus', 'virus', 'virus'], ['trojan', 'trojan', 'trojan', 'trojan']], boss: true },
            // Level 6: DDoS swarm
            { rows: [['ddos', 'ddos', 'ddos', 'ddos', 'ddos', 'ddos', 'ddos', 'ddos'], ['ddos', 'ddos', 'ddos', 'ddos', 'ddos', 'ddos', 'ddos', 'ddos'], ['bug', 'bug', 'bug', 'bug', 'bug']] },
            // Level 7: Ransomware (shielded)
            { rows: [['ransom', 'ransom', 'ransom', 'ransom'], ['virus', 'virus', 'virus', 'virus', 'virus'], ['trojan', 'trojan', 'trojan', 'trojan', 'trojan']] },
            // Level 8: Full assault
            { rows: [['firewall', 'ransom', 'firewall'], ['trojan', 'virus', 'trojan', 'virus', 'trojan'], ['ddos', 'ddos', 'ddos', 'ddos', 'ddos', 'ddos', 'ddos', 'ddos'], ['bug', 'bug', 'bug', 'bug', 'bug', 'bug']], boss: true },
        ];

        // Loop levels after 8 with scaling
        const idx = ((this.level - 1) % configs.length);
        const config = JSON.parse(JSON.stringify(configs[idx])); // deep clone
        return config;
    }

    createWave() {
        this.enemies = [];
        const config = this.getLevelConfig();
        const pad = 15;

        for (let r = 0; r < config.rows.length; r++) {
            const row = config.rows[r];
            const totalW = row.reduce((sum, t) => sum + this.enemyTypes[t].width + pad, -pad);
            const startX = Math.max(20, (this.canvas.width - totalW) / 2);
            let cx = startX;

            for (let c = 0; c < row.length; c++) {
                const typeName = row[c];
                const type = this.enemyTypes[typeName];
                this.enemies.push({
                    x: cx, y: 40 + r * (type.height + pad),
                    width: type.width, height: type.height,
                    typeName, hp: type.hp + Math.floor((this.level - 1) / 8), // Scale HP on loop
                    maxHp: type.hp + Math.floor((this.level - 1) / 8),
                    alive: true, phase: Math.random() * Math.PI * 2
                });
                cx += type.width + pad;
            }
        }
    }

    handleKeyDown(e) {
        if (!this.container || !this.container.offsetParent) return;
        if (e.code === 'ArrowLeft') this.keys.ArrowLeft = true;
        if (e.code === 'ArrowRight') this.keys.ArrowRight = true;
        if (e.code === 'Space' || e.code === 'Enter') {
            this.keys.Space = true;
            if (!this.isPlaying && !this.isGameOver) this.start();
            if (this.waitReady) {
                this.waitReady = false;
                this.reset();
                this.isPlaying = true;
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
            localStorage.setItem('invadersHighScore', this.highScore);
            if (this.highScoreElement) this.highScoreElement.textContent = this.highScore;
        }
        if (this.gameOverOverlay) {
            this.gameOverOverlay.querySelector('h2').textContent = `GAME OVER — Niveau ${this.level}`;
            this.gameOverOverlay.style.display = 'flex';
        }
        // Server leaderboard
        await window.arcadeLeaderboard?.submitScore('invaders', this.score, this.level);
        window.arcadeLeaderboard?.loadLeaderboard('invaders', 'invadersLeaderboard');
    }

    nextLevel() {
        this.level++;
        this.moveInterval = Math.max(15, 60 - this.level * 3);
        window.konamiSound?.play('levelup');
        this.waitReady = true;
        this.spawnPowerup(this.canvas.width / 2, 0); // Bonus powerup on level clear
    }

    initStarfield() {
        this.stars = [];
        for (let i = 0; i < 100; i++) {
            this.stars.push({
                x: Math.random() * 800,
                y: Math.random() * 600,
                size: Math.random() * 2,
                speed: Math.random() * 1 + 0.5,
                opacity: Math.random()
            });
        }
    }

    spawnParticles(x, y, color, count = 8, speed = 4) {
        for (let i = 0; i < count; i++) {
            const angle = Math.random() * Math.PI * 2;
            const s = Math.random() * speed + 1;
            this.particles.push({
                x, y,
                dx: Math.cos(angle) * s,
                dy: Math.sin(angle) * s,
                life: 1.0,
                decay: Math.random() * 0.05 + 0.02,
                size: Math.random() * 3 + 1,
                color
            });
        }
    }

    update() {
        if (!this.isPlaying || this.waitReady) return;
        this.frameCount++;

        // Weapon timer
        if (this.weaponTimer > 0) {
            this.weaponTimer--;
            if (this.weaponTimer <= 0) this.weapon = 'basic';
        }
        if (this.shieldTimer > 0) {
            this.shieldTimer--;
            if (this.shieldTimer <= 0) this.shieldActive = false;
        }

        // Player movement
        if (this.keys.ArrowLeft && this.player.x > 0) this.player.x -= this.player.speed;
        if (this.keys.ArrowRight && this.player.x < this.canvas.width - this.player.width) this.player.x += this.player.speed;

        // Player shooting
        const wep = this.weaponDefs[this.weapon];
        if (this.player.cooldown > 0) this.player.cooldown--;
        if (this.keys.Space && this.player.cooldown === 0) {
            const bw = wep.width || 4;
            const bh = wep.height || 15;
            const cx = this.player.x + this.player.width / 2;

            if (this.weapon === 'spread') {
                // 3 bullets: center + 2 angled
                this.bullets.push({ x: cx - bw / 2, y: this.player.y, width: bw, height: bh, speed: wep.bulletSpeed, dx: 0, color: wep.color });
                this.bullets.push({ x: cx - bw / 2 - 10, y: this.player.y, width: bw, height: bh, speed: wep.bulletSpeed, dx: -2, color: wep.color });
                this.bullets.push({ x: cx - bw / 2 + 10, y: this.player.y, width: bw, height: bh, speed: wep.bulletSpeed, dx: 2, color: wep.color });
            } else {
                this.bullets.push({ x: cx - bw / 2, y: this.player.y, width: bw, height: bh, speed: wep.bulletSpeed, dx: 0, color: wep.color });
            }
            this.player.cooldown = wep.cooldown;
            window.konamiSound?.play('shoot');
        }

        // Update player bullets
        for (let i = this.bullets.length - 1; i >= 0; i--) {
            this.bullets[i].y -= this.bullets[i].speed;
            if (this.bullets[i].dx) this.bullets[i].x += this.bullets[i].dx;
            if (this.bullets[i].y < 0 || this.bullets[i].x < 0 || this.bullets[i].x > this.canvas.width) {
                this.bullets.splice(i, 1);
            }
        }

        // Update powerups
        for (let i = this.powerups.length - 1; i >= 0; i--) {
            let p = this.powerups[i];
            p.y += 2;
            // Player picks up
            if (p.y + 20 > this.player.y && p.y < this.player.y + this.player.height &&
                p.x + 20 > this.player.x && p.x < this.player.x + this.player.width) {
                this.activatePowerup(p);
                this.powerups.splice(i, 1);
                continue;
            }
            if (p.y > this.canvas.height) this.powerups.splice(i, 1);
        }

        // Update enemy bullets
        for (let i = this.enemyBullets.length - 1; i >= 0; i--) {
            let b = this.enemyBullets[i];
            b.y += b.speed;
            if (b.zigzag) b.x += Math.sin(b.y * 0.05) * 2;
            // Hit player
            if (b.y + b.height > this.player.y && b.y < this.player.y + this.player.height &&
                b.x + b.width > this.player.x && b.x < this.player.x + this.player.width) {
                this.screenShake = 15;
                if (this.shieldActive) {
                    this.shieldActive = false;
                    this.shieldTimer = 0;
                    this.enemyBullets.splice(i, 1);
                    this.spawnParticles(b.x, b.y, '#00f3ff');
                    window.konamiSound?.play('bounce');
                    continue;
                }
                this.player.lives--;
                this.spawnParticles(b.x, b.y, '#ff0000', 12, 6);
                this.enemyBullets.splice(i, 1);
                window.konamiSound?.play('hit');
                if (this.player.lives <= 0) { this.gameOver(); return; }
                continue;
            }
            if (b.y > this.canvas.height) this.enemyBullets.splice(i, 1);
        }

        // Starfield update
        for (let s of this.stars) {
            s.y += s.speed;
            if (s.y > this.canvas.height) { s.y = 0; s.x = Math.random() * this.canvas.width; }
        }

        // Particles update
        for (let i = this.particles.length - 1; i >= 0; i--) {
            let p = this.particles[i];
            p.x += p.dx; p.y += p.dy;
            p.life -= p.decay;
            if (p.life <= 0) this.particles.splice(i, 1);
        }

        if (this.screenShake > 0) this.screenShake *= 0.9;
        if (this.screenShake < 0.1) this.screenShake = 0;

        // Alive enemies
        let alive = this.enemies.filter(e => e.alive);
        if (alive.length === 0) { this.nextLevel(); return; }

        // Move enemies
        if (this.frameCount % Math.floor(this.moveInterval) === 0) {
            let r = Math.max(...alive.map(e => e.x + e.width));
            let l = Math.min(...alive.map(e => e.x));
            let moveDown = false;
            if ((r >= this.canvas.width - 15 && this.enemyDirection === 1) || (l <= 15 && this.enemyDirection === -1)) {
                this.enemyDirection *= -1; moveDown = true;
            }
            for (let e of this.enemies) {
                if (!e.alive) continue;
                const type = this.enemyTypes[e.typeName];
                const moveSpeed = type.fast ? 18 : 12;
                if (moveDown) {
                    e.y += type.isBoss ? 10 : 18;
                    if (e.y + e.height >= this.player.y) { this.gameOver(); return; }
                } else {
                    e.x += moveSpeed * this.enemyDirection;
                }
            }

            // Enemy shooting
            for (let e of alive) {
                const type = this.enemyTypes[e.typeName];
                if (Math.random() < type.shootChance * (1 + this.level * 0.1)) {
                    this.enemyBullets.push({
                        x: e.x + e.width / 2 - 2, y: e.y + e.height,
                        width: 4, height: 15,
                        speed: type.bulletSpeed,
                        zigzag: type.zigzag || false
                    });
                }
            }
        }

        // Bullet-enemy collision
        for (let i = this.bullets.length - 1; i >= 0; i--) {
            let b = this.bullets[i]; let hit = false;
            for (let e of this.enemies) {
                if (!e.alive) continue;
                if (b.x < e.x + e.width && b.x + b.width > e.x && b.y < e.y + e.height && b.y + b.height > e.y) {
                    const type = this.enemyTypes[e.typeName];
                    e.hp--;
                    if (e.hp <= 0) {
                        e.alive = false;
                        this.score += type.points * (1 + Math.floor((this.level - 1) / 8));
                        this.spawnParticles(e.x + e.width / 2, e.y + e.height / 2, type.color, 20, 5);
                        this.screenShake = 5;
                        window.konamiSound?.play('kill');
                        if (Math.random() < 0.18) {
                            const pType = this.powerupTypes[Math.floor(Math.random() * this.powerupTypes.length)];
                            this.powerups.push({ x: e.x + e.width / 2 - 10, y: e.y, ...pType });
                        }
                    } else {
                        this.spawnParticles(b.x, b.y, type.color, 4, 3);
                        window.konamiSound?.play('hit');
                    }
                    if (this.scoreElement) this.scoreElement.textContent = this.score;
                    hit = true;
                    // Laser pierces through enemies
                    if (this.weapon !== 'laser') break;
                }
            }
            if (hit && this.weapon !== 'laser') this.bullets.splice(i, 1);
        }
    }

    activatePowerup(p) {
        window.konamiSound?.play('eat');
        if (p.type === 'shield') {
            this.shieldActive = true;
            this.shieldTimer = 600; // ~10 seconds
        } else if (p.type === 'life') {
            this.player.lives = Math.min(5, this.player.lives + 1);
        } else {
            this.weapon = p.type;
            this.weaponTimer = 480; // ~8 seconds
        }
    }

    draw() {
        const ctx = this.ctx;
        ctx.fillStyle = '#0f0f19';
        ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

        // Screen Shake
        const sx = (Math.random() - 0.5) * this.screenShake;
        const sy = (Math.random() - 0.5) * this.screenShake;
        ctx.save();
        ctx.translate(sx, sy);

        // Starfield
        ctx.fillStyle = '#fff';
        for (let s of this.stars) {
            ctx.globalAlpha = s.opacity * (Math.sin(this.frameCount * 0.05) * 0.3 + 0.7);
            ctx.fillRect(s.x, s.y, s.size, s.size);
        }
        ctx.globalAlpha = 1.0;

        // Player ship
        const px = this.player.x, py = this.player.y, pw = this.player.width, ph = this.player.height;
        ctx.shadowBlur = 15; ctx.shadowColor = this.player.color;
        ctx.fillStyle = this.player.color;
        ctx.beginPath();
        ctx.moveTo(px + pw / 2, py);
        ctx.lineTo(px + pw, py + ph);
        ctx.lineTo(px + pw * 0.8, py + ph * 0.8);
        ctx.lineTo(px + pw * 0.2, py + ph * 0.8);
        ctx.lineTo(px, py + ph);
        ctx.closePath();
        ctx.fill();

        // Thruster
        if (this.frameCount % 4 < 2) {
            ctx.fillStyle = '#ff6600'; ctx.shadowColor = '#ff3300';
            ctx.beginPath();
            ctx.moveTo(px + pw * 0.4, py + ph * 0.8);
            ctx.lineTo(px + pw / 2, py + ph + 10);
            ctx.lineTo(px + pw * 0.6, py + ph * 0.8);
            ctx.fill();
        }

        // Particles
        for (let p of this.particles) {
            ctx.globalAlpha = p.life;
            ctx.fillStyle = p.color;
            ctx.fillRect(p.x, p.y, p.size, p.size);
        }
        ctx.globalAlpha = 1.0;

        // Bullets
        for (let b of this.bullets) {
            ctx.fillStyle = b.color;
            ctx.shadowBlur = 10; ctx.shadowColor = b.color;
            ctx.fillRect(b.x, b.y, b.width, b.height);
        }

        // Enemy bullets
        for (let b of this.enemyBullets) {
            ctx.fillStyle = b.zigzag ? '#ff00ff' : '#ff3300';
            ctx.shadowBlur = 8; ctx.shadowColor = ctx.fillStyle;
            ctx.fillRect(b.x, b.y, b.width, b.height);
        }

        // Enemies
        for (let e of this.enemies) {
            if (!e.alive) continue;
            const type = this.enemyTypes[e.typeName];
            let drawX = e.x;
            if (type.zigzag) drawX += Math.sin(this.frameCount * 0.1 + e.phase) * 8;

            ctx.shadowBlur = type.isBoss ? 20 : 10;
            ctx.shadowColor = type.color;
            ctx.strokeStyle = type.color;
            ctx.lineWidth = 2;

            if (type.isBoss) {
                ctx.beginPath();
                ctx.arc(drawX + e.width / 2, e.y + e.height / 2, e.width / 2, 0, Math.PI * 2);
                ctx.stroke();
                // Core
                ctx.fillStyle = '#fff'; ctx.globalAlpha = 0.5 + Math.sin(this.frameCount * 0.2) * 0.3;
                ctx.beginPath(); ctx.arc(drawX + e.width / 2, e.y + e.height / 2, e.width / 4, 0, Math.PI * 2); ctx.fill();
                ctx.globalAlpha = 1.0;
            } else if (type.fast) {
                ctx.beginPath();
                ctx.moveTo(drawX + e.width / 2, e.y); ctx.lineTo(drawX + e.width, e.y + e.height); ctx.lineTo(drawX, e.y + e.height);
                ctx.closePath(); ctx.stroke();
            } else if (type.shield) {
                ctx.strokeRect(drawX, e.y, e.width, e.height);
                ctx.strokeRect(drawX + 5, e.y + 5, e.width - 10, e.height - 10);
            } else {
                ctx.strokeRect(drawX, e.y, e.width, e.height);
                ctx.beginPath(); ctx.moveTo(drawX, e.y); ctx.lineTo(drawX + e.width, e.y + e.height); ctx.stroke();
                ctx.beginPath(); ctx.moveTo(drawX + e.width, e.y); ctx.lineTo(drawX, e.y + e.height); ctx.stroke();
            }

            if (e.maxHp > 1) {
                const hpRatio = e.hp / e.maxHp;
                ctx.fillStyle = 'rgba(255,255,255,0.1)'; ctx.fillRect(drawX, e.y - 8, e.width, 3);
                ctx.fillStyle = type.color; ctx.fillRect(drawX, e.y - 8, e.width * hpRatio, 3);
            }
        }

        // Shield
        if (this.shieldActive) {
            ctx.strokeStyle = '#00f3ff'; ctx.lineWidth = 2; ctx.shadowBlur = 20;
            ctx.beginPath(); ctx.arc(px + pw / 2, py + ph / 2, 35, 0, Math.PI * 2); ctx.stroke();
        }

        ctx.restore();
        ctx.shadowBlur = 0;

        // Scanlines
        ctx.fillStyle = 'rgba(18, 16, 16, 0.1)';
        for (let i = 0; i < this.canvas.height; i += 4) {
            ctx.fillRect(0, i, this.canvas.width, 1);
        }

        // HUD
        ctx.fillStyle = '#00f3ff'; ctx.font = 'bold 16px Courier New'; ctx.textAlign = 'right';
        ctx.fillText(`SCORE: ${this.score}`, this.canvas.width - 20, 30);
        ctx.textAlign = 'left'; ctx.fillStyle = '#ff00ff'; ctx.fillText('❤️'.repeat(this.player.lives), 20, 30);
        ctx.textAlign = 'center'; ctx.font = '12px Courier New';
        ctx.fillText(`LEVEL ${this.level}`, this.canvas.width / 2, 30);

        // Current weapon indicator
        if (this.weapon !== 'basic') {
            const wepDef = this.weaponDefs[this.weapon];
            const timerPct = this.weaponTimer / 480;
            ctx.fillStyle = wepDef.color;
            ctx.font = 'bold 12px Courier New';
            ctx.textAlign = 'center';
            ctx.fillText(`⚔ ${wepDef.label}`, this.canvas.width / 2, this.canvas.height - 10);
            // Timer bar
            const barW = 80;
            ctx.fillStyle = 'rgba(255,255,255,0.2)';
            ctx.fillRect(this.canvas.width / 2 - barW / 2, this.canvas.height - 6, barW, 4);
            ctx.fillStyle = wepDef.color;
            ctx.fillRect(this.canvas.width / 2 - barW / 2, this.canvas.height - 6, barW * timerPct, 4);
        }
        if (this.shieldActive) {
            ctx.fillStyle = '#00f3ff';
            ctx.font = 'bold 12px Courier New';
            ctx.textAlign = 'right';
            ctx.fillText('🛡️ SHIELD', this.canvas.width - 15, this.canvas.height - 10);
        }
        ctx.textAlign = 'left';

        // Powerups
        for (let p of this.powerups) {
            ctx.fillStyle = p.color;
            ctx.shadowColor = p.color;
            ctx.shadowBlur = 8;
            ctx.fillRect(p.x, p.y, 20, 20);
            ctx.shadowBlur = 0;
            ctx.fillStyle = '#000';
            ctx.font = 'bold 8px Courier New';
            ctx.textAlign = 'center';
            ctx.fillText(p.type[0].toUpperCase(), p.x + 10, p.y + 14);
            ctx.textAlign = 'left';
        }

        // Intermission
        if (this.waitReady) {
            ctx.fillStyle = 'rgba(0,0,0,0.85)';
            ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
            ctx.fillStyle = '#00f3ff';
            ctx.font = 'bold 30px Courier New';
            ctx.textAlign = 'center';
            ctx.fillText(`NIVEAU ${this.level - 1} RÉUSSI`, this.canvas.width / 2, this.canvas.height / 2 - 30);

            ctx.fillStyle = '#ff00ff';
            ctx.font = '22px Courier New';
            ctx.fillText(`PREPARATION NIVEAU ${this.level}`, this.canvas.width / 2, this.canvas.height / 2 + 20);

            ctx.fillStyle = '#fff';
            ctx.font = '16px Courier New';
            ctx.fillText('APPUYEZ SUR ESPACE POUR DÉPLOYER LE PATCH', this.canvas.width / 2, this.canvas.height / 2 + 80);
            ctx.textAlign = 'left';
        }
    }

    drawInitialScreen() {
        this.ctx.fillStyle = '#0f0f19';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
        this.ctx.fillStyle = '#00f3ff';
        this.ctx.font = '40px Courier New';
        this.ctx.textAlign = 'center';
        this.ctx.fillText('TICKET INVADERS', this.canvas.width / 2, this.canvas.height / 2 - 20);
        this.ctx.fillStyle = '#fff';
        this.ctx.font = '20px Courier New';
        this.ctx.fillText('ESPACE pour commencer', this.canvas.width / 2, this.canvas.height / 2 + 30);
        this.ctx.textAlign = 'left';
    }

    loop() {
        if (!this.isPlaying && !this.isGameOver) { this.drawInitialScreen(); return; }
        if (this.isPlaying) { this.update(); this.draw(); this.animationId = requestAnimationFrame(this.loop); }
    }
}
