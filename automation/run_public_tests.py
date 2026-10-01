"""Run the broad unit-test surface that is valid in the operations-empty export."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from typing import Iterable


AUTOMATION_ROOT = Path(__file__).resolve().parent
MINIMUM_TEST_COUNT = 300
EXCLUDED_MODULES = {
    # These assert that private production workflows, production UI artifacts,
    # or their architecture-registry entrypoints exist. Their absence is
    # enforced by validate_public_repository.py.
    "test_multi_shop_architecture",
    "test_system_architecture_registry",
    "test_ui_v2_native",
}


def flatten(suite: unittest.TestSuite) -> Iterable[unittest.TestCase]:
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item


def main() -> int:
    sys.path.insert(0, str(AUTOMATION_ROOT))
    discovered = unittest.defaultTestLoader.discover(
        start_dir=str(AUTOMATION_ROOT / "tests"),
        pattern="test_*.py",
        top_level_dir=str(AUTOMATION_ROOT / "tests"),
    )
    selected = unittest.TestSuite()
    excluded = 0
    for test in flatten(discovered):
        module = test.id().split(".", 1)[0]
        if module in EXCLUDED_MODULES:
            excluded += 1
        else:
            selected.addTest(test)

    selected_count = selected.countTestCases()
    if selected_count < MINIMUM_TEST_COUNT:
        print(
            json.dumps(
                {
                    "status": "FAIL",
                    "reason": "PUBLIC_TEST_COUNT_BELOW_MINIMUM",
                    "selected": selected_count,
                    "minimum": MINIMUM_TEST_COUNT,
                },
                indent=2,
            )
        )
        return 1

    result = unittest.TextTestRunner(verbosity=2).run(selected)
    summary = {
        "status": "PASS" if result.wasSuccessful() else "FAIL",
        "selected": selected_count,
        "excludedOperationsDependent": excluded,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
