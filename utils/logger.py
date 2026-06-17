import logging
import os
import sys
import time
import traceback


def setup_logging(log_dir: str) -> tuple[str, str]:
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    error_log = os.path.join(log_dir, "error.log")
    debug_log = os.path.join(log_dir, "debug.log")

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(debug_log, encoding="utf-8", mode="a"),
            logging.FileHandler(error_log, encoding="utf-8", mode="a"),
        ],
    )
    return error_log, debug_log


def install_global_exception_hook(error_log: str) -> None:
    def handle_exception(exc_type, exc_value, exc_traceback):
        error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        try:
            with open(error_log, "a", encoding="utf-8") as f:
                f.write(f"\n{'=' * 60}\n")
                f.write(f"异常时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(error_msg)
                f.write(f"\n{'=' * 60}\n")
        except Exception:
            pass
        try:
            import tkinter.messagebox as messagebox
            messagebox.showerror("程序错误", f"程序发生错误：\n{str(exc_value)}\n\n错误详情已保存到：\n{error_log}")
        except Exception:
            pass

    sys.excepthook = handle_exception
