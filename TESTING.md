# Testing Guidelines

## Philosophy

- Tests are specifications of behavior, not just validation tools
- Each test should clearly express intent and expected outcomes
- Failing tests should provide actionable diagnostic information
- Test design should follow Arrange-Act-Assert pattern with clear comments

## Test Structure

### Unit Tests
- Located in `tests/unit/` with parallel structure to `lamb/`
- Use pytest with async support where appropriate
- Prefer isolated, fast, deterministic tests
- Use mocks and fixtures judiciously - prefer real dependencies when feasible

### Integration Tests
- Located in `tests/integration/`
- Test service interactions with real Dockerized dependencies
- Use `tests/conftest.py` for shared fixtures
- Health-check services before test execution

### Characterization Tests
- Document existing behavior for refactoring safety
- Preserve edge cases and quirks until explicitly changed
- Essential for legacy code coverage

## Test Modes

### Coverage Mode
**Goal**: Understand current system behavior and identify potential issues

**Approach**:
- Create tests as a diagnostic tool for behavior
- Don't aim for 100% pass rate by any means necessary
- Record discrepancies between expectations and reality
- Formulate reasoned doubts and questions

**What to do when issues are discovered**:
1. Analyze the logic of the discrepancy
2. Check documentation and specifications
3. Formulate specific questions about the nature of the problem
4. Leave tests failing as indicators for discussion

**Implementation adjustments**:
- Only for explicit bugs (null pointer, crashes, etc.)
- Never for "fitting" tests
- Only after confirming the problem

### Feature Development Mode
**Goal**: Implement new functionality with complete test coverage

**Approach**:
- Tests as precise specification of behavior
- All tests should pass
- Maintain backward compatibility
- Follow TDD principles

**What to do when tests fail**:
- Fix the implementation, not the tests
- Ensure all existing tests pass
- Strictly follow specifications

## Naming Conventions

- `test_<unit>_<action>_<expected>` for clear intent
- Descriptive test class names for grouping related tests
- Parameterized tests for data-driven scenarios
- Clear, readable assertions with meaningful messages

## Test Data

- Prefer realistic, domain-relevant test data
- Use factories or builders for complex test objects
- Externalize large test datasets to `tests/data/`
- Avoid hardcoded magic values in favor of named constants

## Assertions

- Specific, precise assertions over generic "truthy" checks
- Use pytest's rich assertion introspection
- Include context in assertion messages when values aren't self-explanatory
- Prefer `pytest.approx()` for floating-point comparisons

## Error Handling

- Test both success paths and failure modes
- Verify exception types and messages precisely
- Use `pytest.raises()` with `match=` for message validation
- Test error recovery and state consistency

## Performance

- Mark slow tests with `@pytest.mark.slow`
- Use `pytest.mark.skipif` for environment-dependent tests
- Avoid unnecessary setup/teardown in test loops
- Profile test suites regularly for bottlenecks

## Database Tests

- Use transactions with rollback for test isolation
- Prefer read replicas for non-mutating tests
- Clean up test data explicitly, don't rely on test order
- Use `pytest-lazy-fixture` for complex fixture combinations

## Async Testing

- Use `pytest-asyncio` with `asyncio_mode = "auto"`
- Prefer `async def` test functions for async code
- Use `anyio` backend for cross-async-library compatibility
- Test cancellation and timeout scenarios

## Mocking Strategy

- Prefer state verification over interaction testing
- Use `unittest.mock` for simple cases, `pytest-mock` for fixtures
- Avoid deep mocking that couples tests to implementation details
- Mock at service boundaries, not internal collaborators

## Code Coverage

- Aim for meaningful coverage, not arbitrary percentages
- Critical paths and error handlers must be covered
- Legacy code should gain characterization coverage before changes
- Exclude test files, migrations, and generated code from coverage metrics

## Continuous Integration

- Tests must run in isolated, reproducible environments
- Use Docker Compose for service dependencies
- Parallelize test execution where safe
- Report flaky tests immediately - don't tolerate instability

## Debugging and Diagnostics

- Use `pytest --pdb` for interactive debugging
- Enable verbose output with `-v` for CI diagnostics
- Capture logs with `--log-cli-level=INFO`
- Use `pytest-html` for detailed test reports

## Best Practices Learned

### Test Expectation Alignment
- Always ensure test expectations match actual implementation behavior
- When implementation behavior changes, update tests accordingly rather than changing the implementation
- Pay attention to third-party library behaviors (e.g., `furl` omitting default ports)

### Import and Response Handling
- Use correct imports in tests (e.g., lamb JsonResponse vs Django JsonResponse)
- Handle response parsing correctly (e.g., use `json.loads()` instead of `.json()` method)

### Validator Behavior Understanding
- Understand the exact behavior of validation functions:
  - `empty_as_none=True` requires `allow_none=True` to actually return None
  - Different exception types may be raised than initially expected
- Test edge cases thoroughly to understand actual behavior

### Code Formatting and Style
- Maintain consistent code formatting using `ruff format`
- Fix import ordering issues regularly
- Address linting issues promptly to maintain code quality

### Test Maintenance
- Regularly run the full test suite to catch regressions
- Keep tests up-to-date with implementation changes
- Use characterization tests to safely refactor existing code