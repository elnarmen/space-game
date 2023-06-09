import time
import curses
import asyncio
import random
from itertools import cycle
from pathlib import Path

from curses_tools import draw_frame, read_controls, get_frame_size
from physics import update_speed
from obstacles import Obstacle
from explosion import explode


TIC_TIMEOUT = 0.1
GARBAGE_DIR = Path('frames/space_garbage')
STARS_AMOUNT = 50
START_ROW = START_COLUMN = 1
GARBAGE_INDEX = 5
PHRASES = {
    1957: "First Sputnik",
    1961: "Gagarin flew!",
    1969: "Armstrong got on the moon!",
    1971: "First orbital space station Salute-1",
    1981: "Flight of the Shuttle Columbia",
    1998: 'ISS start building',
    2011: 'Messenger launch to Mercury',
    2020: "Take the plasma gun! Shoot the garbage!",
}
YEAR = 1957

coroutines = []
obstacles = []
obstacles_in_last_collision = []


def get_garbage_delay_tics():
    if YEAR < 1961:
        return None
    elif YEAR < 1969:
        return 20
    elif YEAR < 1981:
        return 14
    elif YEAR < 1995:
        return 10
    elif YEAR < 2010:
        return 8
    elif YEAR < 2020:
        return 6
    else:
        return 2


async def change_year():
    global YEAR
    while True:
        await sleep(15)
        YEAR += 1


def load_frame_from_file(filename):
    with open(filename, 'r') as file:
        frame = file.read()
    return frame


async def sleep(tics=1):
    for _ in range(tics):
        await asyncio.sleep(0)


async def blink(canvas, row, column, symbol='*', displacement=10):
    await sleep(displacement)

    while True:
        canvas.addstr(row, column, symbol, curses.A_DIM)
        await sleep(20)

        canvas.addstr(row, column, symbol)
        await sleep(3)

        canvas.addstr(row, column, symbol, curses.A_BOLD)
        await sleep(5)

        canvas.addstr(row, column, symbol)
        await sleep(3)


async def animate_spaceship(canvas, row, column, frames: tuple):
    rows_number, columns_number = canvas.getmaxyx()
    rocket_frame_1, rocket_frame_2 = frames
    frame_height, frame_width = get_frame_size(rocket_frame_1)

    left_frame_border = column - frame_width // 2
    bottom_frame_border = row - frame_height // 2
    row_speed = column_speed = 0

    rocket_animation_frames = cycle(
        [rocket_frame_1, rocket_frame_1, rocket_frame_2, rocket_frame_2]
    )

    for frame in rocket_animation_frames:
        row_direction, column_direction, space_pressed = read_controls(canvas)
        left_frame_border += column_direction
        bottom_frame_border += row_direction
        row_speed, column_speed = update_speed(
            row_speed, column_speed,
            row_direction, column_direction
        )

        right_frame_border = left_frame_border + frame_width
        upper_frame_border = bottom_frame_border + frame_height

        left_frame_border = min(
            right_frame_border,
            columns_number - START_COLUMN - column_speed
        ) - frame_width

        bottom_frame_border = min(
            upper_frame_border,
            rows_number - START_ROW - row_speed
        ) - frame_height

        left_frame_border = max(left_frame_border + column_speed, START_COLUMN)
        bottom_frame_border = max(bottom_frame_border + row_speed, START_ROW)

        draw_frame(canvas, bottom_frame_border, left_frame_border, frame)
        await asyncio.sleep(0)
        draw_frame(
            canvas, bottom_frame_border,
            left_frame_border, frame, negative=True
        )
        if YEAR >= 2020 and space_pressed:
            ship_indent = 1
            coroutines.append(
                fire(
                    canvas,
                    bottom_frame_border - ship_indent,
                    left_frame_border + frame_width // 2,
                    rows_speed=-1
                )
            )
        for obstacle in obstacles:
            if obstacle.has_collision(
                    bottom_frame_border,
                    left_frame_border,
                    frame_height,
                    frame_width
            ):
                coroutines.append(show_gameover(canvas))
                await explode(canvas, upper_frame_border, left_frame_border)
                return


async def fire(
        canvas, start_row, start_column, rows_speed=-0.3, columns_speed=0
):
    """Display animation of gun shot, direction and speed can be specified."""
    global obstacles
    row, column = start_row, start_column

    canvas.addstr(round(row), round(column), '*')
    await asyncio.sleep(0)

    canvas.addstr(round(row), round(column), 'O')
    await asyncio.sleep(0)
    canvas.addstr(round(row), round(column), ' ')

    row += rows_speed
    column += columns_speed

    symbol = '-' if columns_speed else '|'

    rows_number, columns_number = canvas.getmaxyx()
    max_row, max_column = rows_number - 1, columns_number - 1

    curses.beep()

    while 0 < row < max_row and 0 < column < max_column:
        for obstacle in obstacles:
            if obstacle.has_collision(round(row), round(column)):
                obstacles_in_last_collision.append(obstacle)
                obstacles.remove(obstacle)
                return
        canvas.addstr(round(row), round(column), symbol)
        await asyncio.sleep(0)
        canvas.addstr(round(row), round(column), ' ')
        row += rows_speed
        column += columns_speed


