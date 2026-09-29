"""Handler to split console output into multiple streams without having to rewrite the logging functionale."""

import datetime
import typing

import click


class Tee:
    """Write to primary stream (terminal) and mirror unstyled text with timestamps to others."""

    def __init__(
        self, log_prefix: str, primary: typing.TextIO, *streams: typing.TextIO
    ) -> None:
        """Init tee."""
        self._log_prefix = log_prefix
        self._primary = primary
        self._streams = streams

    def write(self, data: str) -> int:
        """Implement io write."""
        n = self._primary.write(data)
        timestamp = datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")
        for stream in self._streams:
            stream.write(f"[{timestamp}] {self._log_prefix} {click.unstyle(data)}")

        return n

    def flush(self) -> None:
        """Implement io flush."""
        for stream in (self._primary, *self._streams):
            stream.flush()

    def isatty(self) -> bool:
        """Implement io isatty."""
        return self._primary.isatty()


def get_terminal(stream: typing.TextIO) -> typing.TextIO:
    """Return the underlying terminal stream, useful for printing progress bars."""
    return stream._primary if isinstance(stream, Tee) else stream
