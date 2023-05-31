import time
import curses
import asyncio
import random

from animation import draw_frame, read_controls, get_frame_size


TIC_TIMEOUT = 0.1


def load_frame_from_file(filename):
    with open(filename, 'r') as file:
        frame = file.read()
    return frame


async def blink(canvas, row, column, symbol='*', displacement=10):
    for _ in range(displacement):
        await asyncio.sleep(0)

    while True:
        canvas.addstr(row, column, symbol, curses.A_DIM)
        for _ in range(20):
            await asyncio.sleep(0)

        canvas.addstr(row, column, symbol)
        for _ in range(3):
            await asyncio.sleep(0)

        canvas.addstr(row, column, symbol, curses.A_BOLD)
        for _ in range(5):
            await asyncio.sleep(0)

        canvas.addstr(row, column, symbol)
        for _ in range(3):
            await asyncio.sleep(0)


async def animate_spaceship(canvas, row, column, frames: tuple):
    field_height, field_width = canvas.getmaxyx()
    frame_height, frame_width = get_frame_size(frames[0])
    left_frame_border = column - frame_width // 2
    bottom_frame_border = row - frame_height // 2
    field_border = 1

    while True:
        for frame in frames:
            row_direction, column_direction, _ = read_controls(canvas)
            left_frame_border += column_direction
            bottom_frame_border += row_direction

            right_frame_border = left_frame_border + frame_width
            upper_frame_border = bottom_frame_border + frame_height

            left_frame_border = min(right_frame_border,
                                    field_width - field_border) - frame_width
            bottom_frame_border = min(upper_frame_border,
                                      field_height - field_border) - frame_height

            left_frame_border = max(left_frame_border, field_border)
            bottom_frame_border = max(bottom_frame_border, field_border)

            draw_frame(canvas, bottom_frame_border, left_frame_border, frame)
            canvas.refresh()
            for _ in range(2):
                await asyncio.sleep(0)
            draw_frame(
                canvas, bottom_frame_border,
                left_frame_border, frame, negative=True
            )


async def fire(
        canvas, start_row, start_column, rows_speed=-0.3, columns_speed=0
):
    """Display animation of gun shot, direction and speed can be specified."""

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
        canvas.addstr(round(row), round(column), symbol)
        await asyncio.sleep(0)
        canvas.addstr(round(row), round(column), ' ')
        row += rows_speed
        column += columns_speed


def draw(canvas):
    canvas.border()
    curses.curs_set(False)
    canvas.nodelay(True)

    rows_number, columns_number = canvas.getmaxyx()
    start_row, start_column = 1, 1
    end_row = rows_number - 2
    end_column = columns_number - 2
    row_center = end_row // 2
    column_center = end_column // 2

    rocket_frame_1 = load_frame_from_file('animations/rocket_frame_1.txt')
    rocket_frame_2 = load_frame_from_file('animations/rocket_frame_2.txt')

    coroutines = [
        animate_spaceship(
            canvas,
            row_center,
            column_center,
            (rocket_frame_1, rocket_frame_2)
        ),
    ]

    for _ in range(100):
        coroutines.append(
            blink(
                canvas,
                random.randint(start_row, end_row),
                random.randint(start_column, end_column),
                random.choice(['*', '+', '.', ':']),
                random.randint(1, 20)
            )
        )

    while True:
        for coroutine in coroutines.copy():
            try:
                coroutine.send(None)
            except StopIteration:
                coroutines.remove(coroutine)

        canvas.refresh()
        time.sleep(TIC_TIMEOUT)


if __name__ == '__main__':
    curses.update_lines_cols()
    curses.wrapper(draw)
