from __future__ import annotations

# Basic Arithmetic in Jinja2

addition = """The result of 1 + 1 is 2. In Jinja2, this is written as: ```jinja
{{ 1 + 1 }}
```
In Jinja2 documentation, the addition operation is showcased. Addition is a fundamental arithmetic operation that combines two values to calculate their total. In this example, we're working with the numbers 1 and 1.

When you add 1 + 1, the result is 2. This result signifies the sum of the two numbers. In Jinja2, you express this addition using double curly braces {{ }} as follows: {{ 1 + 1 }}. The expression is evaluated, and the result, which is 2, is inserted into the output.

Jinja2's ability to process expressions like {{ 1 + 1 }} is essential for dynamic content in templates. It calculates values based on data and enhances the flexibility of templates in web applications.
"""

subtraction = """The result of 1 - 1 is 0. In Jinja2, this is written as: ```jinja
{{ 1 - 1 }}
```
In the context of Jinja2 documentation, the subtraction operation is demonstrated. Subtraction is a fundamental arithmetic operation that finds the difference between two values. Let's dive into the provided example involving the numbers 1 and 1.

When you subtract 1 - 1, the result is 0. This outcome represents the disparity between the two numbers. In Jinja2, expressing this subtraction employs double curly braces {{ }} as shown: {{ 1 - 1 }}. The enclosed expression is computed, yielding 0, which is then integrated into the output.

The ability of Jinja2 to process expressions such as {{ 1 - 1 }} holds significance for creating dynamic templates in web applications. By performing calculations based on data, it elevates template adaptability.
"""

multiplication = """The result of 2 * 2 is 4. In Jinja2, this is written as: ```jinja
{{ 2 * 2 }}
```
Within the framework of Jinja2 documentation, the concept of multiplication is illustrated. Multiplication, a fundamental arithmetic operation, involves combining values to determine their product. Let's explore the provided instance involving the numbers 2 and 2.

When you multiply 2 * 2, the outcome is 4. This result signifies the product of the two numbers. In Jinja2, articulating this multiplication utilizes double curly braces {{ }} in this format: {{ 2 * 2 }}. The encompassed expression is evaluated, resulting in 4, which is then incorporated into the output.

Jinja2's capability to interpret expressions like {{ 2 * 2 }} is pivotal for crafting dynamic templates in web applications. By conducting computations based on data, it amplifies the flexibility of templates.
"""

division = """The result of 1 / 1 is 1. In Jinja2, this is written as: ```jinja
{{ 1 / 1 }}
```
In the context of Jinja2 documentation, the division operation is presented. Division, a fundamental arithmetic operation, entails distributing one value by another to determine the quotient. Let's explore the provided illustration involving the numbers 1 and 1.

When you divide 1 by 1, the outcome is 1. This result signifies the quotient of the division. In Jinja2, expressing this division involves utilizing double curly braces {{ }} as demonstrated: {{ 1 / 1 }}. The enclosed expression is computed, yielding 1, which is then integrated into the output.

Jinja2's capacity to process expressions like {{ 1 / 1 }} is pivotal for generating dynamic templates in web applications. By executing calculations based on data, it heightens the adaptability of templates.
"""

statements = """Jinja2 documentation introduces the concept of statements, fundamental instructions enclosed between `{%` and `%}`. These statements drive dynamic behavior in templates. For instance, consider the Jinja2 statement: ```jinja
{% set x = 1 %}
```
Here we are setting the variable `x` to the value `1`. We can then use this variable in our template:
```jinja
{{ x }}
```
Here, within double curly braces {{ }}, the variable x is invoked. This incorporation leverages Jinja2's ability to process expressions. Consequently, the value of x, which is 1, is displayed in the output.

Embracing statements using {% %} fosters dynamic template development in Jinja2. By employing constructs like set, variables can be managed and manipulated to enhance template interactivity.
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
```
"""

if_else = """Jinja2 documentation introduces the versatility of if/else statements, allowing conditional execution within templates. Consider the Jinja2 example: ```jinja
{% if 1 == 1 %}
    1 is equal to 1
{% else %}
    1 is not equal to 1
{% endif %}
```
In this structure, the condition 1 == 1 is assessed. Since it's true, the first block executes, outputting "1 is equal to 1." Alternatively, if the condition were false, the second block within the {% else %} section would run.

While indentation is optional, it's recommended for improved readability. Thus, the same logic can be expressed compactly: ```jinja
{% if 1 == 1 %}1 is equal to 1{% else %}1 is not equal to 1{% endif %}
```"""

for_loop = """Jinja2 documentation highlights the utility of for loops, enabling iterative operations within templates. Consider the Jinja2 illustration: ```jinja
{% for i in [1, 2, 3] %}
    {{ i }}
{% endfor %}
In this construct, the loop iterates over the elements [1, 2, 3]. During each iteration, the variable i takes on the value of the current element, and {{ i }} is used to output it.

The loop's flexibility fosters dynamic content generation. Elements can be derived from a variety of sources, making it a powerful tool for template rendering.
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
