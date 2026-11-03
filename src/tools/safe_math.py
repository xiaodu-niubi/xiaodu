"""Bounded numeric expression evaluator; no Python eval or attribute access."""
import ast
import math
import operator

FUNCTIONS = {name: getattr(math, name) for name in ('sqrt', 'sin', 'cos', 'tan', 'log', 'log10', 'log2', 'ceil', 'floor')}
FUNCTIONS.update(abs=abs, round=round)
CONSTANTS = {'pi': math.pi, 'e': math.e}
OPERATORS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
             ast.Div: operator.truediv, ast.Mod: operator.mod}


def bounded(value):
    if not isinstance(value, (int, float)) or not math.isfinite(value) or abs(value) > 1e100:
        raise ValueError('数值过大或无效。')
    return value


def power(base, exponent):
    if abs(exponent) > 1000:
        raise ValueError('指数不能超过 1000。')
    return bounded(base ** exponent)


def calculate(expression):
    if len(expression) > 1000:
        raise ValueError('表达式过长。')
    tree = ast.parse(expression, mode='eval')
    if sum(1 for _ in ast.walk(tree)) > 200:
        raise ValueError('表达式过于复杂。')
    def visit(node):
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return bounded(node.value)
        if isinstance(node, ast.Name) and node.id in CONSTANTS:
            return CONSTANTS[node.id]
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            return bounded(visit(node.operand) * (-1 if isinstance(node.op, ast.USub) else 1))
        if isinstance(node, ast.BinOp):
            left, right = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Pow): return power(left, right)
            if type(node.op) in OPERATORS: return bounded(OPERATORS[type(node.op)](left, right))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and not node.keywords:
            args = [visit(arg) for arg in node.args]
            if node.func.id == 'pow' and len(args) == 2: return power(*args)
            if node.func.id in FUNCTIONS and len(args) <= 2: return bounded(FUNCTIONS[node.func.id](*args))
        raise ValueError('只支持数值、数学函数与算术运算。')
    return visit(tree.body)
