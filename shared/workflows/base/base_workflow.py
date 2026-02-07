from abc import ABC

from pydantic import ValidationError


class Workflow(ABC):
    """Base workflow that validates payloads and runs configured operations in order."""

    operations = ()
    name = ""

    def __init__(self, payload: object):
        """Create a workflow with name-keyed payloads."""
        self.payloads = self._build_payloads(payload)
        self.outputs = {}

    def _build_payloads(self, payload):
        """Build operation payloads from a name-keyed mapping."""
        if isinstance(payload, dict):
            operation_mapping = {
                (operation.name or operation.__name__): operation
                for operation in self.operations
            }

            unknown = set(payload) - set(operation_mapping)

            if unknown:
                unknown_list = ", ".join(sorted(unknown))
                raise ValueError(f"Unknown payload keys: {unknown_list}.")

            payload_models = {}

            first_operation = self.operations[0] if self.operations else None

            if first_operation is None:
                raise ValueError("Workflow has no operations configured.")

            first_name = first_operation.name or first_operation.__name__

            if first_name not in payload:
                raise ValueError(f"Missing payload for operation: {first_name}.")

            for operation_name, operation in operation_mapping.items():
                if operation_name not in payload:
                    continue
                payload_models[operation] = self._validate_payload(
                    operation, payload[operation_name]
                )

            return payload_models

        raise ValueError("Workflow payloads must be a mapping keyed by operation name.")

    def _validate_payload(self, operation, payload):
        """Validate and parse payload for an operation using its Pydantic model."""
        model = operation.payload_model

        if isinstance(payload, model):
            return payload
        try:
            return model.model_validate(payload)
        except ValidationError as exc:
            raise ValueError(
                f"Invalid payload for {operation.__name__}: {exc}"
            ) from exc

    def _run_operations(self, *args, **kwargs):
        """Run operations sequentially and store outputs by operation name."""
        operation_output = None

        for index, operation in enumerate(self.operations):
            if operation in self.payloads:
                payload = self.payloads[operation]
            elif index == 0:  # If first operation doesn't have payload then raise error
                raise ValueError(
                    f"Missing payload for operation: {operation.__name__}."
                )
            else:  # Use output from previous operation as the payload if payload is not explicitly given.
                previous_operation_output = operation_output
                payload = self._validate_payload(operation, previous_operation_output)

            operation_instance = operation(payload)
            operation_instance.outputs = self.outputs

            operation_output = operation_instance.execute(*args, **kwargs)
            operation_name = operation.name or operation.__name__

            self.outputs[operation_name] = operation_output

        return operation_output

    def execute(self, *args, **kwargs):
        """Execute the workflow and return the last operation result."""
        if not self.operations:
            raise ValueError("Workflow has no operations configured.")

        self.validate_payloads()

        return self._run_operations(*args, **kwargs)

    def validate_payloads(self):
        """Validate that all provided payloads map to known operations."""
        for operation in self.payloads:
            if operation not in self.operations:
                raise ValueError(f"Unknown operation payload: {operation.__name__}.")
