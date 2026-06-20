from clip_library import CLIP_LIBRARY_SET

def validate_gloss_output(steps, clip_library=None):
    valid_ids = set(clip_library) if clip_library is not None else CLIP_LIBRARY_SET
    errors = []
    if not isinstance(steps, list):
        return False, ["Output is not a JSON array"]
    if len(steps) == 0:
        errors.append("Empty output")
    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            errors.append(f"Step {i}: not an object")
            continue
        step_type = step.get("type")
        if step_type == "sign":
            sign_id = step.get("id")
            if sign_id not in valid_ids:
                errors.append(f"Step {i}: invalid sign id '{sign_id}' not in clip library")
        elif step_type == "fingerspell":
            if not step.get("text"):
                errors.append(f"Step {i}: fingerspell step missing text")
        else:
            errors.append(f"Step {i}: unknown type '{step_type}'")
    return len(errors) == 0, errors
