import argparse
import json
from contextlib import suppress
import socket
import threading
import time

FIELDS = {"msg_type", "player_id", "payload", "timestamp"}
SYMBOLS = {"Player_1": "X", "Player_2": "O"}
OPPONENT = {"Player_1": "Player_2", "Player_2": "Player_1"}
WIN_CONDITIONS = [
    (0, 1, 2), (3, 4, 5),
    (6, 7, 8), (0, 3, 6),
    (1, 4, 7), (2, 5, 8),
    (0, 4, 8), (2, 4, 6)
]


def parse_port(value):
    try:
        port = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("port must be an integer") from None
    if not 1024 <= port <= 65535:
        raise argparse.ArgumentTypeError("port must be between 1024 and 65535")
    return port


def send_message(sock, msg_type, player_id, **payload):
    message = {
        "msg_type": msg_type,
        "player_id": player_id,
        "payload": payload,
        "timestamp": int(time.time())
    }
    sock.sendall(json.dumps(message).encode("utf-8") + b"\n")


def read_frames(sock):
    # Read complete newline-delimited messages from the TCP stream.
    with sock.makefile("rb") as stream:
        for frame in stream:
            if frame.endswith(b"\n"):
                yield frame[:-1]


def decode_message(frame):
    try:
        message = json.loads(frame.decode("utf-8"))
    except (ValueError, RecursionError):
        raise ValueError("Invalid JSON message") from None
    if (not isinstance(message, dict)
            or message.keys() != FIELDS
            or not isinstance(message["msg_type"], str)
            or message["player_id"] not in (None, "Player_1", "Player_2", "SERVER")
            or not isinstance(message["payload"], dict)
            or type(message["timestamp"]) is not int):
        raise ValueError("Message fields are invalid or missing")
    return message


