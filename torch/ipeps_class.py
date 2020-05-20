import numpy as np
import torch
dtype = torch.float64; device = 'cpu'
torch.autograd.set_detect_anomaly(True)
from torch_trg_quantum import trg_loss

import os
#os.environ['KMP_DUPLICATE_LIB_OK']='True'
from numpy import linalg as LA
# %%%%% Set bond dimension and lattie sites
log2L = 3;  # 2^10 x 2^10 site
chi = 16;  # bond dimension
# RGstep = 2*log2L-2; # remain 4 tensors
whichExample = 1
# %%%%% Initialize Hamiltonian (Heisenberg Model) %%%%%
sX = np.array([[0, 1], [1, 0]]);
sY = np.array([[0, -1j], [1j, 0]])
sZ = np.array([[1, 0], [0, -1]]);
sI = np.eye(2)
Init = {};
if whichExample == 1:
    ##### Example 1: Heisenberg model
    Init = np.load("HeisenInit.npy")  # obtain from iPEPS-TEBD
    EnExact = -0.6694421
    hloc = 0.25 * np.real(np.kron(sX, sX) + np.kron(sY, sY) + np.kron(sZ, sZ))
elif whichExample == 2:
    ##### Example 2: Ising model
    Init = np.load("IsingInit.npy")  # obtain from iPEPS-TEBD
    EnExact = -3.28471
    hmag = 3.1
    hloc = np.real(-np.kron(sX, sX) - hmag * 0.25 * (np.kron(sI, sZ) + np.kron(sZ, sI)))

# hloc = np.array([[-0.5000,  0.0000, -0.0000, -1.0000],
#         [ 0.0000,  0.5000,  0.0000,  0.0000],
#         [-0.0000,  0.0000,  0.5000, -0.0000],
#         [-1.0000,  0.0000, -0.0000, -0.5000]
#  ], dtype=np.float64)
# hloc = hloc /2

uF, sF, vhF = LA.svd(hloc.reshape(2, 2, 2, 2).transpose(0, 2, 1, 3).reshape(4, 4))
chicut = sum(sF > 1e-12)
hl = (uF[:, :chicut] @ np.diag(np.sqrt(abs(sF[:chicut])))).reshape(2, 2, chicut)
hr = ((vhF.T[:, :chicut]) @ np.diag(np.sqrt(abs(sF[:chicut])))).reshape(2, 2, chicut)
chiH = hl.shape[2]

hl = torch.from_numpy(hl)
hr = torch.from_numpy(hr)

Ainit = Init[0]
Binit = Init[1]
Ainit = torch.from_numpy(Ainit)
Ainit.requires_grad_()
Binit = torch.from_numpy(Binit)
Binit.requires_grad_()

class iPEPS(torch.nn.Module):
    def __init__(self, params):
        super(iPEPS, self).__init__()

        self.chi = params[0]
        self.log2L = params[1]
        self.hl = params[2]
        self.hr = params[3]
        # B(phy, up, left, down, right)
        Init = np.load("HeisenInit.npy")
        # Init = np.load("IsingInit.npy")
        Ainit = Init[0]; Binit = Init[1]
        Ainit = torch.from_numpy(Ainit); Ainit.requires_grad_()
        Binit = torch.from_numpy(Binit); Binit.requires_grad_()
        # Ainit = torch.rand(2, 2, 2, 2, 2, dtype=torch.float64, device='cpu')
        # Binit = torch.rand(2, 2, 2, 2, 2, dtype=torch.float64, device='cpu')
        self.A = torch.nn.Parameter(Ainit)
        self.B = torch.nn.Parameter(Binit)

    def forward(self):
        chi,log2L,hl,hr = self.chi, self.log2L, self.hl, self.hr
        A, B = self.A, self.B
        loss = trg_loss(A,B,chi,log2L,hl,hr)
        return loss
params_fix = [chi, log2L, hl, hr]
model = iPEPS(params_fix)
optimizer = torch.optim.LBFGS(model.parameters(), max_iter=10)
# optimizer = torch.optim.Adam(model.parameters(), lr = 0.001)
params = list(model.parameters())
params = list(filter(lambda p: p.requires_grad, params))
nparams = sum([np.prod(p.size()) for p in params])
print('total nubmer of trainable parameters:', nparams)


def closure():
    # print('closure is executed')
    optimizer.zero_grad()
    loss = model.forward()
    loss.backward()
    # print(loss.item(), model.A.grad[0,0,0,0,:])
    return loss

Nepochs = 100
for epoch in range(Nepochs):
    loss = optimizer.step(closure)
    with torch.no_grad():
        # print('torch.no_grad is executed')
        En = model.forward()
        message = ('epoch:{}, ' + 1 * 'En:{:.8f} ').format(epoch, En)
        print(message)