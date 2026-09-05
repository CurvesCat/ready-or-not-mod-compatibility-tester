import os
import sys
import tempfile
import traceback


def _main() -> int:
    from ron_mod_tester.gui_qt import main

    return main()


def _dump_startup_error() -> None:
    try:
        path = os.path.join(tempfile.gettempdir(), "ronct_startup_error.txt")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(traceback.format_exc())
    except OSError:
        pass


if __name__ == "__main__":
    try:
        raise SystemExit(_main())
    except BaseException:
        _dump_startup_error()
        raise
