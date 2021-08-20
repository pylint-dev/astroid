import logging
import logging.handlers
from pathlib import Path
import tempfile

LOGGER = logging.Logger('astroid_logger')
LOGGER.setLevel(logging.DEBUG)

TMPFILE = Path(tempfile.gettempdir()) / "astroid.log"
FILEHANDLER = logging.handlers.RotatingFileHandler(TMPFILE, mode='a', encoding="utf-8", maxBytes=2*1024**2, backupCount=5)
FILEHANDLER.setLevel(logging.DEBUG)

FORMATTER = logging.Formatter('%(asctime)s - %(name)s - %(funcName)s - line: %(lineno)d - %(levelname)s - %(message)s')
FILEHANDLER.setFormatter(FORMATTER)

LOGGER.addHandler(FILEHANDLER)