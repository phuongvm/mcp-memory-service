<!-- 1b855546-b9ec-484f-88c6-6a589fd76943 a0b6e0cd-c4e3-4b2b-a334-0661be03c57d -->
# Test MCP Tools Comprehensive Validation Suite

## Overview

Create a comprehensive test suite for all 7 test-mcp MCP tools that validates each tool's functionality and cross-checks results between tools to ensure data integrity.

## Available Tools to Test

Based on `src/mcp_memory_service/web/api/mcp.py`, the test-mcp service provides:

1. **store_memory** - Store memories with content, tags, metadata, memory_type
2. **retrieve_memory** - Semantic search with query, limit, similarity_threshold
3. **recall_memory** - Time-based retrieval with natural language queries
4. **search_by_tag** - Tag-based search with AND/OR operations
5. **delete_memory** - Delete by content_hash
6. **check_database_health** - Database statistics and health status
7. **list_memories** - Paginated listing with filtering by tag/memory_type

## Test Strategy

### Phase 1: Individual Tool Validation

Create test cases for each tool that verify:

- Required parameters are validated
- Optional parameters work correctly
- Expected response structure is returned
- Edge cases are handled properly

### Phase 2: Cross-Validation Tests

For each operation, verify results using alternative tools:

- After `store_memory`, verify with `retrieve_memory`, `search_by_tag`, and `list_memories`
- After `delete_memory`, confirm deletion via all retrieval methods
- Compare `retrieve_memory` vs `search_by_tag` results for tagged memories
- Validate `recall_memory` time filtering against actual timestamps
- Cross-check `list_memories` pagination totals with `check_database_health` statistics

## Test File Structure

Create `tests/integration/test_mcp_tools_comprehensive.py` with:

### Test Classes

- `TestStoreMemory` - Store operation validation
- `TestRetrieveMemory` - Semantic search validation
- `TestRecallMemory` - Time-based recall validation
- `TestSearchByTag` - Tag search validation
- `TestDeleteMemory` - Deletion validation
- `TestListMemories` - Pagination and filtering validation
- `TestDatabaseHealth` - Health check validation
- `TestCrossValidation` - Cross-tool verification tests

### Key Test Scenarios

**Store Memory Tests:**

- Store with minimal parameters (content only)
- Store with all parameters (tags, metadata, memory_type, client_hostname)
- Verify content_hash generation
- Test duplicate content handling
- Cross-check with retrieve_memory and list_memories

**Retrieve Memory Tests:**

- Semantic search with various queries
- Test similarity_threshold filtering (0.0 to 1.0)
- Test limit parameter
- Verify relevance scores are returned
- Cross-validate with search_by_tag for tagged content

**Recall Memory Tests:**

- Natural language time expressions ("last week", "yesterday", "today")
- Time-based filtering accuracy
- Compare with list_memories filtered by date range
- Verify n_results parameter

**Search By Tag Tests:**

- Single tag search
- Multiple tags with AND operation
- Multiple tags with OR operation
- Non-existent tag handling
- Cross-validate with retrieve_memory for semantic match

**Delete Memory Tests:**

- Delete by valid content_hash
- Delete non-existent content_hash
- Verify deletion with retrieve_memory, search_by_tag, list_memories
- Confirm statistics update in check_database_health

**List Memories Tests:**

- Pagination (page 1, 2, etc.)
- Page size variations (1, 10, 50, 100)
- Filter by single tag
- Filter by memory_type
- Verify total_found count
- Edge cases (page beyond available data)

**Database Health Tests:**

- Verify statistics structure
- Check total_memories count
- Validate against actual stored memories
- Monitor statistics changes after operations

**Cross-Validation Tests:**

- Store → Retrieve → Delete → Verify deletion
- Store with tags → search_by_tag → retrieve_memory (compare results)
- Multiple stores → check_database_health → list_memories (verify counts)
- Time-based: Store → recall_memory → list_memories (verify timestamps)
- Pagination consistency: list_memories across all pages equals total count

## Implementation Details

### Test Setup

- Use pytest fixtures for test database
- Create isolated test environment with clean database
- Implement helper functions for common operations
- Use async/await for all MCP tool calls

### Assertions

- Verify response structure matches expected schema
- Check success/error status codes
- Validate data types of returned fields
- Ensure cross-tool consistency
- Verify timestamps are in ISO format
- Check content_hash uniqueness

### Test Data

- Create varied test memories (different content, tags, types)
- Use predictable content for semantic search testing
- Generate memories with specific timestamps
- Include edge cases (empty tags, long content, special characters)

## Files to Create/Modify

**New file:** `tests/integration/test_mcp_tools_comprehensive.py` (~800-1000 lines)

- All test classes and methods
- Fixtures for database setup/teardown
- Helper functions for MCP tool invocation
- Cross-validation helper methods

**Reference files:**

- `src/mcp_memory_service/web/api/mcp.py` (lines 57-142) - Tool definitions
- `src/mcp_memory_service/web/api/mcp.py` (lines 217-385) - Tool implementations
- `tests/conftest.py` - Existing fixtures
- `tests/integration/test_mcp_memory.py` - Test patterns

## Success Criteria

1. All 7 tools have individual test coverage
2. Each tool has at least 5 test cases
3. Cross-validation tests confirm data consistency
4. Edge cases and error conditions are tested
5. All tests pass with clear assertions
6. Test execution time is reasonable (<2 minutes total)

## Usage for Release Validation

### Pre-Release Checklist

Before each release, run the comprehensive MCP tools test suite:

```bash
# Run the full MCP tools validation suite
pytest tests/integration/test_mcp_tools_comprehensive.py -v

# Run with coverage report
pytest tests/integration/test_mcp_tools_comprehensive.py --cov=src/mcp_memory_service/web/api/mcp --cov-report=html

# Run specific test class
pytest tests/integration/test_mcp_tools_comprehensive.py::TestCrossValidation -v
```

### Integration with CI/CD

Add to your CI/CD pipeline (e.g., `.github/workflows/test.yml`):

```yaml
- name: Run MCP Tools Validation
  run: |
    pytest tests/integration/test_mcp_tools_comprehensive.py -v --tb=short
```

### Release Sign-Off

Before tagging a new release, ensure:

- [ ] All MCP tools tests pass
- [ ] Cross-validation tests confirm data consistency
- [ ] No regressions in existing functionality
- [ ] New features have corresponding tests added
- [ ] Test execution time remains under 2 minutes

## Maintenance

### When to Update This Plan

Update this test plan when:

1. **New MCP tools are added** - Add corresponding test class and scenarios
2. **Tool signatures change** - Update test cases to match new parameters
3. **New edge cases discovered** - Add regression tests
4. **Performance requirements change** - Adjust test execution time targets
5. **Storage backend changes** - Verify all cross-validation logic still applies

### Test Plan Version History

- **v1.0** (2024-10-27) - Initial comprehensive validation plan for 7 MCP tools

## Related Documentation

- [MCP API Reference](../mastery/api-reference.md) - Complete API documentation
- [Testing Guide](test_guide.md) - General testing practices
- [Contributing Guidelines](../../CONTRIBUTING.md) - How to contribute tests


