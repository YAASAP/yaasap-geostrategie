# Protocole de publication — YAASAP Géostratégie

Ce fichier est la consigne exécutée à chaque publication (toutes les 2 heures). Modifiez-le pour changer la ligne éditoriale : la prochaine exécution en tiendra compte.

## 0. Dépôts et accès (modèle freemium)

Deux dépôts sont clonés côte à côte dans le même dossier parent : `yaasap-geostrategie` (public, le site) et `yaasap-geostrategie-prive` (privé : clé de chiffrement, abonnés, sources des analyses archivées). Avant tout : `pip install --break-system-packages cryptography`.

- La **dernière** analyse est en accès libre. Dès qu'une nouvelle analyse est générée, la précédente est **archivée automatiquement** par `generate.py` : son JSON passe dans le dépôt privé (`notes/`) et sa page devient une page chiffrée, réservée aux abonnés (titre, résumé et tags restent publics).
- Ne jamais lire, afficher ni copier `cle.json` ni `abonnes.json`. Ne jamais les committer dans le dépôt public.

## 1. Cadrage

1. Lire l'heure avec l'outil d'heure courante (fuseau Europe/Paris). Ne jamais deviner la date.
2. Lire `data/index.json` : titres et dates des analyses déjà publiées. Lire la dernière note JSON (`data/notes/…`, seule note publique) pour reprendre le même modèle ; les anciennes sont dans `../yaasap-geostrategie-prive/notes/` (lecture permise pour éviter les doublons de sujet).
3. Choisir **un sujet** :
   - priorité à un développement majeur survenu depuis la dernière publication (vote à l'ONU, frappe, accord, sanction, élection, incident maritime…) ;
   - sinon, un théâtre non traité dans les 12 dernières analyses. Théâtres : Moyen-Orient et Golfe, Russie–Ukraine et Europe, Indo-Pacifique et Taïwan, Afrique (Sahel, Sahara, Corne), Amériques, Asie du Sud, énergie et matières premières, détroits et routes maritimes, espace et cyber, sanctions et commerce, élections et institutions.
   - ne jamais republier le même angle qu'une analyse des 6 dernières heures, sauf fait nouveau majeur (le dire dans le lead).
4. Si les sources fiables sont insuffisantes pour un sujet, en choisir un autre. **Ne rien publier plutôt que publier du faible** ; dans ce cas ne rien committer et terminer en expliquant pourquoi.

## 2. Recherche

- Au moins 4 recherches web, et lire en entier (WebFetch) les 2 à 4 articles les plus importants.
- Croiser au moins deux sources indépendantes pour chaque fait central ; citer des sources de camps différents quand le sujet est disputé.
- Chaque chiffre vient d'une source lue pendant l'exécution, avec sa date. Aucun chiffre de mémoire.
- Pour un cours de marché : donner l'heure et la source, ou ne pas le donner.
- Distinguer **fait établi**, **déclaration d'un acteur** et **lecture YAASAP**. Dire quand une source est unique, non vérifiée ou partisane.
- Droit d'auteur : paraphraser. Au plus une citation par source, moins de 15 mots, entre guillemets.

## 3. Rédaction (même modèle que la dernière note)

Ton : direct, factuel, sans langue de bois, chiffres en gras. Jamais « je vous recommande » : « Verdict YAASAP : Attendre / Surveiller / Prudence… ». Aucune promesse de rendement, aucune prévision de cours au-delà de 18 mois, aucune probabilité chiffrée sans donnée. Neutralité : le verdict porte sur le **risque et les marchés**, pas sur le bien-fondé d'un camp.

Structure d'une note (fichier JSON, voir §4) :

1. **Titre** : fait ou chiffre clé + conséquence, 12 mots maximum.
2. **Deck** : 2 phrases, contexte et chiffre immédiat.
3. **6 KPI** (valeur courte, libellé court, couleur `up` / `dn` / `am` / `neu`).
4. **Kicker** : 6 à 8 repères (valeur, libellé, note de source).
5. **Lead** : thèse en une phrase nominale + 2 à 3 phrases de contexte.
6. **Corps** : 5 à 8 sections nommées avec leur contenu réel (jamais « Contexte »). Au minimum : un tableau ou un graphique chiffré, un bloc de positions des acteurs, une chronologie cliquable, des scénarios nommés, les canaux de marché.
7. **Verdict** : phrase de synthèse + 5 à 8 puces, la première commence par la décision, puis condition d'invalidation, catalyseur, risque principal, indicateur à suivre, périmètre.
8. **Sources** : liens réels, tous lus pendant l'exécution, et une note signalant divergences et limites.

## 4. Schéma JSON (`data/notes/AAAAMMJJ-HHMM-slug.json`)

```json
{
  "slug": "mots-cles",
  "published": "2026-10-31T19:58:00+01:00",
  "nav": "Libellé court pour le pied de page",
  "title": "…", "deck": "…",
  "tags": [{"t": "Iran", "hot": true}, {"t": "Énergie"}],
  "kpis": [{"v": "118,07 $", "l": "Brent · 30 oct.", "cls": "am", "to": 118.07, "dec": 2, "suf": " $"}],
  "kicker": [{"l": "…", "v": "…", "n": "…"}],
  "lead": {"hl": "…", "deck": "…"},
  "blocks": [
    {"type": "sec", "title": "…"},
    {"type": "p", "html": "texte avec <strong>gras</strong>"},
    {"type": "pull", "t": "« citation courte »", "a": "auteur · source · date"},
    {"type": "table", "title": "…", "cols": ["…"], "rows": [["…"]], "src": "…"},
    {"type": "chart", "title": "…", "kind": "bar|line|doughnut", "labels": ["…"],
     "datasets": [{"label": "…", "data": [1, 2]}], "unit": "…", "src": "…"},
    {"type": "pos", "items": [{"h": "Acteur", "p": "…", "by": "source"}]},
    {"type": "timeline", "title": "…", "events": [["date", "titre", "texte"]]},
    {"type": "html", "html": "bloc HTML libre (pas de script)"}
  ],
  "verdict": {"hl": "… Verdict : <strong>Attendre</strong>.", "items": ["…"]},
  "sources": [{"t": "Média · titre (date)", "u": "https://…"}],
  "sources_note": "divergences et limites"
}
```

Règles du schéma : exactement 6 KPI ; 5 à 8 puces de verdict ; au moins une source ; `published` en ISO avec fuseau ; badges de tableau `<span class="b-up|b-dn|b-am">…</span>` ; aucune balise `<script>`, `<iframe>` ni attribut `on…=` (le générateur les refuse).

## 5. Génération et publication

```bash
python3 generate.py data/notes/<fichier>.json     # rend la note, archive la précédente, reconstruit accueil + abonnement
```

La commande affiche `ARCHIVÉ …` pour la note précédente et `OK … (verrouillée)` pour sa page chiffrée. Si elle échoue (clé ou dépôt privé introuvable), ne rien publier et le dire.

1. Relire le HTML produit (titres, chiffres, liens). Corriger le JSON puis régénérer si besoin.
2. **Dépôt privé d'abord** : dans `yaasap-geostrategie-prive`, `git add notes/`, commit `Archive : <titre court>`, `git pull --rebase origin main`, `git push origin HEAD:main`. (Rien à committer s'il n'y a pas eu d'archivage.)
3. **Dépôt public ensuite** : `git pull --rebase origin main`, puis `git add -A data notes index.html abonnement.html`. Le fichier `data/notes/<précédente>.json` apparaît comme supprimé : c'est voulu.
4. Commit en français, une ligne : `Analyse : <titre court>` (plus les lignes d'attribution demandées par la session).
5. `git push origin HEAD:main`. En cas de refus « behind » : `git pull --rebase origin main` puis repousser une fois.
6. Résultat attendu : `https://yaasap.github.io/yaasap-geostrategie/notes/<fichier>.html` en ligne après 1 à 2 minutes (GitHub Pages).

## 6. Interdits

- Ne jamais modifier `assets/`, `generate.py` ou ce protocole pendant une publication courante, sauf bug bloquant décrit dans le message de commit.
- Ne jamais supprimer ni réécrire une analyse déjà publiée ; une correction se fait par une nouvelle note ou par un `sources_note` explicite. L'archivage automatique (déplacement vers le dépôt privé) n'est pas une suppression.
- Ne jamais toucher à `access.json` (géré par `tools/acces.py` du dépôt privé) ni afficher un code d'accès.
- Pas d'image protégée, pas de contenu haineux, pas de détail opérationnel pouvant faciliter des violences.
- Jamais de conseil d'investissement personnalisé : la mention « Ne constitue pas un conseil en investissement » est générée automatiquement.
