# Day 01 — Le modèle mental : concurrence, boucle d'événements, coroutines

> **Objectif du jour** : comprendre *pourquoi* asyncio existe, ce qu'est réellement une
> coroutine, et ce que fait `await`. À la fin, tu dois pouvoir dessiner la timeline
> d'exécution d'un programme async **avant** de le lancer.

Durée : 3 h. Ne code pas avant d'avoir lu les sections 1 à 5.

---

## 1. Le problème : ton programme passe sa vie à attendre

Prends un script qui télécharge 3 pages web :

```python
page1 = telecharger("site-a.com")   # 1 s
page2 = telecharger("site-b.com")   # 1 s
page3 = telecharger("site-c.com")   # 1 s
# total : 3 s
```

Pendant ces 3 secondes, combien de temps ton CPU travaille-t-il vraiment ?
**Quelques microsecondes.** Le reste, il est bloqué sur un appel système `recv()` en
attendant que des paquets arrivent par le réseau. Il est *inactif*, mais *indisponible*.

Ordres de grandeur à graver (normalisés sur « 1 cycle CPU = 1 seconde ») :

| Opération | Temps réel | Échelle humaine |
|---|---|---|
| 1 cycle CPU | 0,3 ns | 1 seconde |
| Accès RAM | 100 ns | 6 minutes |
| Lecture SSD | 150 µs | 6 jours |
| Aller-retour réseau (même datacenter) | 0,5 ms | 3 semaines |
| Aller-retour réseau (Paris → Californie) | 150 ms | **15 ans** |

Un programme qui fait 100 requêtes HTTP séquentielles passe **99,99 % de son temps à
ne rien faire**. C'est *ça* que résout asyncio — et rien d'autre.

**Corollaire immédiat et non négociable** : si ton programme calcule (traitement d'image,
boucle numérique, chiffrement), il n'y a pas d'attente à récupérer. asyncio ne t'apportera
**rien**, il te ralentira même un peu. → Vois section 3.

---

## 2. Concurrence ≠ parallélisme

C'est la distinction fondatrice. Rob Pike :

> *« La concurrence, c'est traiter plusieurs choses à la fois. Le parallélisme, c'est
> faire plusieurs choses à la fois. »*

- **Parallélisme** : 3 cuisiniers, 3 plats, 3 fourneaux. Physiquement simultané. Requiert
  plusieurs cœurs.
- **Concurrence** : 1 seul cuisinier. Il met l'eau à bouillir, et *pendant que ça chauffe*
  il épluche les légumes, puis il retourne à l'eau. Un seul cuisinier, mais aucun temps mort.

**asyncio, c'est le cuisinier unique.** Un seul thread, un seul point d'exécution à la fois.
La vitesse ne vient pas d'une multiplication des travailleurs mais de **l'élimination des
temps morts**.

```
Séquentiel (bloquant) :
[req A ══════ attente ══════][req B ══════ attente ══════][req C ══════ attente ══════]
0s                          1s                           2s                          3s

Concurrent (asyncio, 1 seul thread) :
[A][B][C]═══════ les 3 attentes se superposent ═══════[A✓][B✓][C✓]
0s                                                                 1s
```

Le gain n'est pas magique : il vient du fait que **les attentes se recouvrent**.

---

## 3. Les trois outils de Python, et lequel choisir

| | `threading` | `multiprocessing` | `asyncio` |
|---|---|---|---|
| Unité | Thread OS | Processus OS | Coroutine |
| Qui décide de changer de tâche | L'OS (préemptif) | L'OS | **Ton code**, à chaque `await` (coopératif) |
| Coût mémoire d'une unité | ~8 Mo (pile) | ~10 Mo+ | **~1 Ko** |
| Combien en pratique | quelques centaines | quelques dizaines | **des centaines de milliers** |
| Vrai parallélisme CPU | Non (GIL)¹ | **Oui** | Non |
| Bon pour | I/O + libs bloquantes | **calcul pur** | **I/O massive** |
| Risque de data race | Élevé (à tout moment) | Faible (mémoire séparée) | Faible mais **réel** (voir day05) |

¹ *Le GIL (Global Interpreter Lock) empêche deux threads Python d'exécuter du bytecode
simultanément. Il est relâché pendant les I/O — c'est pourquoi les threads restent utiles
pour l'I/O. Python 3.13+ propose un mode « free-threaded » expérimental sans GIL.*

**Règle de décision :**

