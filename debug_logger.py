"""
Add this to final_app.py to enable detailed console logging
"""

import logging
import sys

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler(sys.stdout)  # Ensure logs go to console
    ]
)

# Create logger
logger = logging.getLogger(__name__)

# Add this line after importing your modules
logger.info("Application starting")

# Add more logging statements in crucial parts of your code:
# - Before and after API calls
# - When processing extracted data
# - When handling form submissions
# - When generating 211 files

# Example:
# logger.debug(f"Extracted data structure: {extracted_data.keys()}")
# logger.info(f"PDF text length: {len(text)}")
# logger.error(f"Error in extraction: {str(e)}")
