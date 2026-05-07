const state = {
  data: null,
  selectedToken: null,
  waitingForMove: false,
  autoRunning: false,
  autoTimer: null,
};

const AUTO_STEP_DELAY = 650;

const boardEl = document.getElementById("board");
const statusText = document.getElementById("statusText");
const turnText = document.getElementById("turnText");
const diceValue = document.getElementById("diceValue");
const diceValueSide = document.getElementById("diceValueSide");
const aiModeText = document.getElementById("aiModeText");
const moveButtons = document.getElementById("moveButtons");
const playersList = document.getElementById("playersList");
const logText = document.getElementById("logText");
const rollBtn = document.getElementById("rollBtn");
const newGameBtn = document.getElementById("newGameBtn");
const autoBtn = document.getElementById("autoBtn");

const PLAYER_NAMES = [
  "You",
  "Greedy Best-First Search",
  "Defensive Heuristic Greedy Search",
  "A*-Inspired Informed Search",
];
const PLAYER_CLASSES = ["p0", "p1", "p2", "p3"];
const PLAYER_COLORS = ["yellow", "blue", "red", "green"];

function key(row, col) {
  return `${row},${col}`;
}

function trackCoords() {
  return [
    [6, 1],
    [6, 2],
    [6, 3],
    [6, 4],
    [6, 5],

    [5, 6],
    [4, 6],
    [3, 6],
    [2, 6],
    [1, 6],
    [0, 6],

    [0, 7],

    [0, 8],
    [1, 8],
    [2, 8],
    [3, 8],
    [4, 8],
    [5, 8],

    [6, 9],
    [6, 10],
    [6, 11],
    [6, 12],
    [6, 13],
    [6, 14],

    [7, 14],

    [8, 14],
    [8, 13],
    [8, 12],
    [8, 11],
    [8, 10],
    [8, 9],

    [9, 8],
    [10, 8],
    [11, 8],
    [12, 8],
    [13, 8],
    [14, 8],
    [14, 7],
    [14, 6],
    [13, 6],
    [12, 6],
    [11, 6],
    [10, 6],
    [9, 6],
    [8, 5],
    [8, 4],
    [8, 3],
    [8, 2],
    [8, 1],
    [8, 0],
    [7, 0],
    [6, 0],
  ];
}

function homeLaneCoords(player) {
  if (player === 0)
    return [
      [7, 1],
      [7, 2],
      [7, 3],
      [7, 4],
      [7, 5],
      [7, 6],
    ];

  if (player === 1)
    return [
      [1, 7],
      [2, 7],
      [3, 7],
      [4, 7],
      [5, 7],
      [6, 7],
    ];

  if (player === 2)
    return [
      [7, 13],
      [7, 12],
      [7, 11],
      [7, 10],
      [7, 9],
      [7, 8],
    ];

  return [
    [13, 7],
    [12, 7],
    [11, 7],
    [10, 7],
    [9, 7],
    [8, 7],
  ];
}

function yardSlots(player) {
  if (player === 0)
    return [
      [1, 1],
      [1, 4],
      [4, 1],
      [4, 4],
    ]; // Yellow
  if (player === 1)
    return [
      [1, 10],
      [1, 13],
      [4, 10],
      [4, 13],
    ]; // Blue
  if (player === 2)
    return [
      [10, 10],
      [10, 13],
      [13, 10],
      [13, 13],
    ]; // Red
  return [
    [10, 1],
    [10, 4],
    [13, 1],
    [13, 4],
  ]; // Green
}

function makeBoardMap(data) {
  const map = new Map();
  const track = trackCoords();
  const safeSet = new Set(data.safe_squares);
  const startPositions = data.start_positions;

  for (let r = 0; r < 15; r++) {
    for (let c = 0; c < 15; c++) {
      const entry = { type: "neutral", classes: [] };

      const inTopLeft = r <= 5 && c <= 5;
      const inTopRight = r <= 5 && c >= 9;
      const inBottomLeft = r >= 9 && c <= 5;
      const inBottomRight = r >= 9 && c >= 9;
      const inCenter = r >= 6 && r <= 8 && c >= 6 && c <= 8;

      if (inTopLeft || inTopRight || inBottomLeft || inBottomRight) {
        entry.type = "corner";
        entry.classes.push("corner");
      }

      if (inCenter) {
        entry.type = "center";
        entry.classes.push("center");
      }

      const trackIndex = track.findIndex(([tr, tc]) => tr === r && tc === c);
      if (trackIndex !== -1) {
        entry.type = "track";
        entry.trackIndex = trackIndex;
        entry.classes.push("track");

        if (safeSet.has(trackIndex)) entry.classes.push("safe");

        if (startPositions.includes(trackIndex)) {
          entry.classes.push("start");
          const pIdx = startPositions.indexOf(trackIndex);
          if (pIdx !== -1) entry.classes.push(`start-${PLAYER_COLORS[pIdx]}`);
        }
      }

      for (let p = 0; p < 4; p++) {
        const lane = homeLaneCoords(p);
        const laneIndex = lane.findIndex(([hr, hc]) => hr === r && hc === c);
        if (laneIndex !== -1 && laneIndex < 5) {
          entry.type = "home-lane";
          entry.classes.push("home-lane", PLAYER_COLORS[p]);
        }

        const ySlots = yardSlots(p);
        if (ySlots.some(([yr, yc]) => yr === r && yc === c)) {
          entry.classes.push("yard-slot", `yard-slot-${PLAYER_COLORS[p]}`);
        }
      }

      map.set(key(r, c), entry);
    }
  }

  return { map, track, safeSet, startPositions };
}

