"""
Day 01 — Démo 1 : POURQUOI asyncio ? (la mesure, pas la croyance)

Objectif : voir de tes yeux les deux vérités du jour.
  1. Sur de l'I/O (attente), la concurrence divise le temps total.
  2. Sur du CPU (calcul), la concurrence n'apporte RIEN. Zéro. Parfois pire.

Lance :  python3 cours/01_pourquoi_async.py

AVANT DE LANCER, écris ta prédiction pour les 4 durées affichées.
"""

import asyncio
import time

# ---------------------------------------------------------------------------
# Un petit utilitaire de mesure. Garde-le en tête, on s'en sert toute la semaine.
# ---------------------------------------------------------------------------
DEBUT = time.perf_counter()


def log(message: str) -> None:
    """Affiche un message préfixé du temps écoulé depuis le début du programme."""
    print(f"[{time.perf_counter() - DEBUT:6.2f}s] {message}")


# ===========================================================================
# PARTIE 1 : de l'I/O simulée (une attente réseau)
# ===========================================================================
# asyncio.sleep() est LE simulateur d'attente réseau : il ne consomme pas de CPU,
# il demande juste à la boucle « réveille-moi dans N secondes ».

async def telecharger(nom: str, duree: float) -> str:
    log(f"  → début du téléchargement de {nom}")
    await asyncio.sleep(duree)          # ici, la main est rendue à la boucle
    log(f"  ← {nom} terminé")
    return f"contenu de {nom}"


async def io_sequentiel() -> None:
    """Chaque await attend la fin du précédent : les attentes s'ADDITIONNENT."""
    t0 = time.perf_counter()
    await telecharger("site-a", 2)
    await telecharger("site-b", 2)
    await telecharger("site-c", 2)
    print(f"  ⏱  I/O séquentiel  : {time.perf_counter() - t0:.2f}s\n")


async def io_concurrent() -> None:
    """gather lance les 3 coroutines comme des tâches : les attentes SE RECOUVRENT."""
    t0 = time.perf_counter()
    await asyncio.gather(
        telecharger("site-a", 2),
        telecharger("site-b", 2),
        telecharger("site-c", 2),
    )
    print(f"  ⏱  I/O concurrent  : {time.perf_counter() - t0:.2f}s\n")


# ===========================================================================
# PARTIE 2 : du CPU (un vrai calcul)
# ===========================================================================
# Ici il n'y a AUCUNE attente à récupérer : le CPU travaille à 100 %.
# La boucle d'événements ne peut rien optimiser — elle ne peut même pas
# reprendre la main, puisqu'il n'y a pas de `await` dans le calcul.

def calcul_lourd(n: int) -> int:
    """Somme des carrés de 0 à n. Pur CPU, aucune I/O."""
    return sum(i * i for i in range(n))


async def cpu_tache(nom: str, n: int) -> int:
    log(f"  → début du calcul {nom}")
    resultat = calcul_lourd(n)          # ⚠️ aucun await ici : la boucle est GELÉE
    log(f"  ← calcul {nom} terminé")
    return resultat


async def cpu_sequentiel(n: int) -> None:
    t0 = time.perf_counter()
    await cpu_tache("A", n)
    await cpu_tache("B", n)
    await cpu_tache("C", n)
    print(f"  ⏱  CPU séquentiel  : {time.perf_counter() - t0:.2f}s\n")


async def cpu_concurrent(n: int) -> None:
    t0 = time.perf_counter()
    await asyncio.gather(
        cpu_tache("A", n),
        cpu_tache("B", n),
        cpu_tache("C", n),
    )
    print(f"  ⏱  CPU 'concurrent': {time.perf_counter() - t0:.2f}s\n")


# ===========================================================================
async def main() -> None:
    print("=" * 70)
    print("PARTIE 1 — I/O (attente réseau simulée) : 3 tâches de 1 seconde")
    print("=" * 70)
    await io_sequentiel()
    await io_concurrent()

    print("=" * 70)
    print("PARTIE 2 — CPU (calcul pur) : 3 calculs identiques")
    print("=" * 70)
    N = 3_000_000
    await cpu_sequentiel(N)
    await cpu_concurrent(N)

    print("=" * 70)
    print("CE QU'IL FAUT VOIR :")
    print("  • I/O  : 3.0s → 1.0s   (les attentes se recouvrent : gain réel)")
    print("  • CPU  : identique     (rien à recouvrir : asyncio n'y peut rien)")
    print()
    print("  Observe aussi l'ORDRE des logs en partie 2 : dans la version")
    print("  'concurrente', les calculs s'exécutent quand même l'un APRÈS l'autre,")
    print("  car aucun `await` ne permet à la boucle de reprendre la main.")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())

# ---------------------------------------------------------------------------
# À EXPÉRIMENTER (fais-le vraiment, ne te contente pas de lire) :
#
# 1. Passe les 3 durées de la partie 1 à 1, 2 et 3 secondes.
#    Combien de temps prend io_concurrent ? Pourquoi ce chiffre et pas la somme ?
#
# 2. Dans `cpu_tache`, ajoute `await asyncio.sleep(0)` juste avant le calcul.
#    L'ordre des logs change-t-il ? Le temps total ? Pourquoi ?
#
# 3. Remplace `await asyncio.sleep(duree)` par `time.sleep(duree)` dans
#    `telecharger`, puis relance. Que devient le gain de io_concurrent ?
#    → C'est LE bug numéro 1 des débutants en asyncio.
# ---------------------------------------------------------------------------
