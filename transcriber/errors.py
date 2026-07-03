"""Plain-language error handling.

The owner of this tool cannot read code or debug tracebacks. Every
anticipated failure must be raised as a UserFacingError with a message
that says what happened and exactly what to do next, in Indonesian.
Anything that is NOT a UserFacingError is an unanticipated bug: the CLI
catches it, logs the real traceback to run.log, and points the owner at
that log instead of dumping the traceback to the terminal.
"""

from __future__ import annotations


class UserFacingError(Exception):
    """An error whose message is safe and helpful to show directly to the owner.

    `message` should be in Indonesian, explain what went wrong, and say
    exactly what to do next (a command to run, a file to check, a link
    to open). Never include Python internals.
    """

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message
