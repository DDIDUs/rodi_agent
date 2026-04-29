## Control Flow and Conditional Execution Rules

- Use `for` loops with a specific `COUNT` when executing sequences multiple times.
- Do not use `while(true)` unless an infinite loop is explicitly requested.
- For a fixed time delay in milliseconds, use `sleep(ms)`, not `wait(ms)`.
- Use `wait(condition)` only when the instruction requires waiting until a condition becomes true.
- If the request mentions a time delay, pause, sleep, or waiting for a fixed duration, verify the delay API with `search_rag` before generating final code unless it was already verified in the current turn.
- When calculating pose offsets in a loop, start your index appropriately (e.g. `i=0` to include the base pose) to ensure correct target generation.
- Preserve the exact conditional logic from the instruction.
- Do not unconditionally execute commands that should be guarded by sensor inputs, e.g. `getGeneralDigitalInput(0) == 1`.
- Determine the execution paradigm:
  - Synchronous: e.g. "Do X", "Move to Y". Use standard sequential APIs.
  - Event-driven or conditional: e.g. "When X connects", "On data received", "Only when start condition is satisfied".
- Before defaulting to Event Listener/Wait APIs, check if the desired action API natively accepts a condition like `start_condition` in `opts`.
- If a target action API supports a native conditional option, use the action API directly with that option.
- Only use Event Listeners or WaitNodes if no such parameter exists in the target action API.
- Do not create WaitNodes or Event Listeners if the target Action API already supports conditional execution natively.
