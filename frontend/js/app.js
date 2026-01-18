/**
 * KIRO LABYRINTH - Cyberpunk Maze Challenge
 * Frontend Application
 */

// ===== CONFIGURATION =====
// API URL is configured via window.KIRO_API_URL or auto-detected
// For Railway: Set KIRO_API_URL environment variable at build time
const getApiBaseUrl = () => {
    // Check for injected config (Railway/production)
    if (window.KIRO_API_URL) {
        return window.KIRO_API_URL + '/v1';
    }
    // Use relative path when served through nginx proxy
    if (window.location.port === '3000') {
        return '/v1';
    }
    // Default to localhost for development
    return 'http://localhost:8000/v1';
};

const getConfigUrl = () => {
    if (window.KIRO_API_URL) {
        return window.KIRO_API_URL + '/config';
    }
    if (window.location.port === '3000') {
        return '/config';
    }
    return 'http://localhost:8000/config';
};

const API_BASE_URL = getApiBaseUrl();
const CONFIG_URL = getConfigUrl();

// ===== STATE =====
const state = {
    user: null,
    apiKey: null,
    sessionId: null,
    mazeId: null,
    maze: null,
    mazes: [],
    position: { x: 0, y: 0 },
    turns: 0,
    status: 'READY',
    selectedMaze: 'tutorial',
    wsConnection: null,
    googleClientId: null,
    debugMode: false,
    regeneratingKey: false,  // Flag for API key regeneration via Google OAuth
};

// Fallback sample maze data (used when API is unavailable)
const SAMPLE_MAZES = {
    tutorial: {
        name: 'TUTORIAL',
        size: '15x13',
        data: `XXXXXXXXXXXXXXX
XS..X.........X
X.X.X.XXXXXXX.X
X.X.X.X.....X.X
X.X.X.X.XXX.X.X
X.X...X...X.X.X
X.XXXXX.X.X.X.X
X.......X.X...X
XXXXXXXXX.XXXXX
X.....#.X.....X
X.XXX#X.XXXXX.X
X...X#........E
XXXXXXXXXXXXXXX`
    },
    intermediate: {
        name: 'INTERMEDIATE',
        size: '31x17',
        data: `XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
XS....X.......X...........#.XX
X.XXX.X.XXXXX.X.XXXXXXXXX.X#XX
X...X.X.X...X.X.X.......X.X.XX
XXX.X.X.X.X.X.X.X.XXXXX.X.XXXX
X...X.X...X...X.X.X...X.X...XX
X.XXX.XXXXXXXXX.X.X.X.X.XXX.XX
X.X...X.........X...X.X.....XX
X.X.XXX.XXXXXXXXX.XXX.XXXXXXXX
X.X...X...#.....X.X........#XX
X.XXX.XXX#XXXXX.X.X.XXXXXXX#XX
X...X...X#....X.X.X.X.....X.XX
XXX.XXX.X#XXX.X.X.X.X.XXX.X.XX
X.....X.X.....X...X.X...X.X.XX
X.XXXXX.XXXXXXXXX.X.XXX.X.X.XX
X.................X.....X..EXX
XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX`
    }
};