async def fill_orbit_with_garbage(canvas, garbage_frames):
    _, columns_number = canvas.getmaxyx() #  Return a tuple (y, x) of the height and width of the window.

    while True:
        garbage_delay_tics = get_garbage_delay_tics()
        current_frame = random.choice(garbage_frames)
        column = random.randint(START_COLUMN, columns_number)
        if not garbage_delay_tics:
            await sleep(1)
            continue
        await sleep(garbage_delay_tics)
        coroutines.append(fly_garbage(canvas, column, current_frame))


async def fly_garbage(canvas, column, garbage_frame, speed=0.5):
    """Animate garbage, flying from top to bottom. Сolumn position will stay same, as specified on start."""
    global obstacles

    rows_number, columns_number = canvas.getmaxyx()
    _, frame_width = get_frame_size(garbage_frame)

    left_frame_border = column - frame_width // 2
    right_frame_border = left_frame_border + frame_width

    left_frame_border = min(right_frame_border, columns_number - START_COLUMN) - frame_width
    left_frame_border = max(left_frame_border, START_COLUMN)

    row = START_ROW
    obstacle_rows, obstacle_columns = get_frame_size(garbage_frame)
    obstacle = Obstacle(row, left_frame_border, obstacle_rows, obstacle_columns)
    obstacles.append(obstacle)
    try:
        while row < rows_number:
            if obstacle in obstacles_in_last_collision:
                await explode(canvas, row, left_frame_border)
                return
            draw_frame(canvas, row, left_frame_border, garbage_frame)
            await asyncio.sleep(0)
            draw_frame(canvas, row, left_frame_border, garbage_frame, negative=True)
            row += speed
            obstacle.row = row
    finally:
        if obstacle in obstacles:
            obstacles.remove(obstacle)


async def show_gameover(canvas):
    frame = load_frame_from_file(Path('frames', 'game_over.txt'))
    _, frame_width = get_frame_size(frame)
    rows_number, columns_number = canvas.getmaxyx()
    columns_center = columns_number // 2

    left_frame_border = columns_center - frame_width // 2
    row = rows_number // 2

    while True:
        draw_frame(canvas, row, left_frame_border, frame)
        await sleep(1)


async def show_phrase(canvas):
    rows_number, columns_number = canvas.getmaxyx()
    columns_center = columns_number // 2
    while True:
        phrase = PHRASES.get(YEAR)
        if phrase:
            frame = f'{YEAR} - {phrase}'
        else:
            frame = str(YEAR)
        frame_rows, frame_columns = get_frame_size(frame)
        left_frame_border = columns_center - frame_columns // 2
        draw_frame(canvas, 1, left_frame_border, frame)
        await sleep(1)
        draw_frame(canvas, 1, left_frame_border, frame, negative=True)


def draw(canvas):
    global obstacles_in_last_collision
    obstacles_in_last_collision = []

    curses.curs_set(False)
    canvas.nodelay(True)

    rows_number, columns_number = canvas.getmaxyx()
    start_row, start_column = 2, 1
    end_row = rows_number - 2
    end_column = columns_number - 2
    row_center = end_row // 2
    column_center = end_column // 2

    rocket_frame_1 = load_frame_from_file(Path('frames/rocket_frame_1.txt'))
    rocket_frame_2 = load_frame_from_file(Path('frames/rocket_frame_2.txt'))

    garbage_frames = [
        load_frame_from_file(file) for file in GARBAGE_DIR.glob('*')
    ]

    coroutines.extend(
        [
            animate_spaceship(
                canvas,
                row_center,
                column_center,
                (rocket_frame_1, rocket_frame_2)
            ),
            fill_orbit_with_garbage(canvas, garbage_frames),
            change_year(),
            show_phrase(canvas)
        ]
    )

    coroutines.extend(
        [blink(
            canvas,
            random.randint(start_row, end_row),
            random.randint(start_column, end_column),
            random.choice(['*', '+', '.', ':']),
            random.randint(1, 20)
        ) for _ in range(STARS_AMOUNT)]
    )

    while True:
        for coroutine in coroutines.copy():
            try:
                coroutine.send(None)
            except StopIteration:
                coroutines.remove(coroutine)
        canvas.border()
        canvas.refresh()
        time.sleep(TIC_TIMEOUT)


if __name__ == '__main__':
    curses.update_lines_cols()
    curses.wrapper(draw)