```
Ton goulot d'étranglement est-il l'attente d'une ressource externe (réseau, base, disque) ?
│
├── NON → c'est du CPU → multiprocessing (ou numpy, ou du C, ou Rust)
│
└── OUI → as-tu des bibliothèques asynchrones pour cette ressource ?
     ├── OUI (aiohttp, asyncpg, aioredis…) → asyncio
     └── NON (lib bloquante uniquement)   → threading, OU asyncio + to_thread (day06)
```

---

## 4. La boucle d'événements : le modèle mental à retenir

Imagine **un serveur unique dans un restaurant**. Il ne peut servir qu'une table à la fois,
mais il ne reste jamais planté devant une table.

1. Table 1 : il prend la commande → la donne en cuisine → **il ne l'attend pas**.
2. Table 2 : il prend la commande → cuisine → il ne l'attend pas.
3. Table 3 : idem.
4. La cuisine sonne « plat 2 prêt » → il l'apporte à la table 2.
5. Il repart, regarde qui a besoin de lui, recommence.

Le serveur = **la boucle d'événements** (event loop).
Les tables = **les tâches**.
« Passer commande et ne pas attendre » = **`await`**.
La sonnette de la cuisine = **le notificateur d'I/O de l'OS** (`epoll`/`kqueue`/`select`).

La boucle est, en essence, ceci (tu écriras la vraie version au day03) :

```python
while il_reste_du_travail:
    1. exécuter toutes les tâches prêtes, jusqu'à leur prochain `await`
    2. calculer combien de temps on peut dormir (le plus proche timer)
    3. demander à l'OS : « préviens-moi si une socket est prête, ou après ce délai »
    4. réveiller les tâches dont l'événement est arrivé → retour en 1
```

**Point crucial** : à l'étape 1, une tâche garde la main **jusqu'à ce qu'elle la rende
volontairement**. C'est du multitâche **coopératif**. Si une tâche ne coopère pas
(un `time.sleep(5)`, une boucle de calcul), **tout le programme est gelé**. Personne ne
peut la préempter. Cette phrase explique 80 % des bugs asyncio en production.

---

## 5. La coroutine : ce que c'est *vraiment*

```python
async def salut():
    print("bonjour")

x = salut()      # ← rien ne s'affiche !
print(x)         # <coroutine object salut at 0x104a…>
```

**Appeler une fonction `async def` n'exécute pas son corps.** Ça construit un objet
« coroutine » : une **fonction mise en pause avant sa première ligne**, qui contient
son propre état (variables locales, position dans le code).

C'est exactement la même famille d'objets qu'un générateur. Un générateur peut se
suspendre sur `yield` et reprendre plus tard ; une coroutine peut se suspendre sur `await`
et reprendre plus tard. **La technologie sous-jacente est identique** (day03).

Vocabulaire à ne jamais confondre :

| Terme | Ce que c'est |
|---|---|
| **fonction coroutine** | `async def f(): ...` — la définition |
| **objet coroutine** | `f()` — l'appel, une exécution en pause, pas encore planifiée |
| **awaitable** | tout objet qu'on peut `await` : coroutine, `Task`, `Future` |
| **Task** | une coroutine **confiée à la boucle** pour être exécutée (day02) |

Pour qu'une coroutine s'exécute, il faut **quelqu'un qui la pilote** : la boucle
d'événements. Deux façons de la lui donner :

```python
asyncio.run(main())          # point d'entrée : crée une boucle, exécute, ferme tout
await une_coroutine()        # depuis l'intérieur d'une coroutine déjà pilotée
```

---

## 6. `await` : la phrase à mémoriser

> **`await X` = « je me mets en pause, je rends la main à la boucle, et je ne reprendrai
> que lorsque X sera terminé. »**

Trois conséquences que tout le monde se prend en pleine figure au début :

1. **`await` seul ne crée aucune concurrence.**
   ```python
   await telecharger("a")   # 1 s
   await telecharger("b")   # 1 s  → total 3 s, comme en synchrone !
   await telecharger("c")   # 1 s
   ```
   Tu as rendu la main à la boucle… qui n'avait rien d'autre à faire. Pour du parallélisme
   d'attente, il faut des **tâches** (day02).

2. **`await` marque un point de suspension.** Entre deux `await`, ton code ne peut pas être
   interrompu. C'est une garantie très forte (pas de data race) et un piège (day05).

3. **On ne peut `await` que dans une fonction `async def`.** Sinon : `SyntaxError`.

---

## 7. Le seul vrai piège du jour

