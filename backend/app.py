from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from agents import StrategicAgent, build_agents
from game import LudoGame

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

app = Flask(__name__)
CORS(app)

game = LudoGame(seed=42)
agents = build_agents()
auto_demo_agent = StrategicAgent(0, rollouts=18, horizon_steps=8, seed=2025)
auto_running = False


def state_payload(extra: Optional[Dict[str, Any]] = None):
    payload = game.to_dict()
    payload["legal_moves"] = []
    if game.last_roll is not None and game.current_player == 0 and game.winner is None:
        payload["legal_moves"] = [m.as_dict() for m in game.legal_moves(0, game.last_roll)]
    payload["auto_running"] = auto_running
    if extra:
        payload.update(extra)
    return payload


def current_agent(player: int):
    if player == 0:
        return auto_demo_agent
    return agents.get(player)


def auto_step_once():
    global auto_running

    if game.winner is not None:
        auto_running = False
        return state_payload({"message": "Game finished."})

    player = game.current_player
    dice = game.roll_dice()
    game.last_roll = dice
    legal = game.legal_moves(player, dice)

    if not legal:
        game.last_message = f"Player {player} rolled {dice} and has no legal move."
        game.advance_turn()
        if game.winner is not None:
            auto_running = False
        return state_payload({"auto_step": True, "rolled": dice, "legal_moves_count": 0})

    agent = current_agent(player)
    if agent is None:
        game.last_message = f"No AI agent found for player {player}."
        game.advance_turn()
        return state_payload({"auto_step": True, "rolled": dice, "legal_moves_count": len(legal)})

    move = agent.choose_move(game, dice)
    if move is None:
        game.last_message = f"Player {player} skipped the turn."
        game.advance_turn()
        return state_payload({"auto_step": True, "rolled": dice, "legal_moves_count": len(legal)})

    result = game.apply_move(player, move, dice)

    if game.winner is not None:
        auto_running = False

    return state_payload(
        {
            "auto_step": True,
            "rolled": dice,
            "legal_moves_count": len(legal),
            "move_result": result,
        }
    )


@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/<path:filename>")
def frontend_static(filename):
    return send_from_directory(FRONTEND_DIR, filename)


@app.route("/api/state", methods=["GET"])
def api_state():
    return jsonify(state_payload())


@app.route("/api/new_game", methods=["POST"])
def api_new_game():
    global auto_running
    data = request.get_json(silent=True) or {}
    seed = data.get("seed", 42)
    try:
        auto_running = False
        game.reset(seed=seed)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(state_payload({"message": "New game created."}))


@app.route("/api/roll", methods=["POST"])
def api_roll():
    if auto_running:
        return jsonify(state_payload({"error": "Auto AI is running. Stop it first."})), 400
    if game.winner is not None:
        return jsonify(state_payload({"error": "Game is already finished."})), 400
    if game.current_player != 0:
        return jsonify(state_payload({"error": "It is not the human player's turn."})), 400
    if game.last_roll is not None:
        return jsonify(state_payload({"error": "You already rolled. Choose a token to move."})), 400

    dice = game.roll_dice()
    game.last_roll = dice
    legal = game.legal_moves(0, dice)
    
    if not legal:
        game.last_message = f"You rolled {dice}, but no legal move exists."
        game.advance_turn()
        return jsonify(state_payload({"rolled": dice, "legal_moves_count": 0}))

    game.last_message = f"You rolled {dice}. Choose a token to move."
    return jsonify(state_payload({"rolled": dice, "legal_moves_count": len(legal)}))


@app.route("/api/move", methods=["POST"])
def api_move():
    if auto_running:
        return jsonify(state_payload({"error": "Auto AI is running. Stop it first."})), 400
    if game.winner is not None:
        return jsonify(state_payload({"error": "Game is already finished."})), 400
    if game.current_player != 0:
        return jsonify(state_payload({"error": "It is not the human player's turn."})), 400
    if game.last_roll is None:
        return jsonify(state_payload({"error": "Roll the dice first."})), 400

    data = request.get_json(silent=True) or {}
    token_index = data.get("token_index")
    if token_index is None:
        return jsonify(state_payload({"error": "token_index is required."})), 400

    legal = game.legal_moves(0, game.last_roll)
    chosen = None
    for move in legal:
        if move.token_index == int(token_index):
            chosen = move
            break

    if chosen is None:
        return jsonify(state_payload({"error": "This move is not legal."})), 400

    dice = game.last_roll
    result = game.apply_move(0, chosen, dice)
    game.last_message = f"You moved token {int(token_index) + 1} with dice {dice}."

    return jsonify(state_payload({"move_result": result}))


@app.route("/api/auto/start", methods=["POST"])
def api_auto_start():
    global auto_running
    if game.winner is not None:
        return jsonify(state_payload({"error": "Game is already finished."})), 400
    auto_running = True
    game.last_message = "Auto AI simulation started."
    return jsonify(state_payload({"message": "Auto AI started."}))


@app.route("/api/auto/step", methods=["POST"])
def api_auto_step():
    if not auto_running:
        return jsonify(state_payload({"error": "Auto AI is not running."})), 400
    return jsonify(auto_step_once())


@app.route("/api/auto/stop", methods=["POST"])
def api_auto_stop():
    global auto_running
    auto_running = False
    game.last_message = "Auto AI simulation stopped."
    return jsonify(state_payload({"message": "Auto AI stopped."}))


@app.route("/api/auto", methods=["POST"])
def api_auto():
    return jsonify(auto_step_once())


if __name__ == "__main__":
    app.run(debug=True, port=5000)