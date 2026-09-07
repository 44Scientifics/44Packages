# 44Packages

## 📝 Convention de commits (Conventional Commits)

Format : `<type>(<scope?>): <description en minuscules, impératif>`

Types : `feat` | `fix` | `refactor` | `docs` | `test` | `chore` | `style` | `perf` | `build` | `ci`

Exemples :
- `feat(accounting): ajoute endpoint budgets`
- `fix: corrige le calcul de la balance 6-7`
- `chore: met à jour les dépendances`

Règles :
- Un commit = une intention cohérente (ne pas mélanger feat + fix)
- Jamais de "WIP", "modifs", "update"
- Ne jamais committer : `.venv/`, `__pycache__/`, `node_modules/`, `.env`, `logs/`, `.DS_Store`
