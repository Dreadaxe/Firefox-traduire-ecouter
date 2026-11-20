# Prototype : choisir le moteur de lecture depuis TWP

## Objectif

Depuis la page HTML déjà ouverte dans Firefox Android :
1. Ouvrir le menu de **TWP expérimental**.
2. Sélectionner une des commandes :
   - **🔊 Lire la page avec TWP** : traduire en français si nécessaire, extraire le texte principal et le lire avec le moteur TTS Google/Bing configuré dans TWP.
   - **🎙 Lire avec Read Aloud (autres voix)** : traduire en français si nécessaire, puis demander à Read Aloud expérimental de lire **le même onglet actif** avec les voix de Read Aloud.
   - **⏹ Arrêter la lecture TWP** : arrêter la lecture lancée par TWP (les commandes Read Aloud restent dans Read Aloud).

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
- Le moteur TWP ne possède pas encore de commandes pause/reprise natives dans la notification Android ; la commande **Arrêter** est un premier contrôle interne.
- Le lecteur Read Aloud récupère le DOM de l'onglet traduit. Il faut vérifier s'il conserve bien les textes traduits, l'ordre des paragraphes et les changements de page.
- Certains articles peuvent n'avoir ni `<article>` ni `<main>`, et l'extraction peut alors contenir du texte parasite.
- Un limiteur de 200 000 caractères rejette les textes exceptionnellement longs **avec un message explicite** : le prototype ne les tronque pas silencieusement.
- La validation automatique actuelle vérifie l'application du patch, la syntaxe JavaScript/Python, la présence des commandes et le packaging des XPI, **pas les interactions navigateur**.

## Signatures et versions

Les deux XPI issus de la construction CI sont **non signés**. Ils ne doivent pas remplacer les extensions officielles. Ne pas lancer une nouvelle signature Mozilla tant que les fonctions ci-dessus n'ont pas été revues et testées.

## Suite logique

1. Vérifier le protocole de traduction et lecture sur Firefox Desktop dans un profil temporaire.
2. Vérifier sur Firefox Android en environnement de test et préparer les signatures des versions corrigées.
3. Ajouter les contrôles lecture/pause/reprise/arrêt dans la notification Android si techniquement possibles.
4. Reprendre ensuite l'objectif initial : déclencher le menu depuis le bouton central du téléphone (Tasker ou autre mécanisme).
