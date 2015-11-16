## Assumptions
(read ideas_basic_operations)

```python
>>> from sympy.printing.dot import dotprint
>>> from graphviz import Source
>>> graph = lambda x: Source(dotprint(x))
```

```python
>>> import sympy
>>> from sympy.interactive import printing
>>> printing.init_printing(use_latex='mathjax')
...
>>> from discretizer import coord, momentum_operators, a
>>> from discretizer import substitute_functions
>>> from discretizer import derivate
>>> from discretizer import split_factors
```

## Defining input expression

```python
>>> kx, ky, kz = momentum_operators
>>> Psi = sympy.Function('Psi')(*coord)
>>> A = sympy.Function('A')(*coord)
>>> B = sympy.Symbol('B')
```

# Designing recursive algorithm
We must somehow handle this expression recursively
1. First expand
2. loop over summands to keep them separated.
3. For every summand launch recursive algorithm that discretize it (point 2 above)
short hoppings
4. gather results from summands (after the loop from 2).

```python
>>> from discretizer import discretize_expression
```

### Test1

```python
>>> expr = kx*A*kx*Psi; expr
kₓ⋅A(x, y, z)⋅kₓ⋅Ψ(x, y, z)
```

```python
>>> discretize_expression(expr)
A(-aₓ + x, y, z)⋅Ψ(x, y, z)   A(-aₓ + x, y, z)⋅Ψ(-2⋅aₓ + x, y, z)   A(aₓ + x, 
─────────────────────────── - ─────────────────────────────────── + ──────────
               2                                 2                            
           4⋅aₓ                              4⋅aₓ                             

y, z)⋅Ψ(x, y, z)   A(aₓ + x, y, z)⋅Ψ(2⋅aₓ + x, y, z)
──────────────── - ─────────────────────────────────
    2                                2              
4⋅aₓ                             4⋅aₓ
```

### Test2

```python
>>> expr = kx*ky*Psi; expr
kₓ⋅k_y⋅Ψ(x, y, z)
```

```python
>>> discretize_expression(expr)
  Ψ(-aₓ + x, -a_y + y, z)   Ψ(-aₓ + x, a_y + y, z)   Ψ(aₓ + x, -a_y + y, z)   
- ─────────────────────── + ────────────────────── + ────────────────────── - 
          4⋅aₓ⋅a_y                 4⋅aₓ⋅a_y                 4⋅aₓ⋅a_y          

Ψ(aₓ + x, a_y + y, z)
─────────────────────
       4⋅aₓ⋅a_y
```

### Test3

```python
>>> expr = kx**2*Psi + kx*Psi; expr
                  2           
kₓ⋅Ψ(x, y, z) + kₓ ⋅Ψ(x, y, z)
```

```python
>>> discretize_expression(expr)
ⅈ⋅Ψ(-aₓ + x, y, z)   ⅈ⋅Ψ(aₓ + x, y, z)   Ψ(x, y, z)   Ψ(-2⋅aₓ + x, y, z)   Ψ(2
────────────────── - ───────────────── + ────────── - ────────────────── - ───
       2⋅aₓ                 2⋅aₓ               2                2             
                                           2⋅aₓ             4⋅aₓ              

⋅aₓ + x, y, z)
──────────────
       2      
   4⋅aₓ
```