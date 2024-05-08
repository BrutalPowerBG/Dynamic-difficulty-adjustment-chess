import chess
import chess.engine
import random
import tkinter as tk
from PIL import Image, ImageTk
import os

# Create a Tkinter window
root = tk.Tk()
root.title("Chess Game")

# Create a Canvas widget to draw the chessboard
canvas = tk.Canvas(root, width=400, height=400)
canvas.pack()


# Path to Stockfish executable
stockfish_path = "./stockfish/stockfish-windows-x86-64-avx2.exe"
board = chess.Board()
side = None

def play_game():
    global side
    side = get_user_side()
    if side == None:
        while not board.is_game_over():
            # Display the current board state
            print_board(board)
            #TODO: replace this with canvas tk!!!!!!!!!!!!!!!!!
            print("\n")

            play_engine_turn(board)
            
    else:
        if side == chess.WHITE:
            while not board.is_game_over():
                print_board(board)
                if board.turn == chess.WHITE:
                    play_player_turn(board)
                else:
                    play_engine_turn(board)
        
        if side == chess.BLACK:
             while not board.is_game_over():
                print_board(board)
                if board.turn == chess.WHITE:
                    play_engine_turn(board)
                else:
                    play_player_turn(board)
        
    display_final_board_state(board)
    
def print_board(board):
    print(board)
    # Clear the canvas
    canvas.delete("all")
    
    # Draw the chessboard squares
    for row in range(8):
        for col in range(8):
            color = "white" if (row + col) % 2 == 0 else "gray"
            canvas.create_rectangle(col * 50, row * 50, (col + 1) * 50, (row + 1) * 50, fill=color)
    
    # Directory containing the images
    image_dir = "./Images/"

    # Dictionary mapping piece symbols to image file names
    piece_images = {
        'r': os.path.join(image_dir, 'black_rook.png'),
        'n': os.path.join(image_dir, 'black_knight.png'),
        'b': os.path.join(image_dir, 'black_bishop.png'),
        'q': os.path.join(image_dir, 'black_queen.png'),
        'k': os.path.join(image_dir, 'black_king.png'),
        'p': os.path.join(image_dir, 'black_pawn.png'),
        'R': os.path.join(image_dir, 'white_rook.png'),
        'N': os.path.join(image_dir, 'white_knight.png'),
        'B': os.path.join(image_dir, 'white_bishop.png'),
        'Q': os.path.join(image_dir, 'white_queen.png'),
        'K': os.path.join(image_dir, 'white_king.png'),
        'P': os.path.join(image_dir, 'white_pawn.png')
    }
    
    # Draw the chess pieces
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece is not None:
            image_filename = piece_images.get(piece.symbol(), None)
            if image_filename is not None:
                image = Image.open(image_filename)
                resized_image = image.resize((50, 50), Image.LANCZOS)
                photo = ImageTk.PhotoImage(resized_image)
                canvas.create_image(chess.square_file(square) * 50, (7 - chess.square_rank(square)) * 50, image=photo, anchor="nw")
                canvas.photo = photo  # Save reference to prevent image from being garbage collected
    

def play_player_turn(board):
    while True:
        print("\n")
        user_move = input("Enter your move: ")
        move = parse_move_string(user_move, board)

        if move in board.legal_moves:
            # Make the move on the board
            board.push(move)
            return move 
        else:
            print("Illegal move. Try again.")

def parse_move_string(move_str, board):
    try:
        # Try to parse the input as a UCI move
        move = chess.Move.from_uci(move_str)
    except ValueError:
        try:
            # Try to parse the input as a SAN move
            move = board.parse_san(move_str)
        except ValueError:
            print("Invalid move format. Try again.")
            return None

    return move


