# Structural Fitness Functions - Feature 3

**Version:** 1.0.0
**Date:** 2026-02-03

## Overview

Structural fitness functions verify the codebase maintains proper architecture, dependencies, and design patterns.

## FF-001: Bounded Context Independence

```yaml
Name: Bounded Context Independence
Category: Structural
Related ADR: ADR-009
Rule: No direct database access across bounded contexts
Threshold: 0 violations
Test: Static analysis of imports and dependencies
Tools: Python AST analysis, custom linting rules
Frequency: Every commit (CI)
Owner: Architecture team
Alert: Create GitHub issue on violation
```

**Implementation:**
```python
# tests/fitness/test_bounded_contexts.py
import ast
import os
from pathlib import Path

def test_no_cross_context_database_access():
    """
    FF-001: Bounded contexts should not access other contexts' databases directly
    """
    violations = []

    for py_file in Path("backend/app/contexts").rglob("*.py"):
        tree = ast.parse(py_file.read_text())

        for node in ast.walk(tree):
            # Check for direct model imports from other contexts
            if isinstance(node, ast.ImportFrom):
                module = node.module
                if module and "contexts" in module:
                    source_context = py_file.parts[3]  # Extract context name
                    target_context = module.split("/")[1]

                    if source_context != target_context:
                        violations.append({
                            "file": str(py_file),
                            "line": node.lineno,
                            "import": module
                        })

    assert len(violations) == 0, \
        f"Found {len(violations)} cross-context imports: {violations}"
```

---

## FF-009: Test Coverage

```yaml
Name: Test Coverage
Category: Structural
Related ADR: None
Rule: Code coverage >= 80%
Threshold: 80%
Test: Coverage report
Tools: pytest-cov, coverage.py
Frequency: Every commit
Owner: QA team
Alert: Comment on PR with coverage report
```

**Implementation:**
```bash
# .github/workflows/coverage.yml
- name: Run coverage
  run: |
    pytest --cov=backend/app --cov-report=xml --cov-report=term

- name: Check coverage threshold
  run: |
    coverage=$(coverage report | grep TOTAL | awk '{print $4}' | sed 's/%//')
    if (( $(echo "$coverage < 80" | bc -l) )); then
      echo "Coverage $coverage% is below 80% threshold"
      exit 1
    fi
```

---

## FF-010: Aggregate Size

```yaml
Name: Aggregate Size Limit
Category: Structural
Related ADR: DDD Tactical Design
Rule: Each aggregate should have <= 7 entities
Threshold: Max 7 entities per aggregate
Test: AST analysis or manual review
Tools: Custom script, code review checklist
Frequency: Every PR
Owner: Architecture team
Alert: Comment on PR with oversized aggregates
```

**Implementation:**
```python
# tests/fitness/test_aggregate_size.py
import ast
from pathlib import Path

def test_aggregate_size_limit():
    """
    FF-010: Aggregates should not exceed 7 entities
    """
    aggregates_path = Path("backend/app/contexts")

    for context_dir in aggregates_path.iterdir():
        if not context_dir.is_dir():
            continue

        aggregates_file = context_dir / "domain" / "aggregates.py"
        if not aggregates_file.exists():
            continue

        tree = ast.parse(aggregates_file.read_text())

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Count nested classes (entities)
                entity_count = sum(
                    1 for n in node.body
                    if isinstance(n, ast.ClassDef)
                )

                assert entity_count <= 7, \
                    f"Aggregate {node.name} has {entity_count} entities, exceeds limit of 7"
```

---

## FF-011: Dependency Direction

```yaml
Name: Dependency Direction
Category: Structural
Related ADR: DDD Strategic Design
Rule: Dependencies flow inward (Infrastructure -> Application -> Domain)
Threshold: 0 violations
Test: Static analysis
Tools: dependency-cruiser, pydeps
Frequency: Every commit
Owner: Architecture team
Alert: Fail CI on violation
```

**Implementation:**
```python
# tests/fitness/test_dependency_direction.py
def test_domain_does_not_import_infrastructure():
    """
    FF-011: Domain layer should not import from Infrastructure
    """
    domain_path = Path("backend/app/contexts/*/domain")

    for py_file in domain_path.rglob("*.py"):
        tree = ast.parse(py_file.read_text())

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and "infrastructure" in node.module:
                    assert False, \
                        f"{py_file} imports from Infrastructure: {node.module}"
```

---

## FF-012: No Cyclic Dependencies

```yaml
Name: No Cyclic Dependencies
Category: Structural
Related ADR: None
Rule: No circular dependencies between modules
Threshold: 0 cycles
Test: Dependency graph analysis
Tools: madge, pydeps
Frequency: Every commit
Owner: Development team
Alert: Fail CI on cycles detected
```

**Implementation:**
```bash
# tests/fitness/test_cycles.sh
#!/bin/bash
# FF-012: Check for cyclic dependencies

pydeps backend/app \
    --max-breadth=999 \
    --show-cycles \
    --cluster

if [ $? -ne 0 ]; then
    echo "Cyclic dependencies detected!"
    exit 1
fi
```

---

## FF-013: Repository Interface Compliance

