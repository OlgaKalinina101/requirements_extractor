"""
Helper function to find the page number where a requirement text appears.

Uses semantic search with multiple strategies:
1. Exact match (first 100 chars)
2. Short match (first 50 chars)
3. Keyword matching (filtered tokens)
"""
from typing import List, Optional, Set
import logging
import re

logger = logging.getLogger(__name__)


# Russian stop-words - common words without significant meaning
STOP_WORDS = {
    "а", "и", "в", "на", "с", "у", "к", "о", "из", "за", "по", "от", "до",
    "что", "как", "это", "так", "ты", "я", "мы", "он", "она", "они", "вы",
    "не", "да", "но", "же", "ли", "бы", "то", "ещё", "еще", "уже", "вот",
    "все", "всё", "мне", "меня", "тебе", "тебя", "нам", "нас", "мой", "твой",
    "если", "когда", "чтобы", "потому", "очень", "только", "просто", "прям",
    "какие", "какой", "какая", "какое", "который", "которая", "которое",
    "хочешь", "хочу", "могу", "можешь", "буду", "будет", "есть", "был", "была",
    "опять", "снова", "теперь", "сейчас", "тоже", "также", "быть", "этот",
    "эти", "этим", "этих", "того", "тому", "том", "без", "для", "про", "при",
}


def normalize_text(text: str) -> str:
    """Normalize text for comparison.
    
    - Lowercase
    - Remove punctuation and emojis
    - Trim whitespace
    - Remove extra spaces
    
    Args:
        text: Text to normalize
        
    Returns:
        Normalized text
    """
    # Lowercase
    text = text.lower()
    # Keep only letters, numbers, and spaces
    text = re.sub(r'[^\w\s]', ' ', text)
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def tokenize(text: str) -> Set[str]:
    """Tokenize text into meaningful words.
    
    - Split by whitespace and punctuation
    - Filter stop-words
    - Filter short tokens (< 3 characters)
    
    Args:
        text: Text to tokenize
        
    Returns:
        Set of meaningful tokens (lowercase)
    """
    # Split by whitespace and punctuation
    tokens = re.split(r'[\s,;.!?()\[\]{}"\'\-]+', text)
    
    # Filter and normalize
    meaningful_tokens = {
        token.lower()
        for token in tokens
        if token and len(token) > 3 and token.lower() not in STOP_WORDS
    }
    
    return meaningful_tokens


def calculate_keyword_match_score(query_tokens: Set[str], page_tokens: Set[str]) -> float:
    """Calculate keyword matching score.
    
    Score = (matching tokens / query tokens) * 100
    
    Args:
        query_tokens: Set of tokens from requirement text
        page_tokens: Set of tokens from page text
        
    Returns:
        Match score in range [0, 100]
    """
    if not query_tokens:
        return 0.0
    
    matching_tokens = query_tokens.intersection(page_tokens)
    score = (len(matching_tokens) / len(query_tokens)) * 100
    
    return score


