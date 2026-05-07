
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import random
import copy

BOARD_SIZE = 52
HOME_LEN = 6
FINAL_PROGRESS = BOARD_SIZE + HOME_LEN - 1  # 57

# A classic-style safe-square set on the 52-cell ring.
SAFE_SQUARES = {0, 8, 13, 21, 26, 34, 39, 47}


@dataclass(frozen=True)
class Move:
    token_index: int
    from_progress: int
    to_progress: int

    def as_dict(self) -> Dict[str, int]:
        return {
            "token_index": self.token_index,
            "from_progress": self.from_progress,
            "to_progress": self.to_progress,
        }


class LudoGame:
    """
    Simplified Ludo engine for 4 players.

    Progress encoding per token:
        -1 = in yard/home
         0 = just entered board
      1..51 = around the main track
     52..57 = home lane
        57 = finished

    Notes:
    - This engine allows multiple tokens of the same player to occupy the same square.
    - Landing on a non-safe square with opponent tokens captures all opponent tokens there.
    - A player gets an extra turn after rolling a 6, capturing, or finishing.
    """

    def __init__(self, num_players: int = 4, tokens_per_player: int = 4, seed: Optional[int] = None):
        if num_players != 4:
            raise ValueError("This project is designed for 4 players.")

        self.num_players = num_players
        self.tokens_per_player = tokens_per_player
        self.rng = random.Random(seed)

        # Start positions arranged around the track.
        # 0: top side, 1: right side, 2: bottom side, 3: left side.
        self.start_positions = [0, 13, 26, 39]

        self.tokens: List[List[int]] = [[-1] * tokens_per_player for _ in range(num_players)]
        self.current_player: int = 0
        self.winner: Optional[int] = None
        self.last_roll: Optional[int] = None
        self.last_message: str = "New game started."

    def clone(self) -> "LudoGame":
        g = LudoGame(self.num_players, self.tokens_per_player)
        g.rng.setstate(self.rng.getstate())
        g.start_positions = self.start_positions[:]
        g.tokens = [row[:] for row in self.tokens]
        g.current_player = self.current_player
        g.winner = self.winner
        g.last_roll = self.last_roll
        g.last_message = self.last_message
        return g

    def reset(self, seed: Optional[int] = None) -> None:
        self.rng = random.Random(seed)
        self.tokens = [[-1] * self.tokens_per_player for _ in range(self.num_players)]
        self.current_player = 0
        self.winner = None
        self.last_roll = None
        self.last_message = "New game started."

    def roll_dice(self) -> int:
        return self.rng.randint(1, 6)

    def board_position(self, player: int, progress: int) -> Optional[int]:
        if progress < 0 or progress > BOARD_SIZE - 1:
            return None
        return (self.start_positions[player] + progress) % BOARD_SIZE

    def is_safe_square(self, board_pos: int) -> bool:
        return board_pos in SAFE_SQUARES

    def legal_moves(self, player: int, dice: int) -> List[Move]:
        moves: List[Move] = []
        for i, prog in enumerate(self.tokens[player]):
            if prog == -1:
                if dice == 6:
                    moves.append(Move(i, prog, 0))
            else:
                nxt = prog + dice
                if nxt <= FINAL_PROGRESS:
                    moves.append(Move(i, prog, nxt))
        return moves

    def capture_targets(self, player: int, to_progress: int) -> List[Tuple[int, int]]:
        """
        Returns [(opponent_id, token_index), ...] that will be captured if player lands on to_progress.
        Only applies on main track squares that are not safe.
        """
        if to_progress < 0 or to_progress > BOARD_SIZE - 1:
            return []

        dest = self.board_position(player, to_progress)
        if dest is None or self.is_safe_square(dest):
            return []

        hits = []
        for opp in range(self.num_players):
            if opp == player:
                continue
            for idx, prog in enumerate(self.tokens[opp]):
                if 0 <= prog <= BOARD_SIZE - 1:
                    opp_pos = self.board_position(opp, prog)
                    if opp_pos == dest:
                        hits.append((opp, idx))
        return hits

    def exact_finish(self, to_progress: int) -> bool:
        return to_progress == FINAL_PROGRESS

    def all_finished(self, player: int) -> bool:
        return all(p == FINAL_PROGRESS for p in self.tokens[player])

    def advance_turn(self) -> None:
        self.current_player = (self.current_player + 1) % self.num_players
        self.last_roll = None

    def _apply_move_core(self, player: int, move: Move, dice: int) -> Dict:
        if self.winner is not None:
            raise ValueError("Game already finished.")
        if player != self.current_player:
            raise ValueError("Not this player's turn.")
        if self.tokens[player][move.token_index] != move.from_progress:
            raise ValueError("Token state mismatch.")

        if move.from_progress == -1:
            if dice != 6 or move.to_progress != 0:
                raise ValueError("Only dice 6 can move a token from yard to start.")
        else:
            if move.to_progress <= move.from_progress:
                raise ValueError("Move must go forward.")
            if move.to_progress > FINAL_PROGRESS:
                raise ValueError("Move exceeds final home square.")

        captures = self.capture_targets(player, move.to_progress)

        self.tokens[player][move.token_index] = move.to_progress

        captured_count = 0
        for opp, idx in captures:
            if self.tokens[opp][idx] != -1:
                self.tokens[opp][idx] = -1
                captured_count += 1

        if self.all_finished(player):
            self.winner = player

        extra_turn = (dice == 6) or (captured_count > 0) or self.exact_finish(move.to_progress)

        return {
            "player": player,
            "dice": dice,
            "move": move.as_dict(),
            "captured": [{"player": opp, "token_index": idx} for opp, idx in captures],
            "captured_count": captured_count,
            "extra_turn": extra_turn,
            "winner": self.winner,
        }

    def apply_move(self, player: int, move: Move, dice: int) -> Dict:
        result = self._apply_move_core(player, move, dice)
        self.last_roll = None
        if self.winner is None and not result["extra_turn"]:
            self.advance_turn()
        elif self.winner is not None:
            self.last_message = f"Player {player} won the game."
        else:
            self.last_message = f"Player {player} gets an extra turn."
        return result

    def human_can_move(self) -> bool:
        return self.current_player == 0 and self.last_roll is not None and self.winner is None

    def token_owner_at(self, board_pos: int, exclude_player: Optional[int] = None) -> List[Tuple[int, int]]:
        owners = []
        for p in range(self.num_players):
            if exclude_player is not None and p == exclude_player:
                continue
            for idx, prog in enumerate(self.tokens[p]):
                if 0 <= prog <= BOARD_SIZE - 1 and self.board_position(p, prog) == board_pos:
                    owners.append((p, idx))
        return owners

    def state_utility(self, perspective_player: int) -> float:
        """
        Heuristic utility used by the smarter AI agent.
        Higher is better for perspective_player.
        """
        if self.winner == perspective_player:
            return 100000.0
        if self.winner is not None and self.winner != perspective_player:
            return -100000.0

        score = 0.0
        for p in range(self.num_players):
            for prog in self.tokens[p]:
                if prog == -1:
                    if p == perspective_player:
                        score -= 6
                    else:
                        score += 2
                    continue

                remaining = FINAL_PROGRESS - prog
                if p == perspective_player:
                    score += max(0.0, 20.0 - remaining)
                    if prog == FINAL_PROGRESS:
                        score += 120.0
                    elif 0 <= prog <= BOARD_SIZE - 1:
                        pos = self.board_position(p, prog)
                        if pos is not None and self.is_safe_square(pos):
                            score += 5.5
                        score -= self._danger_exposure(p, prog) * 1.25
                else:
                    score -= max(0.0, 18.0 - remaining)
                    if prog == FINAL_PROGRESS:
                        score -= 30.0
        return score

    def _danger_exposure(self, player: int, progress: int) -> float:
        """
        How much risk a token at 'progress' faces from opponents within 6 steps behind it.
        """
        if not (0 <= progress <= BOARD_SIZE - 1):
            return 0.0

        pos = self.board_position(player, progress)
        if pos is None or self.is_safe_square(pos):
            return 0.0

        exposure = 0.0
        for opp in range(self.num_players):
            if opp == player:
                continue
            for op_prog in self.tokens[opp]:
                if 0 <= op_prog <= BOARD_SIZE - 1:
                    op_pos = self.board_position(opp, op_prog)
                    if op_pos is None:
                        continue
                    dist = (pos - op_pos) % BOARD_SIZE
                    if 1 <= dist <= 6:
                        exposure += (7 - dist)
        return exposure

    def to_dict(self) -> Dict:
        return {
            "num_players": self.num_players,
            "tokens_per_player": self.tokens_per_player,
            "tokens": self.tokens,
            "current_player": self.current_player,
            "winner": self.winner,
            "last_roll": self.last_roll,
            "last_message": self.last_message,
            "start_positions": self.start_positions,
            "safe_squares": sorted(SAFE_SQUARES),
            "board_size": BOARD_SIZE,
            "home_len": HOME_LEN,
            "final_progress": FINAL_PROGRESS,
            "human_player": 0,
        }

    def is_game_over(self) -> bool:
        return self.winner is not None
