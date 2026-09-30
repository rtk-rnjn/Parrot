from __future__ import annotations

from typing import Literal

from discord.ext import commands


class MypyConverter(commands.FlagConverter, case_insensitive=True, delimiter=" ", prefix="--"):
    code: str = commands.flag(description="The code to lint with mypy.")
    # Import Discovery
    no_namespace_packages: bool = commands.flag(description="Do not consider namespace packages when searching for imports.", default=False)
    ignore_missing_imports: bool = commands.flag(description="Ignore missing imports.", default=False)
    follow_imports: Literal["skip", "silent", "error", "normal"] = commands.flag(description="How to handle imports.", default="normal")
    no_site_packages: bool = commands.flag(description="Do not include site packages.", default=False)
    no_silence_site_packages: bool = commands.flag(description="Do not silence site packages.", default=False)

    # Disallow dynamic typing
    disallow_any_unimported: bool = commands.flag(description="Disallow unimported modules.", default=False)
    disallow_any_expr: bool = commands.flag(description="Disallow any expression.", default=False)
    disallow_any_decorated: bool = commands.flag(description="Disallow any decorated function.", default=False)
    disallow_any_explicit: bool = commands.flag(description="Disallow any explicit type.", default=False)

    disallow_any_generics: bool = commands.flag(description="Disallow any generics.", default=False)
    allow_any_generics: bool = commands.flag(description="Allow any generics.", default=False)

    disallow_subclassing_any: bool = commands.flag(description="Disallow subclassing of Any.", default=False)
    allow_subclassing_any: bool = commands.flag(description="Allow subclassing of Any.", default=False)

    # Untyped definitions and calls
    disallow_untyped_calls: bool = commands.flag(description="Disallow untyped calls.", default=False)
    allow_untyped_calls: bool = commands.flag(description="Allow untyped calls.", default=False)

    disallow_untyped_defs: bool = commands.flag(description="Disallow untyped definitions.", default=False)
    allow_untyped_defs: bool = commands.flag(description="Allow untyped definitions.", default=False)

    disallow_incomplete_defs: bool = commands.flag(description="Disallow incomplete definitions.", default=False)
    allow_incomplete_defs: bool = commands.flag(description="Allow incomplete definitions.", default=False)

    check_untyped_defs: bool = commands.flag(description="Check untyped definitions.", default=False)
    no_check_untyped_defs: bool = commands.flag(description="Do not check untyped definitions.", default=False)

    disallow_untyped_decorators: bool = commands.flag(description="Disallow untyped decorators.", default=False)
    allow_untyped_decorators: bool = commands.flag(description="Allow untyped decorators.", default=False)

    # None and Optional handling
    implicit_optional: bool = commands.flag(description="Enable implicit Optional.", default=False)
    no_implicit_optional: bool = commands.flag(description="Disable implicit Optional.", default=False)

    no_strict_optional: bool = commands.flag(description="Disable strict Optional.", default=False)
    strict_optional: bool = commands.flag(description="Enable strict Optional.", default=False)

    # Configuring warnings
    warn_redunant_casts: bool = commands.flag(description="Warn about redundant casts.", default=False)
    no_warn_redunant_casts: bool = commands.flag(description="Do not warn about redundant casts.", default=False)

    warn_unused_ignores: bool = commands.flag(description="Warn about unused ignores.", default=False)
    no_warn_unused_ignores: bool = commands.flag(description="Do not warn about unused ignores.", default=False)

    no_warn_no_return: bool = commands.flag(description="Do not warn about missing return statements.", default=False)
    warn_no_return: bool = commands.flag(description="Warn about missing return statements.", default=False)

    warn_return_any: bool = commands.flag(description="Warn about returning Any.", default=False)
    no_warn_return_any: bool = commands.flag(description="Do not warn about returning Any.", default=False)

    warn_unreachable: bool = commands.flag(description="Warn about unreachable code.", default=False)
    no_warn_unreachable: bool = commands.flag(description="Do not warn about unreachable code.", default=False)

    # Miscellaneous strictness flags
    allow_untyped_globals: bool = commands.flag(description="Allow untyped globals.", default=False)
    disallow_untyped_globals: bool = commands.flag(description="Disallow untyped globals.", default=False)

    allow_redifinition: bool = commands.flag(description="Allow redefinition.", default=False)
    disallow_redifinition: bool = commands.flag(description="Disallow redefinition.", default=False)

    no_implicit_reexport: bool = commands.flag(description="Disable implicit reexport.", default=False)
    implicit_reexport: bool = commands.flag(description="Enable implicit reexport.", default=False)

    strict_equality: bool = commands.flag(description="Enable strict equality.", default=False)
    no_strict_equality: bool = commands.flag(description="Disable strict equality.", default=False)

    strict_concatenate: bool = commands.flag(description="Enable strict concatenation.", default=False)
    no_strict_concatenate: bool = commands.flag(description="Disable strict concatenation.", default=False)

    strict: bool = commands.flag(description="Enable strict mode.", default=False)

    # Configuring error messages
    show_error_context: bool = commands.flag(description="Show error context.", default=False)
    hide_error_context: bool = commands.flag(description="Hide error context.", default=False)

    show_column_numbers: bool = commands.flag(description="Show column numbers.", default=False)
    hide_column_numbers: bool = commands.flag(description="Hide column numbers.", default=False)

    show_error_end: bool = commands.flag(description="Show error end.", default=False)
    hide_error_end: bool = commands.flag(description="Hide error end.", default=False)

    hide_error_codes: bool = commands.flag(description="Hide error codes.", default=False)
    show_error_codes: bool = commands.flag(description="Show error codes.", default=False)

    pretty: bool = commands.flag(description="Enable pretty output.", default=False)


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
