/**
 * KIRO LABYRINTH - Cyberpunk Maze Challenge
 * Frontend Application
 */

// ===== STATE =====
const state = {
    user: null,
    apiKey: null,
    sessionId: null,
    maze: null,
    position: { x: 0, y: 0 },
    turns: 0,
    status: 'READY',
    selectedMaze: 'tutorial'
};

// Sample maze data (would come from API)
const SAMPLE_MAZES = {
    tutorial: {
        name: 'TUTORIAL',
        size: '10x10',
        data: `XXXXXXXXXX
XS.......X
X.XXXXXX.X
X.X....X.X
X.X.XX.X.X
X.X.XX.X.X
X.X....X.X
X.XXXXXX.X
X........E
XXXXXXXXXX`
    },
    intermediate: {
        name: 'INTERMEDIATE',
        size: '31x17',
        data: `XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
XS.....X......X..............X
X.XXXX.X.XXXX.X.XXXXXXXXXXXX.X
X.X....X.X....X.X............X
X.X.XXXX.X.XXXX.X.XXXXXXXXXXXX
X.X.X....X.X....X............X
X.X.X.XXXX.X.XXXX.XXXXXXXXXX.X
X.X.X....X.X....X.X..........X
X.X.XXXX.X.X.XXXX.X.XXXXXXXXXX
X.X....X.X.X.....#X..........X
X.XXXX.X.X.XXXXXXXX.XXXXXXXX.X
X......X.X.........#.........X
XXXXXX.X.XXXXXXXXXX.XXXXXXXXXX
X......X...........#.........X
X.XXXXXXXXXXXXXXXXXXXXXXXX.XXX
X........................#...E
XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX`
    }
};

// Sample leaderboard data
const LEADERBOARD_DATA = [
    { rank: 1, name: 'Paul', score: 1314 },
    { rank: 2, name: 'CyberNinja', score: 1456 },
    { rank: 3, name: 'MazeRunner', score: 1523 },
    { rank: 4, name: 'AlgoMaster', score: 1678 },
    { rank: 5, name: 'PathFinder', score: 1890 },
    { rank: 6, name: 'CodeWalker', score: 2034 },
    { rank: 7, name: 'GridSolver', score: 2156 },
    { rank: 8, name: 'BFSKing', score: 2289 },
    { rank: 9, name: 'Dijkstra', score: 2445 },
    { rank: 10, name: 'Wanderer', score: 2567 }
];

// ===== INITIALIZATION =====
document.addEventListener('DOMContentLoaded', () => {
    log('DOM LOADED - INITIALIZING...');

    // Simulate loading delay
    setTimeout(() => {
        document.getElementById('loading-screen').style.display = 'none';
        document.getElementById('main-content').style.display = 'block';
        log('SYSTEM READY');

        // Load leaderboard
        renderLeaderboard();
    }, 2000);

    // Keyboard controls
    document.addEventListener('keydown', handleKeyPress);
});

// ===== NAVIGATION =====
function showScreen(screenId) {
    const screens = ['welcome-screen', 'register-screen', 'login-screen', 'dashboard-screen'];
    screens.forEach(id => {
        document.getElementById(id).style.display = 'none';
    });
    document.getElementById(screenId).style.display = screenId === 'dashboard-screen' ? 'flex' : 'flex';

    if (screenId === 'dashboard-screen') {
        document.getElementById(screenId).style.flexDirection = 'row';
        selectMaze(state.selectedMaze);
    }

    triggerGlitch();
    log(`SCREEN: ${screenId.replace('-screen', '').toUpperCase()}`);
}

// ===== AUTH HANDLERS =====
function handleRegister(event) {
    event.preventDefault();
    const username = document.getElementById('reg-username').value;
    const email = document.getElementById('reg-email').value;

    // Simulate registration
    state.user = { username, email };
    state.apiKey = generateApiKey();

    log(`USER REGISTERED: ${username}`);
    log(`API KEY GENERATED: ${state.apiKey.substring(0, 8)}...`);

    updateHUD();
    showScreen('dashboard-screen');
}

function handleLogin(event) {
    event.preventDefault();
    const email = document.getElementById('login-email').value;

    // Simulate login
    state.user = { username: email.split('@')[0], email };
    state.apiKey = generateApiKey();

    log(`USER AUTHENTICATED: ${state.user.username}`);

    updateHUD();
    showScreen('dashboard-screen');
}

function generateApiKey() {
    return 'kiro_' + Array.from({ length: 32 }, () =>
        Math.random().toString(36).charAt(2)
    ).join('');
}