class Game:
    def __init__(self):
        self.lock = threading.Lock()
        self.reset()

    def reset(self):
        self.player = {}
        self.board = [""] * 9
        self.turn = "Player_1"
        self.state = "WAITING_FOR_PLAYERS"

    @staticmethod
    def send(sock, msg_type, **payload):
        try:
            send_message(sock, msg_type, "SERVER", **payload)
        except OSError:
            return False
        return True

    def error(self, sock, code, msg):
        self.send(sock, "ERROR", code=code, message=msg)

    def join(self, sock):
        if len(self.player) >= 2:
            self.error(sock, "ROOM_FULL", "Game is full")
            return False

        player = "Player_2" if self.player else "Player_1"
        self.player[player] = sock
        print(f"{player} joined as {SYMBOLS[player]}.", flush=True)

        if player == "Player_1":
            return self.send(
                sock, "LOBBY_WAIT", assigned_id=player, symbol="X",
                message="Waiting for another player to join..."
            )

        self.state = "GAME_START"
        for player, connection in self.player.items():
            if not self.send(
                connection, "GAME_START", assigned_id=player,
                symbol=SYMBOLS[player], board=self.board,
                current_turn=self.turn
            ):
                self.cleanup()
                return False
        self.state = "PLAYER_TURN"
        return True

    def move(self, player, sock, payload):
        if self.state != "PLAYER_TURN":
            self.error(sock, "INVALID_STATE", "Not the right time to make a move")
            return
        if payload.keys() != {"row", "col"}:
            self.error(
                sock, "MALFORMED_MESSAGE",
                "Payload must contain 'row' and 'col'"
            )
            return
        if player != self.turn:
            self.error(sock, "NOT_YOUR_TURN", "It's not your turn")
            return

        self.state = "EVALUATE_MOVE"
        row, col = payload["row"], payload["col"]
        if any(type(value) is not int or not 0 <= value <= 2
               for value in (row, col)):
            self.error(
                sock, "INVALID_COORDINATES",
                "Row and column must be integers from 0 to 2"
            )
        elif self.board[row * 3 + col]:
            self.error(sock, "CELL_OCCUPIED", "Cell is already occupied")
        else:
            self.apply_move(player, row, col)
            return
        self.state = "PLAYER_TURN"

    def apply_move(self, player, row, col):
        symbol = SYMBOLS[player]
        self.board[row * 3 + col] = symbol
        print(f"{player} placed {symbol} at ({row}, {col}).", flush=True)

        if any(all(self.board[i] == symbol for i in line)
               for line in WIN_CONDITIONS):
            self.finish("win", player, "three_in_a_row")
            return
        if all(self.board):
            self.finish("draw", None, "board_full")
            return

        self.turn = OPPONENT[player]
        self.state = "PLAYER_TURN"
        for connection in self.player.values():
            if not self.send(
                connection, "STATE_UPDATE", board=self.board,
                current_turn=self.turn
            ):
                self.leave(connection, "connection_lost")
                break

    def finish(self, result, winner, reason, departing=None):
        self.state = "GAME_OVER"
        scores = {player: int(player == winner) for player in SYMBOLS}
        print(
            f"Game over: {result}. Winner: {winner}. Scores: {scores}.",
            flush=True
        )
        for connection in self.player.values():
            if connection is not departing:
                self.send(
                    connection, "GAME_OVER", result=result,
                    winner_id=winner, reason=reason,
                    board=self.board, scores=scores
                )
        self.cleanup()

    def cleanup(self):
        self.state = "CLEANUP"
        for connection in self.player.values():
            # Wake the client threads so they can close their sockets.
            with suppress(OSError):
                connection.shutdown(socket.SHUT_RDWR)
        self.reset()

    def leave(self, sock, reason):
        for player, connection in self.player.items():
            if connection is sock:
                if self.state == "PLAYER_TURN":
                    self.finish("forfeit", OPPONENT[player], reason, sock)
                else:
                    del self.player[player]
                return

    def handle_message(self, sock, message):
        kind = message["msg_type"]
        claimed_player = message["player_id"]
        payload = message["payload"]
        player = next(
            (p for p, conn in self.player.items() if conn is sock), None
        )

        if kind == "CONNECT":
            if (claimed_player is not None
                    or payload.keys() != {"alias"}
                    or not isinstance(payload["alias"], str)):
                self.error(sock, "MALFORMED_MESSAGE", "CONNECT needs an alias")
            elif player is None:
                return self.join(sock)
            else:
                self.error(
                    sock, "INVALID_STATE", "You are already connected"
                )
        elif player is None:
            self.error(sock, "INVALID_STATE", "Send CONNECT first")
        elif player != claimed_player:
            self.error(
                sock, "PLAYER_ID_MISMATCH",
                "Player ID does not match your connection"
            )
        elif kind == "MOVE":
            self.move(player, sock, payload)
        elif kind == "DISCONNECT":
            if payload == {"reason": "quit"}:
                self.leave(sock, "player_quit")
                return False
            self.error(
                sock, "MALFORMED_MESSAGE",
                "DISCONNECT must have reason 'quit'"
            )
        else:
            self.error(sock, "INVALID_STATE", "Unknown message type")
        return True

    def serve_client(self, sock):
        joined = False
        with sock:
            try:
                for frame in read_frames(sock):
                    # Protect the game state and keep messages in order.
                    with self.lock:
                        registered = sock in self.player.values()
                        if joined and not registered:
                            break
                        try:
                            message = decode_message(frame)
                        except ValueError as e:
                            self.error(sock, "MALFORMED_MESSAGE", str(e))
                            continue
                        if not self.handle_message(sock, message):
                            break
                        joined = sock in self.player.values()
                        if registered and not joined:
                            break
            except OSError:
                pass
            finally:
                with self.lock:
                    self.leave(sock, "connection_lost")


def main():
    parser = argparse.ArgumentParser(description="Tic-Tac-Toe Server")
    parser.add_argument(
        "-p", required=True, type=parse_port,
        help="Port number to listen on (1024-65535)"
    )
    args = parser.parse_args()

    game = Game()
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind(("0.0.0.0", args.p))
            listener.listen()
            print(f"Server listening on 0.0.0.0:{args.p}...", flush=True)
            while True:
                connection, _ = listener.accept()
                threading.Thread(
                    target=game.serve_client,
                    args=(connection,),
                    daemon=True
                ).start()
    except KeyboardInterrupt:
        print("\nServer shutting down.")
    except OSError as e:
        parser.exit(1, f"[ERROR] Server socket: {e}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())