function buildBoard(data) {
  const { map } = makeBoardMap(data);
  boardEl.innerHTML = "";

  const yards = [
    { color: "yellow", area: "1 / 1 / 7 / 7" }, // Top-Left
    { color: "blue", area: "1 / 10 / 7 / 16" }, // Top-Right
    { color: "red", area: "10 / 10 / 16 / 16" }, // Bottom-Right
    { color: "green", area: "10 / 1 / 16 / 7" }, // Bottom-Left
  ];

  yards.forEach((y) => {
    const yard = document.createElement("div");
    yard.className = `big-yard big-yard-${y.color}`;
    yard.style.gridArea = y.area;
    const innerCircle = document.createElement("div");
    innerCircle.className = "yard-inner-circle";
    yard.appendChild(innerCircle);
    boardEl.appendChild(yard);
  });

  const center = document.createElement("div");
  center.className = "board-center";
  center.style.gridArea = "7 / 7 / 10 / 10";
  boardEl.appendChild(center);

  for (let r = 0; r < 15; r++) {
    for (let c = 0; c < 15; c++) {
      const cell = document.createElement("div");
      cell.dataset.row = r;
      cell.dataset.col = c;
      const info = map.get(key(r, c));
      cell.className = "cell";
      cell.style.gridArea = `${r + 1} / ${c + 1} / ${r + 2} / ${c + 2}`;

      if (info) {
        info.classes.forEach((cls) => cell.classList.add(cls));
        if (info.type === "corner" || info.type === "center") {
          cell.classList.add("hidden-cell");
        }
      }

      if (info && info.classes.includes("start")) {
        const arrow = document.createElement("div");
        arrow.className = "start-arrow";
        if (info.classes.includes("start-yellow")) arrow.innerHTML = "▶";
        else if (info.classes.includes("start-blue")) arrow.innerHTML = "▼";
        else if (info.classes.includes("start-red")) arrow.innerHTML = "◀";
        else if (info.classes.includes("start-green")) arrow.innerHTML = "▲";
        cell.appendChild(arrow);
      } else if (info && info.classes.includes("safe")) {
        const star = document.createElement("div");
        star.className = "safe-star";
        star.innerHTML = "☆";
        cell.appendChild(star);
      }

      const stack = document.createElement("div");
      stack.className = "token-stack";
      stack.dataset.count = "0";
      cell.appendChild(stack);
      boardEl.appendChild(cell);
    }
  }

  renderTokens(data);
}

function tokenLabel(progress) {
  if (progress === -1) return "Yard";
  if (progress === 57) return "Finish";
  if (progress >= 52 && progress <= 56) return `Home ${progress - 51}`;
  return `T${progress}`;
}

function cellAt(row, col) {
  return boardEl.querySelector(`.cell[data-row="${row}"][data-col="${col}"]`);
}

function tokenPlacement(data) {
  const placements = [];
  const track = trackCoords();

  for (let p = 0; p < 4; p++) {
    const yard = yardSlots(p);
    const lane = homeLaneCoords(p);

    for (let t = 0; t < data.tokens_per_player; t++) {
      const progress = data.tokens[p][t];
      let row, col;

      if (progress === -1) {
        [row, col] = yard[t % yard.length];
      } else if (progress >= 0 && progress <= 51) {
        const pos = (data.start_positions[p] + progress) % 52;
        [row, col] = track[pos];
      } else if (progress >= 52 && progress <= 56) {
        [row, col] = lane[progress - 52];
      } else {
        [row, col] = lane[5];
      }

      placements.push({ player: p, token: t, row, col, progress });
    }
  }
  return placements;
}

