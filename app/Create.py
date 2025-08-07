Oui, j’ai bien vu sur ta photo que la sortie de la tâche get_passwords_or_create_accounts (via le module cyberack_apigee) est structurée comme ceci :


---

✅ Sortie visible (get_passwords_or_create_accounts)

{
  "changed": false,
  "invocation": { ... },
  "output": [
    {
      "account": {
        "account_type": "ORACLE-LOCAL-SVC",
        "address": "test.apigee.net.intra",
        "comment": "RECONCILE for DBAORACLE/test.apigee.net.intra/410uk207",
        "database": "410uk207",
        "env": "DEV",
        "env_letter": "D",
        "password": "********",
        "port": "4532",
        "role": "RECONCILE",
        "safe_name": "DBAORACLE",
        "user_name": "SVC2ACYBERA8RKECOD",
        "zone": "EMEA"
      },
      "changed": false,
      "retries": 1
    },
    {
      "account": {
        "account_type": "ORACLE-LOCAL-GEN",
        "address": "test.apigee.net.intra",
        "comment": "APS read",
        "database": "410uk207",
        "env": "DEV",
        "env_letter": "D",
        "password": "********",
        "port": "4532",
        "role": "READ",
        "safe_name": "IV2ADATABASE-DEV",
        "user_name": "GEN2ANOREADDATABASED",
        "zone": "EMEA"
      },
      "changed": false,
      "retries": 1
    }
  ]
}


---

🔍 Important :

Tu dois donc extraire la liste des objets account situés dans get_passwords_or_create_result.output[*].account.


---

✅ Tâche 1 : Extraction des comptes

- name: Extraire les comptes CyberArk de la sortie
  set_fact:
    l_cyberark:
      Account: "{{ get_password_or_create_result.output | map(attribute='account') | list }}"


---

✅ Tâche 2 : Ajouter grant et login_profile dynamiquement selon role

- name: Ajouter grant et login_profile selon le rôle de chaque compte
  set_fact:
    l_cyberark:
      Account: >-
        {{ l_cyberark.Account |
          map('combine', {
            'grant': (
              {
                'RECONCILE': ['CONNECT'],
                'READ': ['CONNECT', 'SELECT'],
                'WRITE': ['CONNECT', 'RESOURCE']
              }[item.role] if item.role in ['RECONCILE', 'READ', 'WRITE'] else ['CONNECT']
            ),
            'login_profile': (
              {
                'RECONCILE': ['DEFAULT'],
                'READ': ['READ_ONLY'],
                'WRITE': ['FULL']
              }[item.role] if item.role in ['RECONCILE', 'READ', 'WRITE'] else ['DEFAULT']
            )
          }) |
          list }}
  vars:
    item: "{{ item }}"
  loop: "{{ l_cyberark.Account }}"


---

✅ Résumé :

Étape	Tâche	Résultat

1️⃣	Extraire les comptes	Met en forme la liste l_cyberark.Account
2️⃣	Ajouter grant + login_profile	Ajoute dynamiquement les droits selon le rôle



---

Tu veux que je t’écrive une version qui ne surcharge que si grant ou login_profile ne sont pas déjà présents ?

