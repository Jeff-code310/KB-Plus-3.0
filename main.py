import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.logger import setup_logging, install_global_exception_hook


def main() -> None:
    app_dir = os.path.dirname(os.path.abspath(__file__))
    logs_dir = os.path.join(app_dir, "logs")
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)

    error_log, debug_log = setup_logging(logs_dir)
    install_global_exception_hook(error_log)

    from ui.main_window import MainWindow
    app = MainWindow()
    app.run()


if __name__ == "__main__":
    main()