def find_page_by_text_search(
    requirement_text: str,
    pages: List[str],
    page_start: int,
    page_end: Optional[int] = None,
    min_keyword_score: float = 50.0
) -> Optional[int]:
    """Find the page number where requirement text first appears.
    
    Uses multiple search strategies:
    1. Exact match (first 100 chars) - highest priority
    2. Short match (first 50 chars) - medium priority  
    3. Keyword matching (filtered tokens) - fallback
    
    Args:
        requirement_text: Text of the requirement to find
        pages: List of all page texts (0-indexed)
        page_start: Starting page number to search from (1-indexed)
        page_end: Ending page number to search until (1-indexed, exclusive)
                  None means search until end of document
        min_keyword_score: Minimum keyword match score (0-100) to consider a match
    
    Returns:
        Page number (1-indexed) where requirement was found, or None if not found
    """
    if not requirement_text or not pages:
        return None
    
    # Determine search range
    if page_end is None:
        page_end = len(pages) + 1
    
    # Convert to 0-indexed
    start_idx = page_start - 1
    end_idx = min(page_end - 1, len(pages))
    
    # Normalize requirement text
    req_normalized = normalize_text(requirement_text)
    
    # Strategy 1: Exact match (first 100 chars)
    req_signature_long = req_normalized[:100]
    
    for page_idx in range(start_idx, end_idx):
        page_text = normalize_text(pages[page_idx])
        
        if req_signature_long in page_text:
            page_num = page_idx + 1
            logger.debug(f"[PAGE_SEARCH] Exact match (100 chars) on page {page_num}: '{requirement_text[:50]}...'")
            return page_num
    
    # Strategy 2: Short match (first 50 chars)
    if len(req_normalized) > 50:
        req_signature_short = req_normalized[:50]
        
        for page_idx in range(start_idx, end_idx):
            page_text = normalize_text(pages[page_idx])
            
            if req_signature_short in page_text:
                page_num = page_idx + 1
                logger.debug(f"[PAGE_SEARCH] Short match (50 chars) on page {page_num}: '{requirement_text[:50]}...'")
                return page_num
    
    # Strategy 3: Keyword matching (tokenized)
    req_tokens = tokenize(req_normalized)
    
    if not req_tokens:
        logger.warning(f"[PAGE_SEARCH] No meaningful tokens in requirement: '{requirement_text[:50]}...'")
        return None
    
    logger.debug(f"[PAGE_SEARCH] Keyword search with {len(req_tokens)} tokens: {list(req_tokens)[:5]}")
    
    # Find page with best keyword match
    best_page = None
    best_score = 0.0
    
    for page_idx in range(start_idx, end_idx):
        page_text = normalize_text(pages[page_idx])
        page_tokens = tokenize(page_text)
        
        score = calculate_keyword_match_score(req_tokens, page_tokens)
        
        if score >= min_keyword_score and score > best_score:
            best_score = score
            best_page = page_idx + 1
    
    if best_page:
        logger.debug(f"[PAGE_SEARCH] Keyword match on page {best_page} (score: {best_score:.1f}%): '{requirement_text[:50]}...'")
        return best_page
    
    # Not found
    logger.warning(f"[PAGE_SEARCH] Could not find page for requirement (tried {end_idx - start_idx} pages): '{requirement_text[:50]}...'")
    return None


def assign_page_numbers_to_requirements(
    requirements: List,
    pages: List[str],
    page_start: int,
    page_end: Optional[int] = None,
    fallback_page: int = None,
    min_keyword_score: float = 50.0
) -> None:
    """Assign accurate page numbers to requirements using smart text search.
    
    Uses multiple strategies:
    1. Exact match (first 100 chars) - 100% confidence
    2. Short match (first 50 chars) - 90% confidence
    3. Keyword matching (filtered tokens) - 50%+ confidence
    
    Modifies requirements in-place, setting source_page to the page where
    the requirement text was found.
    
    Args:
        requirements: List of Requirement objects to update
        pages: List of all page texts (0-indexed)
        page_start: Starting page of the section (1-indexed)
        page_end: Ending page of the section (1-indexed, exclusive)
        fallback_page: Page number to use if search fails (default: page_start)
        min_keyword_score: Minimum keyword match score (0-100) for Strategy 3
    
    Example:
        >>> requirements = [req1, req2, req3]
        >>> assign_page_numbers_to_requirements(requirements, pages, 10, 33)
        >>> # requirements[0].source_page might be 12 (exact match)
        >>> # requirements[1].source_page might be 15 (keyword match 78%)
        >>> # requirements[2].source_page might be 10 (fallback)
    """
    if fallback_page is None:
        fallback_page = page_start
    
    found_exact = 0
    found_short = 0
    found_keyword = 0
    fallback_count = 0
    
    for req in requirements:
        # Try to find page by text search
        found_page = find_page_by_text_search(
            requirement_text=req.text,
            pages=pages,
            page_start=page_start,
            page_end=page_end,
            min_keyword_score=min_keyword_score
        )
        
        if found_page:
            req.source_page = found_page
            
            # Classify which strategy found it (for stats)
            req_normalized = normalize_text(req.text)
            page_text = normalize_text(pages[found_page - 1])
            
            if req_normalized[:100] in page_text:
                found_exact += 1
            elif len(req_normalized) > 50 and req_normalized[:50] in page_text:
                found_short += 1
            else:
                found_keyword += 1
        else:
            # Fallback to start of section
            req.source_page = fallback_page
            fallback_count += 1
    
    total = len(requirements)
    found_count = found_exact + found_short + found_keyword
    accuracy = (found_count / total * 100) if total > 0 else 0
    
    logger.info(
        f"[PAGE_ASSIGN] Assigned pages to {total} requirements: "
        f"{found_count} found ({accuracy:.1f}%) = "
        f"{found_exact} exact + {found_short} short + {found_keyword} keyword, "
        f"{fallback_count} fallback"
    )
