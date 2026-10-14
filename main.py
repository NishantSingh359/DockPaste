import sys
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow
from config import APP_NAME, APP_STORAGE_DIR
from utils.app_logging import log_exception, setup_logging
from utils.app_icon import create_app_icon

setup_logging(APP_STORAGE_DIR)
app = QApplication(sys.argv)
app.setApplicationName(APP_NAME)
app.setWindowIcon(create_app_icon())
app.setQuitOnLastWindowClosed(False)

try:
    window = MainWindow()
    app.aboutToQuit.connect(window.shutdown)
    window.show()
except Exception:
    log_exception("Failed to start main window")
    raise


sys.exit(app.exec())
