reduce .[] as $item (
  {
    "summary": {"passed":0, "failed": 0, "total": 0, "collected": 0, "error":0 },
    "duration": 0,
    "tests": []
  };
  {
    "summary": {
      "passed": (.summary.passed + $item.summary.passed),
      "failed": (.summary.failed + $item.summary.failed),
      "total": (.summary.total + $item.summary.total),
      "collected": (.summary.collected + $item.summary.collected),
      "error": (.summary.error + $item.summary.error)
    },
    "duration": (.duration + $item.duration),
    "tests": (.tests + $item.tests)
  }
)