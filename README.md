# Firefox — Traduire et écouter

Prototype expérimental permettant, à terme, de **traduire intégralement l'onglet ouvert avec TWP**, puis de **lire le résultat en français avec Read Aloud**, depuis une commande unique dans Firefox Android.

## Situation réelle

- Les sources amont sont [TWP — Translate Web Pages](https://github.com/FilipePS/Traduzir-paginas-web) et [Read Aloud](https://github.com/Read-Aloud/read-aloud).
- Ce dépôt contient **un script de modification** et un **workflow de construction GitHub Actions**. Il ne contient pas encore une extension validée sur Android.
- Les fichiers issus de la compilation sont **non signés** : ils sont destinés à l'inspection et aux tests de développement, **pas à l'installation durable** dans Firefox Android standard.
- Le déclenchement par Tasker ou par le bouton central du Samsung viendra **après** validation dans Firefox.

## Construction sans ordinateur

1. Dans GitHub, ouvrir **Actions** → **Construire les extensions**.
2. Choisir **Run workflow**.
3. Après l'exécution, télécharger l'artefact **extensions-experimentales-non-signees**.
4. Il contient deux fichiers : `read-aloud-traduire-ecouter.xpi` et `twp-traduire-ecouter.xpi`.

Ces archives sont produites à partir de deux révisions amont précises, pour éviter qu'une mise à jour imprévue ne casse le patch.

## Important : installation sur le téléphone

Sur Firefox Android standard, les extensions personnalisées doivent être **signées par Mozilla** avant une installation durable. Les fichiers téléchargés des Actions **ne sont pas signés**.

Les versions expérimentales possèdent des identifiants distincts et ne sont pas censées remplacer les extensions officielles. Il faut cependant vérifier leur comportement réel sur Firefox Android : coexistence, accès à l'onglet actif, communications entre extensions, lecture audio, et longues pages.

Pour la signature non répertoriée, il faudra un compte Mozilla Add-ons et, pour l'automatiser, des identifiants API Mozilla. **Ne jamais publier de clés secrètes dans ce dépôt**. La signature n'est pas encore automatisée.

## Fonctionnement technique visé

1. Le bouton **« Traduire et écouter »** est ajouté au panneau de Read Aloud expérimental.
2. Il demande à TWP expérimental de traduire l'onglet actif en français.
3. Le patch modifie le traitement progressif de TWP pour traduire les paragraphes hors écran et attendre la fin des requêtes et substitutions connues.
4. Read Aloud démarre la lecture du même onglet après l'accusé de réception de TWP.

**Limites non encore résolues :** contenus chargés après coup, certains sites complexes, traductions avec iframes, onglets masqués, fermeture prématurée du panneau, contrôle multimédia depuis les notifications Android.

## Versions sources épinglées

- Read Aloud (branche `firefox`) : `8053a39541dc77e4ff7719348c406bad9792175a`
- TWP (branche `master`) : `50a92116542ab93524594cc210f4bf4e5d86a925`

## Validation nécessaire

Avant toute proposition d'installation, vérifier que l'action GitHub réussit, que les extensions démarrent ensemble, puis que les longues pages sont réellement lues **en français et intégralement** sur le Samsung Galaxy S10e. Les tests automatisés de syntaxe ne garantissent pas ce fonctionnement.

Aucun droit d'accès aux comptes ou clés Mozilla n'est demandé dans le code.
