import logging
from enum import Enum

from runtools.runcore import util
from runtools.runcore.util import convert_if_number


class Fields(Enum):
    EVENT = 'event'
    OPERATION = 'operation'
    TASK = 'task'
    TIMESTAMP = 'timestamp'
    COMPLETED = 'completed'
    INCREMENT = 'increment'
    TOTAL = 'total'
    UNIT = 'unit'
    RESULT = 'result'


DEFAULT_PATTERN = ''


def field_conversion(parsed):
    converted = {
        Fields.EVENT: parsed.get(Fields.EVENT.value),
        Fields.TASK: parsed.get(Fields.TASK.value),
        Fields.TIMESTAMP: util.parse_datetime(parsed.get(Fields.TIMESTAMP.value)),
        Fields.OPERATION: parsed.get(Fields.OPERATION.value),
        Fields.COMPLETED: convert_if_number(parsed.get(Fields.COMPLETED.value)),
        Fields.INCREMENT: convert_if_number(parsed.get(Fields.INCREMENT.value)),
        Fields.TOTAL: convert_if_number(parsed.get(Fields.TOTAL.value)),
        Fields.UNIT: parsed.get(Fields.UNIT.value),
        Fields.RESULT: parsed.get(Fields.RESULT.value),
    }

    return {key: value for key, value in converted.items() if value is not None}


class OutputToTask:

    def __init__(self, task_tracker, *, parsers, conversion=field_conversion):
        self.tracker = task_tracker
        self.parsers = list(parsers)
        self.conversion = conversion

    def __call__(self, output, is_error=False):
        self.new_output(output, is_error)

    def create_logging_handler(self):
        """
        Creates and returns a logging.Handler instance that forwards log records
        to this OutputToTask instance.
        """
        class InternalHandler(logging.Handler):
            def __init__(self, outer_instance):
                super().__init__()
                self.outer_instance = outer_instance

            def emit(self, record):
                output = self.format(record)  # Convert log record to a string
                is_error = record.levelno >= logging.ERROR
                self.outer_instance(output, is_error)

        return InternalHandler(self)

    def new_output(self, output, is_error=False):
        parsed = {}
        for parser in self.parsers:
            if parsed_kv := parser(output):
                parsed.update(parsed_kv)

        if not parsed:
            return

        kv = self.conversion(parsed)
        if not kv:
            return

        self._update_task(kv)

    def _update_task(self, fields):
        task = fields.get(Fields.TASK)
        prev_task = self.tracker.subtasks[-1] if self.tracker.subtasks else None
        is_finished = False
        if task:
            current_task = self.tracker.subtask(task, timestamp=fields.get(Fields.TIMESTAMP))
            if prev_task == current_task:
                is_finished = True
        else:
            if prev_task and not prev_task.is_finished:
                current_task = prev_task
            else:
                current_task = self.tracker

        is_op = self._update_operation(current_task, fields)
        if (event := fields.get(Fields.EVENT)) and not is_op:
            current_task.event(event, timestamp=fields.get(Fields.TIMESTAMP))

        result = fields.get(Fields.RESULT)
        if result or is_finished:
            current_task.finished(fields.get(Fields.RESULT), timestamp=fields.get(Fields.TIMESTAMP))

    @staticmethod
    def _update_operation(task, fields):
        op_name = fields.get(Fields.OPERATION) or fields.get(Fields.EVENT)
        ts = fields.get(Fields.TIMESTAMP)
        completed = fields.get(Fields.COMPLETED)
        increment = fields.get(Fields.INCREMENT)
        total = fields.get(Fields.TOTAL)
        unit = fields.get(Fields.UNIT)

        if not completed and not increment and not total and not unit:
            return False

        op = task.operation(op_name, timestamp=ts)
        op.update(completed or increment, total, unit, increment=increment is not None, timestamp=ts)
        return True
