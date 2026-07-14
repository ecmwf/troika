# Latent bugs

Pre-existing issues discovered while adding types and ABCs to the code base.
None of these were introduced by the typing work — they are documented here so
they can be triaged and fixed separately.

## 1. `SiteGroup.preprocess` calls a non-existent `Site.preprocess`

**File:** `src/troika/sites/group.py:38`

```python
def preprocess(self, script, user, output):
    """See `troika.sites.base.Site.preprocess`"""
    return self._selected.preprocess(script, user, output)
```

`SiteGroup.preprocess` delegates to `self._selected.preprocess(...)`, and its
docstring references `Site.preprocess`. However **no `Site` class defines a
`preprocess` method** — not the base class (`sites/base.py`), nor any of the
concrete backends (`direct`, `slurm`, `pbs`, `sge`). Any call to this method
would raise `AttributeError` at runtime.

This is either dead code or a feature that was removed from the backends but
left dangling in the group wrapper.

**Options:**
- Remove `SiteGroup.preprocess` if it is genuinely unused.
- Or, if preprocessing is intended, add `preprocess` to the `Site` interface
  (ideally as an abstract or concrete method) and implement it in the backends.

> Note: `preprocess` was intentionally **not** added as an abstract method
> during the ABC conversion of `Site`, because doing so would force every
> backend to implement it and would break instantiation of the existing
> concrete sites.

## 2. `SiteGroup.__init__` does not call `super().__init__()`

**File:** `src/troika/sites/group.py:17`

```python
def __init__(self, config, connection, global_config):
    self._select(config, connection.user, global_config)
    self._connection = self._selected._connection
```

Unlike every other `Site` subclass, `SiteGroup.__init__` skips
`super().__init__(config, connection, global_config)`. As a result, a
`SiteGroup` instance never gets `self.config` or `self._kill_sequence` set.

This is harmless today because `SiteGroup` overrides `submit`, `monitor`,
`kill`, and `check_connection`, delegating all real work to the selected site.
But it is a footgun: if `SiteGroup` ever relies on a concrete `Site` base
method that reads `self.config` or `self._kill_sequence` (e.g.
`create_output_dir`, `get_directive_translation`), it will fail with
`AttributeError`.

**Options:**
- Call `super().__init__(...)` in `SiteGroup.__init__`, or
- Explicitly document that `SiteGroup` is a pure delegating wrapper and is not
  expected to use inherited `Site` behaviour.
