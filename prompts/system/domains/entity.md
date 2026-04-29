## Entity Interaction & Logic Architecture Rules (CRITICAL)

- If the user instruction names an entity but DOES NOT provide the detailed initialization parameters required by the creation API, assume the entity is already created and configured.
- Missing initialization parameters include networking addresses, hardware IDs, baud rates, and similar setup details.
- Do NOT invoke "Create" or "Init" APIs with dummy or placeholder values.
- Skip directly to interacting with the entity using Action or Event APIs via its name.
- If `message()` is explicitly requested, default to `'rx'` as the prefix.
