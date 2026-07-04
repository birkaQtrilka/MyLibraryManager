import re
from pathlib import Path


def _strip_comments_and_strings(content: str) -> str:
    """
    Return a copy of the content with comments and string/char literals
    blanked out (replaced with spaces of the same length), so keyword
    searches don't get fooled by things like:
        // this uses a namespace
        string s = "namespace Foo";
    This is a heuristic, not a full C# tokenizer/parser, but it correctly
    handles the common cases: line comments, block comments, regular
    strings, verbatim strings (@"..."), and interpolated strings ($"...").
    """
    pattern = re.compile(
        r'''
        (?P<line_comment>//[^\n]*)                     # // line comment
        |(?P<block_comment>/\*.*?\*/)                  # /* block comment */
        |(?P<verbatim_string>@"(?:[^"]|"")*")           # @"verbatim string"
        |(?P<interpolated>\$@?"(?:\\.|[^"\\])*"|@\$"(?:[^"]|"")*")  # $"..." or $@"..."
        |(?P<string>"(?:\\.|[^"\\])*")                  # "regular string"
        |(?P<char>'(?:\\.|[^'\\])*')                    # 'c' char literal
        ''',
        re.DOTALL | re.VERBOSE,
    )

    def _blank(match: re.Match) -> str:
        text = match.group(0)
        # Preserve newlines so line numbers/positions stay meaningful,
        # replace everything else with a space.
        return ''.join(ch if ch == '\n' else ' ' for ch in text)

    return pattern.sub(_blank, content)


def _has_real_namespace_declaration(content: str) -> bool:
    """Check whether the code actually declares a namespace, ignoring
    occurrences of the word inside comments or string/char literals."""
    cleaned = _strip_comments_and_strings(content)
    # Matches both block-scoped (`namespace Foo {`) and
    # file-scoped (`namespace Foo;`) declarations.
    return re.search(r'\bnamespace\s+[\w.]+\s*[{;]', cleaned) is not None


def _split_leading_usings(content: str) -> tuple[str, str]:
    """
    Split content into (using_block, remainder), where using_block contains
    the leading `using ...;` directives (including `using static` and
    `global using`), plus any blank lines and comment-only lines interleaved
    among them at the top of the file. Everything from the first
    "real code" line onward goes into remainder.
    """
    lines = content.splitlines(keepends=True)

    using_re = re.compile(r'^\s*(global\s+)?using\s.*?;\s*$')
    comment_re = re.compile(r'^\s*//.*$')
    blank_re = re.compile(r'^\s*$')

    split_index = 0
    for i, line in enumerate(lines):
        if using_re.match(line) or comment_re.match(line) or blank_re.match(line):
            split_index = i + 1
        else:
            break

    # Trim trailing blank lines off the using block so we control spacing
    # ourselves rather than duplicating whatever was already there.
    while split_index > 0 and blank_re.match(lines[split_index - 1]):
        split_index -= 1

    using_block = ''.join(lines[:split_index])
    remainder = ''.join(lines[split_index:])
    return using_block, remainder


def ensure_namespace_in_file(file_path: Path, namespace: str) -> bool:
    """Add namespace wrapper to a C# file if it doesn't have one."""
    if not file_path.suffix == '.cs':
        return False

    content = file_path.read_text(encoding='utf-8')

    if _has_real_namespace_declaration(content):
        return False

    using_block, remainder = _split_leading_usings(content)

    # Indent every non-blank line of the remaining content by 4 spaces
    indented_lines = [
        f"    {line}" if line.strip() else line
        for line in remainder.splitlines()
    ]
    indented_remainder = "\n".join(indented_lines)

    using_section = f"{using_block}\n" if using_block else ""

    wrapped = f"""{using_section}namespace {namespace}
{{
{indented_remainder}
}}
"""

    file_path.write_text(wrapped, encoding='utf-8')
    return True