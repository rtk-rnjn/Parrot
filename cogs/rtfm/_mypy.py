from __future__ import annotations

from typing import Annotated, Literal

from discord.ext import commands


def convert_bool(text: str) -> bool:
    """True/False converter."""
    lowered = str(text).lower()
    true = lowered in {"yes", "y", "true", "t", "1", "enable", "on", "o", "ok", "sure", "yeah", "yup", "right"}
    false = lowered in {"no", "n", "false", "f", "0", "disable", "off", "none", "nah", "nope", "wrong"}
    if true:
        return True
    if false:
        return False

    raise commands.BadBoolArgument(lowered)


class MypyConverter(commands.FlagConverter, case_insensitive=True, delimiter=" ", prefix="--"):
    code: str = commands.flag(description="The code to lint with mypy.")
    # Import Discovery
    no_namespace_packages: Annotated[bool | None, convert_bool] = commands.flag(
        description="Do not consider namespace packages when searching for imports.",
        default=None,
    )
    ignore_missing_imports: Annotated[bool | None, convert_bool] = commands.flag(description="Ignore missing imports.", default=None)
    follow_imports: Literal["skip", "silent", "error", "normal"] = commands.flag(description="How to handle imports.", default="normal")
    no_site_packages: Annotated[bool | None, convert_bool] = commands.flag(description="Do not include site packages.", default=None)
    no_silence_site_packages: Annotated[bool | None, convert_bool] = commands.flag(description="Do not silence site packages.", default=None)

    # Disallow dynamic typing
    disallow_any_unimported: Annotated[bool | None, convert_bool] = commands.flag(description="Disallow unimported modules.", default=None)
    disallow_any_expr: Annotated[bool | None, convert_bool] = commands.flag(description="Disallow any expression.", default=None)
    disallow_any_decorated: Annotated[bool | None, convert_bool] = commands.flag(description="Disallow any decorated function.", default=None)
    disallow_any_explicit: Annotated[bool | None, convert_bool] = commands.flag(description="Disallow any explicit type.", default=None)

    disallow_any_generics: Annotated[bool | None, convert_bool] = commands.flag(description="Disallow any generics.", default=None)
    allow_any_generics: Annotated[bool | None, convert_bool] = commands.flag(description="Allow any generics.", default=None)

    disallow_subclassing_any: Annotated[bool | None, convert_bool] = commands.flag(description="Disallow subclassing of Any.", default=None)
    allow_subclassing_any: Annotated[bool | None, convert_bool] = commands.flag(description="Allow subclassing of Any.", default=None)

    # Untyped definitions and calls
    disallow_untyped_calls: Annotated[bool | None, convert_bool] = commands.flag(description="Disallow untyped calls.", default=None)
    allow_untyped_calls: Annotated[bool | None, convert_bool] = commands.flag(description="Allow untyped calls.", default=None)

    disallow_untyped_defs: Annotated[bool | None, convert_bool] = commands.flag(description="Disallow untyped definitions.", default=None)
    allow_untyped_defs: Annotated[bool | None, convert_bool] = commands.flag(description="Allow untyped definitions.", default=None)

    disallow_incomplete_defs: Annotated[bool | None, convert_bool] = commands.flag(description="Disallow incomplete definitions.", default=None)
    allow_incomplete_defs: Annotated[bool | None, convert_bool] = commands.flag(description="Allow incomplete definitions.", default=None)

    check_untyped_defs: Annotated[bool | None, convert_bool] = commands.flag(description="Check untyped definitions.", default=None)
    no_check_untyped_defs: Annotated[bool | None, convert_bool] = commands.flag(description="Do not check untyped definitions.", default=None)

    disallow_untyped_decorators: Annotated[bool | None, convert_bool] = commands.flag(description="Disallow untyped decorators.", default=None)
    allow_untyped_decorators: Annotated[bool | None, convert_bool] = commands.flag(description="Allow untyped decorators.", default=None)

    # None and Optional handling
    implicit_optional: Annotated[bool | None, convert_bool] = commands.flag(description="Enable implicit Optional.", default=None)
    no_implicit_optional: Annotated[bool | None, convert_bool] = commands.flag(description="Disable implicit Optional.", default=None)

    no_strict_optional: Annotated[bool | None, convert_bool] = commands.flag(description="Disable strict Optional.", default=None)
    strict_optional: Annotated[bool | None, convert_bool] = commands.flag(description="Enable strict Optional.", default=None)

    # Configuring warnings
    warn_redunant_casts: Annotated[bool | None, convert_bool] = commands.flag(description="Warn about redundant casts.", default=None)
    no_warn_redunant_casts: Annotated[bool | None, convert_bool] = commands.flag(description="Do not warn about redundant casts.", default=None)

    warn_unused_ignores: Annotated[bool | None, convert_bool] = commands.flag(description="Warn about unused ignores.", default=None)
    no_warn_unused_ignores: Annotated[bool | None, convert_bool] = commands.flag(description="Do not warn about unused ignores.", default=None)

    no_warn_no_return: Annotated[bool | None, convert_bool] = commands.flag(description="Do not warn about missing return statements.", default=None)
    warn_no_return: Annotated[bool | None, convert_bool] = commands.flag(description="Warn about missing return statements.", default=None)

    warn_return_any: Annotated[bool | None, convert_bool] = commands.flag(description="Warn about returning Any.", default=None)
    no_warn_return_any: Annotated[bool | None, convert_bool] = commands.flag(description="Do not warn about returning Any.", default=None)

    warn_unreachable: Annotated[bool | None, convert_bool] = commands.flag(description="Warn about unreachable code.", default=None)
    no_warn_unreachable: Annotated[bool | None, convert_bool] = commands.flag(description="Do not warn about unreachable code.", default=None)

    # Miscellaneous strictness flags
    allow_untyped_globals: Annotated[bool | None, convert_bool] = commands.flag(description="Allow untyped globals.", default=None)
    disallow_untyped_globals: Annotated[bool | None, convert_bool] = commands.flag(description="Disallow untyped globals.", default=None)

    allow_redifinition: Annotated[bool | None, convert_bool] = commands.flag(description="Allow redefinition.", default=None)
    disallow_redifinition: Annotated[bool | None, convert_bool] = commands.flag(description="Disallow redefinition.", default=None)

    no_implicit_reexport: Annotated[bool | None, convert_bool] = commands.flag(description="Disable implicit reexport.", default=None)
    implicit_reexport: Annotated[bool | None, convert_bool] = commands.flag(description="Enable implicit reexport.", default=None)

    strict_equality: Annotated[bool | None, convert_bool] = commands.flag(description="Enable strict equality.", default=None)
    no_strict_equality: Annotated[bool | None, convert_bool] = commands.flag(description="Disable strict equality.", default=None)

    strict_concatenate: Annotated[bool | None, convert_bool] = commands.flag(description="Enable strict concatenation.", default=None)
    no_strict_concatenate: Annotated[bool | None, convert_bool] = commands.flag(description="Disable strict concatenation.", default=None)

    strict: Annotated[bool | None, convert_bool] = commands.flag(description="Enable strict mode.", default=None)

    # Configuring error messages
    show_error_context: Annotated[bool | None, convert_bool] = commands.flag(description="Show error context.", default=None)
    hide_error_context: Annotated[bool | None, convert_bool] = commands.flag(description="Hide error context.", default=None)

    show_column_numbers: Annotated[bool | None, convert_bool] = commands.flag(description="Show column numbers.", default=None)
    hide_column_numbers: Annotated[bool | None, convert_bool] = commands.flag(description="Hide column numbers.", default=None)

    show_error_end: Annotated[bool | None, convert_bool] = commands.flag(description="Show error end.", default=None)
    hide_error_end: Annotated[bool | None, convert_bool] = commands.flag(description="Hide error end.", default=None)

    hide_error_codes: Annotated[bool | None, convert_bool] = commands.flag(description="Hide error codes.", default=None)
    show_error_codes: Annotated[bool | None, convert_bool] = commands.flag(description="Show error codes.", default=None)

    pretty: Annotated[bool | None, convert_bool] = commands.flag(description="Enable pretty output.", default=None)


