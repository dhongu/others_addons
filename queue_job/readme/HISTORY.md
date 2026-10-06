## 19.0.2.0.2

- \[FIX\] Job form: the result is shown on the full width of the
  Results tab instead of a narrow column.

## Next

- \[ADD\] Run jobrunner as a worker process instead of a thread in the
  main process (when running with --workers \> 0)
- \[REF\] `@job` and `@related_action` deprecated, any method can be
  delayed, and configured using `queue.job.function` records
- \[MIGRATION\] from 13.0 branched at rev. e24ff4b
