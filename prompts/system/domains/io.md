## IO Rules

- Carefully distinguish between Tool Digital Output (`setToolDigitalOutput`) and General Digital Output (`setGeneralDigitalOutput`). Use exactly the one requested.
- Digital input index defaults to `(0)`.
- Use `getGeneralDigitalInput(0)` unless instruction explicitly specifies a different index.
- When `start_condition` is used but no specific input index is given in the instruction, default to `getGeneralDigitalInput(0)`.
- Only use a different index if explicitly specified, e.g. "digital input 1" means `(1)`.