// ===== API HELPER =====
async function apiRequest(endpoint, options = {}) {
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers,
    };

    if (state.apiKey) {
        headers['X-API-Key'] = state.apiKey;
    }

    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            ...options,
            headers,
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Request failed' }));
            throw new Error(error.detail || `HTTP ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        log(`API ERROR: ${error.message}`);
        throw error;
    }
}

// ===== INITIALIZATION =====
document.addEventListener('DOMContentLoaded', () => {
    log('DOM LOADED - INITIALIZING...');

    // Check for stored API key
    const storedApiKey = localStorage.getItem('kiro_api_key');
    if (storedApiKey) {
        state.apiKey = storedApiKey;
        log('API KEY RESTORED FROM STORAGE');
    }

    // Initialize
    setTimeout(async () => {
        document.getElementById('loading-screen').style.display = 'none';
        document.getElementById('main-content').style.display = 'block';
        log('SYSTEM READY');

        // Fetch config (Google Client ID, etc.)
        await loadConfig();

        // Load mazes from API
        await loadMazes();

        // Load leaderboard
        await loadLeaderboard();

        // Initialize Google Sign-In if available
        initGoogleSignIn();

        // If we have an API key, load profile and go to dashboard
        if (state.apiKey && state.apiKey !== 'EXISTING_USER_API_KEY_UNCHANGED') {
            await loadUserProfile();
            showScreen('dashboard-screen');
        }
    }, 2000);

    // Keyboard controls
    document.addEventListener('keydown', handleKeyPress);
});

// ===== CONFIG =====
async function loadConfig() {
    try {
        const response = await fetch(CONFIG_URL);
        const config = await response.json();
        state.googleClientId = config.google_client_id;
        state.debugMode = config.debug;
        log(`CONFIG LOADED (debug: ${config.debug})`);
    } catch (error) {
        log('CONFIG: USING DEFAULTS');
    }
}

let googleSignInRetries = 0;
const MAX_GOOGLE_RETRIES = 10;

function initGoogleSignIn() {
    if (!state.googleClientId) {
        document.getElementById('google-signin-container').innerHTML =
            '<p class="cyber-subtitle" style="font-size: 10px; color: var(--cyber-orange);">Google Sign-In not configured</p>';
        return;
    }

    if (window.google && window.google.accounts) {
        try {
            google.accounts.id.initialize({
                client_id: state.googleClientId,
                callback: handleGoogleCredentialResponse,
                auto_select: false,
            });

            google.accounts.id.renderButton(
                document.getElementById("google-signin-container"),
                {
                    theme: "filled_black",
                    size: "large",
                    text: "signin_with",
                    shape: "rectangular",
                }
            );
            log('GOOGLE SIGN-IN INITIALIZED');
            googleSignInRetries = 0;
        } catch (error) {
            log(`GOOGLE SIGN-IN ERROR: ${error.message}`);
            document.getElementById('google-signin-container').innerHTML =
                '<p class="cyber-subtitle" style="font-size: 10px; color: var(--cyber-orange);">Google Sign-In error. Please refresh.</p>';
        }
    } else {
        googleSignInRetries++;
        if (googleSignInRetries < MAX_GOOGLE_RETRIES) {
            // Retry after Google library loads
            setTimeout(initGoogleSignIn, 500);
        } else {
            log('GOOGLE SIGN-IN: Library failed to load');
            document.getElementById('google-signin-container').innerHTML =
                '<p class="cyber-subtitle" style="font-size: 10px; color: var(--cyber-orange);">Google Sign-In unavailable. Please refresh or check your connection.</p>';
        }
    }
}

// ===== NAVIGATION =====
function showScreen(screenId) {
    const screens = ['welcome-screen', 'register-screen', 'login-screen', 'dashboard-screen'];
    screens.forEach(id => {
        document.getElementById(id).style.display = 'none';
    });
    document.getElementById(screenId).style.display = screenId === 'dashboard-screen' ? 'flex' : 'flex';

    // Hide top-left HUD on dashboard (overlaps with panels)
    const hudTL = document.querySelector('.hud-tl');
    if (hudTL) {
        hudTL.style.display = screenId === 'dashboard-screen' ? 'none' : 'block';
    }

    if (screenId === 'dashboard-screen') {
        document.getElementById(screenId).style.flexDirection = 'row';
        selectMaze(state.selectedMaze);
        connectWebSocket();
    }

    triggerGlitch();
    log(`SCREEN: ${screenId.replace('-screen', '').toUpperCase()}`);
}

// ===== AUTH HANDLERS =====
async function handleRegister(event) {
    event.preventDefault();
    const username = document.getElementById('reg-username').value;
    const email = document.getElementById('reg-email').value;
    const password = document.getElementById('reg-password').value;

    log('REGISTERING USER...');

    try {
        const data = await apiRequest('/auth/register', {
            method: 'POST',
            body: JSON.stringify({ username, email, password }),
        });

        state.user = { username, email };
        log(`USER REGISTERED: ${username}`);

        // In debug mode, API key is returned immediately
        if (data.api_key) {
            state.apiKey = data.api_key;
            localStorage.setItem('kiro_api_key', data.api_key);
            log(`API KEY: ${data.api_key.substring(0, 15)}...`);

            // Show API key modal so user can copy it
            showApiKeyModal(data.api_key);

            updateHUD();
            updateProfileDisplay();
            showScreen('dashboard-screen');
        } else {
            // Production mode - need email verification
            log('CHECK EMAIL FOR VERIFICATION TOKEN');
            showNotification('Registration successful! Check your email for verification.', 'info');
            showScreen('login-screen');
        }

    } catch (error) {
        log(`REGISTRATION FAILED: ${error.message}`);
        showNotification(`Registration failed: ${error.message}`, 'error');
    }
}

async function handleLogin(event) {
    event.preventDefault();
    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;

    log('AUTHENTICATING...');

    // For now, we use the API key directly since there's no login endpoint
    // Users should use their API key from verification
    const apiKeyInput = prompt('Enter your API Key (from verification email):');
    
    if (apiKeyInput && apiKeyInput.startsWith('kiro_')) {
        state.apiKey = apiKeyInput;
        localStorage.setItem('kiro_api_key', apiKeyInput);
        state.user = { username: email.split('@')[0], email };

        log(`USER AUTHENTICATED: ${state.user.username}`);
        updateHUD();
        updateProfileDisplay();  // Show profile button
        showScreen('dashboard-screen');
    } else {
        log('INVALID API KEY FORMAT');
        showNotification('Invalid API key. It should start with "kiro_"', 'error');
    }
}

window.handleGoogleCredentialResponse = async function(response) {
    // Check both state and sessionStorage for regeneration intent
    const isRegenerating = state.regeneratingKey || sessionStorage.getItem('kiro_regenerate_key') === 'true';
    state.regeneratingKey = false;  // Reset state flag
    sessionStorage.removeItem('kiro_regenerate_key');  // Clear sessionStorage flag

    log(isRegenerating ? 'GOOGLE AUTH FOR KEY REGENERATION...' : 'GOOGLE AUTH DETECTED. VERIFYING...');

    try {
        const data = await apiRequest('/auth/google', {
            method: 'POST',
            body: JSON.stringify({
                token: response.credential,
                regenerate_key: isRegenerating
            }),
        });

        // Decode token payload for display info
        const payload = JSON.parse(atob(response.credential.split('.')[1]));

        state.user = {
            username: payload.name || payload.email.split('@')[0],
            email: payload.email
        };

        // If we were regenerating, we always get a new key
        if (isRegenerating) {
            state.apiKey = data.api_key;
            localStorage.setItem('kiro_api_key', data.api_key);
            log(`API KEY REGENERATED: ${state.apiKey.substring(0, 10)}...`);

            // Show the new API key prominently
            showApiKeyModal(data.api_key);

            updateHUD();
            updateProfileDisplay();
            showScreen('dashboard-screen');
            return;
        }

        // Check if this is an existing user (API key message contains instruction)
        const isExistingUser = data.api_key.includes('existing') || data.api_key.includes('Use your');

        if (isExistingUser) {
            log('EXISTING USER - CHECKING FOR SAVED API KEY');

            // Try to restore from localStorage
            const existingKey = localStorage.getItem('kiro_api_key');
            if (existingKey && existingKey.startsWith('kiro_')) {
                state.apiKey = existingKey;
                log(`API KEY RESTORED FROM STORAGE`);
                showNotification('Welcome back!', 'success');
                updateHUD();
                await loadUserProfile();  // Load profile first to populate state.user
                updateProfileDisplay();  // Show profile button
                showScreen('dashboard-screen');
            } else {
                // No saved key - tell user to regenerate via profile
                showNotification('Welcome back! Click PROFILE to regenerate your API key.', 'info');
                // Still go to dashboard, they can regenerate from profile
                updateHUD();
                // state.user is already set above, so show profile button
                updateProfileDisplay();
                showScreen('dashboard-screen');
            }
        } else {
            // New user - save and show API key
            state.apiKey = data.api_key;
            localStorage.setItem('kiro_api_key', data.api_key);
            log(`NEW USER CREATED - API KEY: ${state.apiKey.substring(0, 10)}...`);

            // Show API key modal so user can copy it
            showApiKeyModal(data.api_key);

            updateHUD();
            updateProfileDisplay();
            showScreen('dashboard-screen');
        }
    } catch (error) {
        log(`AUTH ERROR: ${error.message}`);
        showNotification(`Authentication failed: ${error.message}`, 'error');
    }
};

function logout() {
    state.apiKey = null;
    state.user = null;
    state.sessionId = null;
    localStorage.removeItem('kiro_api_key');

    // Hide profile elements
    document.getElementById('profile-btn').style.display = 'none';
    document.getElementById('profile-panel').style.display = 'none';
    document.getElementById('profile-overlay').style.display = 'none';

    log('LOGGED OUT');
    showScreen('welcome-screen');
}

// ===== PROFILE FUNCTIONS =====
async function loadUserProfile() {
    if (!state.apiKey) return;

    try {
        const data = await apiRequest('/auth/me');
        state.user = {
            id: data.id,
            username: data.username,
            email: data.email,
            api_key_prefix: data.api_key_prefix,
            verified: data.verified,
        };
        updateProfileDisplay();
        log(`PROFILE LOADED: ${data.username}`);
    } catch (error) {
        log(`PROFILE ERROR: ${error.message}`);
        // If API key is invalid, don't auto-logout to allow recovery
    }
}

function updateProfileDisplay() {
    if (!state.user) return;

    document.getElementById('profile-username').textContent = state.user.username;
    document.getElementById('profile-email').textContent = state.user.email;

    // Show full API key if available, otherwise show prefix, or prompt to regenerate
    let apiKeyDisplay;
    if (state.apiKey) {
        apiKeyDisplay = state.apiKey;
    } else if (state.user.api_key_prefix) {
        apiKeyDisplay = state.user.api_key_prefix + '...';
    } else {
        apiKeyDisplay = 'Click REGENERATE KEY below';
    }
    document.getElementById('profile-api-key').textContent = apiKeyDisplay;

    // Show profile button
    document.getElementById('profile-btn').style.display = 'block';
}

function toggleProfilePanel() {
    const panel = document.getElementById('profile-panel');
    const overlay = document.getElementById('profile-overlay');

    if (panel.style.display === 'none') {
        panel.style.display = 'block';
        overlay.style.display = 'block';
        log('PROFILE PANEL OPENED');
    } else {
        panel.style.display = 'none';
        overlay.style.display = 'none';
    }
}

function copyApiKey() {
    const apiKey = state.apiKey;
    if (!apiKey) {
        showNotification('No API key available. Please regenerate.', 'error');
        return;
    }

    navigator.clipboard.writeText(apiKey).then(() => {
        showNotification('API key copied to clipboard!', 'success');
        log('API KEY COPIED');
    }).catch(() => {
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = apiKey;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        showNotification('API key copied!', 'success');
    });
}

async function regenerateApiKey() {
    if (!confirm('Are you sure? This will invalidate your current API key.')) {
        return;
    }

    log('REGENERATING API KEY...');

    // If we have a valid API key, try the direct endpoint first
    if (state.apiKey && state.apiKey.startsWith('kiro_')) {
        try {
            const data = await apiRequest('/auth/regenerate-key', {
                method: 'POST',
            });

            // Update state with new key
            state.apiKey = data.api_key;
            localStorage.setItem('kiro_api_key', data.api_key);

            // Show the new API key prominently
            showApiKeyModal(data.api_key);

            log('API KEY REGENERATED');
            updateProfileDisplay();
            return;
        } catch (error) {
            log(`Direct regeneration failed: ${error.message}, trying Google OAuth...`);
        }
    }

    // No API key or direct method failed - use Google OAuth with regenerate flag
    if (!state.googleClientId) {
        showNotification('Google Sign-In not configured. Cannot regenerate key.', 'error');
        return;
    }

    // Store regeneration intent in sessionStorage (persists across sign-in flow)
    sessionStorage.setItem('kiro_regenerate_key', 'true');
    state.regeneratingKey = true;
    log('PLEASE SIGN IN WITH GOOGLE TO REGENERATE YOUR KEY...');

    // Close the profile panel if open
    if (document.getElementById('profile-panel').style.display !== 'none') {
        toggleProfilePanel();
    }

    // Show notification and go to welcome screen for Google Sign-In
    showNotification('Please sign in with Google to verify your identity and regenerate your API key.', 'info');
    showScreen('welcome-screen');
}

function showApiKeyModal(apiKey) {
    document.getElementById('api-key-full-display').textContent = apiKey;
    document.getElementById('api-key-modal').style.display = 'block';
    document.getElementById('api-key-modal-overlay').style.display = 'block';
}

function copyNewApiKey() {
    const apiKey = document.getElementById('api-key-full-display').textContent;
    navigator.clipboard.writeText(apiKey).then(() => {
        showNotification('New API key copied!', 'success');
    }).catch(() => {
        const textArea = document.createElement('textarea');
        textArea.value = apiKey;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        showNotification('API key copied!', 'success');
    });
}

function closeApiKeyModal() {
    document.getElementById('api-key-modal').style.display = 'none';
    document.getElementById('api-key-modal-overlay').style.display = 'none';
}

// ===== MAZE FUNCTIONS =====
async function loadMazes() {
    try {
        const data = await apiRequest('/maze');
        state.mazes = data.mazes || [];

        // Update maze select dropdown
        const select = document.getElementById('maze-select');
        if (select && state.mazes.length > 0) {
            select.innerHTML = state.mazes.map(maze => 
                `<option value="${maze.id}">${maze.name.toUpperCase()} (${maze.width}x${maze.height})</option>`
            ).join('');
        }

        log(`LOADED ${state.mazes.length} MAZES`);
    } catch (error) {
        log('USING OFFLINE MAZE DATA');
        // Use fallback sample mazes
    }
}

async function selectMaze(mazeIdOrName) {
    state.selectedMaze = mazeIdOrName;

    // Try to get maze from API
    const apiMaze = state.mazes.find(m => m.id === mazeIdOrName || m.name.toLowerCase() === mazeIdOrName.toLowerCase());

    if (apiMaze) {
        try {
            const mazeDetail = await apiRequest(`/maze/${apiMaze.id}`);
            state.mazeId = apiMaze.id;
            state.maze = parseMaze(mazeDetail.grid_data);
            // Set initial position to start for preview
            state.position = { ...state.maze.start };
            state.turns = 0;
            state.status = 'READY';
            state.sessionId = null;
            document.getElementById('maze-name').textContent = mazeDetail.name.toUpperCase();
            document.getElementById('maze-size').textContent = `${mazeDetail.width}x${mazeDetail.height}`;
            updateHUD();
            renderMaze();
            log(`MAZE LOADED: ${mazeDetail.name.toUpperCase()}`);
            return;
        } catch (error) {
            log(`FAILED TO LOAD MAZE: ${error.message}`);
        }
    }

    // Fallback to sample data
    const mazeData = SAMPLE_MAZES[mazeIdOrName] || SAMPLE_MAZES.tutorial;
    if (mazeData) {
        state.maze = parseMaze(mazeData.data);
        state.mazeId = null; // No API maze ID for sample data
        // Set initial position to start for preview
        state.position = { ...state.maze.start };
        state.turns = 0;
        state.status = 'READY';
        state.sessionId = null;
        document.getElementById('maze-name').textContent = mazeData.name;
        document.getElementById('maze-size').textContent = mazeData.size;
        updateHUD();
        renderMaze();
    }

    log(`MAZE SELECTED: ${mazeIdOrName.toUpperCase()}`);
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

    // Responsive cell size based on available space
    // Account for left panel (300px), right panel (320px), and padding
    const availableWidth = Math.min(window.innerWidth - 700, 1200);
    const availableHeight = window.innerHeight - 300;

    // Calculate optimal cell size to fit both width and height constraints
    const cellSizeByWidth = Math.floor(availableWidth / state.maze.width);
    const cellSizeByHeight = Math.floor(availableHeight / state.maze.height);

    // Use the smaller dimension to ensure maze fits, with min 12px and max 50px
    const cellSize = Math.max(12, Math.min(50, Math.min(cellSizeByWidth, cellSizeByHeight)));

    grid.style.gridTemplateColumns = `repeat(${state.maze.width}, ${cellSize}px)`;
    grid.style.gridTemplateRows = `repeat(${state.maze.height}, ${cellSize}px)`;

    state.maze.cells.forEach((row, y) => {
        row.forEach((cell, x) => {
            const div = document.createElement('div');
            div.className = 'maze-cell';
            div.style.width = `${cellSize}px`;
            div.style.height = `${cellSize}px`;
            div.style.fontSize = `${Math.max(8, cellSize - 4)}px`;
            div.dataset.x = x;
            div.dataset.y = y;

            switch (cell) {
                case 'X':
                    div.classList.add('maze-cell-wall');
                    break;
                case 'S':
                    div.classList.add('maze-cell-start');
                    if (cellSize >= 12) div.textContent = 'S';
                    break;
                case 'E':
                    div.classList.add('maze-cell-exit');
                    if (cellSize >= 12) div.textContent = 'E';
                    break;
                case '#':
                    div.classList.add('maze-cell-mud');
                    if (cellSize >= 12) div.textContent = '#';
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

async function startSession() {
    if (!state.maze) {
        log('ERROR: NO MAZE SELECTED');
        return;
    }

    if (!state.apiKey) {
        log('ERROR: NOT AUTHENTICATED');
        showNotification('Please log in first', 'error');
        return;
    }

    // Try to start session via API
    if (state.mazeId) {
        try {
            const data = await apiRequest('/session', {
                method: 'POST',
                body: JSON.stringify({ maze_id: state.mazeId }),
            });

            state.sessionId = data.id;
            state.position = { x: data.current_position.x, y: data.current_position.y };
            state.turns = data.turn_count;
            state.status = 'ACTIVE';

            updateHUD();
            renderMaze();

            log(`SESSION STARTED: ${state.sessionId.substring(0, 8)}...`);
            log(`POSITION: ${state.position.x}, ${state.position.y}`);
            return;
        } catch (error) {
            log(`API SESSION FAILED: ${error.message}`);
        }
    }

    // Fallback to local session (scores won't be saved to leaderboard)
    state.sessionId = 'local_' + Date.now().toString(36);
    state.position = { ...state.maze.start };
    state.turns = 0;
    state.status = 'ACTIVE';

    updateHUD();
    renderMaze();

    log(`LOCAL SESSION (scores not saved)`);
    showNotification('Playing in offline mode. Scores will not be saved.', 'info');
    log(`POSITION: ${state.position.x}, ${state.position.y}`);
}

async function move(direction) {
    if (!state.sessionId || state.status !== 'ACTIVE') {
        log('ERROR: NO ACTIVE SESSION');
        return;
    }

    // Try API move if using API session
    if (state.sessionId && !state.sessionId.startsWith('local_')) {
        try {
            const data = await apiRequest(`/session/${state.sessionId}/move`, {
                method: 'POST',
                body: JSON.stringify({ direction }),
            });

            state.position = { x: data.position.x, y: data.position.y };
            state.turns = data.turns;

            if (data.status === 'completed') {
                state.status = 'COMPLETED';
                document.getElementById('player-status').textContent = 'COMPLETED';
                document.getElementById('player-status').style.color = 'var(--cyber-gold)';
                log(`MAZE COMPLETED IN ${state.turns} TURNS!`);
                triggerGlitch();
                document.querySelector('.maze-container').style.boxShadow = '0 0 50px var(--cyber-gold)';
                // Show celebration modal
                const mazeName = document.getElementById('maze-name').textContent;
                showCelebration(state.turns, mazeName);
            } else if (data.status === 'blocked') {
                log('BLOCKED: WALL');
            } else if (data.status === 'mud') {
                log(`MOVED ${direction.toUpperCase()} - STUCK IN MUD!`);
            } else if (data.status === 'stuck') {
                log('STILL STUCK IN MUD');
            } else {
                log(`MOVED ${direction.toUpperCase()}`);
            }

            updateHUD();
            renderMaze();
            return;
        } catch (error) {
            log(`MOVE ERROR: ${error.message}`);
        }
    }

    // Local movement logic
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
        document.querySelector('.maze-container').style.boxShadow = '0 0 50px var(--cyber-gold)';
        // Show celebration modal
        const mazeName = document.getElementById('maze-name').textContent;
        showCelebration(state.turns, mazeName);
    }

    updateHUD();
    renderMaze();
}

async function look() {
    if (!state.sessionId) {
        log('ERROR: NO ACTIVE SESSION');
        return;
    }

    // Try API look if using API session
    if (state.sessionId && !state.sessionId.startsWith('local_')) {
        try {
            const data = await apiRequest(`/session/${state.sessionId}/look`, {
                method: 'POST',
            });

            log(`LOOK: N=${data.north} S=${data.south} E=${data.east} W=${data.west}`);
            highlightAdjacentCells();
            return;
        } catch (error) {
            log(`LOOK ERROR: ${error.message}`);
        }
    }

    // Local look logic
    const { x, y } = state.position;
    const north = y > 0 ? state.maze.cells[y - 1][x] : 'X';
    const south = y < state.maze.height - 1 ? state.maze.cells[y + 1][x] : 'X';
    const east = x < state.maze.width - 1 ? state.maze.cells[y][x + 1] : 'X';
    const west = x > 0 ? state.maze.cells[y][x - 1] : 'X';

    log(`LOOK: N=${north} S=${south} E=${east} W=${west}`);
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
    document.getElementById('session-id').textContent = state.sessionId
        ? state.sessionId.substring(0, 8) + '...'
        : '--';
    // Update both HUD and stats panel turn counts
    document.getElementById('turn-count').textContent = state.turns;
    const statsTurns = document.getElementById('stats-turns');
    if (statsTurns) statsTurns.textContent = state.turns;

    document.getElementById('player-pos').textContent = `${state.position.x}, ${state.position.y}`;

    if (state.status === 'ACTIVE') {
        document.getElementById('player-status').textContent = 'ACTIVE';
        document.getElementById('player-status').style.color = 'var(--cyber-green)';
    }
}

function updateBestScore(score) {
    const statsBest = document.getElementById('stats-best');
    if (statsBest) statsBest.textContent = score || '--';
}

// ===== LEADERBOARD =====
async function loadLeaderboard() {
    try {
        const data = await apiRequest('/leaderboard?limit=10');
        renderLeaderboardData(data.entries || []);
    } catch (error) {
        log('USING SAMPLE LEADERBOARD');
        // Fallback sample data
        const sampleData = [
            { rank: 1, username: 'Paul', score: 1314 },
            { rank: 2, username: 'CyberNinja', score: 1456 },
            { rank: 3, username: 'MazeRunner', score: 1523 },
            { rank: 4, username: 'AlgoMaster', score: 1678 },
            { rank: 5, username: 'PathFinder', score: 1890 },
        ];
        renderLeaderboardData(sampleData);
    }
}

function renderLeaderboardData(entries) {
    const list = document.getElementById('leaderboard-list');
    list.innerHTML = '';

    entries.forEach((entry, index) => {
        const li = document.createElement('li');
        li.className = 'leaderboard-item';
        li.style.animationDelay = `${index * 0.1}s`;
        li.innerHTML = `
            <span class="leaderboard-rank">${entry.rank || index + 1}</span>
            <span class="leaderboard-name">${entry.username || entry.name}</span>
            <span class="leaderboard-score">${(entry.score || 0).toLocaleString()}</span>
        `;
        list.appendChild(li);
    });
}

// ===== WEBSOCKET =====
function connectWebSocket() {
    if (state.wsConnection) {
        return; // Already connected
    }

    // Build WebSocket URL based on current location
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.port === '3000'
        ? window.location.host  // Use nginx proxy
        : 'localhost:8000';     // Direct backend
    const wsUrl = `${protocol}//${host}/v1/leaderboard/ws`;

    try {
        log('WEBSOCKET: CONNECTING...');
        state.wsConnection = new WebSocket(wsUrl);

        state.wsConnection.onopen = () => {
            log('WEBSOCKET: CONNECTED');
        };

        state.wsConnection.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.type === 'leaderboard_update') {
                    log(`LEADERBOARD: ${data.data.username} - ${data.data.score} turns`);
                    loadLeaderboard(); // Refresh leaderboard
                }
            } catch (e) {
                console.error('WebSocket message error:', e);
            }
        };

        state.wsConnection.onclose = () => {
            log('WEBSOCKET: DISCONNECTED');
            state.wsConnection = null;
            // Reconnect after delay
            setTimeout(connectWebSocket, 5000);
        };

        state.wsConnection.onerror = (error) => {
            log('WEBSOCKET: ERROR');
            console.error('WebSocket error:', error);
        };
    } catch (error) {
        log('WEBSOCKET: FAILED TO CONNECT');
        // Fallback to polling
        setInterval(loadLeaderboard, 30000);
    }
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

