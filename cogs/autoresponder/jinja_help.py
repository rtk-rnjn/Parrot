from __future__ import annotations

# Basic Arithmetic in Jinja2

addition = """The result of 1 + 1 is 2. In Jinja2, this is written as: ```jinja
{{ 1 + 1 }}
```"""

subtraction = """The result of 1 - 1 is 0. In Jinja2, this is written as: ```jinja
{{ 1 - 1 }}
```"""

multiplication = """The result of 2 * 2 is 4. In Jinja2, this is written as: ```jinja
{{ 2 * 2 }}
```"""

division = """The result of 1 / 1 is 1. In Jinja2, this is written as:
```jinja
{{ 1 / 1 }}
```"""

statements = """All Jinja2 statements are written between `{%` and `%}`. For example, the following is a Jinja2 statement: ```jinja
{% set x = 1 %}
```
Here we are setting the variable `x` to the value `1`. We can then use this variable in our template:
```jinja
{{ x }}
```
"""

expression = """Jinja2 expressions are written between `{{` and `}}`. For example, the following is a Jinja2 expression: ```jinja
{{ 1 + 1 }}
```"""

comments = """Jinja2 comments are written between `{#` and `#}`. For example, the following is a Jinja2 comment: ```jinja
{# This is a comment #}
```
Multi-line comments are also supported: ```jinja
{# This is a comment
    {{ 1 + 1 }}
    {{ 2 + 2 }}
#}
"""

if_else = """Jinja2 supports if/else statements. For example, the following is a Jinja2 if/else statement: ```jinja
{% if 1 == 1 %}
    1 is equal to 1
{% else %}
    1 is not equal to 1
{% endif %}
```
Indentation is not required, but it is recommended for readability. The following is also valid: ```jinja
{% if 1 == 1 %}1 is equal to 1{% else %}1 is not equal to 1{% endif %}
```"""

for_loop = """Jinja2 supports for loops. For example, the following is a Jinja2 for loop: ```jinja
{% for i in [1, 2, 3] %}
    {{ i }}
{% endfor %}
```"""

filters = """Jinja2 supports filters. For example, the following is a Jinja2 filter: ```jinja
{{ "Hello World" | upper }}
```
This will output `HELLO WORLD`. Filters can also be chained: ```jinja
{{ "Hello World" | upper | lower }}
```
This will output `hello world`. Filters can also take arguments: ```jinja
{{ "Hello World" | replace("World", "Universe") }}
```
This will output `Hello Universe`. Filters can also be used in if statements: ```jinja
{% if "Hello World" | upper == "HELLO WORLD" %}
    Hello World is equal to HELLO WORLD
{% endif %}
```"""

macros = """Jinja2 supports macros. Macros are similar to functions in other programming languages.
For example, the following is a Jinja2 macro: ```jinja
{% macro add(x, y) %}
    {{ x + y }}
{% endmacro %}
```
Macros can then be called like so: ```jinja
{{ add(1, 1) }}
```
This will output `2`. Macros can also be used in if statements: ```jinja
{% if add(1, 1) == 2 %}
    1 + 1 is equal to 2
{% endif %}
```"""

variables = """Jinja2 supports variables. For example, the following is a Jinja2 variable: ```jinja
{% set x = 1 %}
```
Variables can then be used in expressions: ```jinja
{{ x }}
```
This will output `1`. Variables can also be used in if statements: ```jinja
{% if x == 1 %}
    x is equal to 1
{% endif %}
```"""

call = """Jinja2 supports calling macros. For example, the following is a Jinja2 call: ```jinja
{% macro add(x, y) %}
    {{ x + y }}
    {{ caller() }}
{% endmacro %}

{% call add(1, 1) %}
    Other text
{% endcall %}
```"""

scoping = """Jinja2 supports scoping. For example, the following is a Jinja2 scope: ```jinja
{% set x = 1 %}
{% set y = 2 %}

{% if x == 1 %}
    {% set y = 3 %}
    {{ y }}
{% endif %}

{{ y }}
```
However, scoping sometimes does not work as expected. For example, the following is a Jinja2 scope: ```jinja
{% set x = 1 %}

{% for i in [1, 2, 3] %}
    {% set x = 2 %}
{% endfor %}

{{ x }}
```
Here, `x` is still equal to `1` even though we set it to `2` inside the for loop. This is because Jinja2 does not support block scoping.
You can use `namespace` to get around this: ```jinja
{% set x = namespace(value=1) %}
{% for i in [1, 2, 3] %}
    {% set x.value = 2 %}
{% endfor %}
{{ x.value }}
```"""

boolean = """Jinja2 supports boolean values. For example, the following is a Jinja2 boolean: ```jinja
{% set x = true %}
{% if x == true %}
    x is true
{% endif %}
```
`true` is True, `false` is False, and `null` is None."""


operators = """Jinja2 supports the following operators:
```jinja
{# Logical Operators #}
and - Logical and ( ^ )
or  - Logical or ( v )
not - Logical not ( ! )
``````jinja
{# Comparison Operators #}
==  - Equal to
!=  - Not equal to
>   - Greater than
<   - Less than
>=  - Greater than or equal to
<=  - Less than or equal to
``````jinja
{# Arithmetic Operators #}
+   - Addition
-   - Subtraction
*   - Multiplication
/   - Division
``````jinja
{# Other Operators #}
~   - Concatenation
in  - Membership
is  - Identity
./[] - Dot/bracket notation
()  - Function call
```"""

more = """For more information, see the [Jinja2 documentation](https://jinja.palletsprojects.com/en/3.1.x/templates/)."""

TOPICS = {
    "addition": addition,
    "subtraction": subtraction,
    "multiplication": multiplication,
    "division": division,
    "statements": statements,
    "expression": expression,
    "comments": comments,
    "if_else": if_else,
    "for_loop": for_loop,
    "filters": filters,
    "macros": macros,
    "variables": variables,
    "call": call,
    "scoping": scoping,
    "boolean": boolean,
    "operators": operators,
    "more": more,
}
