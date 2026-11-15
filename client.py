import json
import argparse
from contextlib import suppress
import socket
import sys
import threading
import time

FIELDS = {"msg_type", "player_id", "payload", "timestamp"}


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


def show_board(board):
    print("    0   1   2")
    for row in range(3):
        cells = " | ".join(cell or " " for cell in board[row * 3:row * 3 + 3])
        print(f"{row}   {cells}")
        if row < 2:
            print("   ---+---+---")


class Client:
    def __init__(self, sock):
        self.sock = sock
        self.player = None
        self.turn = None
        self.send_lock = threading.Lock()

    def send(self, kind, **payload):
        with self.send_lock:
            send_message(self.sock, kind, self.player, **payload)

    def quit(self):
        with suppress(OSError):
            if self.player:
                self.send("DISCONNECT", reason="quit")
            self.sock.shutdown(socket.SHUT_WR)

    def prompt_move(self):
        while True:
            try:
                move = input("Enter your move (row col), or q to quit: ")
            except EOFError:
                move = "q"
            if move.strip().lower() == "q":
                self.quit()
                return
            try:
                row, col = map(int, move.split())
            except ValueError:
                print(
                    "Invalid input. Please enter row and column numbers "
                    "separated by a space."
                )
                continue
            with suppress(OSError):
                self.send("MOVE", row=row, col=col)
            return

    def prompt_if_turn(self):
        if self.turn == self.player and self.player is not None:
            print("It's your turn.")
            threading.Thread(target=self.prompt_move, daemon=True).start()
        elif self.turn:
            print("Waiting for opponent to make a move...")

    def play(self):
        self.send("CONNECT", alias="Player")
        for frame in read_frames(self.sock):
            message = decode_message(frame)
            kind = message["msg_type"]
            payload = message["payload"]
            if kind in {"LOBBY_WAIT", "GAME_START"}:
                self.player = payload["assigned_id"]
                print(f"You are {self.player} ({payload['symbol']}).")
            if kind == "LOBBY_WAIT":
                print(payload["message"])
            elif kind in {"GAME_START", "STATE_UPDATE"}:
                show_board(payload["board"])
                self.turn = payload["current_turn"]
                self.prompt_if_turn()
            elif kind == "ERROR":
                print(f"[ERROR] {payload['message']}", file=sys.stderr)
                if self.player is None:
                    return 1
                self.prompt_if_turn()
            elif kind == "GAME_OVER":
                show_board(payload["board"])
                winner = payload["winner_id"]
                if winner is None:
                    print("The game ended in a draw.")
                elif winner == self.player:
                    print("Congratulations! You won!")
                else:
                    print("You lost. Better luck next time!")
                if payload["result"] == "forfeit":
                    print("The game ended due to a forfeit.")
                scores = payload["scores"]
                print(
                    f"Final scores: Player_1: {scores['Player_1']}, "
                    f"Player_2: {scores['Player_2']}"
                )
                return 0
        print("Connection closed.")
        return 0


def main():
    parser = argparse.ArgumentParser(description="Tic-Tac-Toe Client")
    parser.add_argument(
        "-i", required=True, dest="hostname",
        help="Server hostname or IP address"
    )
    parser.add_argument(
        "-p", required=True, type=parse_port, dest="port",
        help="Server port number (1024-65535)"
    )
    args = parser.parse_args()

    try:
        server_ip = socket.gethostbyname(args.hostname)
    except socket.gaierror:
        print(
            f"[ERROR] Unable to resolve DNS hostname '{args.hostname}'.",
            file=sys.stderr
        )
        print(
            "Please check your Cisco router DNS configuration "
            "('ip dns server' / 'ip host') or verify domain spelling.",
            file=sys.stderr
        )
        return 1

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((server_ip, args.port))
            print(f"Connected to server at {server_ip}:{args.port}")
            client = Client(sock)
            try:
                return client.play()
            except KeyboardInterrupt:
                client.quit()
                print("\nLeft the game")
                return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"[ERROR] Connection or protocol error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())