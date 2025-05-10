from dataclasses import dataclass

@dataclass(frozen=True)
class ModPayload:
    file_path: str          # path relative to project root
    original: str           # full original source text
    modified: str           # full modified source text