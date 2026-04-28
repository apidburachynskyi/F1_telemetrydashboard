# Revue de code — F1 Telemetry Dashboard

Revue effectuée dans le cadre du cours, sur la base de la checklist des bonnes pratiques de développement.
---

## Conformité à la checklist

### Utilisation de Git

| Critère | Statut | Remarque |
|---|---|---|
|`.gitignore`| + | Couvre `cache/`, `*.pkl`, venvs ...|
| README| + | Bien structuré |
| LICENSE | + | Présente |
| `requirements.txt`| + | Présents |

### Qualité du code

| Critère | Statut | Remarque |
|---|---|---|
| Linter/formatter | ~ |  `.flake8` ignore certains critères|
| Pre-commit hooks | - | Absent |
| Modularité | + | Bien séparés |

### Structure du projet

| Critère | Statut | Remarque |
|---|---|---|
| Code sur GitHub | + | |
| Données sur S3 | + | |
| Config/secrets séparés | ~ | Mot de passe dans le read me, mais due au contexte scolaire |

### Déploiement et infrastructure

| Critère | Statut | Remarque |
|---|---|---|
| Image Docker | + | |
| CI/CD | ~ | Lint + Docker build présents, mais pas de deploiement automatique |
| Déploiement SSP Cloud | + | ArgoCD configuré |
| GitOps | - | Tag Docker `latest` jamais mis à jour|
| Monitoring | + | Page `/monitoring`|
| Automatisation des données | - | Lancé manuellement après chaque week-end de course |

### Tests

| Critère | Statut | Remarque |
|---|---|---|
| Tests unitaires | - | Aucun test |

---

## Pistes d'amélioration

### 1. Ajouter des tests

Cela aurait bien d'avoir des test pour simplifier et controller les futurs changements.

### 2. Mot de passe

C'est du au contexte scolaire mais un mot de passe en dur est présent dans le ReadMe et dans le Monitoring :

```
Login: admin
Password: f1admin2026
```


### 3. Automatiser le déploiement GitOps 

Actuellement, le workflow CI pousse l'image Docker avec le tag `latest`, mais le fichier `k8s/deployment.yaml` n'est jamais mis à jour. ArgoCD surveille ce fichier : s'il ne change pas, il ne redéploie pas.

La correction consiste à injecter le SHA du commit dans le manifest après chaque push sur `main`.


### 4. Automatiser la synchronisation des données

Non présente mais expliquée par les membres.


### 5. Corriger la configuration flake8

Le fichier `.flake8` ignore des règles qui détectent de vraies erreurs :

```ini
# Règles à ne pas ignorer
F401  # imports inutilisés → signe de code mort
F841  # variables inutilisées → signe de code mort
E722  # bare except → mauvaise gestion des erreurs
```


### 6. Séparer les dépendances de développement

`black` et `flake8` sont des outils de développement présents dans `requirements.txt`. Ils sont donc installés dans l'image Docker de production, ce qui l'alourdit inutilement.

### 7. Ajouter des pre-commit hooks

Cela permet de ne pas pouvoir push n'importe quoi.
