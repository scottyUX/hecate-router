# Requirements checklist: Router training v1

- [x] Spec defines input (issue + oracle), label (m1_resolves), and serve rule
- [x] Patch text excluded from router input
- [x] Truncation budget 2048 with logged rate
- [x] 5-fold × 3 seeds with stratification fallback
- [x] Route-AUC vs always-m1 / always-m2 / random / oracle
- [x] Go/no-go does not crash on ≤ 0
- [x] CI has no Hugging Face download
- [x] Optional train extra, not default deps
