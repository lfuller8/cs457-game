# Mermaid Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    participant C1 as Client1(PlayerX)
    participant Server
    participant C2 as Client2(PlayerO)
    
    C1->>Server: MOVE request (row, col)
    
    Note over Server: Acquire threading.Lock
    Note over Server: Validate turn & cell empty & in bounds
    
    alt Valid Move
        Note over Server: Update board[row][col] = 'X'
        Note over Server: Check for win/draw
        
        alt Win Detected
            Note over Server: Set game_state=WIN, winner='X'
            Note over Server: scores[PlayerX] += 1
            Note over Server: Release Lock
            Server->>C1: STATE_UPDATE(board, turn=None)
            Server->>C2: STATE_UPDATE(board, turn=None)
            Server->>C1: GAME_OVER(result='WIN', scores)
            Server->>C2: GAME_OVER(result='LOSS', scores)
        else Draw Detected
            Note over Server: Set game_state=DRAW
            Note over Server: scores[PlayerX] += 0, scores[PlayerO] += 0
            Note over Server: Release Lock
            Server->>C1: STATE_UPDATE(board, turn=None)
            Server->>C2: STATE_UPDATE(board, turn=None)
            Server->>C1: GAME_OVER(result='DRAW', scores)
            Server->>C2: GAME_OVER(result='DRAW', scores)
        else Game Continues
            Note over Server: Switch turn to Player O
            Note over Server: Release Lock
            Server->>C1: STATE_UPDATE(board, turn='O')
            Server->>C2: STATE_UPDATE(board, turn='O')
        end
    else Invalid Move (Out of Turn or Cell Occupied)
        Note over Server: Release Lock
        Server->>C1: ERROR(msg='Invalid move or not your turn')
        Note over Server: Board & turn unchanged
    end
    
    Note over C1,C2: Game state synchronized across clients
    ```