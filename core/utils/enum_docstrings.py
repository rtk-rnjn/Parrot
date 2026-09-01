# Source - https://stackoverflow.com/a/79229811
# Posted by Martijn Pieters
# Retrieved 2026-09-01, License - CC BY-SA 4.0

import ast
import inspect
from enum import Enum
from functools import partial
from operator import is_


def enum_docstrings[E: Enum](enum: type[E]) -> type[E]:
    '''Attach docstrings to enum members

    Docstrings are string literals that appear directly below the enum member
    assignment expression:

    ```
    @enum_docstrings
    class SomeEnum(Enum):
        """Docstring for the SomeEnum enum"""

        foo_member = "foo_value"
        """Docstring for the foo_member enum member"""

    SomeEnum.foo_member.__doc__  # 'Docstring for the foo_member enum member'
    ```

    '''
    try:
        mod = ast.parse(inspect.getsource(enum))
    except OSError:
        # no source code available
        return enum

    if mod.body and isinstance(class_def := mod.body[0], ast.ClassDef):
        # An enum member docstring is unassigned if it is the exact same object
        # as enum.__doc__.
        unassigned = partial(is_, enum.__doc__)
        names = enum.__members__.keys()
        member: E | None = None
        for node in class_def.body:
            match node:
                case ast.Assign(targets=[ast.Name(id=name)]) if name in names:
                    # Enum member assignment, look for a docstring next
                    member = enum[name]
                    continue

                case ast.Expr(value=ast.Constant(value=str(docstring))) if member and unassigned(member.__doc__):
                    # docstring immediately following a member assignment
                    member.__doc__ = docstring

                case _:
                    pass

            member = None

    return enum
