"""Title normalisation. Two views of every title:

full  : all content words.
core  : the case-study clause removed ("... a case study of First Bank Plc"), so the same topic
        resold with a different bank, state or school still matches. Recycling a topic onto a
        new case study is exactly the behaviour the study is trying to count.
"""

import re
import unicodedata

STOPWORDS = frozenset(
    """a an and are as at be by for from in into is it its of on or the this that to with
    within among amongst using use based towards toward via upon their there these those
    selected some study""".split()
)

CASE_STUDY = re.compile(
    r"\b(a\s+)?(case\s+stud(y|ies)|a\s+study\s+of|with\s+reference\s+to|"
    r"with\s+special\s+reference\s+to|using\s+.*?\s+as\s+(a\s+)?case)\b.*$"
)


def _clean(title: str) -> str:
    title = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    title = title.lower().replace("&", " and ")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", title)).strip()


def _stem(word: str) -> str:
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 4 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def tokens(title: str, view: str = "full") -> frozenset:
    text = _clean(title)
    if view == "core":
        stripped = CASE_STUDY.sub("", text).strip()
        # Keep the full title when stripping would leave almost nothing.
        text = stripped if len(stripped.split()) >= 3 else text
    return frozenset(_stem(w) for w in text.split() if w not in STOPWORDS and not w.isdigit())
