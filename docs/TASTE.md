# TASTE

- Testing style preference: Prefer module-level pytest test functions; avoid class-based test containers such as `class TestQueryTickerCallback` unless explicitly requested.
- Agent memory preference: For single-agent chat flows, persist full `result.to_input_list()` items in memory (including tool-related items) and rely on process restart to reset state after tool changes.
