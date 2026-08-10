# Pilot inspection notes (S12)

**Run**: `data/outputs/runs/pilot-20x1-final/`  
**Model**: `qwen/qwen-2.5-7b-instruct`  
**Date**: 2026-08-10

## Totals

| Metric | Value |
|--------|------:|
| Records | 20 |
| `patch_parse_ok=True` | 10 |
| `patch_parse_ok=False` | 9 |
| No response (provider error) | 1 |
| Parse rate among responses | 52.6% |
| Total cost USD | ~0.0068 |
| Cost per paid sample USD | ~0.00029 |
| Wall clock (s) | ~102 |

## Sample OK

`astropy__astropy-12907` — human-readable unified diff touching
`astropy/modeling/separable.py` (fenced `diff --git` style).

## Sample FAIL

`astropy__astropy-14182` — model returned a fenced diff that looks like a patch
but failed S8 structural validation (incomplete / non-conforming hunks). Suggests
extraction strictness + prompt “single valid unified diff” pressure still need
work, not a silent empty response.

## Provider error

`astropy__astropy-7746` — HTTP 400 context length (~32k model limit; prompt ~
126k chars). Runner records `provider_error` and continues.

## Day-2 gate

Patches **do** produce for many tasks, but parse-clean rate is only ~53% and
oversized oracle contexts can refuse. Not a clean pilot.
