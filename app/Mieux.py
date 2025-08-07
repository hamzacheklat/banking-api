Très bon point 💡!

Si tu connais tous les rôles possibles à l'avance et que tu es sûr qu’il n’y aura jamais de rôle inconnu, alors tu peux simplifier le code en supprimant les if/else.


---

✅ Version optimisée sans if / else (plus propre et plus rapide)

🎯 Tâche 1 – Extraction des comptes :

- name: Extraire les comptes CyberArk de la sortie
  set_fact:
    l_cyberark:
      Account: "{{ get_password_or_create_result.output | map(attribute='account') | list }}"


---

🧠 Définition des règles (dans un dictionnaire)

Tu peux définir une fois les rôles et leurs paramètres :

- name: Définir les droits par rôle
  set_fact:
    roles_matrix:
      RECONCILE:
        grant: ['CONNECT']
        login_profile: ['DEFAULT']
      READ:
        grant: ['CONNECT', 'SELECT']
        login_profile: ['READ_ONLY']
      WRITE:
        grant: ['CONNECT', 'RESOURCE']
        login_profile: ['FULL']


---

✅ Tâche 2 – Ajouter grant et login_profile directement à partir de roles_matrix :

- name: Ajouter grant et login_profile selon le rôle
  set_fact:
    l_cyberark:
      Account: >-
        {{ l_cyberark.Account |
          map('combine', {
            'grant': roles_matrix[item.role].grant,
            'login_profile': roles_matrix[item.role].login_profile
          }) |
          list }}
  vars:
    item: "{{ item }}"
  loop: "{{ l_cyberark.Account }}"


---

✅ Ce que tu gagnes :

Plus propre (pas de logique inutile)

Plus rapide à lire et maintenir

Si un jour tu veux changer les droits, tu modifies juste roles_matrix



---

Souhaite-tu que je te mette tout ça dans un seul bloc complet prêt à copier/coller dans ton playbook ?

