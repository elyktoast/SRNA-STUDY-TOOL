"""Include Phase C regression cases in the staging CI discovery root.

The source-level test modules are also directly executable by developers.
"""
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from test_rewrite_answer_integrity_v2 import RewriteAnswerIntegrityTests
from test_screening_state_integration_v2 import ScreeningStateTests
