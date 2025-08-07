- name: Ajouter grant et login_profile selon le rôle (avec cas spécial SERVICE/MONITORING)
  set_fact:
    l_cyberark:
      Account: >-
        {{ l_cyberark.Account |
          map('combine', {
            'grant': (
              item.role == 'SERVICE' and 'MONITORING' in item.user_name
              | ternary(monitoring.grant, roles_matrix[item.role].grant)
            ),
            'login_profile': (
              item.role == 'SERVICE' and 'MONITORING' in item.user_name
              | ternary(monitoring.login_profile, roles_matrix[item.role].login_profile)
            )
          }) |
          list }}
  vars:
    item: "{{ item }}"
  loop: "{{ l_cyberark.Account }}"
