# Maîtriser `asyncio` — parcours en 7 jours

Ce dépôt est un cours complet sur `asyncio`, conçu pour que tu maîtrises **le concept
autant que le code**. Chaque jour suit la même logique :

> **1. Comprendre le modèle mental → 2. Voir le mécanisme en marche → 3. Le reconstruire soi-même → 4. L'appliquer.**

La règle centrale du parcours : **tu ne dois jamais écrire une ligne d'`async` sans
pouvoir dire à qui tu rends la main, et quand tu la récupères.** Tout le cours tourne
autour de cette phrase.

---

## Prérequis

- Python **3.11+** (testé sur 3.14). Vérifie : `python3 --version`
- Savoir écrire une fonction, une classe, un générateur (`yield`), un `with`, un `try/finally`.
- Un terminal. Aucune connaissance préalable d'`asyncio` n'est nécessaire.

Les jours 1 à 5 n'utilisent **aucune dépendance externe** (stdlib pure, volontairement :
tu dois voir la machinerie, pas une couche de confort). Les jours 6 et 7 en ajoutent
quelques-unes :

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Arborescence

```
learning_asyncio/
├── README.md            ← tu es ici
├── PROGRESSION.md       ← check-list de maîtrise + auto-évaluation
├── requirements.txt
├── day01/  Le modèle mental : concurrence, boucle d'événements, coroutines
├── day02/  Tasks : la vraie concurrence (create_task, gather, TaskGroup)
├── day03/  Sous le capot : générateurs, Future, écrire sa propre boucle
├── day04/  Annulation, timeouts, exceptions, ExceptionGroup
├── day05/  Synchronisation, Queue, backpressure, pipelines
├── day06/  I/O réelle : réseau, streams, code bloquant, sous-processus
└── day07/  Async avancé, tests, debug, perf + projet final
```

Chaque dossier `dayXX/` contient :

| Élément | Rôle |
|---|---|
| `README.md` | Le cours du jour : théorie, schémas, pièges, **tâches à faire** |
| `cours/` | Scripts de démo **à exécuter et à modifier**. C'est le laboratoire. |
| `exercices/` | Squelettes avec des `TODO`. C'est ton travail. |
| `solutions/` | À n'ouvrir **qu'après** avoir tenté (ou séché 20 min). |

---

## Comment travailler (méthode, pas décoration)

Chaque jour, dans cet ordre :

1. **Lis le `README.md` du jour en entier** (20–30 min), sans coder. Tu cherches le
   modèle mental, pas la syntaxe.
2. **Exécute chaque script de `cours/`**, un par un. Pour chacun :
   - **avant de lancer**, écris sur papier l'ordre d'affichage que tu prédis ;
   - lance ;
   - si ta prédiction était fausse, **c'est le moment le plus utile de la journée** :
     ne passe pas à la suite avant d'avoir compris pourquoi.
3. **Fais les exercices** dans `exercices/`. Sans regarder les solutions.
4. **Compare** avec `solutions/`, puis note dans `PROGRESSION.md` ce qui t'a bloqué.
5. **Fais les « Tâches du jour »** en fin de `README.md` : ce sont elles qui
   transforment la compréhension en maîtrise.

Durée réaliste : **2 h 30 à 4 h par jour**. Si tu as moins de temps, étale sur 14 jours
plutôt que de sauter les tâches.

### Lancer un script

```bash
cd day01
python3 cours/01_pourquoi_async.py
```

Un outil que tu utiliseras **tout le temps** — le mode debug d'asyncio, qui te prévient
quand tu bloques la boucle ou quand tu oublies d'`await` quelque chose :

```bash
PYTHONASYNCIODEBUG=1 python3 mon_script.py
```

---

## Le fil rouge des 7 jours

| Jour | Question à laquelle tu sauras répondre |
|---|---|
| **01** | Pourquoi async est plus rapide pour l'I/O, et *jamais* pour le calcul ? Qu'est-ce qu'une coroutine, concrètement, en mémoire ? |
| **02** | Quelle est la différence exacte entre `await coro()` et `create_task(coro())` ? Pourquoi mon `gather` ne va-t-il pas plus vite ? |
| **03** | Comment `await` est-il implémenté ? Que fait la boucle d'événements, ligne par ligne ? (tu vas en écrire une) |
| **04** | Que se passe-t-il *exactement* quand j'annule une tâche ? Comment garantir le nettoyage ? |
| **05** | Pourquoi ai-je besoin d'un `Lock` alors qu'il n'y a qu'un seul thread ? Comment éviter d'exploser la RAM avec un producteur trop rapide ? |
| **06** | Comment brancher tout ça sur du vrai réseau, et cohabiter avec du code bloquant existant ? |
| **07** | Comment tester, déboguer, arrêter proprement et mesurer un programme async en production ? |

---

## Les 8 règles d'or (relis-les chaque matin)

1. **Une coroutine appelée n'est pas exécutée.** `f()` fabrique un objet ; `await f()` ou
   `create_task(f())` l'exécute.
2. **`await` ne veut pas dire « attendre »**, il veut dire **« je rends la main, réveille-moi
   quand c'est prêt »**.
3. **Rien ne s'exécute en parallèle.** Un seul thread, un seul point d'exécution à la fois.
   La concurrence vient de l'entrelacement, pas de la simultanéité.
4. **Tout appel bloquant gèle *tout* le programme.** `time.sleep`, `requests.get`,
   `open().read()` sur du réseau, une boucle de calcul de 2 s : la boucle est morte pendant ce temps.
5. **Entre deux `await`, ton code est atomique.** C'est la seule vraie garantie que tu as —
   et la source de tous les bugs de synchronisation quand tu l'oublies.
6. **Garde une référence à tes `Task`**, sinon le ramasse-miettes peut les supprimer en plein vol.
7. **`CancelledError` n'est pas une erreur** : c'est un ordre. On la laisse remonter.
8. **Mesure.** Un `time.perf_counter()` vaut mieux que dix intuitions sur la performance.

---

## Ressources de référence (à garder ouvertes)

- Doc officielle : <https://docs.python.org/3/library/asyncio.html>
- PEP 492 (`async`/`await`) : <https://peps.python.org/pep-0492/>
- PEP 3156 (le design de la boucle d'événements) : <https://peps.python.org/pep-3156/>
- « Structured concurrency » (Nathaniel J. Smith) : <https://vorpus.org/blog/notes-on-structured-concurrency-or-go-statement-considered-harmful/>

Bon parcours. Commence par [day01/README.md](day01/README.md).
