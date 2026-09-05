from __future__ import annotations

import sys


def _is_cli() -> bool:
    return len(sys.argv) > 1


def main() -> int:
    if _is_cli():
        from .cli import main as cli_main

        return cli_main()
    from .gui_qt import main as qt_main

    return qt_main()


if __name__ == "__main__":
    raise SystemExit(main())

