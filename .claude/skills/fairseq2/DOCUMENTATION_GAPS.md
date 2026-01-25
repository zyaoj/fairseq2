# fairseq2 Documentation Gaps

## Purpose

Track discrepancies between documentation and actual codebase. This file helps maintain documentation accuracy through systematic gap detection and resolution.

## How to Use

1. **Detect**: Run `python scripts/check_staleness.py` to find gaps
2. **Log**: Add detected gaps to "Active Gaps" section
3. **Fix**: Update documentation to match codebase
4. **Resolve**: Move fixed gaps to "Resolved Gaps" section

---

## Gap Statistics

| Severity | Active | Resolved | Total |
|----------|--------|----------|-------|
| Critical | 0 | 0 | 0 |
| High | 0 | 0 | 0 |
| Medium | 0 | 0 | 0 |
| Low | 0 | 0 | 0 |
| **Total** | **0** | **0** | **0** |

---

## Active Gaps

<!-- Add new gaps here using the template below -->
<!-- 
### [GAP-XXX] Brief Description
- **Detected**: YYYY-MM-DD
- **Severity**: Critical/High/Medium/Low
- **Doc Says**: [What documentation states]
- **Code Shows**: [What source code actually does]
- **File**: path/to/file.py:line_number
- **Status**: Open
-->

No active gaps.

---

## Resolved Gaps

<!-- Move resolved gaps here with resolution notes -->
<!-- 
### [GAP-XXX] Brief Description
- **Detected**: YYYY-MM-DD
- **Resolved**: YYYY-MM-DD
- **Resolution**: [How it was fixed]
-->

No resolved gaps yet.

---

## Review Schedule

- **Weekly**: Run `check_staleness.py --summary`
- **Monthly**: Review all active gaps and prioritize fixes
- **After major updates**: Full staleness check

---

## Contributing

When you detect a documentation gap:

1. Verify it's a genuine gap (not version mismatch)
2. Add to Active Gaps with all required fields
3. Assign severity based on impact:
   - **Critical**: Incorrect API usage could cause errors
   - **High**: Missing important functionality
   - **Medium**: Outdated examples or minor inaccuracies
   - **Low**: Typos, formatting, cosmetic issues
4. Update Gap Statistics table
