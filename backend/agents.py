
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional
import random

from game import LudoGame, Move, FINAL_PROGRESS, BOARD_SIZE


@dataclass
class PolicyMoveScore:
    move: Move
    score: float


class BaseAgent:
    def __init__(self, player_id: int):
        self.player_id = player_id

    def choose_move(self, game: LudoGame, dice: int) -> Optional[Move]:
        raise NotImplementedError


def candidate_features(game: LudoGame, player_id: int, move: Move, dice: int):
    captures = game.capture_targets(player_id, move.to_progress)
    finishing = move.to_progress == FINAL_PROGRESS
    from_yard = move.from_progress == -1

    danger = 0.0
    safe = 0.0
    progress_gain = 0.0

    if 0 <= move.to_progress <= BOARD_SIZE - 1:
        pos = game.board_position(player_id, move.to_progress)
        if pos is not None and game.is_safe_square(pos):
            safe = 1.0
        danger = game._danger_exposure(player_id, move.to_progress)
    if move.from_progress >= 0:
        progress_gain = move.to_progress - move.from_progress
    else:
        progress_gain = 8.0

    return {
        "captures": len(captures),
        "finishing": finishing,
        "from_yard": from_yard,
        "danger": danger,
        "safe": safe,
        "progress_gain": progress_gain,
    }


class AggressiveAgent(BaseAgent):
    """
    Hunts captures and fast progress.
    """
    def choose_move(self, game: LudoGame, dice: int) -> Optional[Move]:
        moves = game.legal_moves(self.player_id, dice)
        if not moves:
            return None

        def score(m: Move) -> float:
            f = candidate_features(game, self.player_id, m, dice)
            s = 0.0
            s += f["captures"] * 100.0
            s += 22.0 if f["from_yard"] else 0.0
            s += f["progress_gain"] * 3.8
            s += 140.0 if f["finishing"] else 0.0
            s += 8.0 if f["safe"] else 0.0
            s -= f["danger"] * 0.8
            s += m.to_progress * 0.35
            return s

        return max(moves, key=score)


class DefensiveAgent(BaseAgent):
    """
    Prefers safe squares and avoids exposure.
    """
    def choose_move(self, game: LudoGame, dice: int) -> Optional[Move]:
        moves = game.legal_moves(self.player_id, dice)
        if not moves:
            return None

        def score(m: Move) -> float:
            f = candidate_features(game, self.player_id, m, dice)
            s = 0.0
            s += f["safe"] * 45.0
            s -= f["danger"] * 6.0
            s += 24.0 if f["from_yard"] else 0.0
            s += f["captures"] * 30.0
            s += 130.0 if f["finishing"] else 0.0
            s += f["progress_gain"] * 2.2
            s += m.to_progress * 0.15
            return s

        return max(moves, key=score)


class HeuristicProxyAgent(BaseAgent):
    """
    Balanced proxy used by the strategic agent during rollouts
    to approximate how the other players behave.
    """
    def choose_move(self, game: LudoGame, dice: int) -> Optional[Move]:
        moves = game.legal_moves(self.player_id, dice)
        if not moves:
            return None

        def score(m: Move) -> float:
            f = candidate_features(game, self.player_id, m, dice)
            s = 0.0
            s += f["captures"] * 65.0
            s += f["safe"] * 18.0
            s -= f["danger"] * 2.5
            s += 16.0 if f["from_yard"] else 0.0
            s += 120.0 if f["finishing"] else 0.0
            s += f["progress_gain"] * 2.8
            s += m.to_progress * 0.2
            return s

        return max(moves, key=score)


class StrategicAgent(BaseAgent):
    """
    Smarter agent:
    - immediate heuristic ranking
    - multi-rollout lookahead
    - estimates future utility across random dice sequences

    This is intentionally stronger than the other two agents.
    """

    def __init__(self, player_id: int, rollouts: int = 24, horizon_steps: int = 10, seed: Optional[int] = None):
        super().__init__(player_id)
        self.rollouts = rollouts
        self.horizon_steps = horizon_steps
        self.rng = random.Random(seed)
        self.proxy_agents = {
            0: HeuristicProxyAgent(0),
            1: AggressiveAgent(1),
            2: DefensiveAgent(2),
            3: HeuristicProxyAgent(3),
        }

    def _policy_for_player(self, player: int) -> BaseAgent:
        if player == self.player_id:
        
            return HeuristicProxyAgent(player)
        return self.proxy_agents[player]

    def _simulate_once(self, game: LudoGame, steps: int) -> float:
        """
        Simulate a short random future and return utility for self.player_id.
        """
        sim = game.clone()

        local_rng = random.Random(self.rng.randint(0, 10**9))

        for _ in range(steps):
            if sim.winner is not None:
                break

            player = sim.current_player
            dice = local_rng.randint(1, 6)
            legal = sim.legal_moves(player, dice)

            if not legal:
                sim.advance_turn()
                continue

            if player == self.player_id:
                move = max(legal, key=lambda mv: sim.state_utility(self.player_id) + self._immediate_value(sim, mv, dice))
            else:
                agent = self._policy_for_player(player)
                move = agent.choose_move(sim, dice) or legal[0]

            result = sim._apply_move_core(player, move, dice)
            if not result["extra_turn"] and sim.winner is None:
                sim.advance_turn()

        return sim.state_utility(self.player_id)

    def _immediate_value(self, game: LudoGame, move: Move, dice: int) -> float:
        f = candidate_features(game, self.player_id, move, dice)
        value = 0.0
        value += f["captures"] * 90.0
        value += 30.0 if f["safe"] else 0.0
        value -= f["danger"] * 3.5
        value += 16.0 if f["from_yard"] else 0.0
        value += 150.0 if f["finishing"] else 0.0
        value += f["progress_gain"] * 3.0
        return value

    def choose_move(self, game: LudoGame, dice: int) -> Optional[Move]:
        moves = game.legal_moves(self.player_id, dice)
        if not moves:
            return None

        scored: List[tuple[float, Move]] = []
        for move in moves:
            trial = game.clone()
            result = trial._apply_move_core(self.player_id, move, dice)
            if trial.winner is None and not result["extra_turn"]:
                trial.advance_turn()

            immediate = self._immediate_value(game, move, dice)
            future_total = 0.0
            for _ in range(self.rollouts):
                future_total += self._simulate_once(trial, self.horizon_steps)
            average_future = future_total / self.rollouts

            combined = immediate * 0.65 + average_future * 0.35
            scored.append((combined, move))

        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1]


def build_agents() -> dict:
    """
    4-player setup:
    player 0 = human
    player 1 = aggressive AI
    player 2 = defensive AI
    player 3 = strategic AI (the smartest one)
    """
    return {
        1: AggressiveAgent(1),
        2: DefensiveAgent(2),
        3: StrategicAgent(3),
    }
