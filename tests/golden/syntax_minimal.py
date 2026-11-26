from typing import TypedDict

class Empty(TypedDict):
    pass
_OnlyOptionalOptional = TypedDict('_OnlyOptionalOptional', {'a': str}, total=False)

class OnlyOptional(_OnlyOptionalOptional):
    pass
_OnlyRequiredRequired = TypedDict('_OnlyRequiredRequired', {'b': int})

class OnlyRequired(_OnlyRequiredRequired):
    pass

class Documented(TypedDict):
    """Has a docstring and no fields."""
Single = str