```yaml
Name: Repository Interface Compliance
Category: Structural
Related ADR: DDD Tactical Design
Rule: All repositories implement base interface
Threshold: 100% compliance
Test: Interface inheritance check
Tools: Python ABC, pytest
Frequency: Every commit
Owner: Development team
Alert: Comment on PR with non-compliant repositories
```

**Implementation:**
```python
# tests/fitness/test_repository_interfaces.py
from abc import ABC
from pathlib import Path

class RepositoryInterface(ABC):
    """Base repository interface that all repositories must implement"""

    @abstractmethod
    def find_by_id(self, id):
        pass

    @abstractmethod
    def save(self, entity):
        pass

def test_all_repositories_implement_interface():
    """
    FF-013: All repositories must implement RepositoryInterface
    """
    repo_path = Path("backend/app/contexts/*/infrastructure/repositories.py")

    for repo_file in repo_path:
        tree = ast.parse(repo_file.read_text())

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check if class name ends with "Repository"
                if node.name.endswith("Repository"):
                    # Verify it inherits from RepositoryInterface
                    bases = [base.id for base in node.bases if isinstance(base, ast.Name)]
                    assert "RepositoryInterface" in bases, \
                        f"{repo_file}: {node.name} does not implement RepositoryInterface"
```

---

## FF-014: Value Object Immutability

```yaml
Name: Value Object Immutability
Category: Structural
Related ADR: DDD Tactical Design
Rule: All value objects are immutable (frozen dataclass or attrs frozen)
Threshold: 100% compliance
Test: Class decorator check
Tools: Python AST analysis
Frequency: Every PR
Owner: Architecture team
Alert: Comment on PR with mutable VOs
```

**Implementation:**
```python
# tests/fitness/test_value_object_immutability.py
from pathlib import Path

def test_value_objects_are_immutable():
    """
    FF-014: Value objects must be immutable (frozen=True or @frozen)
    """
    vo_path = Path("backend/app/contexts/*/domain/value_objects.py")

    for vo_file in vo_path:
        tree = ast.parse(vo_file.read_text())

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check for @dataclass(frozen=True) or @frozen
                is_frozen_dataclass = False
                is_frozen_attrs = False

                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Call):
                        if decorator.func.id == "dataclass":
                            for keyword in decorator.keywords:
                                if keyword.arg == "frozen" and keyword.value.value is True:
                                    is_frozen_dataclass = True
                    elif isinstance(decorator, ast.Name):
                        if decorator.id == "frozen":
                            is_frozen_attrs = True

                # Class name ending with "VO" or in value_objects.py
                if node.name.endswith("VO") or "value_objects" in str(vo_file):
                    assert is_frozen_dataclass or is_frozen_attrs, \
                        f"{vo_file}: {node.name} is not immutable"
```

---

## Fitness Function Dashboard

### Weekly Report

```markdown
# Structural Fitness Report - Week of 2026-02-03

| ID | Name | Status | Violations | Trend |
|----|------|--------|------------|-------|
| FF-001 | Bounded Context Independence | ✅ PASS | 0 | Stable |
| FF-009 | Test Coverage | ✅ PASS | 82% | +2% |
| FF-010 | Aggregate Size | ✅ PASS | All <= 7 | Stable |
| FF-011 | Dependency Direction | ✅ PASS | 0 violations | Stable |
| FF-012 | No Cyclic Dependencies | ✅ PASS | 0 cycles | Stable |
| FF-013 | Repository Compliance | ⚠️ WARN | 1 non-compliant | New |
| FF-014 | VO Immutability | ✅ PASS | 100% | Stable |

### Action Items

- FF-013: ExportRepository does not implement base interface
  - File: `backend/app/contexts/export/infrastructure/repositories.py`
  - Action: Add `class ExportRepository(RepositoryInterface):`
  - Owner: Backend team
  - Due: 2026-02-10
```

---

## Automation Script

```python
# scripts/fitness/check_structural.py
#!/usr/bin/env python3
"""
Run all structural fitness functions
"""
import subprocess
import sys

checks = [
    ("FF-001", "pytest tests/fitness/test_bounded_contexts.py"),
    ("FF-009", "pytest --cov=backend/app --cov-fail-under=80"),
    ("FF-010", "pytest tests/fitness/test_aggregate_size.py"),
    ("FF-011", "pytest tests/fitness/test_dependency_direction.py"),
    ("FF-012", "bash tests/fitness/test_cycles.sh"),
    ("FF-013", "pytest tests/fitness/test_repository_interfaces.py"),
    ("FF-014", "pytest tests/fitness/test_value_object_immutability.py"),
]

failed = []

for check_id, command in checks:
    print(f"\n{'='*60}")
    print(f"Running {check_id}: {command}")
    print('='*60)

    result = subprocess.run(command, shell=True)

    if result.returncode != 0:
        failed.append(check_id)

print(f"\n{'='*60}")
print("SUMMARY")
print('='*60)

if failed:
    print(f"❌ Failed checks: {', '.join(failed)}")
    sys.exit(1)
else:
    print("✅ All structural fitness functions passed!")
    sys.exit(0)
```

---

## Related Documentation

- [DDD Tactical Design](../ddd/tactical/) - Aggregate definitions
- [Architecture Decisions](../adr/) - Structural rules
- [Development Environment](../completion/COMPLETION_CHECKLIST.md) - Setup instructions
