"""Finds functions and classes in JavaScript, TypeScript and Java using tree-sitter.

tree-sitter reads code into a tree (a "syntax tree"), the same way Python's `ast` does for Python,
so we can cut at real function boundaries instead of every 60 lines.

Returns "spans": (start_line, end_line, kind, name), with 1-based line numbers.
"""
from functools import lru_cache

import tree_sitter_java
import tree_sitter_javascript
import tree_sitter_typescript
from tree_sitter import Language, Node, Parser

Span = tuple[int, int, str, str]

GRAMMARS = {
    "javascript": tree_sitter_javascript.language,   # also understands JSX
    "typescript": tree_sitter_typescript.language_typescript,
    "tsx": tree_sitter_typescript.language_tsx,
    "java": tree_sitter_java.language,
}

SUFFIX_GRAMMAR = {
    ".js": "javascript", ".jsx": "javascript", ".mjs": "javascript", ".cjs": "javascript",
    ".ts": "typescript", ".tsx": "tsx", ".java": "java",
}

FUNCTION_TYPES = {
    "function_declaration", "generator_function_declaration",   # JS/TS: function login() {}
    "method_declaration", "constructor_declaration",            # Java
    "method_definition",                                         # JS class methods
}
CLASS_TYPES = {
    "class_declaration", "abstract_class_declaration", "interface_declaration",
    "enum_declaration", "record_declaration",
}
# Values that make `const x = <value>` worth its own chunk, e.g. const Home = () => {...}
FUNCTION_VALUES = {"arrow_function", "function_expression", "function", "generator_function"}

MIN_CALLBACK_LINES = 3   # router.get('/x', (req, res) => {...}) must be at least this long to count
SPLIT_CLASS_LINES = 80   # classes longer than this are split into one chunk per method


@lru_cache(maxsize=None)
def get_parser(grammar: str) -> Parser:
    return Parser(Language(GRAMMARS[grammar]()))


def supports(suffix: str) -> bool:
    return suffix.lower() in SUFFIX_GRAMMAR


def text(node: Node | None) -> str:
    return node.text.decode("utf-8", errors="ignore") if node is not None else ""


def lines_of(node: Node) -> tuple[int, int]:
    return node.start_point[0] + 1, node.end_point[0] + 1


def callback_name(statement: Node) -> str | None:
    """For `router.post('/login', async (req, res) => {...})` return "router.post('/login')"."""
    call = statement.named_children[0] if statement.named_children else None
    if call is None or call.type != "call_expression":
        return None
    args = call.child_by_field_name("arguments")
    if args is None or not any(a.type in FUNCTION_VALUES for a in args.named_children):
        return None
    first_string = next((a for a in args.named_children if a.type in ("string", "template_string")), None)
    callee = text(call.child_by_field_name("function"))
    return f"{callee}({text(first_string)})" if first_string else callee


def classify(node: Node) -> tuple[str, str] | None:
    """Return (kind, name) if this top-level statement deserves its own chunk."""
    inner = node
    if node.type == "export_statement":  # export function x / export default class Y / export const z = ...
        inner = node.child_by_field_name("declaration") or node.child_by_field_name("value") or node

    if inner.type in FUNCTION_TYPES:
        return "function", text(inner.child_by_field_name("name")) or "default"
    if inner.type in CLASS_TYPES or inner.type == "class":
        return "class", text(inner.child_by_field_name("name")) or "default"
    if inner.type in FUNCTION_VALUES:  # export default () => {...}
        return "function", "default"
    if inner.type in ("lexical_declaration", "variable_declaration"):
        for declarator in inner.named_children:
            value = declarator.child_by_field_name("value")
            if value is not None and value.type in FUNCTION_VALUES | {"class"}:
                kind = "class" if value.type == "class" else "function"
                return kind, text(declarator.child_by_field_name("name"))
    if inner.type == "expression_statement":
        start, end = lines_of(inner)
        name = callback_name(inner)
        if name and end - start + 1 >= MIN_CALLBACK_LINES:
            return "function", name
    return None


def class_member_spans(class_node: Node, class_name: str) -> list[Span]:
    """Split a big class into one span per method, named like UserService.register."""
    body = class_node.child_by_field_name("body")
    if body is None:
        return []
    spans = []
    for member in body.named_children:
        if member.type in FUNCTION_TYPES:
            start, end = lines_of(member)
            method = text(member.child_by_field_name("name")) or "constructor"
            spans.append((start, end, "function", f"{class_name}.{method}"))
    return spans


def find_spans(source: str, suffix: str) -> list[Span]:
    tree = get_parser(SUFFIX_GRAMMAR[suffix.lower()]).parse(source.encode("utf-8"))
    spans: list[Span] = []
    for node in tree.root_node.named_children:
        found = classify(node)
        if found is None:
            continue
        kind, name = found
        start, end = lines_of(node)

        if kind == "class" and end - start + 1 > SPLIT_CLASS_LINES:
            inner = node
            if node.type == "export_statement":
                inner = node.child_by_field_name("declaration") or node
            methods = class_member_spans(inner, name)
            if methods:
                spans.extend(methods)  # fields and the class header end up in the module chunk
                continue
        spans.append((start, end, kind, name))
    return spans
