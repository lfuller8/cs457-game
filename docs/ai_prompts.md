# AI Prompts and Constraints

The prompts below tell the AI to follow protocol_blueprint.md and fsm_specification.md when helping write the game code.

## Protocol Prompt

Use protocol_blueprint.md to write the JSON message sender and receiver in Python. Use TCP with UTF-8 newline-delimited JSON. Every message must end with a newline. Save incomplete messages until more bytes arrive, and handle several messages arriving in one recv(). Use only the message types and fields listed in the blueprint. Check the field types before processing a message. Do not add extra features or change the protocol.

## Game State Prompt

Use fsm_specification.md and protocol_blueprint.md to write the server's game logic. Assign the first player Player_1 and X, and the second player Player_2 and O. Player_1 goes first. Check each player's ID against their connection. Invalid moves and out-of-turn moves must send ERROR without changing the board or turn. Check for a win or draw after every valid move. Follow the disconnect and cleanup rules in the documents. Do not add extra game modes or change the states.

## Review

I will compare the generated code with the two design files. I will check that the messages use the correct fields, that incomplete messages are saved, and that turns and invalid moves are handled correctly. I will also check that disconnects end the game and clear the connections.