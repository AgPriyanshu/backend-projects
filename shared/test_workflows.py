from rest_framework.test import APITestCase

from shared.workflows.base import Operation, Workflow
from shared.workflows.schemas import StrictPayload


class AddPayload(StrictPayload):
    value: int


class MultiplyPayload(StrictPayload):
    value: int
    factor: int


class Add(Operation[AddPayload, int]):
    name = "add"

    def execute(self, *args, **kwargs) -> int:
        return self.payload.value + 1


class Multiply(Operation[MultiplyPayload, int]):
    name = "multiply"

    def execute(self, *args, **kwargs) -> int:
        return self.payload.value * self.payload.factor


class AddMultiplyWorkflow(Workflow):
    operations = (Add, Multiply)


class TestWorkflowExecution(APITestCase):
    def test_simple_workflow(self):
        payloads = {
            "add": {"value": 1},
            "multiply": {"value": 2, "factor": 3},
        }
        workflow = AddMultiplyWorkflow(payloads)
        result = workflow.execute()
        self.assertEqual(result, 6)
        self.assertEqual(workflow.outputs["add"], 2)
        self.assertEqual(workflow.outputs["multiply"], 6)
