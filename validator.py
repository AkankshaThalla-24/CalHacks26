def validate_gloss_output(steps):
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
            if not step.get("id"):
                errors.append(f"Step {i}: sign step missing id")
        elif step_type == "fingerspell":
            if not step.get("text"):
                errors.append(f"Step {i}: fingerspell step missing text")
        else:
            errors.append(f"Step {i}: unknown type '{step_type}'")
    return len(errors) == 0, errors
