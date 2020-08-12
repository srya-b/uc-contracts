import logging.config
import os
from pathlib import Path

import yaml


CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parent