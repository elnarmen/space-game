import os
import time
import curses
import asyncio
import random
from itertools import cycle
from pathlib import Path

from curses_tools import draw_frame, read_controls, get_frame_size
from physics import update_speed
from obstacles import Obstacle, show_obstacles
from explosion import explode


TIC_TIMEOUT = 0.1
GARBAGE_DIR = Path('frames/space_garbage')
COROUTINES = []
OBSTACLES = []
OBSTACLES_IN_LAST_COLLISION = []
STARS_AMOUNT = 100
FIELD_INDENT = 1
GARBAGE_INDEX = 5


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
    field_height, field_width = canvas.getmaxyx()
    rocket_frame_1, rocket_frame_2 = frames
    frame_height, frame_width = get_frame_size(rocket_frame_1)

    left_frame_border = column - frame_width // 2
    bottom_frame_border = row - frame_height // 2
    ship_indent = 1
    row_speed = column_speed = 0

    rocket_animation_frames = cycle([rocket_frame_1, rocket_frame_1, rocket_frame_2, rocket_frame_2])

    for frame in rocket_animation_frames:
        row_direction, column_direction, space_pressed = read_controls(canvas)
        left_frame_border += column_direction
        bottom_frame_border += row_direction
        row_speed, column_speed = update_speed(row_speed, column_speed, row_direction, column_direction)

        right_frame_border = left_frame_border + frame_width
        upper_frame_border = bottom_frame_border + frame_height

        left_frame_border = min(right_frame_border,
                                field_width - FIELD_INDENT - column_speed) - frame_width
        bottom_frame_border = min(upper_frame_border,
                                  field_height - FIELD_INDENT - row_speed) - frame_height

        left_frame_border = max(left_frame_border + column_speed, FIELD_INDENT)
        bottom_frame_border = max(bottom_frame_border + row_speed, FIELD_INDENT)

        draw_frame(canvas, bottom_frame_border, left_frame_border, frame)
        await asyncio.sleep(0)
        draw_frame(
            canvas, bottom_frame_border,
            left_frame_border, frame, negative=True
        )
        if space_pressed:
            COROUTINES.append(
                fire(
                    canvas,
                    bottom_frame_border - ship_indent,
                    left_frame_border + frame_width // 2,
                    rows_speed=-1
                )
            )
        for obstacle in OBSTACLES:
            if obstacle.has_collision(
                    bottom_frame_border,
                    left_frame_border,
                    frame_height,
                    frame_width
            ):
                COROUTINES.append(show_gameover(canvas))
                await explode(canvas, upper_frame_border, left_frame_border)
                return


async def fire(
        canvas, start_row, start_column, rows_speed=-0.3, columns_speed=0
):
    """Display animation of gun shot, direction and speed can be specified."""
    global OBSTACLES
    row, column = start_row, start_column

    canvas.addstr(round(row), round(column), '*')
    await asyncio.sleep(0)

    canvas.addstr(round(row), round(column), 'O')
    await asyncio.sleep(0)
    canvas.addstr(round(row), round(column), ' ')

    row += rows_speed
    column += columns_speed

    symbol = '-' if columns_speed else '|'

    rows, columns = canvas.getmaxyx()
    max_row, max_column = rows - 1, columns - 1

    curses.beep()

    while 0 < row < max_row and 0 < column < max_column:
        for obstacle in OBSTACLES:
            if obstacle.has_collision(round(row), round(column)):
                OBSTACLES_IN_LAST_COLLISION.append(obstacle)
                OBSTACLES.remove(obstacle)
                return
        canvas.addstr(round(row), round(column), symbol)
        await asyncio.sleep(0)
        canvas.addstr(round(row), round(column), ' ')
        row += rows_speed
        column += columns_speed


async def fill_orbit_with_garbage(canvas, garbage_frames):
    _, field_width = canvas.getmaxyx()

    while True:
        current_frame = random.choice(garbage_frames)
        column = random.randint(FIELD_INDENT, field_width)
        COROUTINES.append(fly_garbage(canvas, column, current_frame))
        await sleep(GARBAGE_INDEX)


async def fly_garbage(canvas, column, garbage_frame, speed=0.5):
    """Animate garbage, flying from top to bottom. Сolumn position will stay same, as specified on start."""
    global OBSTACLES

    rows_number, columns_number = canvas.getmaxyx()
    _, frame_width = get_frame_size(garbage_frame)

    left_frame_border = column - frame_width // 2
    right_frame_border = left_frame_border + frame_width

    left_frame_border = min(right_frame_border, columns_number - FIELD_INDENT) - frame_width
    left_frame_border = max(left_frame_border, FIELD_INDENT)

    row = 0
    obstacle_rows, obstacle_columns = get_frame_size(garbage_frame)
    obstacle = Obstacle(row, left_frame_border, obstacle_rows, obstacle_columns)
    OBSTACLES.append(obstacle)
    try:
        while row < rows_number:
            if obstacle in OBSTACLES_IN_LAST_COLLISION:
                await explode(canvas, row, left_frame_border)
                return
            draw_frame(canvas, row, left_frame_border, garbage_frame)
            await asyncio.sleep(0)
            draw_frame(canvas, row, left_frame_border, garbage_frame, negative=True)
            row += speed
            obstacle.row = row
    finally:
        if obstacle in OBSTACLES:
            OBSTACLES.remove(obstacle)


async def show_gameover(canvas):
    frame = load_frame_from_file(Path('frames', 'game_over.txt'))
    _, frame_width = get_frame_size(frame)
    rows_number, columns_number = canvas.getmaxyx()
    columns_center = columns_number // 2

    left_frame_border = columns_center - frame_width // 2
    row = rows_number // 2

    while True:
        draw_frame(canvas, row, left_frame_border, frame)
        await asyncio.sleep(0)


def draw(canvas):
    global OBSTACLES_IN_LAST_COLLISION
    OBSTACLES_IN_LAST_COLLISION = []

    canvas.border()
    curses.curs_set(False)
    canvas.nodelay(True)

    rows_number, columns_number = canvas.getmaxyx()
    start_row, start_column = 1, 1
    end_row = rows_number - 2
    end_column = columns_number - 2
    row_center = end_row // 2
    column_center = end_column // 2

    rocket_frame_1 = load_frame_from_file(Path('frames/rocket_frame_1.txt'))
    rocket_frame_2 = load_frame_from_file(Path('frames/rocket_frame_2.txt'))

    garbage_frames = [
        load_frame_from_file(file) for file in GARBAGE_DIR.glob('*')
    ]

    COROUTINES.extend(
        [
            animate_spaceship(
                canvas,
                row_center,
                column_center,
                (rocket_frame_1, rocket_frame_2)
            ),
            fill_orbit_with_garbage(canvas, garbage_frames)
        ]
    )

    COROUTINES.extend(
        [blink(
            canvas,
            random.randint(start_row, end_row),
            random.randint(start_column, end_column),
            random.choice(['*', '+', '.', ':']),
            random.randint(1, 20)
        ) for _ in range(STARS_AMOUNT)]
    )

    while True:
        for coroutine in COROUTINES.copy():
            try:
                coroutine.send(None)
            except StopIteration:
                COROUTINES.remove(coroutine)

        canvas.refresh()
        time.sleep(TIC_TIMEOUT)


if __name__ == '__main__':
    curses.update_lines_cols()
    curses.wrapper(draw)

