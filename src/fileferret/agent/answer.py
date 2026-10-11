"""Answer and citation types returned by the agent."""

from dataclasses import dataclass, field


@dataclass
class Citation:
    path: str
    line_start: int
    line_end: int
    page: int | None = None
    quote: str = ""
    # False when the cited file/lines don't exist, i.e. the model got the location wrong.
    verified: bool = False

    def location(self) -> str:
        page = f"p{self.page}:" if self.page else ""
        lines = f"L{self.line_start}" + (f"-L{self.line_end}" if self.line_end != self.line_start else "")
        return f"{self.path}:{page}{lines}"


@dataclass
class Answer:
    text: str
    citations: list[Citation] = field(default_factory=list)
    steps: int = 0
