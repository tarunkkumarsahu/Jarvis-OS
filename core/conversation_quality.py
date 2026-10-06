"""Detect stale repeated AI answers without flagging short legitimate replies."""
import re
from difflib import SequenceMatcher


def _normalize(text):
    return re.sub(r"\s+", " ", str(text or "").casefold()).strip()


def is_stale_reply(user_text, answer, recent_turns):
    """A substantial near-duplicate to *another* question signals a stale reply.

    Short answers (yes, hello, time, etc.) may legitimately repeat. A response
    to the exact same question may also legitimately be the same.
    """
    current_question = _normalize(user_text)
    current_answer = _normalize(answer)
    if len(current_answer) < 70:
        return False
    for turn in recent_turns:
        if _normalize(turn.get("user_text")) == current_question:
            continue
        prior_answer = _normalize(turn.get("assistant_text"))
        if len(prior_answer) < 70:
            continue
        if current_answer == prior_answer:
            return True
        if SequenceMatcher(None, current_answer, prior_answer, autojunk=False).ratio() >= 0.94:
            return True
    return False
