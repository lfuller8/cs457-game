# Application Protocol Blueprint

TCP will be used to connect two clients to a server. The messages between them will be JSON objects, using UTF-8 and newline-delimited (`\n`) JSON payloads.

The `\n` marks the end of each message. The receiver saves incoming bytes until it has a complete message. One `recv()` may contain several messages or only part of one. Incomplete messages are saved until more bytes arrive.

An example of this is:

```text
{"msg_type":"MOVE","player_id":"Player_1","payload":{"row":0,"col":2},"timestamp":1727000000}\n{"msg_type":"MOVE","player_id":"Player_2","payload":{"row":1,"col":1},"timestamp":1727000005}\n
```

Every message will contain the following:

- `msg_type`: The type is a string, and it contains what message type the action is.
- `player_id`: The type is a string or null. It is null in CONNECT, otherwise it is Player_1, Player_2, or SERVER.
- `payload`: The type is an object containing the fields specified for the message type.
- `timestamp`: The type is an integer and is used for logging actions.

The server gives the person who connected first Player_1 and X. Player_2 is assigned to the next person, who is assigned O. The server checks each player's ID against their connection. Rows and columns use numbers 0–2. The board stores nine cells, ordered left to right and top to bottom. Each cell contains "X", "O", or "" for an empty space.

## Message Types

### CONNECT

This is sent from the client to the server to join the game. The player_id is null because the server has not assigned the player an ID yet.

The payload contains:
- `alias`: A string containing the player's display name.

```text
{"msg_type":"CONNECT","player_id":null,"payload":{"alias":"Liam"},"timestamp":1727000000}\n
```

### LOBBY_WAIT

This is sent from the server to Player_1 to let them know it is waiting for Player_2.

The payload contains:
- `assigned_id`: A string containing "Player_1".
- `symbol`: A string containing "X".
- `message`: A string explaining that the server is waiting.

```text
{"msg_type":"LOBBY_WAIT","player_id":"SERVER","payload":{"assigned_id":"Player_1","symbol":"X","message":"Waiting for Player_2"},"timestamp":1727000001}\n
```

### GAME_START

This is sent from the server to both clients when both players have joined. Each client receives their assigned ID and symbol. Player_1 goes first.

The payload contains:
- `assigned_id`: A string containing "Player_1" or "Player_2".
- `symbol`: A string containing "X" or "O".
- `board`: An array containing nine empty strings.
- `current_turn`: A string containing "Player_1".

```text
{"msg_type":"GAME_START","player_id":"SERVER","payload":{"assigned_id":"Player_2","symbol":"O","board":["","","","","","","","",""],"current_turn":"Player_1"},"timestamp":1727000002}\n
```

### MOVE

This is sent from the client to the server when the player chooses a cell. The server checks that it is their turn and that the cell is empty before placing their symbol.

The payload contains:
- `row`: An integer from 0–2.
- `col`: An integer from 0–2.

```text
{"msg_type":"MOVE","player_id":"Player_1","payload":{"row":0,"col":2},"timestamp":1727000005}\n
```

### STATE_UPDATE

This is sent from the server to both clients after a valid move if the game is still going. It shows the updated board and whose turn is next.

The payload contains:
- `board`: An array containing nine strings, using "X", "O", or "".
- `current_turn`: A string containing "Player_1" or "Player_2".

```text
{"msg_type":"STATE_UPDATE","player_id":"SERVER","payload":{"board":["","","X","","","","","",""],"current_turn":"Player_2"},"timestamp":1727000006}\n
```

### ERROR

This is sent from the server to the client that sent an invalid message or move. The board and the current turn stay the same.

The payload contains:
- `code`: A string containing the error type.
- `message`: A string explaining the error.

The error codes are:
- `MALFORMED_MESSAGE`: The message is not valid JSON or has missing or incorrect fields.
- `INVALID_COORDINATES`: The row or column is not an integer from 0–2.
- `CELL_OCCUPIED`: The cell already contains X or O.
- `NOT_YOUR_TURN`: The player moved when it was the other player's turn.
- `INVALID_STATE`: The message is not allowed at this point in the game.
- `PLAYER_ID_MISMATCH`: The ID does not match the player's connection.
- `ROOM_FULL`: Two players have already joined.

```text
{"msg_type":"ERROR","player_id":"SERVER","payload":{"code":"CELL_OCCUPIED","message":"That cell is already taken"},"timestamp":1727000007}\n
```

### DISCONNECT

This is sent from the client to the server when the player chooses to leave. If the game is going, the other player wins by forfeit.

The payload contains:
- `reason`: A string containing "quit".

```text
{"msg_type":"DISCONNECT","player_id":"Player_1","payload":{"reason":"quit"},"timestamp":1727000008}\n
```

### GAME_OVER

This is sent from the server to the connected clients when someone wins, the game is a draw, or a player leaves.

The payload contains:
- `result`: A string containing "win", "draw", or "forfeit".
- `winner_id`: A string containing the winning player's ID, or null for a draw.
- `reason`: A string containing "three_in_a_row", "board_full", "player_quit", or "connection_lost".
- `board`: An array containing the nine final cells.
- `scores`: An object containing integer scores for Player_1 and Player_2. The winner gets 1 and the other player gets 0. Both get 0 for a draw.

```text
{"msg_type":"GAME_OVER","player_id":"SERVER","payload":{"result":"win","winner_id":"Player_1","reason":"three_in_a_row","board":["X","X","X","O","O","","","",""],"scores":{"Player_1":1,"Player_2":0}},"timestamp":1727000010}\n
```

## Connection Termination

When a player chooses to leave, the client sends DISCONNECT and closes its socket. Closing the socket starts the TCP FIN process.

If `recv()` returns `b""`, it means the connection has closed. The server stops reading from that socket and handles the player leaving.

The server catches `ConnectionResetError`, `BrokenPipeError`, and `ConnectionAbortedError`. A TCP reset can cause ConnectionResetError, and sending to a closed connection can cause BrokenPipeError. A network drop can also be detected by a configured timeout.

If a player leaves during the game, the remaining player wins by forfeit. The server sends GAME_OVER to the remaining player if their connection is still working.

If Player_1 leaves while waiting, the server clears their slot and waits for another player. After a game ends, the server closes the game connections, resets the board, and clears the player assignments.