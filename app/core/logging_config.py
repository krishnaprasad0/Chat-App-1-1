import logging
import os
from logging.handlers import TimedRotatingFileHandler

def setup_logging():
    # 1. Create logs directory if it doesn't exist
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_file = os.path.join(log_dir, "app.log")

    # 2. Define the format
    log_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # 3. Setup TimedRotatingFileHandler
    # Rotates every 7 days, keeps 1 backup (the previous 7 days)
    # The user said "clear after every 7 days", so rotation is the standard way.
    file_handler = TimedRotatingFileHandler(
        log_file,
        when="D",
        interval=7,
        backupCount=1,
        encoding="utf-8"
    )
    file_handler.setFormatter(log_format)

    # 4. Setup StreamHandler for console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_format)

    # 5. Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Clear existing handlers to avoid duplicates (important during reloads)
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
        
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Set some common library loggers to WARNING to avoid noise
    logging.getLogger("uvicorn.access").disabled = True # We'll handle this in custom middleware
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    
    logging.info("Logging initialized. Logs will be saved to %s and rotated every 7 days.", log_file)