function renderTokens(data) {
  Array.from(boardEl.querySelectorAll(".token-stack")).forEach((stack) => {
    stack.innerHTML = "";
    stack.dataset.count = "0";
  });

  const placements = tokenPlacement(data);

  const isHumanTurn =
    data.current_player === 0 &&
    data.last_roll !== null &&
    data.winner === null &&
    !data.auto_running;
  const legalMoves = data.legal_moves || [];

  placements.forEach(({ player, token, row, col, progress }) => {
    const cell = cellAt(row, col);
    if (!cell) return;

    const stack = cell.querySelector(".token-stack");
    const el = document.createElement("div");

    el.className = `token ${PLAYER_CLASSES[player]}`;
    el.dataset.token = token + 1;
    el.title = `${PLAYER_NAMES[player]} token ${token + 1} — ${tokenLabel(progress)}`;

    if (
      state.selectedToken &&
      state.selectedToken.player === player &&
      state.selectedToken.token === token
    ) {
      el.classList.add("token-selected");
    }

    if (player === 0 && isHumanTurn) {
      const canMove = legalMoves.some((m) => m.token_index === token);
      if (canMove) {
        el.classList.add("clickable-token");
        el.onclick = (e) => {
          e.stopPropagation();
          makeMove(token);
        };
      }
    }

    stack.appendChild(el);
  });

  Array.from(boardEl.querySelectorAll(".token-stack")).forEach((stack) => {
    stack.dataset.count = stack.children.length;
  });
}

function renderPlayers(data) {
  playersList.innerHTML = "";

  for (let p = 0; p < 4; p++) {
    const card = document.createElement("div");
    card.className =
      "player-card" + (data.current_player === p ? " active" : "");

    const top = document.createElement("div");
    top.className = "player-top";

    const name = document.createElement("div");
    name.className = "player-name";
    name.textContent = PLAYER_NAMES[p];

    const badge = document.createElement("div");
    badge.className = "player-badge";
    if (data.winner === p) badge.textContent = "Winner";
    else if (data.current_player === p) badge.textContent = "Turn";
    else badge.textContent = p === 0 ? "Human" : "AI";

    top.appendChild(name);
    top.appendChild(badge);

    const tokensRow = document.createElement("div");
    tokensRow.className = "tokens-row";
    data.tokens[p].forEach((progress, idx) => {
      const token = document.createElement("div");
      token.className = "mini-token";
      token.textContent = `T${idx + 1}: ${tokenLabel(progress)}`;
      tokensRow.appendChild(token);
    });

    card.appendChild(top);
    card.appendChild(tokensRow);
    playersList.appendChild(card);
  }
}

function renderControls(data) {
  const currentRoll =
    data.rolled !== undefined ? data.rolled : (data.last_roll ?? "-");

  diceValue.textContent = currentRoll;
  diceValueSide.textContent = currentRoll;

  if (data.current_player !== 0 && currentRoll !== "-") {
    diceValue.parentElement.style.boxShadow =
      "0 0 15px rgba(142, 242, 196, 0.5)";
    setTimeout(() => {
      if (diceValue.parentElement) {
        diceValue.parentElement.style.boxShadow = "";
      }
    }, 800);
  }

  const aiStatus = data.auto_running
    ? "Auto simulation running"
    : data.current_player === 0
      ? "Human turn"
      : data.current_player === 1
        ? "Aggressive AI"
        : data.current_player === 2
          ? "Defensive AI"
          : "Strategic AI";

  aiModeText.textContent =
    data.winner !== null && data.winner !== undefined
      ? "Match finished"
      : aiStatus;
  rollBtn.disabled = !(
    data.current_player === 0 &&
    data.last_roll === null &&
    data.winner === null &&
    !data.auto_running
  );

  moveButtons.innerHTML = "";
  if (data.auto_running) {
    state.waitingForMove = false;
    const msg = document.createElement("div");
    msg.className = "hint";
    msg.textContent = "Auto AI is playing every turn automatically.";
    moveButtons.appendChild(msg);
  } else if (
    data.current_player === 0 &&
    data.last_roll !== null &&
    data.winner === null
  ) {
    const legal = data.legal_moves || [];
    state.waitingForMove = legal.length > 0;

    if (legal.length === 0) {
      const msg = document.createElement("div");
      msg.className = "hint";
      msg.textContent = "No legal move. The turn will pass automatically.";
      moveButtons.appendChild(msg);
    } else {
      legal.forEach((move) => {
        const btn = document.createElement("button");
        btn.className = "move-btn";
        btn.textContent = `Token ${move.token_index + 1}`;
        btn.onclick = () => makeMove(move.token_index);
        moveButtons.appendChild(btn);
      });
    }
  } else {
    state.waitingForMove = false;
    const msg = document.createElement("div");
    msg.className = "hint";
    msg.textContent =
      data.current_player === 0
        ? "Roll the dice to see your options."
        : "AI is thinking and moving automatically.";
    moveButtons.appendChild(msg);
  }
}