```python
import time, asyncio

async def mauvais():
    time.sleep(1)          # ❌ BLOQUE TOUT LE PROGRAMME pendant 1 s

async def bon():
    await asyncio.sleep(1) # ✅ rend la main : les autres tâches tournent
```

`time.sleep` ne rend pas la main à la boucle : il bloque le thread, donc la boucle, donc
**toutes** les tâches. `asyncio.sleep` dit à la boucle « programme un timer et réveille-moi ».

La même erreur se décline partout :

| Bloquant ❌ | Asynchrone ✅ |
|---|---|
| `time.sleep()` | `await asyncio.sleep()` |
| `requests.get()` | `await session.get()` (aiohttp / httpx) |
| `open(f).read()` sur réseau | `await aiofiles...` ou `await asyncio.to_thread(...)` |
| `input()` | lecture via un exécuteur (day06) |
| une boucle de calcul de 3 s | `run_in_executor` / process (day06) |

---

## 8. Le laboratoire — `cours/`

Exécute-les **dans l'ordre**, et pour chacun : prédis la sortie avant de lancer.

| Script | Ce qu'il te montre |
|---|---|
| `cours/01_pourquoi_async.py` | La mesure : séquentiel vs concurrent, et le cas CPU où async ne sert à rien |
| `cours/02_anatomie_coroutine.py` | Une coroutine démontée à la main : `send()`, `StopIteration`, l'état interne |
| `cours/03_ordre_execution.py` | Qui s'exécute quand — la timeline, et le gel provoqué par `time.sleep` |

```bash
cd day01
python3 cours/01_pourquoi_async.py
python3 cours/02_anatomie_coroutine.py
python3 cours/03_ordre_execution.py
```

---

## 9. Exercices — `exercices/`

| Fichier | Sujet |
|---|---|
| `ex1_premiers_pas.py` | Écrire tes premières coroutines et mesurer |
| `ex2_predire_la_trace.py` | **Prédire** la sortie avant de lancer (l'exercice le plus formateur du jour) |
| `ex3_chasse_au_bloquant.py` | Débusquer et corriger le code qui gèle la boucle |

Consigne : **aucune solution avant d'avoir passé 20 minutes bloqué.** Les corrigés sont
dans `solutions/`, avec les explications.

---

## 10. Tâches du jour (c'est là que ça rentre)

- [ ] **Tâche 1 — Le dessin.** Sur papier, dessine la timeline (axe du temps horizontal,
      une ligne par coroutine) de `ex2_predire_la_trace.py`. Marque d'une croix chaque
      point où la main est rendue à la boucle. Compare avec la sortie réelle.
- [ ] **Tâche 2 — L'explication orale.** Explique à voix haute (ou à quelqu'un, ou à ton
      téléphone qui enregistre) en 2 minutes : *« pourquoi asyncio accélère 100 requêtes
      HTTP mais pas 100 calculs de factorielle »*. Réécoute-toi. Si tu hésites, relis §1–3.
- [ ] **Tâche 3 — Le tableau personnel.** Dans un fichier `day01/mes_notes.md`, écris ta
      propre version du tableau bloquant/non-bloquant de §7, avec **3 exemples issus de ton
      domaine** (agri-tech : lecture de capteurs, appels d'API météo, requêtes en base…).
- [ ] **Tâche 4 — Le chrono.** Écris un décorateur `@chrono` qui mesure le temps d'une
      coroutine et l'affiche. Tu le réutiliseras toute la semaine.
      Indice : `functools.wraps`, `time.perf_counter()`, et un wrapper `async def`.
- [ ] **Tâche 5 — La prédiction inversée.** Écris un script de 15 lignes avec 3 coroutines,
      donne-le à un collègue (ou à Claude) et demande-lui de prédire la sortie. Corrige-le.
      Savoir *poser* la question prouve que tu as compris.

---

## 11. Récapitulatif — les cartes mémoire du jour

```
async def f(): ...    → définit une fonction coroutine
f()                   → crée un objet coroutine ; N'EXÉCUTE RIEN
await f()             → exécute, rend la main pendant l'attente, récupère le résultat
asyncio.run(main())   → crée la boucle, exécute main, ferme la boucle. UNE SEULE FOIS.
asyncio.sleep(n)      → attente coopérative (la boucle continue de tourner)
time.sleep(n)         → attente égoïste (tout gèle) ❌
```

**La phrase du jour** : *un seul thread, aucune préemption, et le seul endroit où la main
peut changer de tâche, c'est un `await`.*

➡️ Demain (day02) : créer de la **vraie** concurrence avec les `Task`, `gather` et `TaskGroup`.
