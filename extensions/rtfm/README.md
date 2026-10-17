# RTFM

Developer documentation and programming-resource search tools.

## Scope

Python tags, PyPI, npm, crates, GitHub, Stack Overflow, Real Python, cheat sheets, code execution, and programming contest data.

`kontests` lists upcoming and ongoing contests from Codeforces, AtCoder, HackerRank, HackerEarth and CS Academy in one
tabbed, paginated message. Each site lives in its own module under `_kontests/`, typed against the payload it serves and
reduced to one `Contest` shape, so a site changing a field drops that contest with a log line instead of the command.

`rtfd` searches Sphinx-based Python docs plus MDN (HTML, CSS, JavaScript, Web APIs, HTTP), cppreference (C, C++),
the Rust std docs, the JDK Javadoc (packages, types and members; `System.out.println` is followed through the field's
type to `PrintStream.println`), PostgreSQL's SQL commands, git manual pages and Hoogle, with page details rendered in chat.

`syntax` answers "how is this written" questions (`syntax rust match`, `syntax python comprehension`) from each
language's own references: Python's language reference, tutorial, glossary and FAQ; the Java Tutorials and the JLS;
cppreference's C and C++ language pages; the Rust Reference, Book and Rust by Example; MDN's JavaScript guides,
statements and operators; the Go specification and Effective Go. Any other language, a topic those do not cover, or
the "Search the web" button falls back to DuckDuckGo, listing documentation hosts first.
