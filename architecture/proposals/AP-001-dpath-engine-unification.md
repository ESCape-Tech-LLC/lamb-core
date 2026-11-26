# DPath Engine Unification Proposal

## Status
**Proposed** - Not yet implemented

## Problem
Current dpath implementation has multiple issues:
- Two different engines (dpath library vs functools.reduce) with inconsistent behavior
- Performance overhead from external dependencies
- Complex configuration logic (LAMB_DPATH_DICT_ENGINE setting)
- Inconsistent error handling across engines
- Difficulty distinguishing "key missing" from "transformation error"

## Solution
Unify all dictionary-based path extraction into a single optimized engine.

### Unified Engine Features
1. **Single Implementation** - Replace both `_impl_dict_dpath` and `_impl_dict_reduce` with `_impl_dict_unified`
2. **Slash Notation Support** - Support "key/subkey/value" paths (replacing dpath functionality)
3. **Multiple Input Formats** - Handle strings, lists, tuples uniformly
4. **Performance Optimization** - Fast paths for common cases
5. **Path Compilation Cache** - Cache parsed paths for repeated use

### Error Handling Unification
- All engines will consistently throw `InvalidBodyStructureError` for missing keys
- Differentiate between "key missing" (always throws) and "transformation errors" (uses default)
- Clear separation of concerns in error processing

### Configuration Simplification
- Remove `LAMB_DPATH_DICT_ENGINE` setting
- Eliminate dpath library dependency
- Simplify adapter logic

### API Cleanup
- Cleaner function signatures
- More intuitive parameter names
- Better documentation and type hints

## Benefits
- **Performance**: 5-50x speed improvement for common cases
- **Maintainability**: Single code path to maintain
- **Consistency**: Uniform behavior across all data sources
- **Reliability**: Predictable error handling
- **Simplicity**: Reduced configuration complexity

## Impact Assessment
### Affected Components
- `lamb/utils/dpath.py` - Main implementation
- Configuration system - Remove LAMB_DPATH_DICT_ENGINE
- Dependency management - Remove dpath library

### Backward Compatibility
- Full API compatibility maintained
- All existing path formats continue to work
- All current tests should pass without modification
- After success migration tests can be adapted to new logic and simplified  

### Migration Path
1. Implement unified engine alongside existing engines
2. Redirect all dictionary-based extraction to new engine
3. Remove old engines and configuration options
4. Update documentation and examples

## Implementation Plan
(TBD - Will be detailed when implementation begins)

## Decision Points
- Error handling strategy for default values
- Path caching strategy and size limits
- Final API signature and parameter names
