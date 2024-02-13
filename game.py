import time
from enum import Enum
import os, sys
import queue
import threading
import keyboard
import glob
from pathlib import Path
import random
import numpy as np

# 10x20 ただし、20マス目まで表示だが21マス目を用意
# 0は左上

STATE_EMPTY = "　"
STATE_FIXED_BLOCK = "🔳"
STATE_FALLING_BLOCK = "🔲"
STATE_CLEARED = "💯"
GUIDE_LINE_BLOCK = "🌟"
FRAME = "🔷"


HEIGHT = 20
WIDTH = 9

FRAME_RATE = 60
INPUT_SLEEP_SEC = 0.05
FALLING_SEC = 0.5
    
def load_minos(dir_path: Path):
    def convert_to_state(line: str):
        conversion = {"0": STATE_EMPTY, "1": STATE_FALLING_BLOCK}
        return [conversion[char] for char in line if char in conversion]
    
    minos = []
    for file in dir_path.glob("*"):
        with open(file) as f: lines = f.readlines()
        minos.append([convert_to_state(line) for line in lines])
    return minos

def check_falling_mino_movable(direction_x, direction_y):
    for y in range(HEIGHT):
        for x in range(WIDTH):
            if state[y][x] is not STATE_FALLING_BLOCK: 
                continue
            if y+direction_y < 0 or y+direction_y >=HEIGHT: 
                return False
            if x+direction_x < 0 or x+direction_x >=WIDTH: 
                return False
            if state[y+direction_y][x+direction_x] == STATE_FIXED_BLOCK: 
                return False
    return True

def move_falling_mino(direction_x, direction_y):
    # 必ず動く方向から捜査する
    columns = [i for i in range(WIDTH)]
    if direction_x > 0: columns = columns[::-1]
    
    for y in range(HEIGHT)[::-1]:
        for x in columns:
            if state[y][x] == STATE_FALLING_BLOCK:
                state[y+direction_y][x+direction_x] = STATE_FALLING_BLOCK
                state[y][x] = STATE_EMPTY
    
    global mino_center_x
    global mino_center_y
    global debug_str
    mino_center_x += direction_x
    mino_center_y += direction_y
    debug_str = f"{mino_center_x}, {mino_center_y}"
    
def rotate_falling_mino(rotate_right=True):
    global falling_mino_shape
    shape: np.array = np.array(falling_mino_shape)
    if rotate_right: new_shape = np.rot90(shape, 3)
    else: new_shape =np.rot90(shape)
    new_shape = new_shape.tolist()
    
    height = len(new_shape)
    width = len(new_shape[0])
    # print(mino_center_x, mino_center_y)
    
    # はみ出さないかのチェック
    start_x = mino_center_x - (width / 2) - 0.5
    start_y = mino_center_y - (height / 2) - 0.5
    
    def clamp(n, smallest, largest):
        return max(smallest, min(n, largest))
    start_x = clamp(start_x, 0, WIDTH - width)
        
    start_x, start_y = int(start_x), int(start_y)
    for x in range(WIDTH):
        for y in range(HEIGHT):
            if state[y][x] == STATE_FALLING_BLOCK:
                state[y][x] = STATE_EMPTY
    
    for x in range(width):
        for y in range(height):
            state[start_y + y][start_x + x] = new_shape[y][x]
    falling_mino_shape = new_shape
    
def fix_mino():
    for y in range(HEIGHT):
        for x in range(WIDTH):
            if state[y][x] == STATE_FALLING_BLOCK: state[y][x] = STATE_FIXED_BLOCK

def render_screen(state):
    os.system('cls')
    for line in state:
        output = [FRAME] + line + [FRAME]
        print("".join(output), flush=True)
    print(FRAME * (WIDTH + 2), flush=True)
    print("score:", score, flush=True)
    print(debug_str, flush=True)
    sys.stdout.flush()

def step_falling_mino():
    if check_falling_mino_movable(0, 1):
        move_falling_mino(0, 1)
        return True
    fix_mino()
    return False
    
def generate_mino(all_minos: list):
    target_mino = random.choice(all_minos)
    start_x = WIDTH // 2
    for y in range(len(target_mino)):
        for x in range(len(target_mino[y])):
            state[y][start_x + x] = target_mino[y][x]
    mino_center_x = start_x + (len(target_mino[0]) / 2) + 0.5
    mino_center_y = (len(target_mino) / 2) + 0.5
    return target_mino, mino_center_x, mino_center_y
    
def check_lines():
    global score
    cleared_indexes = []
    for y in range(HEIGHT)[::-1]:
        is_line_filled = [block == STATE_FIXED_BLOCK for block in state[y]]
        if all(is_line_filled):
            for x in range(WIDTH):
                state[y][x] = STATE_CLEARED
            cleared_indexes.append(y + len(cleared_indexes))
    if len(cleared_indexes) == 0: return
    
    score += 100 * len(cleared_indexes)
    render_screen(state)
    time.sleep(1)
    
    for line in cleared_indexes:
        state.pop(line)
        state.insert(0, [STATE_EMPTY] * WIDTH)
    render_screen(state)
    pass

def receive_keyboard_input():
    while True:
        event = keyboard.read_event()
        if event.event_type == keyboard.KEY_DOWN:
            key = event.name
            process_keyboard_input(key)
            # render_screen(state)

def process_keyboard_input(key):
    if key == "a" and check_falling_mino_movable(-1, 0):
        move_falling_mino(-1, 0)
    elif key == "d" and check_falling_mino_movable(1, 0):
        move_falling_mino(1, 0)
    elif key == "w":
        rotate_falling_mino()
    elif key == "s" and check_falling_mino_movable(0, 1):
        move_falling_mino(0, 1)
    
def game():
    global score
    global state
    global falling_mino_shape
    global mino_center_x
    global mino_center_y
    global debug_str
    
    time_to_fall_step = FALLING_SEC
    score = 0
    state = [[STATE_EMPTY]*WIDTH for _ in range(HEIGHT)]
    mino_center_x, mino_center_y = 0, 0
    debug_str = ""
    
    input_thread = threading.Thread(target=receive_keyboard_input)
    input_thread.daemon = True
    input_thread.start()
    
    all_minos = load_minos(Path("minos"))
    print(all_minos)
    falling_mino_shape, mino_center_x, mino_center_y = generate_mino(all_minos)
    last_step_time = time.time()
    while True:
        render_screen(state)
        if time.time() - last_step_time > time_to_fall_step:
            is_steped = step_falling_mino()
            check_lines()
            last_step_time = time.time()
        
            if not is_steped: 
                falling_mino_shape, mino_center_x, mino_center_y = generate_mino(all_minos)
            
        time.sleep(1 / FRAME_RATE)
        

if __name__ == '__main__':
    game()