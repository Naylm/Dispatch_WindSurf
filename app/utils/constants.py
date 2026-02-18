
TECHNICIAN_FAQ = [
    {
        "title": "Prise en main quotidienne",
        "items": [
            {
                "question": "Où voir mes incidents affectés ?",
                "answer": (
                    "Depuis l'accueil, la vue technicien affiche uniquement les incidents "
                    "affectés à votre compte. Utilisez la recherche et les filtres pour "
                    "trouver rapidement un dossier."
                ),
            },
            {
                "question": "Comment mettre à jour le statut d'un incident ?",
                "answer": (
                    "Utilisez la liste déroulante de statut dans la carte de l'incident. "
                    "La modification est synchronisée en temps réel pour les admins."
                ),
            },
            {
                "question": "Quelle est la différence entre note dispatch et note technicien ?",
                "answer": (
                    "La note dispatch est réservée au pilotage par les admins. "
                    "La note technicien sert au suivi terrain (diagnostic, actions, résultats)."
                ),
            },
            {
                "question": "Que faire si un incident disparaît de ma vue ?",
                "answer": (
                    "L'incident a probablement été réaffecté, archivé ou mis à jour "
                    "sur un filtre que vous n'affichez pas. Rafraîchissez la page puis "
                    "contactez un admin si besoin."
                ),
            },
        ],
    },
    {
        "title": "Suivi d'intervention",
        "items": [
            {
                "question": "Comment planifier un RDV sur un incident ?",
                "answer": (
                    "Dans la carte de l'incident, renseignez la date de RDV puis validez. "
                    "La date est enregistrée et visible immédiatement."
                ),
            },
            {
                "question": "À quoi servent les cases de relance ?",
                "answer": (
                    "Elles permettent de tracer les relances effectuées sur un ticket "
                    "(client, prestataire, fournisseur) pour garder un historique clair."
                ),
            },
            {
                "question": "Comment prioriser mon travail ?",
                "answer": (
                    "Traitez d'abord les urgences élevées puis les incidents bloqués "
                    "depuis longtemps. En cas de conflit de priorité, alertez l'admin."
                ),
            },
            {
                "question": "Puis-je modifier mes coordonnées ?",
                "answer": (
                    "Oui, dans Mon profil vous pouvez mettre à jour téléphone, email, "
                    "mot de passe et photo de profil."
                ),
            },
        ],
    },
    {
        "title": "Support et documentation",
        "items": [
            {
                "question": "Où trouver les procédures internes ?",
                "answer": (
                    "Consultez la Base de connaissances (Wiki) depuis le menu latéral. "
                    "Vous y trouverez les guides et retours d'expérience."
                ),
            },
            {
                "question": "Comment signaler une info wiki obsolète ?",
                "answer": (
                    "Demandez une mise à jour dans l'article concerné ou contactez un admin "
                    "pour validation et publication."
                ),
            },
            {
                "question": "Que faire si je dois changer mon mot de passe à la connexion ?",
                "answer": (
                    "Suivez l'écran de réinitialisation forcée: saisissez votre mot de passe "
                    "actuel puis un nouveau mot de passe d'au moins 8 caractères."
                ),
            },
        ],
    },
]

ADMIN_FAQ = [
    {
        "title": "Pilotage des incidents",
        "items": [
            {
                "question": "Quels champs sont obligatoires à la création d'un incident ?",
                "answer": (
                    "Numéro, site, sujet, priorité, technicien, date d'affectation et statut "
                    "doivent être renseignés pour assurer un suivi exploitable."
                ),
            },
            {
                "question": "Comment réaffecter proprement un incident ?",
                "answer": (
                    "Modifiez le technicien dans l'incident, ajoutez une note dispatch "
                    "courte sur la raison, puis vérifiez que la notification est bien partie."
                ),
            },
            {
                "question": "Quand archiver un incident ?",
                "answer": (
                    "Archivez uniquement les tickets clôturés et vérifiez que les notes "
                    "de résolution sont complètes pour l'historique."
                ),
            },
            {
                "question": "Comment éviter les incohérences pendant les éditions simultanées ?",
                "answer": (
                    "Évitez les modifications parallèles sur le même ticket, sauvegardez "
                    "rapidement et rafraîchissez la vue en cas de doute."
                ),
            },
        ],
    },
    {
        "title": "Gestion des comptes et sécurité",
        "items": [
            {
                "question": "Comment ajouter un technicien en toute sécurité ?",
                "answer": (
                    "Créez le compte depuis Gestion techniciens, attribuez le rôle adapté "
                    "et forcez la réinitialisation du mot de passe à la première connexion."
                ),
            },
            {
                "question": "Quand utiliser la réinitialisation forcée de mot de passe ?",
                "answer": (
                    "À utiliser après suspicion de compromission, oubli de mot de passe, "
                    "ou changement de poste/mission."
                ),
            },
            {
                "question": "Quelle différence entre désactiver et supprimer un technicien ?",
                "answer": (
                    "Désactiver conserve l'historique et bloque l'accès. "
                    "Supprimer doit rester exceptionnel et précède d'un transfert des incidents."
                ),
            },
            {
                "question": "Qui peut voir la FAQ Admin ?",
                "answer": (
                    "Cette section est visible uniquement pour les comptes admin."
                ),
            },
        ],
    },
    {
        "title": "Paramétrage, exports et supervision",
        "items": [
            {
                "question": "Quand modifier les listes de sujets, priorités, sites et statuts ?",
                "answer": (
                    "Modifiez ces référentiels uniquement lors d'un besoin métier validé, "
                    "puis informez l'équipe des changements."
                ),
            },
            {
                "question": "Quels exports utiliser selon le besoin ?",
                "answer": (
                    "Excel pour l'analyse détaillée, PDF pour le partage formel, "
                    "CSV pour intégration externe ou BI."
                ),
            },
            {
                "question": "Comment suivre la charge globale de l'activité ?",
                "answer": (
                    "Utilisez le dashboard statistiques pour suivre KPI, répartition par "
                    "technicien, et évolution des statuts."
                ),
            },
            {
                "question": "Comment gérer une migration de base en limitant les risques ?",
                "answer": (
                    "Utilisez d'abord l'aperçu d'import pour contrôler les données, puis "
                    "exécutez la migration sur un jeu validé avec sauvegarde préalable."
                ),
            },
        ],
    },
]
