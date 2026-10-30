/**
 * PAC-MAN MINI — AUTHENTIC ARCADE GAME ENGINE
 * Hardened HTML5 Canvas Vanilla JavaScript Engine
 */

(function () {
    "use strict";

    // --- Grid Constants ---
    const COLS = 19;
    const ROWS = 19;
    const CELL_SIZE = 24; // 19 x 24 = 456px
    const CANVAS_WIDTH = COLS * CELL_SIZE;
    const CANVAS_HEIGHT = ROWS * CELL_SIZE;

    // 1 = Wall, 0 = Pellet, 2 = Corridor/Empty, 3 = Power Pellet, 4 = Ghost Pen
    // Baris 9 kolom 0 dan 18 = Terowongan Warp Kiri-Kanan (Warp Tunnel)
    const INITIAL_MAZE = [
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        [1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1],
        [1, 3, 1, 1, 0, 1, 1, 1, 0, 1, 0, 1, 1, 1, 0, 1, 1, 3, 1],
        [1, 0, 1, 1, 0, 1, 1, 1, 0, 1, 0, 1, 1, 1, 0, 1, 1, 0, 1],
        [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
        [1, 0, 1, 1, 0, 1, 0, 1, 1, 1, 1, 1, 0, 1, 0, 1, 1, 0, 1],
        [1, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 1],
        [1, 1, 1, 1, 0, 1, 1, 1, 2, 1, 2, 1, 1, 1, 0, 1, 1, 1, 1],
        [1, 1, 1, 1, 0, 1, 2, 2, 2, 2, 2, 2, 2, 1, 0, 1, 1, 1, 1],
        [2, 2, 2, 2, 0, 2, 2, 1, 1, 4, 1, 1, 2, 2, 0, 2, 2, 2, 2], // Warp Tunnel di kedua ujung
        [1, 1, 1, 1, 0, 1, 2, 1, 4, 4, 4, 1, 2, 1, 0, 1, 1, 1, 1],
        [1, 1, 1, 1, 0, 1, 2, 1, 1, 1, 1, 1, 2, 1, 0, 1, 1, 1, 1],
        [1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1],
        [1, 0, 1, 1, 0, 1, 1, 1, 0, 1, 0, 1, 1, 1, 0, 1, 1, 0, 1],
        [1, 3, 0, 1, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 1, 0, 3, 1],
        [1, 1, 0, 1, 0, 1, 0, 1, 1, 1, 1, 1, 0, 1, 0, 1, 0, 1, 1],
        [1, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 1],
        [1, 0, 1, 1, 1, 1, 1, 1, 0, 1, 0, 1, 1, 1, 1, 1, 1, 0, 1],
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
    ];

    let maze = [];

    // --- Audio Synthesis (Web Audio API) ---
    let audioCtx = null;
    let soundEnabled = true;
    let chompToggle = false;

    function initAudio() {
        if (!audioCtx) {
            const AudioContextClass = window.AudioContext || window.webkitAudioContext;
            if (AudioContextClass) {
                audioCtx = new AudioContextClass();
            }
        }
        if (audioCtx && audioCtx.state === "suspended") {
            audioCtx.resume();
        }
    }

    function playTone(freq, type, duration, gainVal = 0.05) {
        if (!soundEnabled || !audioCtx) return;
        try {
            const osc = audioCtx.createOscillator();
            const gainNode = audioCtx.createGain();
            osc.type = type;
            osc.frequency.setValueAtTime(freq, audioCtx.currentTime);
            gainNode.gain.setValueAtTime(gainVal, audioCtx.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + duration);
            osc.connect(gainNode);
            gainNode.connect(audioCtx.destination);
            osc.start();
            osc.stop(audioCtx.currentTime + duration);
        } catch (e) {}
    }

    function playChomp() {
        initAudio();
        chompToggle = !chompToggle;
        const freq = chompToggle ? 420 : 280;
        playTone(freq, "triangle", 0.07, 0.04);
    }

    function playEatGhostTone() {
        initAudio();
        playTone(550, "square", 0.1, 0.08);
        setTimeout(() => playTone(880, "square", 0.15, 0.08), 80);
    }

    function playDeathSequence() {
        initAudio();
        if (!soundEnabled || !audioCtx) return;
        try {
            const osc = audioCtx.createOscillator();
            const gain = audioCtx.createGain();
            osc.type = "sawtooth";
            osc.frequency.setValueAtTime(500, audioCtx.currentTime);
            osc.frequency.linearRampToValueAtTime(60, audioCtx.currentTime + 0.65);
            gain.gain.setValueAtTime(0.12, audioCtx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.65);
            osc.connect(gain);
            gain.connect(audioCtx.destination);
            osc.start();
            osc.stop(audioCtx.currentTime + 0.65);
        } catch (e) {}
    }

    function playWinSequence() {
        initAudio();
        playTone(523.25, "square", 0.12, 0.07);
        setTimeout(() => playTone(659.25, "square", 0.12, 0.07), 120);
        setTimeout(() => playTone(783.99, "square", 0.22, 0.07), 240);
    }

    // --- DOM Elements ---
    const canvas = document.getElementById("gameCanvas");
    const ctx = canvas.getContext("2d");
    const currentScoreEl = document.getElementById("currentScore");
    const topScoreEl = document.getElementById("topScore");
    const gameTimerEl = document.getElementById("gameTimer");
    const pelletCountEl = document.getElementById("pelletCount");
    const livesIndicatorEl = document.getElementById("livesIndicator");
    const arcadeOverlay = document.getElementById("arcadeOverlay");
    const startBtn = document.getElementById("startBtn");
    const pauseBtn = document.getElementById("pauseBtn");
    const resetBtn = document.getElementById("resetBtn");
    const soundBtn = document.getElementById("soundBtn");
    const refreshBtn = document.getElementById("refreshBtn");
    const leaderboardList = document.getElementById("leaderboardList");
    const searchPlayerForm = document.getElementById("searchPlayerForm");
    const searchPlayerInput = document.getElementById("searchPlayerInput");
    const searchOutput = document.getElementById("searchOutput");

    // Modal Elements
    const scoreModal = document.getElementById("scoreModal");
    const modalHeader = document.getElementById("modalHeader");
    const modalSubtext = document.getElementById("modalSubtext");
    const finalScoreVal = document.getElementById("finalScoreVal");
    const finalTimeVal = document.getElementById("finalTimeVal");
    const recordForm = document.getElementById("recordForm");
    const initialsInput = document.getElementById("initialsInput");
    const modalMsg = document.getElementById("modalMsg");
    const modalDismissBtn = document.getElementById("modalDismissBtn");

    // --- State Variables ---
    let score = 0;
    let highScore = 0;
    let lives = 3;
    let pelletsLeft = 0;
    let isRunning = false;
    let isPaused = false;
    let isDying = false; // Freeze saat Pac-Man terkena hantu
    let gameStartTime = null;
    let pauseStart = null;
    let totalPausedDuration = 0;
    let animationFrameId = null;
    let frightenedTimer = 0; // Frames ghost is vulnerable
    let deathTimeoutId = null; // Tracks death freeze setTimeout to prevent stale callbacks

    // --- Entity: Pac-Man ---
    const pacman = {
        gridX: 9,
        gridY: 14,
        x: 9 * CELL_SIZE + CELL_SIZE / 2,
        y: 14 * CELL_SIZE + CELL_SIZE / 2,
        speed: 2,
        dirX: 0,
        dirY: 0,
        nextDirX: 0,
        nextDirY: 0,
        radius: 9,
        mouthAngle: 0.2,
        mouthSpeed: 0.035,
        mouthDir: 1,
        angleOffset: 0,

        reset: function () {
            this.gridX = 9;
            this.gridY = 14;
            this.x = this.gridX * CELL_SIZE + CELL_SIZE / 2;
            this.y = this.gridY * CELL_SIZE + CELL_SIZE / 2;
            this.dirX = 0;
            this.dirY = 0;
            this.nextDirX = 0;
            this.nextDirY = 0;
            this.angleOffset = 0;
            this.mouthAngle = 0.2;
        },

        update: function () {
            // Immediate reversal if opposite direction pressed
            if (
                this.nextDirX === -this.dirX &&
                this.nextDirY === -this.dirY &&
                (this.dirX !== 0 || this.dirY !== 0)
            ) {
                this.dirX = this.nextDirX;
                this.dirY = this.nextDirY;
                this.nextDirX = 0;
                this.nextDirY = 0;
            }

            // Tile Center Check
            const atCenterX = (this.x - CELL_SIZE / 2) % CELL_SIZE === 0;
            const atCenterY = (this.y - CELL_SIZE / 2) % CELL_SIZE === 0;

            if (atCenterX && atCenterY) {
                this.gridX = Math.round((this.x - CELL_SIZE / 2) / CELL_SIZE);
                this.gridY = Math.round((this.y - CELL_SIZE / 2) / CELL_SIZE);

                // Try steering into next direction if requested
                if (this.nextDirX !== 0 || this.nextDirY !== 0) {
                    const nextTile = maze[this.gridY + this.nextDirY]?.[this.gridX + this.nextDirX];
                    if (nextTile !== undefined && nextTile !== 1 && nextTile !== 4) {
                        this.dirX = this.nextDirX;
                        this.dirY = this.nextDirY;
                        this.nextDirX = 0;
                        this.nextDirY = 0;
                    }
                }

                // Check wall block ahead
                const forwardTile = maze[this.gridY + this.dirY]?.[this.gridX + this.dirX];
                if (forwardTile === undefined || forwardTile === 1 || forwardTile === 4) {
                    this.dirX = 0;
                    this.dirY = 0;
                }
            }

            this.x += this.dirX * this.speed;
            this.y += this.dirY * this.speed;

            // Warp Tunnel Logic (Row 9)
            if (this.gridY === 9) {
                if (this.x < -CELL_SIZE / 2) {
                    this.x = CANVAS_WIDTH + CELL_SIZE / 2;
                } else if (this.x > CANVAS_WIDTH + CELL_SIZE / 2) {
                    this.x = -CELL_SIZE / 2;
                }
            }

            // Mouth Animation & Direction Rotation
            if (this.dirX !== 0 || this.dirY !== 0) {
                this.mouthAngle += this.mouthSpeed * this.mouthDir;
                if (this.mouthAngle > 0.38) this.mouthDir = -1;
                else if (this.mouthAngle < 0.04) this.mouthDir = 1;

                if (this.dirX > 0) this.angleOffset = 0;
                else if (this.dirY > 0) this.angleOffset = 0.5 * Math.PI;
                else if (this.dirX < 0) this.angleOffset = Math.PI;
                else if (this.dirY < 0) this.angleOffset = 1.5 * Math.PI;
            }

            // Pellet Eating
            const curTileX = Math.floor(this.x / CELL_SIZE);
            const curTileY = Math.floor(this.y / CELL_SIZE);
            if (maze[curTileY] && maze[curTileY][curTileX] !== undefined) {
                const tile = maze[curTileY][curTileX];
                if (tile === 0) {
                    maze[curTileY][curTileX] = 2;
                    score += 10;
                    pelletsLeft--;
                    playChomp();
                    updateScoreboard();
                } else if (tile === 3) {
                    // Power Pellet
                    maze[curTileY][curTileX] = 2;
                    score += 50;
                    pelletsLeft--;
                    frightenedTimer = 420; // 7 seconds at 60 fps
                    playTone(600, "square", 0.2, 0.08);
                    updateScoreboard();
                }
            }
        },

        draw: function () {
            ctx.save();
            ctx.translate(this.x, this.y);
            ctx.rotate(this.angleOffset);

            ctx.beginPath();
            ctx.arc(
                0,
                0,
                this.radius,
                this.mouthAngle * Math.PI,
                (2 - this.mouthAngle) * Math.PI
            );
            ctx.lineTo(0, 0);
            ctx.fillStyle = "#ffff00";
            ctx.fill();
            ctx.closePath();

            ctx.restore();
        }
    };

    // --- Entity: Ghost ---
    class Ghost {
        constructor(name, color, startX, startY) {
            this.name = name;
            this.baseColor = color;
            this.startX = startX;
            this.startY = startY;
            this.radius = 9;
            this.reset();
        }

        reset() {
            this.gridX = this.startX;
            this.gridY = this.startY;
            this.x = this.startX * CELL_SIZE + CELL_SIZE / 2;
            this.y = this.startY * CELL_SIZE + CELL_SIZE / 2;
            this.dirX = 0;
            this.dirY = -1;
            this.isEaten = false;
        }

        update() {
            // Adjust speed based on state
            let currentSpeed = 2;
            if (this.isEaten) {
                currentSpeed = 4; // Returning quickly to pen
            } else if (frightenedTimer > 0) {
                currentSpeed = 1; // Slower when vulnerable
            }

            const atCenterX = (this.x - CELL_SIZE / 2) % CELL_SIZE === 0;
            const atCenterY = (this.y - CELL_SIZE / 2) % CELL_SIZE === 0;

            if (atCenterX && atCenterY) {
                this.gridX = Math.round((this.x - CELL_SIZE / 2) / CELL_SIZE);
                this.gridY = Math.round((this.y - CELL_SIZE / 2) / CELL_SIZE);

                // If in pen or eaten, navigate towards pen or out
                if (this.isEaten) {
                    if (this.gridX === 9 && this.gridY === 9) {
                        this.isEaten = false;
                        this.dirX = 0;
                        this.dirY = -1;
                    } else {
                        this.chooseBestDir(9, 9);
                    }
                } else if (this.gridY === 10 && (this.gridX >= 8 && this.gridX <= 10)) {
                    // Inside Ghost Pen: move straight up
                    this.dirX = 0;
                    this.dirY = -1;
                } else {
                    // Regular Maze Pathfinding with Ghost Pen Barrier Rule
                    const validMoves = [
                        { dx: 1, dy: 0 },
                        { dx: -1, dy: 0 },
                        { dx: 0, dy: 1 },
                        { dx: 0, dy: -1 }
                    ].filter((m) => {
                        // Avoid immediate 180 reverse unless cornered
                        if (m.dx === -this.dirX && m.dy === -this.dirY) return false;
                        const nextY = this.gridY + m.dy;
                        const nextX = this.gridX + m.dx;
                        const t = maze[nextY]?.[nextX];
                        if (t === undefined || t === 1) return false;
                        // Sarang Hantu (tile 4): Hantu normal dilarang masuk kembali kecuali jika isEaten
                        if (t === 4 && !this.isEaten && this.gridY !== 10) return false;
                        return true;
                    });

                    if (validMoves.length > 0) {
                        if (frightenedTimer > 0) {
                            // Random frightened movement
                            const r = validMoves[Math.floor(Math.random() * validMoves.length)];
                            this.dirX = r.dx;
                            this.dirY = r.dy;
                        } else if (this.name === "Blinky" && Math.random() < 0.75) {
                            // Blinky chases Pac-Man directly
                            validMoves.sort((a, b) => {
                                const distA = Math.hypot(
                                    (this.gridX + a.dx) * CELL_SIZE - pacman.x,
                                    (this.gridY + a.dy) * CELL_SIZE - pacman.y
                                );
                                const distB = Math.hypot(
                                    (this.gridX + b.dx) * CELL_SIZE - pacman.x,
                                    (this.gridY + b.dy) * CELL_SIZE - pacman.y
                                );
                                return distA - distB;
                            });
                            this.dirX = validMoves[0].dx;
                            this.dirY = validMoves[0].dy;
                        } else {
                            // Inky or patrol
                            const chosen = validMoves[Math.floor(Math.random() * validMoves.length)];
                            this.dirX = chosen.dx;
                            this.dirY = chosen.dy;
                        }
                    } else {
                        // Dead end: reverse
                        this.dirX = -this.dirX;
                        this.dirY = -this.dirY;
                    }
                }
            }

            this.x += this.dirX * currentSpeed;
            this.y += this.dirY * currentSpeed;

            // Warp Tunnel Logic for Ghosts (Row 9)
            if (this.gridY === 9) {
                if (this.x < -CELL_SIZE / 2) {
                    this.x = CANVAS_WIDTH + CELL_SIZE / 2;
                } else if (this.x > CANVAS_WIDTH + CELL_SIZE / 2) {
                    this.x = -CELL_SIZE / 2;
                }
            }
        }

        chooseBestDir(targetGridX, targetGridY) {
            const moves = [
                { dx: 0, dy: -1 },
                { dx: -1, dy: 0 },
                { dx: 1, dy: 0 },
                { dx: 0, dy: 1 }
            ].filter((m) => {
                if (m.dx === -this.dirX && m.dy === -this.dirY) return false;
                const nextY = this.gridY + m.dy;
                const nextX = this.gridX + m.dx;
                const t = maze[nextY]?.[nextX];
                return t !== undefined && t !== 1;
            });

            if (moves.length === 0) {
                this.dirX = -this.dirX;
                this.dirY = -this.dirY;
                return;
            }

            moves.sort((a, b) => {
                const da = Math.hypot(this.gridX + a.dx - targetGridX, this.gridY + a.dy - targetGridY);
                const db = Math.hypot(this.gridX + b.dx - targetGridX, this.gridY + b.dy - targetGridY);
                return da - db;
            });

            this.dirX = moves[0].dx;
            this.dirY = moves[0].dy;
        }

        draw() {
            const x = this.x;
            const y = this.y;
            const r = this.radius;

            ctx.save();

            if (this.isEaten) {
                this.drawEyes(x, y);
                ctx.restore();
                return;
            }

            let ghostColor = this.baseColor;
            if (frightenedTimer > 0) {
                // Flash white in last 2 seconds (120 frames)
                if (frightenedTimer < 120 && Math.floor(frightenedTimer / 15) % 2 === 0) {
                    ghostColor = "#ffffff";
                } else {
                    ghostColor = "#2121ff";
                }
            }

            ctx.fillStyle = ghostColor;
            ctx.beginPath();
            ctx.arc(x, y - 2, r, Math.PI, 0, false);
            ctx.lineTo(x + r, y + r);
            ctx.lineTo(x + r * 0.66, y + r * 0.6);
            ctx.lineTo(x + r * 0.33, y + r);
            ctx.lineTo(x, y + r * 0.6);
            ctx.lineTo(x - r * 0.33, y + r);
            ctx.lineTo(x - r * 0.66, y + r * 0.6);
            ctx.lineTo(x - r, y + r);
            ctx.closePath();
            ctx.fill();

            if (frightenedTimer > 0) {
                // Frightened face (small dots and squiggly mouth)
                ctx.fillStyle = "#ffb8ff";
                ctx.fillRect(x - 4, y - 2, 2, 2);
                ctx.fillRect(x + 2, y - 2, 2, 2);
            } else {
                this.drawEyes(x, y);
            }

            ctx.restore();
        }

        drawEyes(x, y) {
            const eyeShiftX = this.dirX * 2;
            const eyeShiftY = this.dirY * 2;

            ctx.fillStyle = "#ffffff";
            ctx.beginPath();
            ctx.arc(x - 4 + eyeShiftX, y - 3 + eyeShiftY, 3, 0, Math.PI * 2);
            ctx.arc(x + 4 + eyeShiftX, y - 3 + eyeShiftY, 3, 0, Math.PI * 2);
            ctx.fill();

            ctx.fillStyle = "#0000aa";
            ctx.beginPath();
            ctx.arc(x - 4 + eyeShiftX * 1.5, y - 3 + eyeShiftY * 1.5, 1.5, 0, Math.PI * 2);
            ctx.arc(x + 4 + eyeShiftX * 1.5, y - 3 + eyeShiftY * 1.5, 1.5, 0, Math.PI * 2);
            ctx.fill();
        }
    }

    const ghosts = [
        new Ghost("Blinky", "#ff0000", 9, 8),
        new Ghost("Inky", "#00ffff", 9, 10)
    ];

    // --- Maze Renderer ---
    function renderMaze() {
        ctx.fillStyle = "#000000";
        ctx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);

        for (let r = 0; r < ROWS; r++) {
            for (let c = 0; c < COLS; c++) {
                const cell = maze[r][c];
                const cx = c * CELL_SIZE;
                const cy = r * CELL_SIZE;

                if (cell === 1) {
                    // Authentic double outline cobalt maze
                    ctx.fillStyle = "#000000";
                    ctx.fillRect(cx, cy, CELL_SIZE, CELL_SIZE);
                    ctx.strokeStyle = "#2121ff";
                    ctx.lineWidth = 2;
                    ctx.strokeRect(cx + 2, cy + 2, CELL_SIZE - 4, CELL_SIZE - 4);
                } else if (cell === 0) {
                    // Biscuit pellet
                    ctx.beginPath();
                    ctx.arc(cx + CELL_SIZE / 2, cy + CELL_SIZE / 2, 2, 0, Math.PI * 2);
                    ctx.fillStyle = "#ffb8ae";
                    ctx.fill();
                } else if (cell === 3) {
                    // Flashing energizer
                    const pulse = 4.5 + Math.sin(Date.now() / 120) * 1.5;
                    ctx.beginPath();
                    ctx.arc(cx + CELL_SIZE / 2, cy + CELL_SIZE / 2, pulse, 0, Math.PI * 2);
                    ctx.fillStyle = "#ffff00";
                    ctx.fill();
                } else if (cell === 4 && r === 9 && c === 9) {
                    // Ghost Pen Gate Line
                    ctx.strokeStyle = "#ffb8ff";
                    ctx.lineWidth = 3;
                    ctx.beginPath();
                    ctx.moveTo(cx, cy + 2);
                    ctx.lineTo(cx + CELL_SIZE, cy + 2);
                    ctx.stroke();
                }
            }
        }
    }

    // --- Scoreboard & Status Updates ---
    function updateScoreboard() {
        currentScoreEl.textContent = String(score).padStart(2, "0");
        if (score > highScore) {
            highScore = score;
            topScoreEl.textContent = String(highScore).padStart(4, "0");
        }
        pelletCountEl.textContent = pelletsLeft;
        const lifeCount = Math.max(0, lives);
        livesIndicatorEl.innerHTML =
            '<span class="life" aria-hidden="true">ᗧ</span>'.repeat(lifeCount) +
            '<span class="sr-only">' + lifeCount + ' lives</span>';

        if (isRunning && !isPaused && !isDying && gameStartTime) {
            const elapsed = ((Date.now() - gameStartTime - totalPausedDuration) / 1000).toFixed(1);
            gameTimerEl.textContent = `${elapsed}S`;
        }
    }

    function initMazeData() {
        maze = JSON.parse(JSON.stringify(INITIAL_MAZE));
        pelletsLeft = 0;
        for (let r = 0; r < ROWS; r++) {
            for (let c = 0; c < COLS; c++) {
                if (maze[r][c] === 0 || maze[r][c] === 3) {
                    pelletsLeft++;
                }
            }
        }
    }

    function initGame() {
        // Cancel any pending death freeze timeout to prevent stale callbacks
        if (deathTimeoutId !== null) {
            clearTimeout(deathTimeoutId);
            deathTimeoutId = null;
        }
        // Cancel any pending animation frame
        if (animationFrameId !== null) {
            cancelAnimationFrame(animationFrameId);
            animationFrameId = null;
        }
        initMazeData();
        pacman.reset();
        ghosts.forEach((g) => g.reset());
        score = 0;
        lives = 3;
        frightenedTimer = 0;
        isRunning = false;
        isPaused = false;
        isDying = false;
        gameStartTime = null;
        pauseStart = null;
        totalPausedDuration = 0;
        pauseBtn.textContent = "Pause";
        updateScoreboard();
        renderMaze();
        pacman.draw();
        ghosts.forEach((g) => g.draw());
    }

    function startGame() {
        initAudio();
        arcadeOverlay.classList.add("hidden");
        isRunning = true;
        isPaused = false;
        isDying = false;
        gameStartTime = Date.now();
        totalPausedDuration = 0;
        pauseStart = null;
        pauseBtn.textContent = "Pause";
        animationFrameId = requestAnimationFrame(gameLoop);
    }

    function togglePause() {
        if (!isRunning || isDying) return;
        isPaused = !isPaused;
        if (isPaused) {
            pauseStart = Date.now();
            pauseBtn.textContent = "Resume";
        } else {
            if (pauseStart) {
                totalPausedDuration += Date.now() - pauseStart;
                pauseStart = null;
            }
            pauseBtn.textContent = "Pause";
            animationFrameId = requestAnimationFrame(gameLoop);
        }
    }

    function triggerGameOver(isWin = false) {
        isRunning = false;
        isDying = false;
        // Cancel pending death timeout
        if (deathTimeoutId !== null) {
            clearTimeout(deathTimeoutId);
            deathTimeoutId = null;
        }
        // Cancel animation frame
        if (animationFrameId !== null) {
            cancelAnimationFrame(animationFrameId);
            animationFrameId = null;
        }

        const duration = ((Date.now() - gameStartTime - totalPausedDuration) / 1000).toFixed(2);

        // Reset inline color to let CSS handle it, then set per state
        modalHeader.style.color = "";
        if (isWin) {
            playWinSequence();
            modalHeader.textContent = "VICTORY!";
            modalHeader.classList.add("win");
            modalSubtext.textContent = "ALL PELLETS CONSUMED";
        } else {
            playDeathSequence();
            modalHeader.textContent = "GAME OVER";
            modalHeader.classList.remove("win");
            modalSubtext.textContent = "OUT OF LIVES";
        }

        finalScoreVal.textContent = score;
        finalTimeVal.textContent = `${duration}S`;
        modalMsg.className = "modal-msg hidden";
        modalMsg.textContent = "";

        scoreModal.classList.remove("hidden");
        document.getElementById("recordSubmitBtn").focus();
    }

    // --- Main Game Loop ---
    function gameLoop() {
        if (!isRunning || isPaused) return;

        if (isDying) {
            // Saat death freeze: cukup render kondisi saat ini dan tampilkan pesan READY!
            renderMaze();
            pacman.draw();
            ghosts.forEach((g) => g.draw());
            ctx.fillStyle = "#ffff00";
            ctx.font = "bold 14px 'JetBrains Mono', monospace";
            ctx.textAlign = "center";
            ctx.fillText("READY!", CANVAS_WIDTH / 2, 275);
            animationFrameId = requestAnimationFrame(gameLoop);
            return;
        }

        if (frightenedTimer > 0) {
            frightenedTimer--;
        }

        pacman.update();
        ghosts.forEach((g) => g.update());

        // Collision Checks
        for (const ghost of ghosts) {
            const dist = Math.hypot(pacman.x - ghost.x, pacman.y - ghost.y);
            if (dist < pacman.radius + ghost.radius - 3) {
                if (frightenedTimer > 0 && !ghost.isEaten) {
                    // Eat Ghost!
                    ghost.isEaten = true;
                    score += 200;
                    playEatGhostTone();
                    updateScoreboard();
                } else if (!ghost.isEaten) {
                    // Pac-Man caught by ghost
                    lives--;
                    frightenedTimer = 0; // Reset frightened mode on death
                    playDeathSequence();
                    updateScoreboard();

                    if (lives <= 0) {
                        triggerGameOver(false);
                        return;
                    } else {
                        // Death Freeze: jeda 1 detik sebelum respawn agar tidak instan/mengejutkan
                        isDying = true;
                        pacman.reset();
                        ghosts.forEach((g) => g.reset());
                        // Cancel any previous death timeout to prevent stacking
                        if (deathTimeoutId !== null) {
                            clearTimeout(deathTimeoutId);
                        }
                        deathTimeoutId = setTimeout(() => {
                            // Guard: only act if still dying (user may have pressed Reset)
                            if (!isDying) return;
                            isDying = false;
                            deathTimeoutId = null;
                        }, 1000);
                        animationFrameId = requestAnimationFrame(gameLoop);
                        return;
                    }
                }
            }
        }

        // Win Condition
        if (pelletsLeft <= 0) {
            triggerGameOver(true);
            return;
        }

        // Render Frame
        renderMaze();
        pacman.draw();
        ghosts.forEach((g) => g.draw());
        updateScoreboard();

        animationFrameId = requestAnimationFrame(gameLoop);
    }

    // --- Keyboard Event Handler with Input Guard ---
    window.addEventListener("keydown", (e) => {
        // Modal Escape key: close modal and return to start screen
        if (e.key === "Escape" && !scoreModal.classList.contains("hidden")) {
            scoreModal.classList.add("hidden");
            initGame();
            arcadeOverlay.classList.remove("hidden");
            startBtn.focus();
            return;
        }

        if (!scoreModal.classList.contains("hidden")) {
            if (e.key === "Tab") {
                const first = document.getElementById("recordSubmitBtn");
                const last = modalDismissBtn;
                if (e.shiftKey && (document.activeElement === first || document.activeElement === initialsInput)) {
                    e.preventDefault(); last.focus();
                } else if (!e.shiftKey && document.activeElement === last) {
                    e.preventDefault(); first.focus();
                }
            }
            return;
        }

        // Critical: Do not intercept keys if user is typing into an input field!
        if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") {
            return;
        }

        switch (e.key) {
            case "ArrowUp":
            case "w":
            case "W":
                pacman.nextDirX = 0;
                pacman.nextDirY = -1;
                e.preventDefault();
                break;
            case "ArrowDown":
            case "s":
            case "S":
                pacman.nextDirX = 0;
                pacman.nextDirY = 1;
                e.preventDefault();
                break;
            case "ArrowLeft":
            case "a":
            case "A":
                pacman.nextDirX = -1;
                pacman.nextDirY = 0;
                e.preventDefault();
                break;
            case "ArrowRight":
            case "d":
            case "D":
                pacman.nextDirX = 1;
                pacman.nextDirY = 0;
                e.preventDefault();
                break;
            case "p":
            case "P":
                togglePause();
                break;
            case "r":
            case "R":
                initGame();
                arcadeOverlay.classList.remove("hidden");
                break;
        }
    });

    // --- Mobile Touch Gestures (Swipe Detection) ---
    let touchStartX = 0;
    let touchStartY = 0;

    canvas.addEventListener(
        "touchstart",
        (e) => {
            if (e.touches.length > 0) {
                touchStartX = e.touches[0].clientX;
                touchStartY = e.touches[0].clientY;
            }
        },
        { passive: true }
    );

    canvas.addEventListener(
        "touchmove",
        (e) => {
            if (e.touches.length > 0) {
                const touchEndX = e.touches[0].clientX;
                const touchEndY = e.touches[0].clientY;
                const dx = touchEndX - touchStartX;
                const dy = touchEndY - touchStartY;

                if (Math.hypot(dx, dy) > 20) {
                    if (Math.abs(dx) > Math.abs(dy)) {
                        pacman.nextDirX = dx > 0 ? 1 : -1;
                        pacman.nextDirY = 0;
                    } else {
                        pacman.nextDirX = 0;
                        pacman.nextDirY = dy > 0 ? 1 : -1;
                    }
                    touchStartX = touchEndX;
                    touchStartY = touchEndY;
                }
            }
        },
        { passive: true }
    );

    // --- Virtual D-Pad Touch Buttons (untuk Mobile Viewport) ---
    const dpadUp = document.getElementById("dpadUp");
    const dpadDown = document.getElementById("dpadDown");
    const dpadLeft = document.getElementById("dpadLeft");
    const dpadRight = document.getElementById("dpadRight");

    if (dpadUp) {
        dpadUp.addEventListener("click", () => {
            pacman.nextDirX = 0;
            pacman.nextDirY = -1;
        });
    }
    if (dpadDown) {
        dpadDown.addEventListener("click", () => {
            pacman.nextDirX = 0;
            pacman.nextDirY = 1;
        });
    }
    if (dpadLeft) {
        dpadLeft.addEventListener("click", () => {
            pacman.nextDirX = -1;
            pacman.nextDirY = 0;
        });
    }
    if (dpadRight) {
        dpadRight.addEventListener("click", () => {
            pacman.nextDirX = 1;
            pacman.nextDirY = 0;
        });
    }

    // --- Button Event Handlers ---
    startBtn.addEventListener("click", () => {
        startGame();
    });

    pauseBtn.addEventListener("click", () => {
        togglePause();
    });

    resetBtn.addEventListener("click", () => {
        initGame();
        arcadeOverlay.classList.remove("hidden");
    });

    soundBtn.addEventListener("click", () => {
        initAudio();
        soundEnabled = !soundEnabled;
        soundBtn.textContent = soundEnabled ? "Sound: On" : "Sound: Off";
    });

    modalDismissBtn.addEventListener("click", () => {
        scoreModal.classList.add("hidden");
        initGame();
        arcadeOverlay.classList.remove("hidden");
        startBtn.focus();
    });

    // --- API Integrations: Leaderboard & Score Posting ---
    async function apiFetch(url, options = {}) {
        const res = await fetch(url, options);
        if (res.status === 401) {
            window.location.assign("/");
            throw new Error("Sesi berakhir");
        }
        return res;
    }

    async function fetchLeaderboard() {
        try {
            leaderboardList.innerHTML = `<tr><td colspan="4" class="muted">FETCHING DATA...</td></tr>`;
            const res = await apiFetch("/api/leaderboard");
            if (!res.ok) throw new Error("Fetch failed");
            const data = await res.json();

            if (!data || data.length === 0) {
                leaderboardList.innerHTML = `<tr><td colspan="4" class="muted">NO SCORES RECORDED</td></tr>`;
                return;
            }

            // Sync high score with #1 rank
            if (data[0] && data[0].score > highScore) {
                highScore = data[0].score;
                topScoreEl.textContent = String(highScore).padStart(4, "0");
            }

            const rankLabels = ["1ST", "2ND", "3RD", "4TH", "5TH"];
            const rankClasses = ["rk-gold", "rk-silver", "rk-bronze", "", ""];

            leaderboardList.innerHTML = data
                .map((row, idx) => {
                    const rkText = rankLabels[idx] || `${idx + 1}TH`;
                    const rkClass = rankClasses[idx] || "";
                    return `
                    <tr>
                        <td class="${rkClass}">${rkText}</td>
                        <td class="score-col-td">${row.score}</td>
                        <td class="name-col-td">${escapeText(row.player_name)}</td>
                        <td class="time-col-td">${row.duration_seconds}S</td>
                    </tr>
                `;
                })
                .join("");
        } catch (err) {
            leaderboardList.innerHTML = `<tr><td colspan="4" class="api-error">Tidak dapat memuat skor. Coba segarkan.</td></tr>`;
        }
    }

    refreshBtn.addEventListener("click", () => {
        fetchLeaderboard();
    });

    // Score Submission
    recordForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const rawName = initialsInput.value.trim();
        const scoreVal = parseInt(finalScoreVal.textContent, 10) || 0;
        const durationVal = parseFloat(finalTimeVal.textContent) || 0;

        if (!rawName) return;

        modalMsg.className = "modal-msg saving";
        modalMsg.textContent = "SAVING TO ROM...";

        try {
            const res = await apiFetch("/api/score", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRF-Token": document.querySelector('meta[name="csrf-token"]').content
                },
                body: JSON.stringify({
                    score: scoreVal,
                    duration_seconds: durationVal
                })
            });

            const data = await res.json();
            if (res.ok) {
                modalMsg.className = "modal-msg success";
                modalMsg.textContent = "RECORD REGISTERED!";
                await fetchLeaderboard();
                setTimeout(() => {
                    scoreModal.classList.add("hidden");
                    initGame();
                    arcadeOverlay.classList.remove("hidden");
                }, 1000);
            } else {
                modalMsg.className = "modal-msg error";
                modalMsg.textContent = data.message || "FAILED TO REGISTER";
            }
        } catch (err) {
            modalMsg.className = "modal-msg error";
            modalMsg.textContent = "NETWORK CONNECTION ERROR";
        }
    });

    // Player Search
    searchPlayerForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const query = searchPlayerInput.value.trim();
        if (!query) return;

        searchOutput.innerHTML = `<div class="muted">SEARCHING...</div>`;
        try {
            const res = await apiFetch(`/api/search?player_name=${encodeURIComponent(query)}`);
            if (!res.ok) throw new Error("Search failed");
            const results = await res.json();

            if (!results || results.length === 0) {
                searchOutput.innerHTML = `<div class="muted">NO RECORDS FOR "${escapeText(query)}"</div>`;
                return;
            }

            searchOutput.innerHTML = results
                .map(
                    (r) => `
                <div class="search-feed-row">
                    <span>${escapeText(r.player_name)}</span>
                    <span class="score-result">${r.score} PTS (${r.duration_seconds}S)</span>
                </div>
            `
                )
                .join("");
        } catch (err) {
            searchOutput.innerHTML = `<div class="api-error">Pencarian gagal. Silakan coba lagi.</div>`;
        }
    });

    function escapeText(str) {
        if (!str) return "";
        return str
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    // Initialize on Load
    window.addEventListener("DOMContentLoaded", () => {
        initGame();
        fetchLeaderboard();
    });
})();
