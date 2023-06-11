from __future__ import annotations

from typing import Literal, Optional

from discord.ext import commands
from utilities.converters import convert_bool


class MypyConverter(
    commands.FlagConverter, case_insensitive=True, delimiter=" ", prefix="--"
):
    code: str
    # Import Discovery
    no_namespace_packages: Optional[convert_bool] = None
    ignore_missing_imports: Optional[convert_bool] = None
    follow_imports: Literal["skip", "silent", "error", "normal"] = "normal"
    no_site_packages: Optional[convert_bool] = None
    no_silence_site_packages: Optional[convert_bool] = None

    # Disallow dynamic typing
    disallow_any_unimported: Optional[convert_bool] = None
    disallow_any_expr: Optional[convert_bool] = None
    disallow_any_decorated: Optional[convert_bool] = None
    disallow_any_explicit: Optional[convert_bool] = None

    disallow_any_generics: Optional[convert_bool] = None
    allow_any_generics: Optional[convert_bool] = None

    disallow_subclassing_any: Optional[convert_bool] = None
    allow_subclassing_any: Optional[convert_bool] = None

    # Untyped definitions and calls
    disallow_untyped_calls: Optional[convert_bool] = None
    allow_untyped_calls: Optional[convert_bool] = None

    disallow_untyped_defs: Optional[convert_bool] = None
    allow_untyped_defs: Optional[convert_bool] = None

    disallow_incomplete_defs: Optional[convert_bool] = None
    allow_incomplete_defs: Optional[convert_bool] = None

    check_untyped_defs: Optional[convert_bool] = None
    no_check_untyped_defs: Optional[convert_bool] = None

    disallow_untyped_decorators: Optional[convert_bool] = None
    allow_untyped_decorators: Optional[convert_bool] = None

    # None and Optional handling
    implicit_optional: Optional[convert_bool] = None
    no_implicit_optional: Optional[convert_bool] = None

    no_strict_optional: Optional[convert_bool] = None
    strict_optional: Optional[convert_bool] = None

    # Configuring warnings
    warn_redunant_casts: Optional[convert_bool] = None
    no_warn_redunant_casts: Optional[convert_bool] = None

    warn_unused_ignores: Optional[convert_bool] = None
    no_warn_unused_ignores: Optional[convert_bool] = None

    no_warn_no_return: Optional[convert_bool] = None
    warn_no_return: Optional[convert_bool] = None

    warn_return_any: Optional[convert_bool] = None
    no_warn_return_any: Optional[convert_bool] = None

    warn_unreachable: Optional[convert_bool] = None
    no_warn_unreachable: Optional[convert_bool] = None

    # Miscellaneous strictness flags
    allow_untyped_globals: Optional[convert_bool] = None
    disallow_untyped_globals: Optional[convert_bool] = None

    allow_redifinition: Optional[convert_bool] = None
    disallow_redifinition: Optional[convert_bool] = None

    no_implicit_reexport: Optional[convert_bool] = None
    implicit_reexport: Optional[convert_bool] = None

    strict_equality: Optional[convert_bool] = None
    no_strict_equality: Optional[convert_bool] = None

    strict_concatenate: Optional[convert_bool] = None
    no_strict_concatenate: Optional[convert_bool] = None

    strict: Optional[convert_bool] = None

    # Configuring error messages
    show_error_context: Optional[convert_bool] = None
    hide_error_context: Optional[convert_bool] = None

    show_column_numbers: Optional[convert_bool] = None
    hide_column_numbers: Optional[convert_bool] = None

    show_error_end: Optional[convert_bool] = None
    hide_error_end: Optional[convert_bool] = None

    hide_error_codes: Optional[convert_bool] = None
    show_error_codes: Optional[convert_bool] = None

    pretty: Optional[convert_bool] = None


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
