
# Verification

- execute pre-commit hooks
- Use `ruff` for linting and formatting
- Check types via `mypy`
  - prefer immutable data structures for annotations, in particular `collections.abc.Sequence` instead of `list` and `collections.abc.Mapping` instead of `dict`.
- where it makes sense introduce subtypes via NewType
