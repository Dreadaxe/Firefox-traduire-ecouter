# Firefox — Traduire et écouter

Prototype expérimental permettant, à terme, de **traduire intégralement l'onglet ouvert avec TWP**, puis de **lire le résultat en français avec Read Aloud**, depuis une commande unique dans Firefox Android.

## Situation réelle

- Les sources amont sont [TWP — Translate Web Pages](https://github.com/FilipePS/Traduzir-paginas-web) et [Read Aloud](https://github.com/Read-Aloud/read-aloud).
- Ce dépôt contient **un script de modification** et un **workflow de construction/signature GitHub Actions**. Il ne contient pas encore une extension validée sur Android.
- Le workflow construit toujours deux **XPI non signés** pour les contrôles. Lorsque Mozilla autorise la signature, il produit également deux **XPI signés** destinés aux tests Android. La signature n'est pas une preuve de fonctionnement.
- Le déclenchement par Tasker ou par le bouton central du Samsung viendra **après** validation dans Firefox.

## Construction sans ordinateur

1. Dans GitHub, ouvrir **Actions** → **Construire et signer les extensions (prototype)**.
2. Choisir **Run workflow**, ou consulter la dernière exécution déclenchée par un changement du code.
3. Consulter le statut de l'étape de signature. Si elle est validée, télécharger l'artefact **extensions-experimentales-signees-mozilla** (deux XPI signés).
4. L'artefact **extensions-experimentales-non-signees** reste disponible pour les diagnostics seulement.

Ces archives sont produites à partir de deux révisions amont précises, pour éviter qu'une mise à jour imprévue ne casse le patch.

## Important : installation sur le téléphone

Sur Firefox Android standard, les extensions personnalisées doivent être **signées par Mozilla** avant une installation durable. **N'installer que des XPI issus de l'artefact signé** ; s'il n'existe pas, la signature a échoué et il faut examiner les logs.

Les versions expérimentales possèdent des identifiants distincts et ne sont pas censées remplacer les extensions officielles. Il faut cependant vérifier leur comportement réel sur Firefox Android : coexistence, accès à l'onglet actif, communications entre extensions, lecture audio, et longues pages.

Le workflow utilise les secrets GitHub `AMO_JWT_ISSUER` et `AMO_JWT_SECRET` lors de `web-ext sign --channel unlisted`. **Ne jamais publier de clés secrètes dans ce dépôt.** Si Mozilla refuse l'authentification, revérifier leurs valeurs dans les paramètres GitHub et sur le compte développeur Mozilla. Ne pas transmettre les valeurs dans une conversation.

## Fonctionnement technique visé

1. Le bouton **« Traduire et écouter »** est ajouté au panneau de Read Aloud expérimental.
2. Il demande à TWP expérimental de traduire l'onglet actif en français.
3. Le patch modifie le traitement progressif de TWP pour traduire les paragraphes hors écran et attendre la fin des requêtes et substitutions connues.
4. Read Aloud démarre la lecture du même onglet après l'accusé de réception de TWP.

**Limites non encore résolues :** contenus chargés après coup, certains sites complexes, traductions avec iframes, onglets masqués, fermeture prématurée du panneau, contrôle multimédia depuis les notifications Android.

## Versions sources épinglées

- Read Aloud (branche `firefox`) : `8053a39541dc77e4ff7719348c406bad9792175a`
- TWP (branche `master`) : `50a92116542ab93524594cc210f4bf4e5d86a925`

## Signature TWP indépendante (depuis novembre 2026)

L'ancien workflow soumettait d'abord Read Aloud, puis TWP. Si Mozilla tardait à approuver Read Aloud, TWP **n'était jamais soumis**. Read Aloud a été validé depuis, mais la seconde soumission n'avait pas été lancée.

Le workflow [Soumettre TWP experimental a Mozilla](https://github.com/Dreadaxe/Firefox-traduire-ecouter/actions/workflows/signer-twp.yml) est désormais **indépendant** et ne renvoie pas Read Aloud à Mozilla. Il emploie les mêmes secrets GitHub, vérifie les sources et soumet uniquement TWP à la signature privée.

Si Mozilla approuve avant la limite d'attente de l'outil, un artefact `twp-experimental-signe-mozilla` est publié. Sinon, le journal peut afficher un lien vers la page développeur où récupérer le XPI **une fois approuvé**. Un échec pour délai dépassé ne signifie pas à lui seul un refus de Mozilla. Éviter de relancer plusieurs soumissions sans vérifier le statut de la version existante.

## Validation nécessaire

Avant toute proposition d'installation, vérifier que l'action GitHub réussit, que les extensions démarrent ensemble, puis que les longues pages sont réellement lues **en français et intégralement** sur le Samsung Galaxy S10e. Les tests automatisés de syntaxe ne garantissent pas ce fonctionnement.

Aucun droit d'accès aux comptes ou clés Mozilla n'est demandé dans le code.
