from pathlib import Path

from app.services import syntax_chunker
from app.services.chunker import chunk_file

EXPRESS_ROUTES = """const express = require('express');
const router = express.Router();

router.post('/login', async (req, res) => {
  const user = await User.findOne({ email: req.body.email });
  if (!user) return res.status(404).send('no user');
  res.json(user);
});

router.get('/health', (req, res) => res.send('ok'));

function hashPassword(password) {
  return bcrypt.hash(password, 10);
}

module.exports = router;
"""

REACT_COMPONENT = """import { useState } from 'react';

export const Counter = () => {
  const [count, setCount] = useState(0);
  return <button onClick={() => setCount(count + 1)}>{count}</button>;
};

export default function App() {
  return <Counter />;
}
"""

TS_SERVICE = """import { Injectable } from '@angular/core';

export interface User {
  id: number;
  name: string;
}

export class UserService {
  private users: User[] = [];

  add(user: User): void {
    this.users.push(user);
  }
}
"""


def java_class(method_count: int) -> str:
    methods = "\n".join(
        f"    public int method{i}(int x) {{\n" + "        x = x + 1;\n" * 10 + "        return x;\n    }\n"
        for i in range(method_count)
    )
    return f"package app;\n\nimport java.util.List;\n\npublic class UserService {{\n    private int count;\n\n{methods}}}\n"


def chunks_for(tmp_path: Path, name: str, source: str):
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return chunk_file(path, tmp_path)


def test_express_routes_become_named_chunks(tmp_path):
    chunks = chunks_for(tmp_path, "auth.js", EXPRESS_ROUTES)
    names = [c.name for c in chunks if c.kind == "function"]

    assert "router.post('/login')" in names
    assert "hashPassword" in names
    # The one-line /health route is too short to be its own topic
    assert "router.get('/health')" not in names
    module = next(c for c in chunks if c.kind == "module")
    assert "require('express')" in module.content


def test_react_arrow_and_default_export_components(tmp_path):
    chunks = chunks_for(tmp_path, "App.jsx", REACT_COMPONENT)
    by_name = {c.name: c for c in chunks if c.name}

    assert set(by_name) == {"Counter", "App"}
    assert by_name["Counter"].content.startswith("export const Counter")
    assert by_name["Counter"].language == "JavaScript"


def test_typescript_interfaces_and_classes(tmp_path):
    chunks = chunks_for(tmp_path, "user.service.ts", TS_SERVICE)
    kinds = {c.name: c.kind for c in chunks if c.name}

    assert kinds == {"User": "class", "UserService": "class"}


def test_small_java_class_stays_whole(tmp_path):
    chunks = chunks_for(tmp_path, "UserService.java", java_class(2))
    named = [c for c in chunks if c.name]

    assert [(c.kind, c.name) for c in named] == [("class", "UserService")]


def test_big_java_class_is_split_into_methods(tmp_path):
    chunks = chunks_for(tmp_path, "UserService.java", java_class(8))
    names = [c.name for c in chunks if c.kind == "function"]

    assert names == [f"UserService.method{i}" for i in range(8)]
    # Fields and the class header are kept in the module chunk
    module = next(c for c in chunks if c.kind == "module")
    assert "private int count;" in module.content


def test_line_numbers_point_at_the_code(tmp_path):
    chunks = chunks_for(tmp_path, "auth.js", EXPRESS_ROUTES)
    login = next(c for c in chunks if c.name == "router.post('/login')")
    lines = EXPRESS_ROUTES.splitlines()

    assert lines[login.start_line - 1].startswith("router.post('/login'")
    assert lines[login.end_line - 1] == "});"


def test_supports_only_known_suffixes():
    assert syntax_chunker.supports(".tsx")
    assert syntax_chunker.supports(".JAVA")
    assert not syntax_chunker.supports(".go")
