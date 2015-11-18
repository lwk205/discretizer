import itertools
import sympy
import numpy as np
from math import factorial
from collections import defaultdict


# ************************** Some globals *********************************
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

    Examples:
    ---------
    >>> A = sympy.Symbol('A')
    >>> x = discretizer.coord[0]
    >>> kx = discretizer.momentum_operators[0]
    >>> derivate(A(x), kx)
    -I*(-A(-a_x + x)/(2*a_x) + A(a_x + x)/(2*a_x))
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
    """ Split symbolic `expression` for a discretization step.

    Parameters:
    -----------
    expression : sympy expression
        symbolic expression to be split that represents single summand

    Output:
    -------
    lhs : sympy expression
        part of expression standing to the left from operators
        that acts in current discretization step

    operators: sympy expression
        operator that perform discretization in current step

    rhs : sympy expression
        part of expression that is derivated in current step

    Raises:
    -------
    AssertionError
        if input `expression` is of type ``sympy.Add``
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

    outputs = []
    for summand in summands:
        outputs.append(discretize_summand(summand))

    outputs = [extract_hoppings(summand) for summand in outputs]
    outputs = [shortening(summand) for summand in outputs]

    output = defaultdict(int)
    for summand in outputs:
        for k, v in summand.items():
                output[k] += v

    return dict(output)



# ****** extracring hoppings ***********
def read_hopping_from_wf(inp_psi):
    """ Read hopping from an input wave function.

    Parameters:
    -----------
    inpt_psi : ``~discretizer.algorithms.wf`` like object
        example could be: wf(x + ax, y + 2 * ay, z + 3 * nz)

    Returns:
    --------
    offset: tuple
        offset of a wave function in respect to (x, y, z)

    Examples:
    ---------
    >>> import discretizer
    >>> wf = discretizer.algorithms.wf
    >>> ax, ay, az = discretizer.algorithms.lattice_constants
    >>> x, y, z = discretizer.algorithms.coord
    >>> subs = {x: x+ax, y: y + 2 * ay, z: z + 3 * az}
    >>> expr = wf.subs(subs)
    >>> read_hopping_from_wf(expr)
    (1, 2, 3)
    """
    assert inp_psi.func == wf.func, 'Input should be correct wf used in module.'
    offset = []
    for argument in inp_psi.args:
        temp = sympy.expand(argument)
        if temp in sympy.symbols('x y z', commutative = False):
            offset.append(0)
        elif temp.func == sympy.Add:
            for arg_summands in temp.args:
                if arg_summands.func == sympy.Mul:
                    if len(arg_summands.args) > 2:
                        print('More than two factors in an argument of inp_psi')
                    if not arg_summands.args[0] in sympy.symbols('a_x a_y a_z'):
                        offset.append(arg_summands.args[0])
                    else:
                        offset.append(arg_summands.args[1])
                elif arg_summands in sympy.symbols('a_x a_y a_z'):
                    offset.append(1)
        else:
            print('Argument of \inp_psi is neither a sum nor a single space variable.')
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
            if not summand.func == wf.func:
                for i in range(len(summand.args)):
                    if summand.args[i].func == wf.func:
                        index = i
                if index < len(summand.args) - 1:
                    print('Psi is not in the very end of the term. Output will be wrong!')

                try:
                    hoppings[read_hopping_from_wf(summand.args[-1])] += sympy.Mul(*summand.args[:-1])
                except:
                    hoppings[read_hopping_from_wf(summand.args[-1])] = sympy.Mul(*summand.args[:-1])
            else:
                try:
                    hoppings[read_hopping_from_wf(summand)] += 1
                except:
                    hoppings[read_hopping_from_wf(summand)] = 1

    else:
        if not expr.func == wf.func:
            for i in range(len(expr.args)):
                if expr.args[i].func == wf.func:
                    index = i
            if index < len(expr.args) - 1:
                print('Psi is not in the very end of the term. Output will be wrong!')

            try:
                hoppings[read_hopping_from_wf(expr.args[-1])] += sympy.Mul(*expr.args[:-1])
            except:
                hoppings[read_hopping_from_wf(expr.args[-1])] = sympy.Mul(*expr.args[:-1])
        else:
            try:
                hoppings[read_hopping_from_wf(expr)] += 1
            except:
                hoppings[read_hopping_from_wf(expr)] = 1
    return hoppings


def shortening(hoppings):
    # make a list of all hopping kinds we have to consider during the shortening
    hops_kinds = np.array(list(hoppings))
    # find the longest hopping range in each direction
    longest_ranges = [np.max(hops_kinds[:,i]) for i in range(len(hops_kinds[0,:]))]
    # define an array in which we are going to store by which factor we
    # can shorten the hoppings in each direction
    shortening_factors = np.ones_like(longest_ranges)
    # Loop over the direction and each potential shortening factor.
    # Inside the loop test whether the hopping distances are actually
    # multiples of the potential shortening factor.
    for dim in np.arange(len(longest_ranges)):
        for factor in np.arange(longest_ranges[dim])+1:
            modulos = np.mod(hops_kinds[:, dim], factor)
            if np.sum(modulos) < 0.1:
                shortening_factors[dim] = factor
    # Apply the shortening factors on the hopping.
    short_hopping = {}
    for hopping_kind in hoppings.keys():
        short_hopping_kind = tuple(np.array(hopping_kind) / shortening_factors)

        for i in short_hopping_kind:
            if isinstance(i, float):
                assert i.is_integer()
        short_hopping_kind = tuple(int(i) for i in short_hopping_kind)

        short_hopping[short_hopping_kind] = hoppings[hopping_kind]
        for lat_const, factor in zip(lattice_constants, shortening_factors):
            factor = int(factor)
            subs = {lat_const: lat_const/factor}
            short_hopping[short_hopping_kind] = short_hopping[short_hopping_kind].subs(subs)
    return short_hopping
