---
oncalls: ['fairseq2']
description: Maintenance workflow for fairseq2 skill. Run periodic checks to keep documentation synchronized with codebase.
apply_to_user_prompt: 'maintain fairseq2|fairseq2 maintenance|check staleness|update docs'
---

# fairseq2 Skill Maintenance

## Overview

This sub-skill provides workflows for maintaining the fairseq2 skill documentation in sync with the codebase.

## When to Use

- After significant fairseq2 codebase changes
- Weekly/monthly maintenance cycles
- When documentation gaps are detected
- When preparing for major releases

## Quick Commands

```bash
# Check documentation staleness
python scripts/check_staleness.py --summary

# Validate all links and breadcrumbs
python scripts/update_links.py --check all

# Fix breadcrumbs automatically
python scripts/update_links.py --fix breadcrumbs --apply

# Update documentation index
python scripts/update_index.py --apply

# Run all tests
python -m pytest tests/ -v

# Generate health report
python scripts/update_links.py --output reports/link_health.md
```

## Maintenance Workflow

### Weekly Check (5 min)

1. Run staleness check:
   ```bash
   python scripts/check_staleness.py --summary
   ```
2. Review any HIGH/CRITICAL issues
3. Update DOCUMENTATION_GAPS.md if needed

### Monthly Review (30 min)

1. Run full validation:
   ```bash
   python scripts/check_staleness.py --output reports/staleness.md
   python scripts/update_links.py --output reports/link_health.md
   ```
2. Review both reports
3. Fix any broken links or stale references
4. Update gap statistics
5. Run test suite:
   ```bash
   python -m pytest tests/ -v
   ```

### After Major Code Changes

1. Identify affected documentation from changed files
2. Update relevant doc files with new APIs/patterns
3. Run staleness check on updated docs
4. Add any detected gaps to DOCUMENTATION_GAPS.md
5. Mark resolved gaps as fixed

## Gap Tracking

When you detect a documentation gap:

1. Add entry to `DOCUMENTATION_GAPS.md`:
   ```markdown
   ### [GAP-XXX] Brief Description
   - **Detected**: YYYY-MM-DD
   - **Severity**: High/Medium/Low
   - **Doc Says**: [What documentation states]
   - **Code Shows**: [What source code actually does]
   - **File**: path/to/file.py:line_number
   - **Status**: Open
   ```

2. Update Gap Statistics table
3. Prioritize fix based on severity
4. After fixing, move to Resolved Gaps section

## Integration with Main Skill

This maintenance skill complements the main `SKILL.md` by:

- Keeping code references accurate
- Maintaining navigation links
- Tracking documentation health over time
- Providing reproducible maintenance workflows

## Troubleshooting

### Staleness Check Fails

```bash
# Check if codebase path is correct
python -c "from scripts.config import get_codebase_root; print(get_codebase_root())"

# Verify docs directory
python -c "from scripts.config import get_docs_dir; print(get_docs_dir())"
```

### Link Validation Errors

```bash
# List all broken links with details
python scripts/update_links.py --check links

# Preview breadcrumb fixes
python scripts/update_links.py --fix breadcrumbs --preview
```

### Tests Failing

```bash
# Run with verbose output
python -m pytest tests/ -v --tb=long

# Run specific test file
python -m pytest tests/test_config.py -v
```