function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        left: 50%;
        transform: translateX(-50%);
        padding: 12px 24px;
        background: ${type === 'error' ? 'rgba(255, 0, 100, 0.9)' : type === 'success' ? 'rgba(0, 255, 136, 0.9)' : 'rgba(0, 255, 255, 0.9)'};
        color: #000;
        font-family: 'Orbitron', sans-serif;
        font-weight: bold;
        border-radius: 4px;
        z-index: 9999;
        animation: slideIn 0.3s ease;
    `;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.remove();
    }, 3000);
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

// ===== CELEBRATION MODAL =====

function showCelebration(turns, mazeName) {
    // Set celebration data
    document.getElementById('celebration-turns').textContent = turns.toLocaleString();
    document.getElementById('celebration-maze').textContent = mazeName || 'UNKNOWN';

    // Custom message based on turn count
    let message = 'Congratulations, Navigator!';
    if (turns <= 50) {
        message = 'LEGENDARY! Speed run complete!';
    } else if (turns <= 100) {
        message = 'EXCELLENT! Master navigator!';
    } else if (turns <= 200) {
        message = 'IMPRESSIVE! Well navigated!';
    }
    document.getElementById('celebration-message').textContent = message;

    // Show modal
    document.getElementById('celebration-modal').style.display = 'flex';

    // Log the achievement
    log(`ACHIEVEMENT UNLOCKED: ${mazeName} in ${turns} turns!`);
}

function closeCelebration() {
    document.getElementById('celebration-modal').style.display = 'none';
    // Reload leaderboard to show updated scores
    loadLeaderboard();
}

function playAgain() {
    closeCelebration();
    // Reset maze container glow
    document.querySelector('.maze-container').style.boxShadow = '';
    // Start a new session
    startSession();
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
    
    // Create download link
    const link = document.createElement('a');
    link.href = '/downloads/starter-package.zip';
    link.download = 'kiro-labyrinth-starter.zip';
    
    // Fallback: show instructions if download not available
    link.onerror = () => {
        alert(`Starter Package Contents:\n
- maze_client.py - Python SDK for API
- solver_template.py - Template for your solver
- examples/ - Sample solvers (BFS, DFS, etc.)
- sample_mazes/ - Test mazes

Clone from: https://github.com/kiro-labyrinth/starter-package`);
    };

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// Handle window resize for responsive maze
window.addEventListener('resize', () => {
    if (state.maze) {
        renderMaze();
    }
});
