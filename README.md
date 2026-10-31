# YAASAP Géostratégie

Analyses géostratégiques indépendantes, au format de [YAASAP Notes](https://yaasap.github.io/dailywatch/) : chiffres d'abord, positions de chaque acteur, scénarios nommés, verdict tranché sur le risque et les marchés, sources citées.

Site : https://yaasap.github.io/yaasap-geostrategie/

Une nouvelle analyse est publiée toutes les 2 heures par une tâche planifiée qui suit [`PROTOCOLE.md`](PROTOCOLE.md).

## Structure

| Chemin | Rôle |
|---|---|
| `index.html` | Accueil et archives (généré) |
| `notes/` | Analyses publiées (générées) |
| `data/notes/*.json` | Source de chaque analyse |
| `data/index.json` | Liste des analyses (générée) |
| `assets/` | Feuille de style et scripts communs |
| `generate.py` | Générateur : JSON → HTML |
| `PROTOCOLE.md` | Consigne éditoriale et technique de chaque publication |

## Utilisation

```bash
python3 generate.py data/notes/<fichier>.json   # rend une analyse et reconstruit l'accueil
python3 generate.py --rebuild                   # reconstruit tout (après un changement de gabarit)
```

Aucune dépendance : Python 3.9+ uniquement. Les graphiques utilisent Chart.js via CDN.

*Ne constitue pas un conseil en investissement. Par Yacine AOUABED.*
