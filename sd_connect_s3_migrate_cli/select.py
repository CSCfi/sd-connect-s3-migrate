"""Curses rendering for TUI to select the project and buckets."""

import curses

import sd_connect_s3_migrate_cli.types

bucket_type = (
    list[sd_connect_s3_migrate_cli.types.OpenstackBucket]
    | list[sd_connect_s3_migrate_cli.types.OpenstackProject]
)


def _truncate(text: str, width: int) -> str:
    """Truncate row to fit the terminal."""
    if width <= 0:
        return ""

    if len(text) <= width:
        return text

    if width <= 3:
        return "." * width

    return text[: width - 3] + "..."


def _selection_screen(
    stdscr: curses.window,
    buckets: bucket_type,
    message: str,
) -> (
    list[sd_connect_s3_migrate_cli.types.OpenstackBucket]
    | list[sd_connect_s3_migrate_cli.types.OpenstackProject]
    | None
):
    """Display a selector for a project or bucket list using curses."""
    curses.curs_set(0)

    current_index = 0
    top_index = 0

    selected: set[int] = set()

    while True:
        height, width = stdscr.getmaxyx()

        stdscr.erase()

        header = (
            "Space: toggle selection  " "↑/↓: navigate  " "Enter: confirm  " "q: cancel"
        )

        stdscr.addnstr(0, 0, header, width - 1)

        # Display validation message
        if message:
            stdscr.addnstr(
                1, 0, _truncate("Error: " + message, width - 1), width - 1, curses.A_BOLD
            )

        starting_row = 2
        visible_rows = max(starting_row, height - 2)

        if current_index < top_index:
            top_index = current_index

        if current_index >= top_index + visible_rows:
            top_index = current_index - visible_rows + 1

        for row in range(visible_rows):
            bucket_index = top_index + row

            if bucket_index >= len(buckets):
                break

            bucket = buckets[bucket_index]
            checked = bucket_index in selected
            prefix = "[x] " if checked else "[ ] "
            available_width = max(1, width - len(prefix) - 1)
            name = _truncate(bucket["name"], available_width)
            line = prefix + name

            if bucket_index == current_index:
                stdscr.addnstr(
                    row + starting_row,
                    0,
                    line,
                    width - 1,
                    curses.A_REVERSE,
                )
            else:
                stdscr.addnstr(
                    row + starting_row,
                    0,
                    line,
                    width - 1,
                )

        stdscr.refresh()
        key = stdscr.getch()

        if key in (curses.KEY_UP, ord("k")):
            if current_index > 0:
                current_index -= 1
        elif key in (curses.KEY_DOWN, ord("j")):
            if current_index < len(buckets) - 1:
                current_index += 1
        elif key == ord(" "):
            if current_index in selected:
                selected.remove(current_index)
            else:
                selected.add(current_index)
        elif key in (10, 13, curses.KEY_ENTER):
            return [bucket for i, bucket in enumerate(buckets) if i in selected]  # type: ignore
        elif key == ord("q"):
            return None


def select_buckets(
    buckets: list[sd_connect_s3_migrate_cli.types.OpenstackBucket],
    message: str,
) -> list[sd_connect_s3_migrate_cli.types.OpenstackBucket] | None:
    return curses.wrapper(_selection_screen, buckets, message)  # type: ignore


def select_projects(
    projects: list[sd_connect_s3_migrate_cli.types.OpenstackProject],
    message: str,
) -> list[sd_connect_s3_migrate_cli.types.OpenstackProject] | None:
    return curses.wrapper(_selection_screen, projects, message)  # type: ignore
