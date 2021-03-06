import numpy as np
import math

#TOP DOWN


def bit_reversal():
    pass


def fft(x, eps=1e-8):
    e = complex(eps, eps)
    N = len(x)
    M = math.floor(math.log2(N))
    if (N-1) >> M == 1:
        x1 = np.zeros(1 << (M+1), dtype=np.complex)
        x1[0:N] = x
        x = x1
    y1 = raw_fft(x)
    return y1[:N]


def w(k, N):
    re = math.cos(2 * math.pi * k / N)
    im = - math.sin(2 * math.pi * k / N)
    return complex(re, im)


def raw_fft(x):
    '''
    N should be 2 ** M
    :param x:
    :return:
    '''
    N = len(x)
    M = math.floor(math.log2(N))
    left_list = []
    right_list = []
    for i in range(N):
        if not i & 1:
            left_list.append(i)
        else:
            right_list.append(i)
    if M == 1:
        y1 = x[left_list] + w(0, N) * x[right_list]
        y2 = x[left_list] - w(0, N) * x[right_list]
        return np.array([y1, y2]).squeeze()
    else:
        x1 = raw_fft(x[left_list])
        x2 = raw_fft(x[right_list])
        assert len(x1) == len(x2)
        y1 = np.zeros(1 << (M - 1), dtype=np.complex)
        y2 = y1.copy()
        for i in range(1 << (M - 1)):
            y1[i] = x1[i] + w(i, N) * x2[i]
            y2[i] = x1[i] - w(i, N) * x2[i]
        return np.hstack([y1, y2])


def ifft(x):
    x1 = np.conjugate(x)
    y = fft(x1)
    return y / len(x)


if __name__ == '__main__':
    np.random.seed(5)
    a = np.random.rand(128)
    b = np.fft.fft(a)
    c = fft(a)
    print(a)
    print(ifft(c))
    print(np.real(ifft(c)) - a)
    print(b)
    print(c)
    print(b - c)