// ===== MAZE FUNCTIONS =====
function selectMaze(mazeId) {
    state.selectedMaze = mazeId;
    const mazeData = SAMPLE_MAZES[mazeId];

    if (mazeData) {
        state.maze = parseMaze(mazeData.data);
        document.getElementById('maze-name').textContent = mazeData.name;
        document.getElementById('maze-size').textContent = mazeData.size;
        renderMaze();
    }

    log(`MAZE SELECTED: ${mazeId.toUpperCase()}`);
}

function parseMaze(mazeString) {
    const lines = mazeString.trim().split('\n');
    const cells = [];
    let startPos = { x: 0, y: 0 };
    let exitPos = { x: 0, y: 0 };

    lines.forEach((line, y) => {
        const row = [];
        for (let x = 0; x < line.length; x++) {
            const char = line[x];
            row.push(char);

            if (char === 'S') {
                startPos = { x, y };
            } else if (char === 'E') {
                exitPos = { x, y };
            }
        }
        cells.push(row);
    });

    return {
        cells,
        width: cells[0]?.length || 0,
        height: cells.length,
        start: startPos,
        exit: exitPos
    };
}

function renderMaze() {
    if (!state.maze) return;

    const grid = document.getElementById('maze-grid');
    grid.innerHTML = '';
    grid.style.gridTemplateColumns = `repeat(${state.maze.width}, 20px)`;

    state.maze.cells.forEach((row, y) => {
        row.forEach((cell, x) => {
            const div = document.createElement('div');
            div.className = 'maze-cell';
            div.dataset.x = x;
            div.dataset.y = y;

            switch (cell) {
                case 'X':
                    div.classList.add('maze-cell-wall');
                    break;
                case 'S':
                    div.classList.add('maze-cell-start');
                    div.textContent = 'S';
                    break;
                case 'E':
                    div.classList.add('maze-cell-exit');
                    div.textContent = 'E';
                    break;
                case '#':
                    div.classList.add('maze-cell-mud');
                    div.textContent = '#';
                    break;
                default:
                    div.classList.add('maze-cell-path');
            }

            // Player position
            if (x === state.position.x && y === state.position.y) {
                div.classList.add('maze-cell-player');
            }

            grid.appendChild(div);
        });
    });
}

function startSession() {
    if (!state.maze) return;

    state.sessionId = 'sess_' + Date.now().toString(36);
    state.position = { ...state.maze.start };
    state.turns = 0;
    state.status = 'ACTIVE';

    updateHUD();
    renderMaze();

    log(`SESSION STARTED: ${state.sessionId}`);
    log(`POSITION: ${state.position.x}, ${state.position.y}`);
}

function move(direction) {
    if (!state.sessionId || state.status !== 'ACTIVE') {
        log('ERROR: NO ACTIVE SESSION');
        return;
    }

    const deltas = {
        north: { x: 0, y: -1 },
        south: { x: 0, y: 1 },
        east: { x: 1, y: 0 },
        west: { x: -1, y: 0 }
    };

    const delta = deltas[direction];
    const newX = state.position.x + delta.x;
    const newY = state.position.y + delta.y;

    // Check bounds
    if (newY < 0 || newY >= state.maze.height || newX < 0 || newX >= state.maze.width) {
        log('BLOCKED: OUT OF BOUNDS');
        return;
    }

    const targetCell = state.maze.cells[newY][newX];

    // Check wall
    if (targetCell === 'X') {
        log('BLOCKED: WALL');
        return;
    }

    // Move
    state.position = { x: newX, y: newY };
    state.turns++;

    // Check mud
    if (targetCell === '#') {
        state.status = 'STUCK';
        log(`MOVED ${direction.toUpperCase()} - STUCK IN MUD!`);
        document.getElementById('player-status').textContent = 'STUCK';
        document.getElementById('player-status').style.color = 'var(--cyber-orange)';

        // Auto-unstick after delay
        setTimeout(() => {
            if (state.status === 'STUCK') {
                state.status = 'ACTIVE';
                document.getElementById('player-status').textContent = 'ACTIVE';
                document.getElementById('player-status').style.color = 'var(--cyber-green)';
                log('ESCAPED MUD');
            }
        }, 1000);
    } else {
        log(`MOVED ${direction.toUpperCase()}`);
    }

    // Check exit
    if (targetCell === 'E') {
        state.status = 'COMPLETED';
        document.getElementById('player-status').textContent = 'COMPLETED';
        document.getElementById('player-status').style.color = 'var(--cyber-gold)';
        log(`MAZE COMPLETED IN ${state.turns} TURNS!`);
        triggerGlitch();

        // Celebration effect
        document.querySelector('.maze-container').style.boxShadow = '0 0 50px var(--cyber-gold)';
    }

    updateHUD();
    renderMaze();
}

