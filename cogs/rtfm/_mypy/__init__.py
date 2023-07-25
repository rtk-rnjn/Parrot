from __future__ import annotations

from typing import Literal

from discord.ext import commands
from utilities.converters import convert_bool


class MypyConverter(commands.FlagConverter, case_insensitive=True, delimiter=" ", prefix="--"):
    code: str
    # Import Discovery
    no_namespace_packages: convert_bool | None = None
    ignore_missing_imports: convert_bool | None = None
    follow_imports: Literal["skip", "silent", "error", "normal"] = "normal"
    no_site_packages: convert_bool | None = None
    no_silence_site_packages: convert_bool | None = None

    # Disallow dynamic typing
    disallow_any_unimported: convert_bool | None = None
    disallow_any_expr: convert_bool | None = None
    disallow_any_decorated: convert_bool | None = None
    disallow_any_explicit: convert_bool | None = None

    disallow_any_generics: convert_bool | None = None
    allow_any_generics: convert_bool | None = None

    disallow_subclassing_any: convert_bool | None = None
    allow_subclassing_any: convert_bool | None = None

    # Untyped definitions and calls
    disallow_untyped_calls: convert_bool | None = None
    allow_untyped_calls: convert_bool | None = None

    disallow_untyped_defs: convert_bool | None = None
    allow_untyped_defs: convert_bool | None = None

    disallow_incomplete_defs: convert_bool | None = None
    allow_incomplete_defs: convert_bool | None = None

    check_untyped_defs: convert_bool | None = None
    no_check_untyped_defs: convert_bool | None = None

    disallow_untyped_decorators: convert_bool | None = None
    allow_untyped_decorators: convert_bool | None = None

    # None and Optional handling
    implicit_optional: convert_bool | None = None
    no_implicit_optional: convert_bool | None = None

    no_strict_optional: convert_bool | None = None
    strict_optional: convert_bool | None = None

    # Configuring warnings
    warn_redunant_casts: convert_bool | None = None
    no_warn_redunant_casts: convert_bool | None = None

    warn_unused_ignores: convert_bool | None = None
    no_warn_unused_ignores: convert_bool | None = None

    no_warn_no_return: convert_bool | None = None
    warn_no_return: convert_bool | None = None

    warn_return_any: convert_bool | None = None
    no_warn_return_any: convert_bool | None = None

    warn_unreachable: convert_bool | None = None
    no_warn_unreachable: convert_bool | None = None

    # Miscellaneous strictness flags
    allow_untyped_globals: convert_bool | None = None
    disallow_untyped_globals: convert_bool | None = None

    allow_redifinition: convert_bool | None = None
    disallow_redifinition: convert_bool | None = None

    no_implicit_reexport: convert_bool | None = None
    implicit_reexport: convert_bool | None = None

    strict_equality: convert_bool | None = None
    no_strict_equality: convert_bool | None = None

    strict_concatenate: convert_bool | None = None
    no_strict_concatenate: convert_bool | None = None

    strict: convert_bool | None = None

    # Configuring error messages
    show_error_context: convert_bool | None = None
    hide_error_context: convert_bool | None = None

    show_column_numbers: convert_bool | None = None
    hide_column_numbers: convert_bool | None = None

    show_error_end: convert_bool | None = None
    hide_error_end: convert_bool | None = None

    hide_error_codes: convert_bool | None = None
    show_error_codes: convert_bool | None = None

    pretty: convert_bool | None = None


def validate_flag(flag: MypyConverter) -> str:
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
