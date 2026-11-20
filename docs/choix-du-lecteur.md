# Prototype : choisir le moteur de lecture depuis TWP

## Objectif

Depuis la page HTML déjà ouverte dans Firefox Android :
1. Ouvrir le menu de **TWP expérimental**.
2. Sélectionner une des commandes :
   - **🔊 Lire la page avec TWP** : traduire en français si nécessaire, extraire le texte principal et le lire avec le moteur TTS Google/Bing configuré dans TWP.
   - **🎙 Lire avec Read Aloud (autres voix)** : traduire en français si nécessaire, puis demander à Read Aloud expérimental de lire **le même onglet actif** avec les voix de Read Aloud.
   - **⏸ Pause TWP / ▶ Reprendre TWP / ⏹ Arrêter TWP** : contrôler le lecteur TWP (Read Aloud conserve ses propres commandes).

Ces commandes sont **déjà codées dans le patch expérimental de cette branche** et font partie d'un premier prototype. Aucun écran spécial supplémentaire n'est nécessaire ; elles se placent dans le menu déroulant de la barre TWP sur Android.

## Deux niveaux d'indépendance

- **TWP seul** doit pouvoir traduire et lire un article, sans Read Aloud.
- **TWP + Read Aloud expérimentaux** permettent de choisir d'autres voix ; TWP prépare l'onglet et signale à Read Aloud de démarrer sur ce même onglet. Les versions officielles ne disposent pas de ce protocole personnalisé.

## Détails du prototype

- L'extraction de texte donne la priorité à `<article>`, puis à `[role=main]` ou `<main>`, et enfin au corps du document ; elle écarte les menus et les éléments non destinés à la lecture.
- TWP prépare une traduction française de la page, y compris les paragraphes hors écran selon le mécanisme de synchronisation du patch préexistant.
- Le lecteur TWP segmente le texte en lots pour ne pas demander simultanément des centaines de fichiers audio.
- Les échanges entre extensions vérifient l'identifiant dédié de l'extension émettrice et l'onglet actif.
- Aucun nouvel onglet ni service de copie externe n'est requis.

## Limites à traiter avant une installation

- **Aucun essai réel sur Firefox Android** n'a encore vérifié le fonctionnement du protocole inter-extensions.
- Les pages longues, sites à chargement dynamique, contenus embarqués et traductions partielles restent à tester.
- Le prototype ajoute **Pause/Reprise/Arrêt** au menu de TWP. Il essaie d'enregistrer ces mêmes commandes dans `navigator.mediaSession` quand Firefox les autorise, **mais l'affichage dans le panneau des notifications Android reste non vérifié**. Les suspensions qui surviennent pendant le chargement d'un fragment audio doivent être testées.
- Le lecteur Read Aloud récupère le DOM de l'onglet traduit. Il faut vérifier s'il conserve bien les textes traduits, l'ordre des paragraphes et les changements de page.
- Certains articles peuvent n'avoir ni `<article>` ni `<main>`, et l'extraction peut alors contenir du texte parasite.
- Un limiteur de 200 000 caractères rejette les textes exceptionnellement longs **avec un message explicite** : le prototype ne les tronque pas silencieusement.
- Les **7 tests automatiques Node.js** vérifient l'extraction sur un article de 600 paragraphes, l'ordre et le découpage du texte, le ciblage de l'onglet actif, les restrictions sur l'identifiant des extensions, l'arrêt avant le segment suivant, et les commandes MediaSession simulées. Les tests ne sont **pas** un test réel dans Firefox ni sur Android.

## Signatures et versions

Les deux XPI issus de la construction CI sont **non signés**. Ils ne doivent pas remplacer les extensions officielles. Ne pas lancer une nouvelle signature Mozilla tant que les fonctions ci-dessus n'ont pas été revues et testées.

## Suite logique

1. Vérifier le protocole de traduction et lecture sur Firefox Desktop dans un profil temporaire.
2. Vérifier sur Firefox Android en environnement de test et préparer les signatures des versions corrigées.
3. Vérifier si Firefox Android affiche les commandes MediaSession en notification et si la pause/reprise fonctionne lors d'un téléchargement audio.
4. Reprendre ensuite l'objectif initial : déclencher le menu depuis le bouton central du téléphone (Tasker ou autre mécanisme).
