## Motion Semantics & Parameter Rules (CRITICAL)

- **"based on TCP" ALWAYS means motion reference frame, NOT socket communication**:
  - When user says "based on TCP" for motion commands, use `'tcp'` as the frame parameter.
  - "based on TCP" does NOT mean create a socket connection.
  - This is a MOTION FRAME specification, not networking.
- If the description indicates a default value (e.g. `100 max velocity`, `true`), treat that initial token as the default value to initialize your variable with.
- If an API requires a pose type (`'flange'` vs `'tcp'`) but the user instruction does NOT specify which one to use, **ALWAYS default to `'flange'`**.
- When passing standard arguments and an `opts` object, the `opts` object MUST be the final argument (e.g. `moveLinear('flange', POSE, 100, 100, {async_mode: true})`). Do not place standard parameters inside `opts`.
- All motion commands except joint moves, when specifying motion parameters, must explicitly include velocity and acceleration parameters.
- If the API signature and task context suggest velocity and acceleration are needed (e.g. `moveCircle`, `moveArc`), include them explicitly.
- For `createDirection`, pass exactly three positional numeric arguments (`x`, `y`, `z`), not an object.
- When waiting for asynchronous motions to end, always use the explicit `waitForMoveEnd(COMMAND_ID)` API, not undocumented wait functions.
