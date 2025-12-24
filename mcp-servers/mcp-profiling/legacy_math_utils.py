def bad_calc(n):
    if n<1: return n
    return bad_calc(n-1) + bad_calc(n-2)
