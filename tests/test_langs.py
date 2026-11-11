from archdoc.langs import extract_go, extract_javascript, extract_typescript

TS = """import { readFile } from "fs";
const fs = require('path');

/**
 * Add two numbers.
 * @param a first
 */
export function add(a: number, b: number): number {
  const inner = () => { return 1; };
  return a + b;
}

function hidden(x) { return x; }

/** A shape. */
export class Shape {
  /** Area of the shape. */
  area(scale: number): number {
    if (scale) { return 1; }
    return 0;
  }

  private secret() { return 1; }
  #internal() { return 2; }
  constructor() {}
}

export const double = (n: number): number => n * 2;
export const single = n => n;
export interface Options { verbose: boolean; }
export type Id = string;
const notFn = (1 + 2);
"""

GO = """// Package demo shows things.
package demo

import (
	"fmt"
	str "strings"
)

import "os"

// Greeter greets.
type Greeter struct {
	name string
}

type hidden interface {
	Do()
}

// Hello says hello.
func (g *Greeter) Hello(name string) string {
	return fmt.Sprintf("hi %s", name)
}

func helper() {}

// New builds a Greeter.
func New(name string) (*Greeter, error) {
	return &Greeter{name: name}, nil
}
"""


def test_typescript_symbols():
    info = extract_typescript(TS, "m.ts")
    by = {s.name: s for s in info.symbols}
    assert info.language == "typescript"
    assert info.imports == ["fs", "path"]
    assert set(by) == {
        "add",
        "hidden",
        "Shape",
        "Shape.area",
        "double",
        "single",
        "Options",
        "Id",
    }
    assert by["add"].signature == "(a: number, b: number): number"
    assert by["add"].summary == "Add two numbers."
    assert by["add"].public and not by["hidden"].public
    assert by["Shape.area"].kind == "method"
    assert by["Shape.area"].summary == "Area of the shape."
    assert by["double"].signature == "(n: number): number"
    assert by["single"].signature == "(n)"
    assert by["add"].end_lineno == 11


def test_javascript_without_exports_is_public():
    info = extract_javascript("function a() {}\nclass B {\n  m() {}\n}\n", "x.js")
    assert all(s.public for s in info.symbols)
    assert {s.name for s in info.symbols} == {"a", "B", "B.m"}


def test_go_symbols():
    info = extract_go(GO, "demo.go")
    by = {s.name: s for s in info.symbols}
    assert info.language == "go"
    assert info.docstring == "Package demo shows things."
    assert info.imports == ["fmt", "os", "strings"]
    assert set(by) == {"Greeter", "hidden", "Greeter.Hello", "helper", "New"}
    assert by["Greeter.Hello"].kind == "method"
    assert by["Greeter.Hello"].signature == "(name string) string"
    assert by["Greeter.Hello"].summary == "Hello says hello."
    assert by["New"].signature == "(name string) (*Greeter, error)"
    assert by["Greeter"].public and not by["hidden"].public and not by["helper"].public
