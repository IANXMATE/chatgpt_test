from __future__ import annotations

import math
import numpy as np


EULER_GAMMA = 0.577215664901532860606512090082402431


class LinearSieveFunctions:
    """Numerical method-of-steps solution for the classical linear-sieve F,f.

    Let A(s)=sF(s), B(s)=sf(s).  Then
        A'(s)=f(s-1) for s>3,
        B'(s)=F(s-1) for s>2,
    with A(s)=2e^gamma on 1<=s<=3 and B(s)=0 on 1<=s<=2.

    This evaluates the genuine sieve functions dynamically instead of using
    the paper's rounded constants.  It is numerical, not interval certified.
    """

    def __init__(self, step: float = 2e-5, s_max: float = 10.0):
        inv = int(round(1.0 / step))
        if abs(inv * step - 1.0) > 1e-12:
            raise ValueError("linear-sieve step must divide 1")
        self.step = float(step)
        self.inv = inv
        self.s_max = float(s_max)

        self.s = np.arange(1.0, self.s_max + 0.5*self.step, self.step)
        n = len(self.s)
        A = np.zeros(n, dtype=float)
        B = np.zeros(n, dtype=float)

        i3 = self._idx(3.0)
        A[:i3+1] = 2.0 * math.exp(EULER_GAMMA)

        for k in range(2, int(math.ceil(self.s_max))):
            lo = float(k)
            hi = min(float(k+1), self.s_max)
            if hi <= lo:
                continue
            i0, i1 = self._idx(lo), self._idx(hi)
            idx = np.arange(i0, i1+1)
            delayed = idx - self.inv

            # B'(s)=F(s-1), s>2.
            f_delay_for_B = A[delayed] / self.s[delayed]
            incB = 0.5*self.step*(f_delay_for_B[:-1] + f_delay_for_B[1:])
            B[idx[1:]] = B[i0] + np.cumsum(incB)

            # A'(s)=f(s-1), s>3.
            if lo >= 3.0:
                b_delay = B[delayed] / self.s[delayed]
                incA = 0.5*self.step*(b_delay[:-1] + b_delay[1:])
                A[idx[1:]] = A[i0] + np.cumsum(incA)

        self._F = A / self.s
        self._f = B / self.s

    def _idx(self, x: float) -> int:
        return int(round((x - 1.0)/self.step))

    def F(self, x):
        a = np.asarray(x, dtype=float)
        if np.any(a < 1.0) or np.any(a > self.s_max):
            raise ValueError(f"F requested outside [1,{self.s_max}]")
        y = np.interp(a, self.s, self._F)
        return float(y) if y.ndim == 0 else y

    def f(self, x):
        a = np.asarray(x, dtype=float)
        if np.any(a < 0.0) or np.any(a > self.s_max):
            raise ValueError(f"f requested outside [0,{self.s_max}]")
        y = np.zeros_like(a)
        mask = a >= 1.0
        y[mask] = np.interp(a[mask], self.s, self._f)
        return float(y) if y.ndim == 0 else y


class BuchstabFunction:
    """Dynamic Buchstab function on u>=1 by method of steps.

    Set W(u)=u*w(u).  Then W(u)=1 on [1,2] and
        W'(u)=w(u-1)=W(u-1)/(u-1), u>2.

    This removes the artificial u>=3 / 3.16 / 3.5 rejection used by the
    previous random-search prototype.  The paper's Section 5.4 original
    formulas already contain w(argument) before replacing it by constants.
    """

    def __init__(self, step: float = 2e-5, u_max: float = 40.0):
        inv = int(round(1.0 / step))
        if abs(inv * step - 1.0) > 1e-12:
            raise ValueError("Buchstab step must divide 1")
        self.step = float(step)
        self.inv = inv
        self.u_max = float(u_max)

        self.u = np.arange(1.0, self.u_max + 0.5*self.step, self.step)
        W = np.zeros_like(self.u)
        i2 = self._idx(2.0)
        W[:i2+1] = 1.0

        for k in range(2, int(math.ceil(self.u_max))):
            lo = float(k)
            hi = min(float(k+1), self.u_max)
            if hi <= lo:
                continue
            i0, i1 = self._idx(lo), self._idx(hi)
            idx = np.arange(i0, i1+1)
            delayed = idx - self.inv
            deriv = W[delayed] / self.u[delayed]
            inc = 0.5*self.step*(deriv[:-1] + deriv[1:])
            W[idx[1:]] = W[i0] + np.cumsum(inc)

        self._w = W / self.u

    def _idx(self, x: float) -> int:
        return int(round((x - 1.0)/self.step))

    def w(self, x):
        a = np.asarray(x, dtype=float)
        if np.any(a < 1.0) or np.any(a > self.u_max):
            lo = float(np.min(a))
            hi = float(np.max(a))
            raise ValueError(
                f"Buchstab w requested outside [1,{self.u_max}], got [{lo},{hi}]"
            )
        y = np.interp(a, self.u, self._w)
        return float(y) if y.ndim == 0 else y
