import time
import curses
import asyncio


TIC_TIMEOUT = 0.1
BLINK_AMOUNT = 4


async def blink(canvas, row, column, symbol='*'):
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


def draw(canvas):
    coroutines = [blink(canvas, 5, column) for column in range(10, 35, 5)]
    canvas.border()
    curses.curs_set(False)
    while True:
        for _ in range(BLINK_AMOUNT):
            for coroutine in coroutines.copy():
                coroutine.send(None)
            canvas.refresh()
            time.sleep(TIC_TIMEOUT)


if __name__ == '__main__':
    curses.update_lines_cols()
    curses.wrapper(draw)
