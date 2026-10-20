"""Temporal pooling over encoder hidden states."""

from __future__ import annotations

import torch
import torch.nn as nn


def hidden_state_attention_mask(
    encoder: torch.nn.Module,
    hidden_states: torch.Tensor,
    attention_mask: torch.Tensor | None,
) -> torch.Tensor | None:
    """Project sample-level padding masks to encoder sequence length when needed."""
    if attention_mask is None:
        return None
    if attention_mask.shape[-1] == hidden_states.shape[1]:
        return attention_mask
    if not hasattr(encoder, "_get_feat_extract_output_lengths"):
        return None
    input_lengths = attention_mask.long().sum(dim=-1)
    output_lengths = encoder._get_feat_extract_output_lengths(input_lengths)
    max_length = hidden_states.shape[1]
    positions = torch.arange(max_length, device=hidden_states.device).unsqueeze(0)
    return (positions < output_lengths.unsqueeze(1)).to(dtype=hidden_states.dtype)


def masked_mean_pool(
    hidden_states: torch.Tensor,
    attention_mask: torch.Tensor | None = None,
) -> torch.Tensor:
    """Mean-pool over time excluding padded positions."""
    if hidden_states.ndim != 3:
        raise ValueError(f"Expected hidden states [B, T, H], got {tuple(hidden_states.shape)}")
    if attention_mask is None:
        return hidden_states.mean(dim=1)
    mask = attention_mask.unsqueeze(-1).to(dtype=hidden_states.dtype)
    summed = (hidden_states * mask).sum(dim=1)
    counts = mask.sum(dim=1).clamp_min(1.0)
    return summed / counts


class MaskedMeanPooling(nn.Module):
    """Module wrapper so alternate pooling strategies can be swapped later."""

    def forward(
        self,
        hidden_states: torch.Tensor,
        attention_mask: torch.Tensor | None = None,
    ) -> torch.Tensor:
        return masked_mean_pool(hidden_states, attention_mask)
