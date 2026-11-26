"""Message types for a run."""
from typing import Any, Dict, List, Literal, TypedDict, Union
Phase = Literal['start', 'end']
'Where a run is.'
_WindowRequired = TypedDict('_WindowRequired', {'from': int})
_WindowOptional = TypedDict('_WindowOptional', {'to': int}, total=False)

class Window(_WindowRequired, _WindowOptional):
    """A range of line numbers.

    from: The first line, inclusive.
    to: The last line, exclusive.
    """
_RedactionRequired = TypedDict('_RedactionRequired', {'in': str, 'class': Union[str, None]})

class Redaction(_RedactionRequired):
    pass
_RunEndRequired = TypedDict('_RunEndRequired', {'event': Literal['end'], '_schema': str, 'phase': Phase, 'counts': Dict[str, int], 'ok': bool})
_RunEndOptional = TypedDict('_RunEndOptional', {'window': Window, 'redactions': List[Redaction], 'ratio': float, 'detail': Any, 'next': 'Step'}, total=False)

class RunEnd(_RunEndRequired, _RunEndOptional):
    """The last line of a run.

    It closes the run.

    event: Always ``end``.
    next: A later step.
        Defined below.
    """
_StepRequired = TypedDict('_StepRequired', {'name': str, 'children': List['Step']})
_StepOptional = TypedDict('_StepOptional', {'flag': Literal[1, True]}, total=False)

class Step(_StepRequired, _StepOptional):
    pass
Message = Union[RunEnd, Step]
