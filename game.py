import time
import os, sys
import threading
import keyboard
from pathlib import Path
import random
import numpy as np

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
    """ミノをファイルから読み込む"""
    def convert_to_state(line: str):
        conversion = {"0": STATE_EMPTY, "1": STATE_FALLING_BLOCK}
        return [conversion[char] for char in line if char in conversion]
    
    minos = []
    for file in dir_path.glob("*"):
        with open(file) as f: lines = f.readlines()
        minos.append([convert_to_state(line) for line in lines])
    return minos

def is_falling_mino_movable(direction_x, direction_y):
    """ミノが特定の方向に動けるか確認する"""
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

def move_falling_mino(direction_x, direction_y, rt_state=False):
    """ミノを動かす。rt_state=Trueの場合、stateに上書きしない"""
    if direction_x == 0 and direction_y == 0: 
        return
    # 必ず動く方向から捜査する
    columns = [i for i in range(WIDTH)]
    if direction_x > 0: columns = columns[::-1]
    
    target_state = state
    if rt_state:
        target_state = [l.copy() for l in state]
    
    for y in range(HEIGHT)[::-1]:
        for x in columns:
            if state[y][x] == STATE_FALLING_BLOCK:
                target_state[y+direction_y][x+direction_x] = STATE_FALLING_BLOCK
                target_state[y][x] = STATE_EMPTY
    if rt_state:
        return target_state
        
    global mino_center_x
    global mino_center_y
    mino_center_x += direction_x
    mino_center_y += direction_y
    
def rotate_falling_mino(rotate_right=True):
    """ミノを回転させる"""
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
    
def get_drop_direction():
    global debug_str
    """何マス下に落とせるかを計算する"""
    drop_height = 0
    is_mino_exists = [STATE_FALLING_BLOCK in line for line in state]
    if not any(is_mino_exists):
        return 0
    
    for drop_height in range(HEIGHT):
        if not is_falling_mino_movable(0, drop_height):
            break
    return drop_height - 1
    
def fix_mino():
    """ミノを固定する"""
    for y in range(HEIGHT):
        for x in range(WIDTH):
            if state[y][x] == STATE_FALLING_BLOCK: state[y][x] = STATE_FIXED_BLOCK

def step_falling_mino():
    """ミノを自由落下させる、落下できた場合Trueを返す"""
    if is_falling_mino_movable(0, 1):
        move_falling_mino(0, 1)
        return True
    fix_mino()
    return False
    
def generate_mino(mino_shape=None):
    """新しいミノを生成する"""
    global remaining_minos
    
    target_mino = remaining_minos.pop(0) if mino_shape is None else mino_shape
    start_x = WIDTH // 2
    for y in range(len(target_mino)):
        for x in range(len(target_mino[y])):
            state[y][start_x + x] = target_mino[y][x]
    mino_center_x = start_x + (len(target_mino[0]) / 2) + 0.5
    mino_center_y = (len(target_mino) / 2) + 0.5
    return target_mino, mino_center_x, mino_center_y
    
def claer_line():
    """消せる行を消す"""
    global score, debug_str
    cleared_indexes = []
    for y in range(HEIGHT)[::-1]:
        is_line_filled = [block == STATE_FIXED_BLOCK for block in state[y]]
        if all(is_line_filled):
            for x in range(WIDTH):
                state[y][x] = STATE_CLEARED
            cleared_indexes.append(y + len(cleared_indexes))
    if len(cleared_indexes) == 0: return
    if len(cleared_indexes) == 4: debug_str = "FUCKIN TETRIZ BABY"
    
    score += 100 * len(cleared_indexes)
    render_screen(state)
    time.sleep(1)
    
    for line in cleared_indexes:
        state.pop(line)
        state.insert(0, [STATE_EMPTY] * WIDTH)
        debug_str = ""
    render_screen(state)
    
