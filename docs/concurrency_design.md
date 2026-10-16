# Multi-Threading

## What is Multi-Threading?

Multi-threading is when we use multiple threads at the same time in order to host multiple clients at the same time. For Tic-Tac-Toe, the server will be using Python's threading. Each client will have its own thread, which will allow the server to receive messages from either player without blocking any other players messages. The main server thread will listen for new connections while the client threads will handle the game's communications. The server will use threading.Lock to protect game information and prevent multiple threads from changing information at the same time, such as the game's board, player's turn, connected clients, and the scores.

## Conncection Lifecycle

1. Server Startup: The server will create a TCP socket using socket(), binding it to an IP address and port using bind(), then it will start listening for connections using listen().

2. Client Connection: When a client connects, the server will accept the connection using accept() and create a new thread using threading.Thread, which will handle the clients communication. The main thread will continue listening for other connections.

3. Player Connection: The first client send a CONNECT message and is then assigned as Player_1 (X). The server then sends LOBBY_WAIT until another player connects, which will be assigned Player_2 (O). Then the server will send GAME_START to both clients.

4. Game's Communication: Each client's thread will listen for messages from its player. When a player sends a MOVE, the server checks if the action of the player is valid, such as is an empty space and is their turn. If it is valid, the board will update and a STATE_UPDATE message is sent to both clients. If the move isn't valud, the player will recieve an error message.

5. Multiple Conncections: The server supports two active players at a time. and each client has a seperate thread. So one client waiting to send a message will not prevent the other client from communicating with the server. Any other connections will be rejected while the game is full. 

6. Client Disconnection: When a player disconnects, the server closes their sockey and removes them from the connected clients list. If a game is currently active, the remaining player will be notified and the game session will end. The disconnected client's thread will then be terminated.