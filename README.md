# Ludo AI Arena

A web-based Ludo project for Artificial Intelligence practice.

## Stack
- Frontend: HTML, CSS, JavaScript
- Backend: Python Flask API
- AI: 3 intelligent agents
  - Aggressive Agent
  - Defensive Agent
  - Strategic Agent with rollout lookahead

## How to run
1. Open a terminal in the `backend` folder.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the server:
   ```bash
   python app.py
   ```
4. Open the game in your browser:
   ```text
   http://127.0.0.1:5000
   ```

## Notes
- Player 0 is the human player.
- The other 3 players are AI agents.
- The board is rendered as a classic-style 15x15 grid with colored corner homes, track cells, home lanes, and a central finish area.
- The numbered tokens make it easier to tell pieces apart.