def validate_flag(flag: MypyConverter) -> str:
    options = [
        option
        for enabled, option in (
            (flag.no_namespace_packages, "--no-namespace-packages"),
            (flag.ignore_missing_imports, "--ignore-missing-imports"),
            (flag.follow_imports, f"--follow-imports {flag.follow_imports}"),
            (flag.no_site_packages, "--no-site-packages"),
            (flag.no_silence_site_packages, "--no-silence-site-packages"),
            (flag.disallow_any_unimported, "--disallow-any-unimported"),
            (flag.disallow_any_expr, "--disallow-any-expr"),
            (flag.disallow_any_decorated, "--disallow-any-decorated"),
            (flag.disallow_any_explicit, "--disallow-any-explicit"),
            (flag.disallow_any_generics, "--disallow-any-generics"),
            (flag.allow_any_generics, "--allow-any-generics"),
            (flag.disallow_subclassing_any, "--disallow-subclassing-any"),
            (flag.allow_subclassing_any, "--allow-subclassing-any"),
            (flag.disallow_untyped_calls, "--disallow-untyped-calls"),
            (flag.allow_untyped_calls, "--allow-untyped-calls"),
            (flag.disallow_untyped_defs, "--disallow-untyped-defs"),
            (flag.allow_untyped_defs, "--allow-untyped-defs"),
            (flag.disallow_incomplete_defs, "--disallow-incomplete-defs"),
            (flag.allow_incomplete_defs, "--allow-incomplete-defs"),
            (flag.check_untyped_defs, "--check-untyped-defs"),
            (flag.no_check_untyped_defs, "--no-check-untyped-defs"),
            (flag.disallow_untyped_decorators, "--disallow-untyped-decorators"),
            (flag.allow_untyped_decorators, "--allow-untyped-decorators"),
            (flag.implicit_optional, "--implicit-optional"),
            (flag.no_implicit_optional, "--no-implicit-optional"),
            (flag.no_strict_optional, "--no-strict-optional"),
            (flag.strict_optional, "--strict-optional"),
            (flag.warn_redunant_casts, "--warn-redunant-casts"),
            (flag.no_warn_redunant_casts, "--no-warn-redunant-casts"),
            (flag.warn_unused_ignores, "--warn-unused-ignores"),
            (flag.no_warn_unused_ignores, "--no-warn-unused-ignores"),
            (flag.no_warn_no_return, "--no-warn-no-return"),
            (flag.warn_no_return, "--warn-no-return"),
            (flag.warn_return_any, "--warn-return-any"),
            (flag.no_warn_return_any, "--no-warn-return-any"),
            (flag.warn_unreachable, "--warn-unreachable"),
            (flag.no_warn_unreachable, "--no-warn-unreachable"),
            (flag.allow_untyped_globals, "--allow-untyped-globals"),
            (flag.disallow_untyped_globals, "--disallow-untyped-globals"),
            (flag.allow_redifinition, "--allow-redifinition"),
            (flag.disallow_redifinition, "--disallow-redifinition"),
            (flag.no_implicit_reexport, "--no-implicit-reexport"),
            (flag.implicit_reexport, "--implicit-reexport"),
            (flag.strict_equality, "--strict-equality"),
            (flag.no_strict_equality, "--no-strict-equality"),
            (flag.strict_concatenate, "--strict-concatenate"),
            (flag.no_strict_concatenate, "--no-strict-concatenate"),
            (flag.strict, "--strict"),
            (flag.show_error_context, "--show-error-context"),
            (flag.hide_error_context, "--hide-error-context"),
            (flag.show_column_numbers, "--show-column-numbers"),
            (flag.hide_column_numbers, "--hide-column-numbers"),
            (flag.show_error_end, "--show-error-end"),
            (flag.hide_error_end, "--hide-error-end"),
            (flag.hide_error_codes, "--hide-error-codes"),
            (flag.show_error_codes, "--show-error-codes"),
            (flag.pretty, "--pretty"),
        )
        if enabled
    ]
    return f"mypy {' '.join(options)} "
