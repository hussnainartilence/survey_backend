import astroid
from pylint.interfaces import IAstroidChecker
from pylint.checkers import BaseChecker
from pylint.checkers.utils import only_required_for_messages


def is_get_session_call(call_node):
    return (
        call_node.func
        and isinstance(call_node.func, astroid.Attribute)
        and call_node.func.attrname == "get_session"
    )


class AsyncSessionChecker(BaseChecker):
    __implements__ = IAstroidChecker

    name = "async_session_checker"
    priority = -1
    msgs = {
        "W9901": (
            "AsyncSession should be used with async with statement",
            "async-session-without-async-with",
            "AsyncSession should be used with async with statement",
        ),
    }

    @only_required_for_messages("async-session-without-async-with")
    def visit_assign(self, node):
        if (
            node.targets
            and len(node.targets) == 1
            and isinstance(node.targets[0], astroid.AssignName)
            and node.targets[0].name == "_session"
            and node.value
        ):
            if isinstance(node.value, astroid.Call) and is_get_session_call(
                node.value
            ):
                self.add_message("async-session-without-async-with", node=node)


def register(linter):
    linter.register_checker(AsyncSessionChecker(linter))
