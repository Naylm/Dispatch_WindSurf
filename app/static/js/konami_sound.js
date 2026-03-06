/**
 * static/js/konami_sound.js
 * Global sound manager for the Konami Hub arcade games.
 * Provides a single AudioContext, a mute toggle, and named sound effects.
 */

class KonamiSound {
    constructor() {
        this.muted = localStorage.getItem('konamiHubMuted') === 'true';
        this.ctx = null; // lazily created
    }

    getContext() {
        if (!this.ctx) {
            const AC = window.AudioContext || window.webkitAudioContext;
            if (!AC) return null;
            this.ctx = new AC();
        }
        if (this.ctx.state === 'suspended') this.ctx.resume();
        return this.ctx;
    }

    toggleMute() {
        this.muted = !this.muted;
        localStorage.setItem('konamiHubMuted', this.muted);
        return this.muted;
    }

    isMuted() { return this.muted; }

    play(type) {
        if (this.muted) return;
        const ctx = this.getContext();
        if (!ctx) return;

        try {
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.connect(gain);
            gain.connect(ctx.destination);

            const t = ctx.currentTime;

            switch (type) {
                case 'jump':
                    osc.type = 'square';
                    osc.frequency.setValueAtTime(300, t);
                    osc.frequency.exponentialRampToValueAtTime(600, t + 0.1);
                    gain.gain.setValueAtTime(0.07, t);
                    gain.gain.exponentialRampToValueAtTime(0.01, t + 0.1);
                    osc.start(t); osc.stop(t + 0.1);
                    break;

                case 'shoot':
                    osc.type = 'square';
                    osc.frequency.setValueAtTime(800, t);
                    osc.frequency.exponentialRampToValueAtTime(300, t + 0.1);
                    gain.gain.setValueAtTime(0.05, t);
                    gain.gain.exponentialRampToValueAtTime(0.01, t + 0.1);
                    osc.start(t); osc.stop(t + 0.1);
                    break;

                case 'kill':
                case 'hit':
                    osc.type = 'sawtooth';
                    osc.frequency.setValueAtTime(200, t);
                    osc.frequency.exponentialRampToValueAtTime(100, t + 0.12);
                    gain.gain.setValueAtTime(0.08, t);
                    gain.gain.exponentialRampToValueAtTime(0.01, t + 0.12);
                    osc.start(t); osc.stop(t + 0.12);
                    break;

                case 'eat':
                case 'flip':
                case 'bounce':
                    osc.type = 'sine';
                    osc.frequency.setValueAtTime(500, t);
                    osc.frequency.exponentialRampToValueAtTime(800, t + 0.08);
                    gain.gain.setValueAtTime(0.06, t);
                    gain.gain.exponentialRampToValueAtTime(0.01, t + 0.08);
                    osc.start(t); osc.stop(t + 0.08);
                    break;

                case 'match':
                    osc.type = 'square';
                    osc.frequency.setValueAtTime(400, t);
                    osc.frequency.setValueAtTime(600, t + 0.1);
                    gain.gain.setValueAtTime(0.05, t);
                    gain.gain.exponentialRampToValueAtTime(0.01, t + 0.2);
                    osc.start(t); osc.stop(t + 0.2);
                    break;

                case 'error':
                    osc.type = 'sawtooth';
                    osc.frequency.setValueAtTime(150, t);
                    osc.frequency.exponentialRampToValueAtTime(100, t + 0.2);
                    gain.gain.setValueAtTime(0.08, t);
                    gain.gain.exponentialRampToValueAtTime(0.01, t + 0.2);
                    osc.start(t); osc.stop(t + 0.2);
                    break;

                case 'die':
                    osc.type = 'square';
                    osc.frequency.setValueAtTime(150, t);
                    osc.frequency.exponentialRampToValueAtTime(40, t + 0.4);
                    gain.gain.setValueAtTime(0.12, t);
                    gain.gain.exponentialRampToValueAtTime(0.01, t + 0.4);
                    osc.start(t); osc.stop(t + 0.4);
                    break;

                case 'levelup':
                case 'win':
                    osc.type = 'sine';
                    osc.frequency.setValueAtTime(523.25, t);
                    osc.frequency.setValueAtTime(659.25, t + 0.15);
                    osc.frequency.setValueAtTime(783.99, t + 0.3);
                    gain.gain.setValueAtTime(0.1, t);
                    gain.gain.linearRampToValueAtTime(0, t + 0.5);
                    osc.start(t); osc.stop(t + 0.5);
                    break;

                default:
                    osc.type = 'sine';
                    osc.frequency.setValueAtTime(440, t);
                    gain.gain.setValueAtTime(0.05, t);
                    gain.gain.exponentialRampToValueAtTime(0.01, t + 0.1);
                    osc.start(t); osc.stop(t + 0.1);
            }
        } catch (e) { /* silent fail */ }
    }
}

// Instantiate globally
window.konamiSound = new KonamiSound();
