from gpytorch.mlls import ExactMarginalLogLikelihood
from .gp_regression_mixed import NewMixedSingleTaskGP
import torch
from .hb import HistoryBoard
from gpytorch.constraints import GreaterThan


print_freq = 20

from typing import List

def fit_model_partial(
        hb : HistoryBoard = None,
        opt_indices : list = None,
        init_ind : int = None,
        prev_indices : int = None,
        params : dict = {},
        fit_iter : int = 20,
        device = None,
    ):
    # 获取设备（如果没有提供，自动检测：优先GPU，找不到则CPU）
    if device is None:
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    surrogate_model, train_X = get_data_and_model_partial(hb, opt_indices, init_ind, prev_indices, device=device)
    if params:
        surrogate_model.load_state_dict(params)
    # Use the adam optimizer
    optimizer = torch.optim.Adam([
    {'params': surrogate_model.parameters()},  # Includes GaussianLikelihood parameters
    ], lr=0.1) # 0.1

    mll = ExactMarginalLogLikelihood(surrogate_model.likelihood, surrogate_model).to(device)
    for i in range(fit_iter):
        optimizer.zero_grad()
        output = surrogate_model(train_X)
        loss = -mll(output, surrogate_model.train_targets)
        loss.backward()
        optimizer.step()
    return surrogate_model

def get_data_and_model_partial(hb, opt_indices, init_ind, prev_indices, device=None):
    # 获取设备（如果没有提供，自动检测：优先GPU，找不到则CPU）
    if device is None:
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    train_Y = torch.cat([hb.eval_Y[prev_indices].view(len(prev_indices),1), hb.eval_Y[init_ind:]], dim=0)
    train_Y = train_Y.to(dtype=torch.double)
    train_X_center = hb.eval_X_reduced[prev_indices][:,opt_indices].view(len(prev_indices),-1).to(device)
    train_X = hb.eval_X_reduced[init_ind:, opt_indices].to(device)
    train_X = torch.cat([train_X_center, train_X], dim=0)
    train_X = train_X.to(dtype=torch.double)
    _, L = train_X.shape

    surrogate_model = NewMixedSingleTaskGP(train_X=train_X, train_Y=train_Y, cat_dims=list(range(L)), device=device).to(device)
    surrogate_model.likelihood.noise_covar.register_constraint("raw_noise", GreaterThan(1e-5))
    surrogate_model.mean_module.initialize(constant=-1.0)
    surrogate_model.train()
    return surrogate_model, train_X
