"""Settings for readerbot: plain constants, read at start-up."""

from pathlib import Path

MODELS_DIR = Path(__file__).parent / "models"

# --- Model ---

CONTEXT_TOKENS = 32768  # context to allocate; capped at the model's training
STEP_MAX_TOKENS = 2048  # longest single model reply (it may carry a file)
MAX_STEPS = 12  # model replies per question; the last one must be an answer
TEMPERATURE = 0.2

# --- Tools ---

OUTLINE_MAX_HEADINGS = 50  # most headings listed by outline_md
READ_MAX_CHARS = 6000  # longest read_md result
SEARCH_MAX_HITS = 20  # matching lines listed by search_md
SNIPPET_CHARS = 160  # text shown around each search hit
WRITE_MAX_CHARS = 8000  # most text one create/append/edit call may write
PANDOC_TIMEOUT_SECONDS = 120