function look() {
    if (!state.sessionId) {
        log('ERROR: NO ACTIVE SESSION');
        return;
    }

    const { x, y } = state.position;
    const north = y > 0 ? state.maze.cells[y - 1][x] : 'X';
    const south = y < state.maze.height - 1 ? state.maze.cells[y + 1][x] : 'X';
    const east = x < state.maze.width - 1 ? state.maze.cells[y][x + 1] : 'X';
    const west = x > 0 ? state.maze.cells[y][x - 1] : 'X';

    log(`LOOK: N=${north} S=${south} E=${east} W=${west}`);

    // Visual feedback
    highlightAdjacentCells();
}

function highlightAdjacentCells() {
    const { x, y } = state.position;
    const adjacent = [
        { x: x, y: y - 1 },
        { x: x, y: y + 1 },
        { x: x + 1, y: y },
        { x: x - 1, y: y }
    ];

    adjacent.forEach(({ x: ax, y: ay }) => {
        const cell = document.querySelector(`.maze-cell[data-x="${ax}"][data-y="${ay}"]`);
        if (cell) {
            cell.style.boxShadow = '0 0 10px var(--cyber-pink)';
            setTimeout(() => {
                cell.style.boxShadow = '';
            }, 500);
        }
    });
}

// ===== HUD =====
function updateHUD() {
    document.getElementById('session-id').textContent = state.sessionId || '--';
    document.getElementById('turn-count').textContent = state.turns;
    document.getElementById('player-pos').textContent = `${state.position.x}, ${state.position.y}`;

    if (state.status === 'ACTIVE') {
        document.getElementById('player-status').textContent = 'ACTIVE';
        document.getElementById('player-status').style.color = 'var(--cyber-green)';
    }
}

// ===== LEADERBOARD =====
function renderLeaderboard() {
    const list = document.getElementById('leaderboard-list');
    list.innerHTML = '';

    LEADERBOARD_DATA.forEach((entry, index) => {
        const li = document.createElement('li');
        li.className = 'leaderboard-item';
        li.style.animationDelay = `${index * 0.1}s`;
        li.innerHTML = `
            <span class="leaderboard-rank">${entry.rank}</span>
            <span class="leaderboard-name">${entry.name}</span>
            <span class="leaderboard-score">${entry.score.toLocaleString()}</span>
        `;
        list.appendChild(li);
    });
}

// ===== UTILITIES =====
function log(message) {
    console.log(message);
    const logElement = document.getElementById('status-log');
    const line = document.createElement('div');
    line.className = 'status-log-line';
    line.textContent = message;
    logElement.prepend(line);

    // Keep only last 3 messages
    while (logElement.children.length > 3) {
        logElement.removeChild(logElement.lastChild);
    }
}

function triggerGlitch() {
    const huds = document.querySelectorAll('.hud');
    huds.forEach(hud => {
        hud.style.animation = 'glitch 0.3s ease';
        setTimeout(() => {
            hud.style.animation = '';
        }, 300);
    });
}

function handleKeyPress(event) {
    if (state.status !== 'ACTIVE') return;

    const keyMap = {
        'ArrowUp': 'north',
        'ArrowDown': 'south',
        'ArrowRight': 'east',
        'ArrowLeft': 'west',
        'w': 'north',
        's': 'south',
        'd': 'east',
        'a': 'west',
        ' ': 'look'
    };

    const action = keyMap[event.key];
    if (action === 'look') {
        look();
    } else if (action) {
        move(action);
    }
}

function downloadStarter() {
    log('DOWNLOADING STARTER PACKAGE...');
    // In production, this would trigger actual file download
    alert('Starter package download would start here.\n\nIncludes:\n- maze_client.py\n- solver_template.py\n- Example solvers\n- Sample mazes');
}

// ===== WEBSOCKET (simulated) =====
function connectWebSocket() {
    // In production, this would connect to real WebSocket
    log('WEBSOCKET: CONNECTING...');

    setTimeout(() => {
        log('WEBSOCKET: CONNECTED');

        // Simulate leaderboard updates
        setInterval(() => {
            if (Math.random() > 0.7) {
                const randomScore = Math.floor(Math.random() * 500) + 1500;
                const randomUser = ['Neo', 'Trinity', 'Morpheus', 'Cypher'][Math.floor(Math.random() * 4)];
                log(`LEADERBOARD UPDATE: ${randomUser} - ${randomScore} turns`);
            }
        }, 10000);
    }, 1000);
}

// Initialize WebSocket simulation when on dashboard
setTimeout(connectWebSocket, 3000);
