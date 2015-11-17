import itertools
import sympy
import numpy as np
from math import factorial
from functools import reduce
from operator import mul


# Some globals
momentum_operators = sympy.symbols('k_x k_y k_z', commutative=False)
coord = sympy.symbols('x y z', commutative=False)
wf = sympy.Symbol('Psi')(*coord)

lattice_constants = sympy.symbols('a_x a_y a_z')
a = sympy.Symbol('a')


# **************** Operation on sympy expressions **************************
def substitute_functions(expr, space_dependent=[]):
    """ Substitute space_dependent symbols with function of (x, y, z) """
    symbols = [s for s in expr.atoms(sympy.Symbol) if s.name in space_dependent]
    subs = {s: sympy.Function(s.name)(*coord) for s in symbols}

    return expr.subs(subs)


def derivate(expression, operator):
    """ Calculate derivate of expression for given momentum operator:

    Parameters:
    -----------
    expression : sympy expression
        Valid sympy expression containing functions to to be derivated
    operator : sympy symbol
        Sympy symbol representing momentum operator

    Returns:
    --------
    expression : derivate of input expression
    """
    assert operator in momentum_operators, \
            "Operator '{}' does not belong to [kx, ky, kz].".format(operator)

    if isinstance(expression, (int, float)):
        return 0
    else:
        ind = momentum_operators.index(operator)
        expr1 = expression.subs(coord[ind], coord[ind] + lattice_constants[ind])
        expr2 = expression.subs(coord[ind], coord[ind] - lattice_constants[ind])
        output = (expr1 - expr2) / 2 / lattice_constants[ind]
        return -sympy.I * sympy.expand(output)


def split_factors(expression):
    """ Split symbolic expression for a discretization step.

    Parameters:
    -----------
    expression : sympy expression
        symbolic expression to be split

    Output:
    -------
    lhs : sympy expression
        part of expression standing to the left from operators
        that acts in current discretization step

    operators: sympy expression
        operator that perform discretization in current step

    rhs : sympy expression
        part of expression that is derivated in current step

    """
    assert not isinstance(expression, sympy.Add), 'input expression must not be sympy.Add'
    output = {'rhs': [1], 'operator': [1], 'lhs': [1]}

    if isinstance(expression, sympy.Pow):
        output['operator'].append(expression.args[0])
        output['lhs'].append(sympy.Pow(expression.args[0], expression.args[1]-1))

    elif isinstance(expression, (int, float, sympy.Integer, sympy.Float)):
        output['rhs'].append(expression)

    elif isinstance(expression, (sympy.Symbol, sympy.Function)):
        if expression in momentum_operators:
            output['operator'].append(expression)
        else:
            output['rhs'].append(expression)

    elif isinstance(expression, sympy.Mul):
        iterator = iter(expression.args[::-1])
        for factor in iterator:
            if factor in momentum_operators:
                output['operator'].append(factor)
                break
            elif factor.func == sympy.Pow and factor.args[0] in momentum_operators:
                operator = factor.args[0]
                power = factor.args[1]
                output['operator'].append(operator)
                output['lhs'].append(sympy.Pow(operator, power-1))
                break
            else:
                output['rhs'].append(factor)

        for factor in iterator:
            output['lhs'].append(factor)

    output = tuple(sympy.Mul(*output[key][::-1])
                   for key in ['lhs', 'operator', 'rhs'])
    return output


def discretize_summand(summand):
    """ Discretize one summand. """
    assert not isinstance(summand, sympy.Add), "Input should be one summand."

    def do_stuff(expr):
        """ Derivate expr recursively. """
        expr = sympy.expand(expr)

        if isinstance(expr, sympy.Add):
            return do_stuff(expr.args[-1]) + do_stuff(sympy.Add(*expr.args[:-1]))

        lhs, operator, rhs = split_factors(expr)
        if rhs == 1 and operator != 1:
            return 0
        elif operator == 1:
            return lhs*rhs
        elif lhs == 1:
            return derivate(rhs, operator)
        else:
            return do_stuff(lhs*derivate(rhs, operator))

    return do_stuff(summand)


def discretize_expression(hamiltonian):
    """ Discretize expression.

    Recursive derivation implemented in discretize_summand is applied
    on every summand. Shortening should be applied before return on output.
    """
    assert wf not in hamiltonian.atoms(sympy.Function), \
            "Hamiltonian should not contain {}".format(wf)
    expression = sympy.expand(hamiltonian * wf)

    if expression.func == sympy.Add:
        summands = expression.args
    else:
        summands = [expression]

    output = []
    for summand in summands:
        output.append(discretize_summand(summand))

    return sympy.expand(sympy.Add(*output))


# ****** extracring hoppings ***********
def Psi_to_hopping(Psi):
    offset = []
    for argument in Psi.args:
        temp = sympy.expand(argument)
        if temp in sympy.symbols('x y z', commutative = False):
            offset.append(0)
        elif temp.func == sympy.Add:
            for arg_summands in temp.args:
                if arg_summands.func == sympy.Mul:
                    if len(arg_summands.args) > 2:
                        print('More than two factors in an argument of Psi')
                    if not arg_summands.args[0] == sympy.symbols('a'):
                        offset.append(arg_summands.args[0])
                    else:
                        offset.append(arg_summands.args[1])
                elif arg_summands == a:
                    offset.append(1)
        else:
            print('Argument of \Psi is neither a sum nor a single space variable.')
    return tuple(offset)


# This function will not have the shortening included
def extract_hoppings(expr):
    # this line should be unneccessary in the long run. Now I want to avoid errors due to wrong formats of the input.
    expr = sympy.expand(expr)

    # The output will be stored in a dictionary, with terms for each hopping kind
    # This format is probably not good in the long run
    hoppings = {}

    if expr.func == sympy.Add:
        for summand in expr.args:
            #find a way to make it readable
            if not summand.func == sympy.Function('Psi'):
                for i in range(len(summand.args)):
                    if summand.args[i].func == sympy.Function('Psi'):
                        index = i
                if index < len(summand.args) - 1:
                    print('Psi is not in the very end of the term. Output will be wrong!')

                try:
                    hoppings[Psi_to_hopping(summand.args[-1])] += sympy.Mul(summand.args[:-1])
                except:
                    hoppings[Psi_to_hopping(summand.args[-1])] = sympy.Mul(summand.args[:-1])
            else:
                try:
                    hoppings[Psi_to_hopping(summand)] += 1
                except:
                    hoppings[Psi_to_hopping(summand)] = 1

    else:
        if not expr.func == sympy.Function('Psi'):
            for i in range(len(expr.args)):
                if expr.args[i].func == sympy.Function('Psi'):
                    index = i
            if index < len(expr.args) - 1:
                print('Psi is not in the very end of the term. Output will be wrong!')

            try:
                hoppings[Psi_to_hopping(expr.args[-1])] += sympy.Mul(expr.args[:-1])
            except:
                hoppings[Psi_to_hopping(expr.args[-1])] = sympy.Mul(expr.args[:-1])
        else:
            try:
                hoppings[Psi_to_hopping(expr)] += 1
            except:
                hoppings[Psi_to_hopping(expr)] = 1
    return hoppings
