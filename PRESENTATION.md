# Présentation du Projet : Dispatch Manager

## Vision
Dispatch Manager est né de la nécessité de simplifier la communication entre les répartiteurs (dispatchers) et les techniciens de terrain. L'objectif est de réduire le temps de traitement des incidents tout en améliorant la satisfaction client grâce à une visibilité en temps réel.

## Concepts Clés

### 1. Centralisation de l'Information
Fini les fichiers Excel et les emails éparpillés. Chaque ticket centralise l'historique, les notes techniques, et les documents liés à une intervention.

### 2. Ergonomie au Service de la Performance
Le design n'est pas qu'esthétique. L'utilisation du **Glassmorphism** et des transitions fluides réduit la fatigue visuelle des opérateurs qui utilisent l'outil toute la journée. Le **Mode Sombre** est conçu pour les environnements de centre de contrôle (NOC).

### 3. Évolutivité & Robustesse
Grâce à une architecture conteneurisée (Docker), le déploiement est identique du développement à la production. L'utilisation de Redis et WebSockets garantit que tous les opérateurs voient les mêmes données au même moment, sans rafraîchir la page.

## Roadmap & Futur
*   **Intégration de l'IA** : Pour l'auto-assignation des tickets selon la géolocalisation et les compétences des techniciens.
*   **Application Mobile** : Native pour les techniciens (React Native) avec mode hors-ligne.
*   **Module de BI** : Reporting et statistiques avancées pour l'aide à la décision.
