```mermaid
stateDiagram-v2
    [*] --> INIT
    INIT --> WAITING_FOR_PLAYERS: server starts listening
    
    WAITING_FOR_PLAYERS --> WAITING_FOR_PLAYERS: Player 1 connects\nassign X, send LOBBY_WAIT
    WAITING_FOR_PLAYERS --> WAITING_FOR_PLAYERS: Player disconnects\nclear slot
    WAITING_FOR_PLAYERS --> GAME_START: Player 2 connects\nassign O, send GAME_START
    
    GAME_START --> PLAYER_TURN: initialize board\nsend GAME_START to both\nX moves first
    
    PLAYER_TURN --> EVALUATE_MOVE: active player sends MOVE
    PLAYER_TURN --> PLAYER_TURN: out-of-turn or malformed\nsend ERROR
    
    EVALUATE_MOVE --> PLAYER_TURN: invalid coordinates\nor occupied cell\nsend ERROR
    EVALUATE_MOVE --> PLAYER_TURN: valid move, no win/draw\nupdate board, switch turns\nsend STATE_UPDATE
    EVALUATE_MOVE --> GAME_OVER: victory or draw\nsend result to both
    
    PLAYER_TURN --> GAME_OVER: player disconnect\ndeclare opponent winner\nby forfeit
    
    GAME_OVER --> CLEANUP: close game connections
    CLEANUP --> WAITING_FOR_PLAYERS: reset board\nclear player assignments