def play_engine_turn(board):
    with chess.engine.SimpleEngine.popen_uci(stockfish_path) as engine:
        # Initialize variables for the move closest to evaluation 0
        closest_to_zero_move = None
        closest_to_zero_eval_diff = float('inf')  # Initialize to positive infinity

        #Get all evaluations and print them
        all_evaluations = get_all_evaluations(board)
        print_evaluations(all_evaluations)
        
        move_to_play = decide_move_to_play(all_evaluations)
        move_san = board.san(chess.Move.from_uci(str(move_to_play)))
       
        print("Engine played move: ", move_san)
        # # Get all legal moves
        # legal_moves = list(board.legal_moves)
        # for move in legal_moves:
        #     # Make the move on a copy of the board
        #     board_copy = board.copy()
        #     board_copy.push(move)

        #     # Evaluate the position after the move
        #     result = engine.analyse(board_copy, chess.engine.Limit(time=2.0))
        #     eval_diff = abs(result["score"].relative.score(mate_score=2000) / 100)  # Evaluation difference

        #     # Update the closest_to_zero move if the current move is closer to evaluation 0
        #     if eval_diff < closest_to_zero_eval_diff:
        #         closest_to_zero_move = move
        #         closest_to_zero_eval_diff = eval_diff

         # Convert the UCI string to a Move object
        move_obj = parse_move_string(move_to_play, board)
        # Make the closest_to_zero move on the board
        board.push(move_obj)
        
        # # Get the best move from Stockfish
        # result = engine.play(board, chess.engine.Limit(time=2.0))
        # move_uci = result.move.uci()
        # # Make the move on the board
        # board.push_uci(move_uci)


def get_all_evaluations(board):
    if board.turn == chess.WHITE:
        white_to_move = True
    else:
        white_to_move = False

    evaluations = {}

    with chess.engine.SimpleEngine.popen_uci(stockfish_path) as engine:
        for move in board.legal_moves:
            # Make the move on a copy of the board
            board_copy = board.copy()
            board_copy.push(move)

            # Evaluate the position after the move
            result = engine.analyse(board_copy, chess.engine.Limit(time=1.0))
            # Convert the score to a numeric value
            evaluations[move.uci()] = result["score"].relative.score(mate_score=2000)  
            #Divide the score by 100 to make it closer to chess.com evaluation
            evaluations[move.uci()] = evaluations[move.uci()]/100

            #Make it so that the score is actually 
            if white_to_move:
                evaluations[move.uci()] = -evaluations[move.uci()]
    # Sort the evaluations by score in descending order
    sorted_evaluations = sorted(evaluations.items(), key=lambda x: x[1], reverse=white_to_move)

    return sorted_evaluations

def print_evaluations(all_evaluations):
    print("Move\t\t\tScore")
    print("---------------------------")
    for move, score in all_evaluations:
        san_move = board.san(chess.Move.from_uci(str(move)))
        print(f"{san_move.ljust(20)}\t{score}")
    print("\n")
    
def decide_move_to_play(all_evaluations):
    if len(all_evaluations) == 1:
        return all_evaluations[0]
    closest_to_zero_move = min(all_evaluations, key=lambda x: abs(x[1]))
    move = closest_to_zero_move[0]
    
    #This variable makes the computer choose the best move instead of the closest to zero if the difference between the first best move and the closest to zero is too high
    min_difference_between_move_ranking_for_overriding_closest_to_zero = 2.5
    global side
    if side == chess.BLACK:
        best_for_white = max(all_evaluations, key=lambda x: x[1])
        if best_for_white[1]>closest_to_zero_move[1] + min_difference_between_move_ranking_for_overriding_closest_to_zero:
            move = best_for_white[0]
    elif side == chess.WHITE:
        best_for_black = all_evaluations[0]
        if best_for_black[1]<closest_to_zero_move[1] - min_difference_between_move_ranking_for_overriding_closest_to_zero:
            move = best_for_black[0]
    
        
    return move

def get_play_or_watch():
    while True:
        user_side = input(": ").upper()

def get_user_side():
    while True:
        user_side = input("Choose wheather you want to (O)bserve OR Choose your side (W)hite, (B)lack, or (R)andom: ").upper()
        if user_side in ['O','W', 'B', 'R']:
            if user_side == 'O':
                return None
            elif user_side == 'W':
                player_color = chess.WHITE
                computer_color = chess.BLACK
            elif user_side == 'B':
                player_color = chess.BLACK
                computer_color = chess.WHITE
            elif user_side == 'R':
                color = random.choice(['W', 'B'])
                if color=='W':
                    player_color = chess.WHITE
                    computer_color = chess.BLACK
                else:
                    player_color = chess.BLACK
                    computer_color = chess.WHITE
                
                print("Player color:", color)
    
            return player_color
        else:
            print("Invalid choice. Please enter W, B, or R.")


def display_final_board_state(board):
    # Display the final board state
    print_board(board)
    print("\n")
    print("Game Over")

if __name__ == "__main__":
    play_game()