function renderStatus(data) {
  if (data.winner !== null && data.winner !== undefined) {
    statusText.textContent = `${PLAYER_NAMES[data.winner]} won the game!`;
  } else if (data.auto_running) {
    statusText.textContent = "Auto simulation is running";
  } else if (data.current_player === 0) {
    statusText.textContent =
      data.last_roll === null ? "Your turn" : "Choose a token";
  } else {
    statusText.textContent = `${PLAYER_NAMES[data.current_player]} is moving`;
  }

  const turnName =
    data.winner !== null && data.winner !== undefined
      ? "Game finished"
      : `Current turn: ${PLAYER_NAMES[data.current_player]}`;
  turnText.textContent = turnName;

  logText.textContent = data.last_message || "Ready.";
}

function render(data) {
  state.data = data;
  state.autoRunning = Boolean(data.auto_running);
  buildBoard(data);
  renderPlayers(data);
  renderControls(data);
  renderStatus(data);
  autoBtn.textContent = state.autoRunning ? "Stop Auto AI" : "Auto AI";
}

async function api(path, payload = null) {
  const res = await fetch(path, {
    method: "POST",
    headers: payload ? { "Content-Type": "application/json" } : {},
    body: payload ? JSON.stringify(payload) : undefined,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Request failed");
  return data;
}

async function refresh() {
  const res = await fetch("/api/state");
  const data = await res.json();
  render(data);
  return data;
}

function syncAutoUI(isRunning) {
  state.autoRunning = Boolean(isRunning);
  autoBtn.textContent = state.autoRunning ? "Stop Auto AI" : "Auto AI";
  rollBtn.disabled = state.autoRunning;
}

async function stopAuto(silent = false) {
  clearInterval(state.autoTimer);
  state.autoTimer = null;
  syncAutoUI(false);
  if (!silent) {
    try {
      await api("/api/auto/stop", {});
    } catch (err) {}
  }
  await refresh();
}

async function newGame() {
  try {
    await stopAuto(true);
    state.selectedToken = null;
    const data = await api("/api/new_game", {
      seed: Math.floor(Math.random() * 999999),
    });
    render(data);
    await refresh();
  } catch (err) {
    alert(err.message);
  }
}

let isProcessingAI = false;

async function processAITurns() {
  if (isProcessingAI || state.autoRunning) return;
  isProcessingAI = true;

  while (
    state.data &&
    state.data.current_player !== 0 &&
    state.data.winner === null &&
    !state.autoRunning
  ) {
    await new Promise((resolve) => setTimeout(resolve, 3000));

    try {
      const data = await api("/api/auto", {});
      render(data);
    } catch (err) {
      console.error("AI turn error:", err);
      break;
    }
  }

  isProcessingAI = false;
}

async function rollDice() {
  try {
    if (state.autoRunning) return;
    const data = await api("/api/roll", {});
    render(data);

    if (data.current_player !== 0) {
      await processAITurns();
    }
  } catch (err) {
    alert(err.message);
  }
}

async function makeMove(tokenIndex) {
  try {
    if (state.autoRunning) return;
    state.selectedToken = { player: 0, token: tokenIndex };
    const data = await api("/api/move", { token_index: tokenIndex });
    render(data);
    state.selectedToken = null;

    if (data.current_player !== 0) {
      await processAITurns();
    }
  } catch (err) {
    alert(err.message);
  }
}

async function autoStep() {
  if (!state.autoRunning) return;
  try {
    const data = await api("/api/auto/step", {});
    render(data);
    await refresh();
    if (data.winner !== null && data.winner !== undefined) await stopAuto(true);
  } catch (err) {
    await stopAuto(true);
    alert(err.message);
  }
}

async function startAuto() {
  try {
    const data = await api("/api/auto/start", {});
    render(data);
    await refresh();
    syncAutoUI(true);
    if (state.autoTimer) clearInterval(state.autoTimer);
    state.autoTimer = setInterval(autoStep, AUTO_STEP_DELAY);
    await autoStep();
  } catch (err) {
    alert(err.message);
  }
}

async function autoAI() {
  if (state.autoRunning) await stopAuto();
  else await startAuto();
}

rollBtn.addEventListener("click", rollDice);
newGameBtn.addEventListener("click", newGame);
autoBtn.addEventListener("click", autoAI);

refresh().then((data) => {
  syncAutoUI(Boolean(data && data.auto_running));
  if (
    data &&
    data.current_player !== 0 &&
    data.winner === null &&
    !data.auto_running
  ) {
    processAITurns();
  }
});