def hold_mino():
    global holding_mino
    global falling_mino_shape
    global mino_center_x, mino_center_y
    global debug_str
    
    generate_mino_shape = holding_mino
    holding_mino = falling_mino_shape
    debug_str = "holded!"
    for x in range(WIDTH):
        for y in range(HEIGHT):
            if state[y][x] == STATE_FALLING_BLOCK:
                state[y][x] = STATE_EMPTY
    falling_mino_shape, mino_center_x, mino_center_y = generate_mino(generate_mino_shape)

def receive_keyboard_input():
    """キー入力を受け取る"""
    while True:
        event = keyboard.read_event()
        if event.event_type == keyboard.KEY_DOWN:
            key = event.name
            # process_keyboard_input(key)
            try:
                process_keyboard_input(key)
            except:
                pass

def process_keyboard_input(key):
    """キー入力を処理する"""
    global is_holded
    if key == "f" and not is_holded:
        hold_mino()
        is_holded = True
    elif key == "e":
        rotate_falling_mino()
    elif key == "q":
        rotate_falling_mino(False)
    elif key == "a" and is_falling_mino_movable(-1, 0):
        move_falling_mino(-1, 0)
    elif key == "d" and is_falling_mino_movable(1, 0):
        move_falling_mino(1, 0)
    elif key == "s" and is_falling_mino_movable(0, 1):
        move_falling_mino(0, 1)
    elif key== "w":
        drop_height = get_drop_direction()
        move_falling_mino(0, drop_height)
        
def render_screen(state):
    """画面を描画する"""
    global remaining_minos
    global holding_mino
    # ガイド等を表示するので表示用に配列をコピーしておく
    display_state = [l.copy() for l in state]
    
    try:
        drop_height = get_drop_direction()
        dropped_state = move_falling_mino(0, drop_height, True)
        for x in range(WIDTH):
            for y in range(HEIGHT):
                if dropped_state[y][x] == STATE_FALLING_BLOCK and display_state[y][x] != STATE_FALLING_BLOCK:
                    display_state[y][x] = GUIDE_LINE_BLOCK
    except:
        pass
    
    os.system('cls')
    output_lines = []
    for line in display_state:
        output = [FRAME] + line + [FRAME]
        output_lines.append(output)
    output_lines.append(FRAME * (WIDTH + 2))
    output_lines.append(f"score: {score}")
    output_lines.append(debug_str)
    
    # NEXTの描画
    another_display = ["NEXT"]
    for line in remaining_minos[0]:
        another_display.append("　" + "".join(line))
    
    if holding_mino is not None:
        another_display.append("")
        another_display.append("HOLD")
        for line in holding_mino:
            another_display.append("　" + "".join(line))
    
    # NEXT, HOLDを元の行に足す
    for i, l in enumerate(another_display):
        output_lines[i] += l
    
    for output in output_lines:
        print("".join(output), flush=True)
    
    sys.stdout.flush()
    
def game():
    global score
    global state
    global falling_mino_shape
    global mino_center_x
    global mino_center_y
    global debug_str
    global holding_mino
    global remaining_minos
    global is_holded
    
    time_to_fall_step = FALLING_SEC
    score = 0
    state = [[STATE_EMPTY]*WIDTH for _ in range(HEIGHT)]
    mino_center_x, mino_center_y = 0, 0
    debug_str = ""
    holding_mino = None
    is_holded = False
    
    input_thread = threading.Thread(target=receive_keyboard_input)
    input_thread.daemon = True
    input_thread.start()
    
    all_minos = load_minos(Path("minos"))
    remaining_minos = all_minos.copy()
    random.shuffle(remaining_minos)
    falling_mino_shape, mino_center_x, mino_center_y = generate_mino()
    
    last_step_time = time.time()
    while True:
        render_screen(state)
        if time.time() - last_step_time > time_to_fall_step:
            is_steped = step_falling_mino()
            claer_line()
            last_step_time = time.time()
        
            if not is_steped: 
                falling_mino_shape, mino_center_x, mino_center_y = generate_mino()
                is_holded = False
                if len(remaining_minos) == 1:
                    addition = all_minos.copy()
                    random.shuffle(addition)
                    remaining_minos += addition
            
        time.sleep(1 / FRAME_RATE)
        

if __name__ == '__main__':
    game()