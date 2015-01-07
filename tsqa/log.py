import logging
import os

logging.root.setLevel(os.environ.get('TSQA_LOG_LEVEL', logging.INFO))
handler = logging.StreamHandler()
handler.setLevel(os.environ.get('TSQA_LOG_LEVEL', logging.INFO))
handler.setFormatter(logging.Formatter("%(levelname)s %(asctime)-15s - %(message)s"))
logging.root.addHandler(handler)

# quiet a few loggers...
logging.getLogger('urllib3').setLevel(logging.CRITICAL)
logging.getLogger('requests').setLevel(logging.WARNING)
