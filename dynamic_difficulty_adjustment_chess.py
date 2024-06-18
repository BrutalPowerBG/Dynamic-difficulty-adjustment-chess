import chess
import chess.engine
import chess.svg
import random
import tkinter as tk
from PIL import Image, ImageTk
import os

######################################################################################                   
# Pre-Setup
# Most of these global variables will be defined in  global_parameter_definitions()
# Variables with comments next to them will likely not be defined in  global_parameter_definitions()
######################################################################################
chess_ui = None
#chess_ui.mainloop()
stockfish_path = None
board = None
side = None # Will be set by player
image = None # Declared only to store piece images in the global scope so they aren't deleted by Tkinter
player_rating = None
move_random_range = None


# Bounded value between 0 and 1
class Percent:
    def __init__(self, initial_value, is_fraction = True):
        self._value = None
        if is_fraction:
            self.value = initial_value
        else:
            self.value = initial_value / 100

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, new_value):
        if 0 <= new_value <= 1:
            self._value = new_value
        elif new_value < 0:
            self._value = 0
        elif new_value > 1:
            self._value = 1
        else:
            raise ValueError("Value must be between 0 and 1")
        
# Move
class Move:
    def __init__(self, board, move_uci, evaluation = None):
        self._board = board
        self._move_uci = move_uci
        self._evaluation = None
        if evaluation:
            self._evaluation = evaluation
        # Eval is transformed into a percent between 0 and 100
        self._move_accuracy = self.get_move_accuracy()
        
    def get_move_evaluation(self):
        return get_move_evaluation(self._board, self._move_uci)

    def get_move_accuracy(self):
       #Get all evaluations
        all_evaluations = get_all_evaluations(self._board)
        
        best_move = all_evaluations[0]
        worst_move = all_evaluations[len(all_evaluations) - 1]
        
        move_played_evaluation = None
        for move, evaluation in all_evaluations:
            if move == self._move_uci:
                move_played_evaluation = evaluation
                self._evaluation = evaluation
                break
        if move_played_evaluation is None:
            raise ValueError("Move evaluation not found")

        # Ensure we don't divide by zero
        if best_move[1] == worst_move[1]:
            move_accuracy = 1.0
        else:
            move_accuracy = abs(move_played_evaluation - worst_move[1]) / abs(best_move[1] - worst_move[1]) 
        move_accuracy = Percent(move_accuracy).value
        return move_accuracy
    


# Player rating
class Rating:
    def __init__(self, initial_value=0.5):
        # Rating is clamped between 0 and 1
        self._value = Percent(initial_value).value
        self._certainty = Percent(0).value
        self._turns_played = 0
    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, new_value):
        self._value = Percent(new_value).value        
        
    @property
    def certainty(self):
       return self._certainty
   
    @certainty.setter
    def certainty(self, new_certainty):
        self._certainty = Percent(new_certainty).value
        
    @property
    def turns_played(self):
       return self._turns_played
   
    def increment_turns_played(self):
        self._turns_played += 1
        print('Turn: ', self._turns_played)
        
    def update_rating_with_move_accuracy(self, accuracy):
        turns = self._turns_played
        old_rating = self._value
        # How much the new accuracy is relevant compared to the old accuracies 
        accuracy_multiplier = 2 + min((turns/3.5), 12)
        new_rating = ( old_rating * turns + accuracy  * accuracy_multiplier) / (turns + accuracy_multiplier)
        self._value = new_rating
        if self._certainty < 1:
            self._certainty += 0.02
        return new_rating



