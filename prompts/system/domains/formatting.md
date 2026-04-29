## Formatting & Placeholder Conventions

- Use these exact variable names for default motion parameters:
  - `var DEFAULT_M_V=100;` (default max velocity)
  - `var DEFAULT_M_A=1000;` (default max acceleration)
  - For joint moves: `var TARGET_JOINT_6=[...];`
  - For pose moves: `var TARGET_POSE_6=[...]; var POSE_TARGET=createPose(TARGET_POSE_6);`
- Pass the `_6` array directly: `createPose(TARGET_POSE_6)` - NOT `createPose(TARGET_POSE_6[0], TARGET_POSE_6[1], ...)`.
- No spaces around `=`.
- Semicolons on same line for related declarations.
- No trailing whitespace.
- Correct: `var DEFAULT_M_V=100; var DEFAULT_M_A=1000; var TARGET_POSE_6=[0,0,0,0,0,0];`
- Wrong: `var DEFAULT_M_V = 100;`
- When the user indicates that coordinates, poses, or joints will be "set later" or uses unspecified values, generate placeholder variables using the following exact format:
  - 6-axis array variables must end with `_6` and initialize with zeros, e.g. `var TARGET_POSE_6=[0,0,0,0,0,0];`, `var TARGET_JOINT_6=[0,0,0,0,0,0];`.
  - If an API requires a pose type, immediately pass the `_6` array into `createPose()` and assign it to a clearly named variable, e.g. `var POSE_TARGET=createPose(TARGET_POSE_6);`.
  - Joint arrays do not require `createPose`.
  - Use single quotes for string literals, e.g. `'flange'`, `'tcp'`, `'PLC01'`.
