import re
import unicodedata

_SYMBOLS = {"+": " plus ", "#": " sharp ", ".": " dot ", "/": " "}


def skill_slug(name: str) -> str:
    """
    Slug that keeps symbol-heavy names distinct: C -> "c", C++ -> "c-plus-plus",
    C# -> "c-sharp", .NET -> "dot-net", Node.js -> "node-dot-js".
    """
    text = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    for symbol, word in _SYMBOLS.items():
        text = text.replace(symbol, word)
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text[:100]
