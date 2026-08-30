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


def validate_flag(flag: MypyConverter) -> str:  # noqa: C901, PLR0912, PLR0915
    cmd_str = "mypy"

    if flag.no_namespace_packages:
        cmd_str += " --no-namespace-packages"
    if flag.ignore_missing_imports:
        cmd_str += " --ignore-missing-imports"
    if flag.follow_imports:
        cmd_str += f" --follow-imports {flag.follow_imports}"
    if flag.no_site_packages:
        cmd_str += " --no-site-packages"
    if flag.no_silence_site_packages:
        cmd_str += " --no-silence-site-packages"

    if flag.disallow_any_unimported:
        cmd_str += " --disallow-any-unimported"
    if flag.disallow_any_expr:
        cmd_str += " --disallow-any-expr"
    if flag.disallow_any_decorated:
        cmd_str += " --disallow-any-decorated"
    if flag.disallow_any_explicit:
        cmd_str += " --disallow-any-explicit"

    if flag.disallow_any_generics:
        cmd_str += " --disallow-any-generics"
    if flag.allow_any_generics:
        cmd_str += " --allow-any-generics"

    if flag.disallow_subclassing_any:
        cmd_str += " --disallow-subclassing-any"
    if flag.allow_subclassing_any:
        cmd_str += " --allow-subclassing-any"

    if flag.disallow_untyped_calls:
        cmd_str += " --disallow-untyped-calls"
    if flag.allow_untyped_calls:
        cmd_str += " --allow-untyped-calls"

    if flag.disallow_untyped_defs:
        cmd_str += " --disallow-untyped-defs"
    if flag.allow_untyped_defs:
        cmd_str += " --allow-untyped-defs"

    if flag.disallow_incomplete_defs:
        cmd_str += " --disallow-incomplete-defs"
    if flag.allow_incomplete_defs:
        cmd_str += " --allow-incomplete-defs"

    if flag.check_untyped_defs:
        cmd_str += " --check-untyped-defs"
    if flag.no_check_untyped_defs:
        cmd_str += " --no-check-untyped-defs"

    if flag.disallow_untyped_decorators:
        cmd_str += " --disallow-untyped-decorators"
    if flag.allow_untyped_decorators:
        cmd_str += " --allow-untyped-decorators"

    if flag.implicit_optional:
        cmd_str += " --implicit-optional"
    if flag.no_implicit_optional:
        cmd_str += " --no-implicit-optional"

    if flag.no_strict_optional:
        cmd_str += " --no-strict-optional"
    if flag.strict_optional:
        cmd_str += " --strict-optional"

    if flag.warn_redunant_casts:
        cmd_str += " --warn-redunant-casts"
    if flag.no_warn_redunant_casts:
        cmd_str += " --no-warn-redunant-casts"

    if flag.warn_unused_ignores:
        cmd_str += " --warn-unused-ignores"
    if flag.no_warn_unused_ignores:
        cmd_str += " --no-warn-unused-ignores"

    if flag.no_warn_no_return:
        cmd_str += " --no-warn-no-return"
    if flag.warn_no_return:
        cmd_str += " --warn-no-return"

    if flag.warn_return_any:
        cmd_str += " --warn-return-any"
    if flag.no_warn_return_any:
        cmd_str += " --no-warn-return-any"

    if flag.warn_unreachable:
        cmd_str += " --warn-unreachable"
    if flag.no_warn_unreachable:
        cmd_str += " --no-warn-unreachable"

    if flag.allow_untyped_globals:
        cmd_str += " --allow-untyped-globals"
    if flag.disallow_untyped_globals:
        cmd_str += " --disallow-untyped-globals"

    if flag.allow_redifinition:
        cmd_str += " --allow-redifinition"
    if flag.disallow_redifinition:
        cmd_str += " --disallow-redifinition"

    if flag.no_implicit_reexport:
        cmd_str += " --no-implicit-reexport"
    if flag.implicit_reexport:
        cmd_str += " --implicit-reexport"

    if flag.strict_equality:
        cmd_str += " --strict-equality"

    if flag.no_strict_equality:
        cmd_str += " --no-strict-equality"

    if flag.strict_concatenate:
        cmd_str += " --strict-concatenate"

    if flag.no_strict_concatenate:
        cmd_str += " --no-strict-concatenate"

    if flag.strict:
        cmd_str += " --strict"

    if flag.show_error_context:
        cmd_str += " --show-error-context"
    if flag.hide_error_context:
        cmd_str += " --hide-error-context"

    if flag.show_column_numbers:
        cmd_str += " --show-column-numbers"
    if flag.hide_column_numbers:
        cmd_str += " --hide-column-numbers"

    if flag.show_error_end:
        cmd_str += " --show-error-end"
    if flag.hide_error_end:
        cmd_str += " --hide-error-end"

    if flag.hide_error_codes:
        cmd_str += " --hide-error-codes"
    if flag.show_error_codes:
        cmd_str += " --show-error-codes"

    if flag.pretty:
        cmd_str += " --pretty"

    return f"{cmd_str} "