class ChessUI(tk.Tk):
    def __init__(self, width=400, height=400):
        super().__init__()
        
        self.title("Chess UI")
        self.geometry(f"{width}x{height}")
        self.width = width
        self.height = height

        global board
        self.board = board

        self.canvas = tk.Canvas(self, width=width, height=height)
        self.canvas.pack()
        
        self.square_size = min(width, height) // 8
        self.piece_images = []

        self.draw_board()
        self.draw_pieces()
        
        # Bind mouse click events to handle player input
        self.canvas.bind("<Button-1>", self.on_square_click)

        # Variables to store clicked square and selected piece
        self.selected_square = None
        self.selected_piece = None

    def draw_board(self):
        for row in range(8):
            for col in range(8):
                color = "white" if (row + col) % 2 == 0 else "darkgoldenrod"
                self.canvas.create_rectangle(
                    col * self.square_size, 
                    row * self.square_size, 
                    (col + 1) * self.square_size, 
                    (row + 1) * self.square_size, 
                    fill=color
                )

    def draw_pieces(self, initial_square = None, destination_square = None):
        # Clear the pieces first to avoid duplications
        self.clear_pieces()
        
        # Mark recent square moves
        self.canvas.delete("marker")
        if initial_square and destination_square:
            col_initial = chess.square_file(initial_square)
            row_initial = 7 - chess.square_rank(initial_square)
            self.canvas.create_rectangle(
                col_initial * self.square_size, 
                row_initial * self.square_size, 
                (col_initial + 1) * self.square_size, 
                (row_initial + 1) * self.square_size, 
                fill="yellow",
                tag = "marker"
            )
            
            col_destination = chess.square_file(destination_square)
            row_destination = 7 - chess.square_rank(destination_square)
            self.canvas.create_rectangle(
                col_destination * self.square_size, 
                row_destination * self.square_size, 
                (col_destination + 1) * self.square_size, 
                (row_destination + 1) * self.square_size, 
                fill="yellow",
                tag = "marker"
            )

        # Redraw the pieces
        for square in chess.SQUARES:
            piece = self.board.piece_at(square)
            if piece is not None:
                piece_image = self.get_piece_image(piece)
                self.piece_images.append(piece_image)
                
                coords = self.square_to_coords(square)
                if piece_image is not None:
                    self.canvas.create_image(coords, image=piece_image, anchor="c", tags="piece")
                else:
                    print(f"Failed to load image for piece at square {square}.")
                
    def clear_pieces(self):
        # Clear only the pieces by deleting items with the "piece" tag
        self.canvas.delete("piece")
        self.piece_images=[]

    def get_piece_image(self, piece):        
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
        piece_symbol = piece.symbol()
        
        image_filename = piece_images.get(piece_symbol, None)
        global image
        image = Image.open(image_filename)
        if image_filename:
            image = Image.open(image_filename)
            resized_image = image.resize((self.square_size, self.square_size), Image.LANCZOS)
            imageTk = ImageTk.PhotoImage(resized_image, name=piece_symbol)
            return imageTk
        else:
            print(f"Failed to load image for piece {piece_symbol}.")
            return None

    def square_to_coords(self, square):
        file, rank = chess.square_file(square), chess.square_rank(square)
        x = (file * self.square_size) + self.square_size // 2
        y = ((7 - rank) * self.square_size) + self.square_size // 2
        return x, y
    
    def on_square_click(self, event):
        # Convert click coordinates to square
        col = event.x // self.square_size
        row = 7 - (event.y // self.square_size)
        square = chess.square(col, row)

        if self.selected_square is None:
            # No square previously clicked
            self.selected_square = square
            self.selected_piece = self.board.piece_at(square)
        else:
            if self.selected_square != square:
                # Move the piece if it's a legal move
                if self.selected_piece is not None:
                    # If the move is a pawn promotion
                    if self.selected_piece.piece_type == chess.PAWN and (row == 0 or row == 7):
                        move = chess.Move(self.selected_square, square, promotion=chess.QUEEN)
                    else:
                        move = chess.Move(self.selected_square, square)
                    if move in self.board.legal_moves:
                        # Assign board side if there is none selected 
                        global side
                        if side == None:
                            side = self.selected_piece.color

                        old_board = board.copy()
                        self.board.push(move)
                        self.selected_piece = None
                        self.draw_pieces(self.selected_square, square)
                        
                        # Update the UI to show the pieces before the engine calculates its move
                        self.update_idletasks()
                        
                        update_player_rating(old_board, move)
                        
                        play_engine_turn(self.board)
                    else:
                        self.selected_piece = None
                else:
                    piece = self.board.piece_at(square)
                    if piece is not None and piece.color == self.board.turn:
                        self.selected_piece = piece
                    self.selected_square = square
 


######################################################################################  
# Setup
###################################################################################### 
def global_parameter_definitions():
    # Set the logical board
    global board
    board = chess.Board()
    # Set board scale
    global chess_ui_scale 
    chess_ui_scale = 800
    # Show chess UI board
    global chess_ui
    chess_ui = ChessUI(800, 800)
    # Set Stockfish path
    global stockfish_path
    stockfish_path = "./stockfish/stockfish-windows-x86-64-avx2.exe"
    # Set player rating
    global player_rating
    player_rating = Rating(50)
    # This random range will define how close the bot can search around the evaluation to alternate and play a different move 
    global move_random_range
    move_random_range = 0.2

def play_game():    
    global side
    side = get_user_side()
    print_board(board)
    
    if side == None:
        while not board.is_game_over():
            # Display the current board state
            print_board(board)

            play_engine_turn(board)
            
    else:
        if side == chess.WHITE:
            while not board.is_game_over():
               
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
    
def print_board(board, initial_square = None, destination_square = None):
    print(board)
    print("\n")
    
    global chess_ui
    chess_ui.draw_pieces(initial_square, destination_square)    

def play_player_turn(board):
    while True:
        user_move = input("Enter your move: ")
        move = parse_move_string(user_move, board)

        if move in board.legal_moves:
            update_player_rating(board, move)
            # Make the move on the board
            board.push(move)
            print_board(board)
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

def update_player_rating(board, move_played):    
    move = Move(board, move_played.uci())
    accuracy = move.get_move_accuracy()
    player_rating.update_rating_with_move_accuracy(accuracy)
    player_rating.increment_turns_played()
    

def play_engine_turn(board):
    #Get all evaluations and print them
    all_evaluations = get_all_evaluations(board)
    print_evaluations(all_evaluations)
    
    move_to_play = decide_move_to_play(all_evaluations)
    move_san = board.san(chess.Move.from_uci(str(move_to_play)))
    
    print("Engine played move: ", move_san)

    # Convert the UCI string to a Move object
    move_obj = parse_move_string(move_to_play, board)
    # Make the closest_to_zero move on the board
    board.push(move_obj)
    
    # Extract the starting and final squares for the marking
    from_square = move_obj.from_square
    to_square = move_obj.to_square
    
    print_board(board, from_square, to_square)


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
            result = engine.analyse(board_copy, chess.engine.Limit(time=0.1))
            # Convert the score to a numeric value
            evaluations[move.uci()] = result["score"].relative.score(mate_score=2000)  
            #Divide the score by 100 to make it closer to chess.com evaluation
            evaluations[move.uci()] = evaluations[move.uci()]/100

            #Make it so that the score is actually correct
            if white_to_move:
                evaluations[move.uci()] = -evaluations[move.uci()]
    # Sort the evaluations by score in descending order
    sorted_evaluations = sorted(evaluations.items(), key=lambda x: x[1], reverse=white_to_move)

    return sorted_evaluations

def get_move_evaluation(board, move):
    with chess.engine.SimpleEngine.popen_uci(stockfish_path) as engine:
        # Make the move on a copy of the board
        board_copy = board.copy()
        board_copy.push(move)

        # Evaluate the position after the move
        result = engine.analyse(board_copy, chess.engine.Limit(time=0.1))
        #Divide the score by 100 to make it closer to chess.com evaluation
        evaluation = result["score"].relative.score(mate_score=2000) / 100

        # Adjust the evaluation based on whose turn it is
        if board.turn == chess.WHITE:
            evaluation = -evaluation

    return evaluation

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
    # Default move
    move = closest_to_zero_move
    
    best_move = all_evaluations[0]
    worst_move = all_evaluations[len(all_evaluations) - 1]
    # Ensure we don't divide by zero in the linear interpolation
    if best_move[1] == worst_move[1]:
        return move[0]
    
    rating = player_rating.value
    # Calculate move eval based on rating
    # Linear interpolation between best_move and worst_move with rating being between 0 and 1, swaying to worst_move or best_move respectively
    move_evaluation_based_on_rating = linearly_interpolate(worst_move[1], best_move[1], rating)
    
    # Balance move with board state 
    # Linearly interpolate between evaluation based on rating and zero eval move, based on % certainty of the player rating
    # weight = min(1, player_rating.certainty + abs(best_move[1]/10))
    if move_evaluation_based_on_rating > 0:
        move_evaluation_based_on_rating = linearly_interpolate(0, move_evaluation_based_on_rating, player_rating.certainty)
    else:
        move_evaluation_based_on_rating = linearly_interpolate(move_evaluation_based_on_rating, 0, 1 - player_rating.certainty)

    # Punish mistakes
    # This variable makes the computer improve the targeted move evaluation if the difference between the first best move and the closest to zero is too high
    min_difference_to_choose_better_value = 1.0
    # This variable determines the power to which the rating determines the interpolation - Higher values of Power means less interpolation, but the higher the player's rating is, the more he is punished for mistakes 
    rating_power = 4
    global side
    if side == chess.BLACK:
        if best_move[1]>move_evaluation_based_on_rating + min_difference_to_choose_better_value:
            move_evaluation_based_on_rating = linearly_interpolate(move_evaluation_based_on_rating, best_move[1], rating ** rating_power)
    elif side == chess.WHITE:
        if best_move[1]<move_evaluation_based_on_rating - min_difference_to_choose_better_value:
            move_evaluation_based_on_rating = linearly_interpolate(move_evaluation_based_on_rating, best_move[1], rating ** rating_power)
    
    # Gets a random move within the range
    moves_in_range_close = get_moves_within_range(move_evaluation_based_on_rating, all_evaluations, move_random_range)
    if len(moves_in_range_close) > 0:
        move = random.choice(moves_in_range_close)
    else:
        # If there are no moves in the close range, find a move where a weaker piece captures a higher value piece
        moves_in_range_long = get_moves_within_range(move_evaluation_based_on_rating, all_evaluations, move_random_range * 10, True)
        if len(moves_in_range_long) > 0:
            move = random.choice(moves_in_range_long)
        else:
            # If we still can't find a move, just get the closest move to evaluation
            move = get_move_closest_to_eval(move_evaluation_based_on_rating, all_evaluations)
    return move[0]

def linearly_interpolate(worse_move, better_move, weight):
    return weight*(better_move - worse_move) + worse_move
    
    
def get_move_closest_to_eval(target_eval, all_evaluations):
    closest_move = None
    closest_diff = float('inf')
    
    for move, evaluation in all_evaluations:
        diff = abs(evaluation - target_eval)
        if diff < closest_diff:
            closest_diff = diff
            closest_move = (move, evaluation)
            
    return closest_move

def get_moves_within_range(target_eval, all_evaluations, range, is_capture = False):
    # Define the range
    lower_bound = target_eval - range
    upper_bound = target_eval + range
    
    # Get moves within the specified range
    moves_in_range = [
        (move, evaluation)
        for move, evaluation in all_evaluations if lower_bound <= evaluation <= upper_bound and (not is_capture or is_capture_by_weaker_piece(board, move))]

    return moves_in_range
    
def is_capture_by_weaker_piece(board, move):
    piece_values = {
        chess.PAWN: 1,
        chess.KNIGHT: 3,
        chess.BISHOP: 3,
        chess.ROOK: 5,
        chess.QUEEN: 9,
        chess.KING: float('inf')
    }

    capturing_piece = board.piece_at(chess.Move.from_uci(move).from_square)
    captured_piece = board.piece_at(chess.Move.from_uci(move).to_square)

    if captured_piece is None:
        return False  # Not a capture move

    capturing_value = piece_values[capturing_piece.piece_type]
    captured_value = piece_values[captured_piece.piece_type]

    return capturing_value < captured_value

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
    global_parameter_definitions()
    play_game()