"""
Data Persistence in JSON

This module handles all file I/O for portfolio_history.json.
"""

import json
import os
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

HISTORY_FILE = 'portfolio_history.json'


def save_snapshot(snapshot_data: Dict[str, Any]) -> None:
    """
    Appends a new snapshot to the portfolio_history.json file.
    
    Args:
        snapshot_data: Dictionary conforming to the Snapshot JSON Schema
    """
    try:
        # Read existing history
        history = []
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, 'r') as f:
                    content = f.read().strip()
                    if content:
                        history = json.loads(content)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Could not read existing history file, starting fresh: {e}")
                history = []
        
        # Ensure history is a list
        if not isinstance(history, list):
            logger.warning("History file format invalid, starting fresh")
            history = []
        
        # Append new snapshot
        history.append(snapshot_data)
        
        # Write back to file
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Successfully saved snapshot to {HISTORY_FILE}. Total snapshots: {len(history)}")
        
    except Exception as e:
        logger.error(f"Failed to save snapshot: {e}")
        raise


def get_latest_snapshot() -> Optional[Dict[str, Any]]:
    """
    Retrieves the most recent snapshot from the history file.
    
    Returns:
        dict: The latest snapshot object, or None if the file is empty
    """
    try:
        if not os.path.exists(HISTORY_FILE):
            logger.info(f"History file {HISTORY_FILE} does not exist")
            return None
        
        with open(HISTORY_FILE, 'r') as f:
            content = f.read().strip()
            if not content:
                logger.info("History file is empty")
                return None
            
            history = json.loads(content)
            
            if not isinstance(history, list):
                logger.warning("History file format invalid")
                return None
            
            if len(history) == 0:
                logger.info("No snapshots in history")
                return None
            
            latest = history[-1]
            logger.info(f"Retrieved latest snapshot from {latest.get('timestamp', 'unknown time')}")
            return latest
            
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Failed to read latest snapshot: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error reading latest snapshot: {e}")
        return None


def get_all_snapshots() -> List[Dict[str, Any]]:
    """
    Retrieves all snapshots from the history file.
    
    Returns:
        list: All snapshot objects, or empty list if file doesn't exist or is empty
    """
    try:
        if not os.path.exists(HISTORY_FILE):
            logger.info(f"History file {HISTORY_FILE} does not exist")
            return []
        
        with open(HISTORY_FILE, 'r') as f:
            content = f.read().strip()
            if not content:
                logger.info("History file is empty")
                return []
            
            history = json.loads(content)
            
            if not isinstance(history, list):
                logger.warning("History file format invalid")
                return []
            
            logger.info(f"Retrieved {len(history)} snapshots from history")
            return history
            
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Failed to read snapshots: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error reading snapshots: {e}")
        return []