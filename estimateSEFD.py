#!/usr/bin/env python

import numpy as np

# Script for antenna SEFD estimation based on correlator report ratio_snr tables.
# Based off Lucia's sefd_estimation_lucia.m MATLAB function.
# Can be either imported into another Python script and run using extracted correlator report arrays, or arrays below can be manually edited and the script run from the command line.
# Script maintained by Tiege.

# Scheduled SEFDs
X0 = np.array([5000, 4500, 5000, 8000, 1400])

# Table from correlator report
# X n_X S n_S
corrtab=np.array([[0.90,182,0.75,173],
                 [0.77, 209, 0.93, 210],
                 [0.99, 140, 0.92, 133],
                 [1.03, 401, 1.05, 389],
                 [1.07, 229, 0.91, 228],
                 [1.67, 468, 1.03, 468],
                 [1.40, 224, 0.98, 223],
                 [1.18, 290, 1.11, 290],
                 [1.17, 460, 1.19, 461],
                 [1.56, 184, 1.24, 184]])

# Baseline pairs corresponding to each line of corrtable                 
basnum = np.array([[0, 4],
                   [1, 4],
                   [3, 4],
                   [2, 4],
                   [0, 1],
                   [0, 3],
                   [0, 2],
                   [1, 3],
                   [1, 2],
                   [2, 3]])

def inv(m):
    a, b = m.shape
    if a != b:
        raise ValueError("Only square matrices are invertible.")
    i = np.eye(a, a)
    return np.linalg.lstsq(m, i, rcond=None)[0]
    ## function written by Procope on Stack Overflow. 
    ## This inverts matrices even if they are singular by using the linalg.lstsq method.

def main(X0, corrtab, basnum):
    # Make sure any baselines with r_snr = 0  get removed
    valid_mask = np.where(corrtab[:,1] != 0)
    corrtab = corrtab[valid_mask]
    basnum = basnum[valid_mask]
    # Check there are more than 3 stations
    if len(corrtab) < 3:
        print('Need at least 3 stations to estimate SEFD.')
        X = ['NULL']
        return X
    # Determine observables
    L =[]
    for i in range(0,len(basnum)):
        const = (np.sqrt(X0[basnum[i][0]]*X0[basnum[i][1]]))/(corrtab[i][0])
        L.append(const)
    L = np.asarray(L)  

    # Approximate observables
    L0 = []
    for i in range(0,len(basnum)):
        const = (np.sqrt(X0[basnum[i][0]]*X0[basnum[i][1]]))
        L0.append(const)
    L0 = np.asarray(L0)  

    # reduced observation vector
    l = np.transpose((L - L0))

    # Design Matrix
    A = np.zeros([len(l),len(X0)])

    for i in range(0, len(basnum)):
        A[i][basnum[i, 0]] = 0.5*(X0[basnum[i, 0]]*X0[basnum[i, 1]])**(-0.5)*X0[basnum[i, 1]]
        A[i][basnum[i, 1]] = 0.5*(X0[basnum[i, 0]]*X0[basnum[i, 1]])**(-0.5)*X0[basnum[i, 0]]
                    
    # Weight Matrix
    P = np.diag(corrtab[:,1])

    A_T = np.transpose(A)
    N = np.matmul(A_T, np.matmul(P,A))
    x = np.matmul(np.matmul(inv(N), A_T), np.matmul(P, l))     

    X = X0+x
    print(X)
    return X
    
    
if __name__ == '__main__':
    main(X0, corrtab, basnum)

