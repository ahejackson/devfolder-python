# Coding Style - Python

## Core Principles

- **Type Hints Everywhere**: Use type hints for all function signatures, class attributes, and complex variables. Target full mypy strict mode compatibility.
- **Explicit Over Implicit**: Be clear and explicit in your code. Avoid magic and clever tricks that obscure intent.
- **Pythonic Patterns**: Embrace Python idioms (list comprehensions, context managers, generators) but balance with readability.

## Type Hints

- **Complete Annotations**: Annotate all function parameters, return types, and class attributes:
  ```python
  def process_data(items: list[str], threshold: int = 10) -> dict[str, int]:
      ...
  ```
- **Modern Syntax**: Use built-in types for generics (Python 3.9+): `list[str]`, `dict[str, int]`, `tuple[int, ...]` instead of `List`, `Dict`, `Tuple` from typing.
- **Optional Types**: Use `Type | None` (Python 3.10+) instead of `Optional[Type]`.
- **Protocol for Duck Typing**: Use `Protocol` from `typing` for structural subtyping when you need duck-typing with type safety.
- **TypedDict**: Use `TypedDict` for dictionary structures with known keys rather than plain dicts.
- **Generic Types**: Create generic classes and functions with `TypeVar` when writing reusable components.
- **Literal Types**: Use `Literal` for specific string/int values that act as enums.

## Error Handling

- **Specific Exceptions**: Catch specific exceptions, not bare `except:`. Create custom exception classes for domain errors.
- **EAFP**: Follow "Easier to Ask for Forgiveness than Permission" - use try-except rather than checking conditions when appropriate.
- **Context Managers**: Use context managers for resource management. Implement `__enter__` and `__exit__` or use `contextlib` for custom contexts.
- **Exception Chaining**: Use `raise ... from ...` to preserve exception context.

## Module Organization

- **Flat is Better Than Nested**: Prefer flatter package structures. Deep nesting makes imports cumbersome.
- **Clear Exports**: Define `__all__` in modules to explicitly declare public API.
- **Single Responsibility**: Each module should have one clear purpose.
- **Avoid Circular Imports**: Structure dependencies to avoid circular imports. Use type checking imports with `if TYPE_CHECKING:` for type-only dependencies.

## UV and Dependency Management

- **UV for Everything**: Use UV for creating virtual environments, installing dependencies, and running scripts:
  ```bash
  uv venv
  uv pip install package-name
  uv run script.py
  ```
- **Pyproject.toml**: Define all project metadata, dependencies, and tool configurations in `pyproject.toml`.
- **Dependency Groups**: Use optional dependency groups for dev tools, testing, etc.
- **Lock Files**: Commit `uv.lock` for reproducible builds.

## Data Classes and Models

- **Dataclasses**: Use `@dataclass` for simple data containers. Enable `frozen=True` for immutability when appropriate.
- **Pydantic**: Use Pydantic for data validation at system boundaries (APIs, config files, external data):
  ```python
  from pydantic import BaseModel, Field
  
  class User(BaseModel):
      name: str
      age: int = Field(gt=0)
      email: str
  ```
- **Slots**: Consider `__slots__` for classes with many instances to reduce memory footprint.

## Function Design

- **Pure Functions**: Prefer pure functions (no side effects) when possible for easier testing and reasoning.
- **Small Functions**: Keep functions focused. Extract helper functions liberally.
- **Keyword Arguments**: Use keyword-only arguments (after `*`) for optional parameters to improve call-site clarity.
- **Avoid Mutable Defaults**: Never use mutable objects as default arguments. Use `None` and initialize inside:
  ```python
  def process(items: list[str] | None = None) -> None:
      if items is None:
          items = []
  ```

## Iteration and Collections

- **Comprehensions**: Use list/dict/set comprehensions for simple transformations. For complex logic, use explicit loops.
- **Generators**: Use generators for large datasets or lazy evaluation. Use `yield` instead of building large lists in memory.
- **Built-in Functions**: Leverage built-in functions (`map`, `filter`, `zip`, `enumerate`, `any`, `all`) where they improve clarity.
- **Iterator Tools**: Use `itertools` for advanced iteration patterns.

## Async Programming

- **Async When Needed**: Use async/await for I/O-bound operations (network, file system). Avoid for CPU-bound work.
- **Async Libraries**: Use async-compatible libraries (httpx, aiofiles, asyncpg) in async contexts.
- **Structured Concurrency**: Use `asyncio.gather()` or `asyncio.TaskGroup` (Python 3.11+) for managing concurrent tasks.
- **Type Hints**: Annotate async functions with `async def` and return type `Coroutine` or specific awaitable type.

## Testing

- **Pytest**: Use pytest as the test framework. Leverage fixtures for setup and teardown.
- **Type Checking in Tests**: Type-hint tests for better IDE support and catching errors.
- **Property-Based Testing**: Consider hypothesis for property-based testing of complex functions.
- **Test Organization**: Mirror package structure in tests. Use conftest.py for shared fixtures.

## Modern Python Features

- **Match Statement**: Use structural pattern matching (Python 3.10+) for complex conditional logic.
- **Walrus Operator**: Use `:=` assignment expressions to reduce duplication in comprehensions and conditions.
- **F-Strings**: Always use f-strings for string formatting. Use `=` specifier for debug prints: `f"{variable=}"`.
- **Path Objects**: Use `pathlib.Path` instead of string manipulation for file paths.

## Performance

- **Profile Before Optimizing**: Use profiling tools (cProfile, line_profiler) before optimizing.
- **List Comprehensions**: List comprehensions are faster than equivalent for loops with append.
- **Local Variables**: Access local variables is faster than global or attribute access. Cache frequently accessed attributes in local variables.
- **Avoid Premature Optimization**: Write clear code first, optimize only when profiling shows bottlenecks.

## Code Quality

- **Docstrings**: Write docstrings for all public functions, classes, and modules. Use Google or NumPy style consistently.
- **Type Comments**: Use type comments only for variables where the type isn't obvious from context.
- **Names**: Use descriptive names. Follow PEP 8: `snake_case` for functions/variables, `PascalCase` for classes, `UPPER_CASE` for constants.
- **Line Length**: Keep lines under 88 characters (Black's default) or 100 characters maximum.
- **Imports**: Group imports (standard library, third-party, local) with blank lines between groups. Sort alphabetically within groups.

## Linting and Type Checking

- **Mypy**: Run mypy in strict mode. Configure in pyproject.toml:
  ```toml
  [tool.mypy]
  strict = true
  warn_unreachable = true
  warn_return_any = true
  ```
- **Ruff**: Use Ruff for fast linting and formatting (replaces Black, isort, flake8).
- **Pre-commit Hooks**: Set up pre-commit hooks for automatic checks before commits.

## Anti-Patterns to Avoid

- **Don't Use Wildcard Imports**: Avoid `from module import *`. Be explicit.
- **Don't Override Built-ins**: Never shadow built-in names like `list`, `dict`, `str`, `id`, etc.
- **Don't Use eval()**: Avoid `eval()` and `exec()` for security and maintainability.
- **Don't Ignore Type Errors**: Don't use `type: ignore` without a specific comment explaining why.
