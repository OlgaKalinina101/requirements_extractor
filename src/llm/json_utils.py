"""JSON parsing utilities for AI responses with error recovery."""

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def parse_json_safely(content: str, context: str = "") -> Any:
    """Safely parse JSON from AI response with error handling and recovery.

    Attempts multiple strategies to extract valid JSON:
    1. Extract JSON from code blocks
    2. Find JSON array/object boundaries
    3. Fix common JSON errors (unterminated strings, trailing commas)
    4. Try parsing partial JSON if full parse fails

    Args:
        content: Raw content from AI response
        context: Context string for error messages

    Returns:
        Parsed JSON data (list, dict, or other valid JSON type)

    Raises:
        ValueError: If JSON cannot be parsed after all attempts
    """
    # Strategy 1: Extract from code blocks
    if "```json" in content:
        json_start = content.find("```json") + 7
        json_end = content.find("```", json_start)
        if json_end > json_start:
            content = content[json_start:json_end].strip()
    elif "```" in content:
        parts = content.split("```")
        if len(parts) > 1:
            for part in parts[1:]:
                part = part.strip()
                if part.startswith("{") or part.startswith("["):
                    content = part
                    break

    # Strategy 2: Find JSON boundaries
    if not content.strip().startswith(("[", "{")):
        array_start = content.find("[")
        obj_start = content.find("{")
        if array_start >= 0 and (obj_start < 0 or array_start < obj_start):
            content = content[array_start:]
        elif obj_start >= 0:
            content = content[obj_start:]

    # Strategy 3: Find JSON end (try to find matching brackets)
    if content.strip().startswith("["):
        bracket_count = 0
        last_valid_pos = len(content)
        for i, char in enumerate(content):
            if char == "[":
                bracket_count += 1
            elif char == "]":
                bracket_count -= 1
                if bracket_count == 0:
                    last_valid_pos = i + 1
                    break
        content = content[:last_valid_pos]
    elif content.strip().startswith("{"):
        brace_count = 0
        last_valid_pos = len(content)
        for i, char in enumerate(content):
            if char == "{":
                brace_count += 1
            elif char == "}":
                brace_count -= 1
                if brace_count == 0:
                    last_valid_pos = i + 1
                    break
        content = content[:last_valid_pos]

    # Strategy 4: Fix common JSON errors
    content = content.strip()
    content = re.sub(r',\s*([}\]])', r'\1', content)

    lines = content.split('\n')
    fixed_lines = []
    in_string = False
    for i, line in enumerate(lines):
        quote_count = len(re.findall(r'(?<!\\)"', line))
        if quote_count > 0:
            if quote_count % 2 != 0:
                in_string = not in_string
            else:
                in_string = False

        if in_string and i == len(lines) - 1:
            if not line.rstrip().endswith(('"', ',', ']', '}')):
                line = line.rstrip() + '"'
                in_string = False

        fixed_lines.append(line)
    content = '\n'.join(fixed_lines)

    if in_string and not content.rstrip().endswith('"'):
        content = content.rstrip() + '"'

    # Strategy 5: Try parsing
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        logger.warning(f"JSON parse error {context}: {e}")
        logger.debug(f"Failed to parse content (first 500 chars): {content[:500]}")

        # Strategy 6: Try to extract partial JSON
        if content.strip().startswith("["):
            items = []
            start_pos = content.find("[") + 1
            brace_count = 0
            item_start = None

            for i in range(start_pos, len(content)):
                char = content[i]
                if char == "{":
                    if brace_count == 0:
                        item_start = i
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1
                    if brace_count == 0 and item_start is not None:
                        try:
                            item_str = content[item_start:i+1]
                            item = json.loads(item_str)
                            items.append(item)
                        except json.JSONDecodeError:
                            pass
                        item_start = None
                elif char == "]" and brace_count == 0:
                    break

            if items:
                logger.info(f"Extracted {len(items)} valid items from partial JSON")
                return items

        logger.error(f"Failed to parse JSON after all attempts. Error: {e}")
        logger.error(f"Content length: {len(content)}, First 1000 chars:\n{content[:1000]}")
        raise ValueError(f"Failed to parse JSON response: {e}. Context: {context}")
