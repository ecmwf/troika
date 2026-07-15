# Latent bugs

Pre-existing issues discovered while adding types and ABCs to the code base.
None were introduced by the typing work. Both have now been resolved; the
findings are kept here as a record.

## 1. `SiteGroup.preprocess` called a non-existent `Site.preprocess` — RESOLVED

**Was:** `src/troika/sites/group.py`

```python
def preprocess(self, script, user, output):
    """See `troika.sites.base.Site.preprocess`"""
    return self._selected.preprocess(script, user, output)
```

`SiteGroup.preprocess` delegated to `self._selected.preprocess(...)`, but **no
`Site` class defined a `preprocess` method** — not the base, nor any backend
(`direct`, `slurm`, `pbs`, `sge`). Any call would have raised `AttributeError`.
It was dead code (a feature removed from the backends but left dangling in the
group wrapper).

**Fix:** the dangling `preprocess` method was removed from `SiteGroup`.

## 2. `SiteGroup` was an incomplete delegating wrapper — RESOLVED

**Was:** `src/troika/sites/group.py`

```python
def __init__(self, config, connection, global_config):
    self._select(config, connection.user, global_config)
    self._connection = self._selected._connection
```

`SiteGroup` skipped `super().__init__()`, so `self.config` and
`self._kill_sequence` were never set. It only forwarded `submit`, `monitor`,
`kill`, and `check_connection` to the selected site, but **inherited** the other
`Site` methods instead of delegating them. Those inherited methods are called on
the top-level site object by other parts of Troika:

- `controllers/base.py` reads `self.site.config` and calls
  `self.site.get_directive_translation()` / `self.site.get_native_parser()`;
- `hooks/common.py` calls `site.create_output_dir(...)` /
  `site.remove_previous_output(...)` and reads `site._connection`.

For a group site this meant:

- `site.config` and `create_output_dir` / `get_directive_translation` raised
  `AttributeError` (`self.config` unset), and
- `get_native_parser` returned `None` and directive translation was empty —
  silently wrong — instead of the selected backend's.

Simply calling `super().__init__()` would have masked the crash with
plausible-but-wrong state: the inherited methods would then run against the
*group's* own config (default `pmkdir_command`, empty `directive_translate`)
rather than the selected backend's — turning a loud failure into a silent one.
The root cause was that `Site` mixed *interface* with *shared implementation*,
and `SiteGroup` wanted the interface but not the implementation.

**Fix:** split interface from implementation and make the group a true proxy.

- `Site` (ABC) is now the pure interface: the eight methods every site exposes,
  plus the `config` and `_connection` attributes that external code reads.
- `BaseSite(Site)` carries the shared implementation (config/connection handling,
  `create_output_dir`, `get_directive_translation`, …). The concrete backends
  (`direct`, `slurm`, `pbs`, `sge`) now extend `BaseSite`.
- `SiteGroup(Site)` implements the interface by **delegating every method** to
  the selected backend and mirroring its `config` / `_connection`. It holds no
  site state of its own and deliberately does **not** call `super().__init__()`.

Because the group implements `Site` directly, the ABC now guarantees it is a
complete implementation — a method can no longer be silently left un-delegated.
