- name: Ajouter grant et login_profile selon le rôle (cas SERVICE + MONITORING user_name)
  set_fact:
    l_cyberark:
      Account: >-
        {{ l_cyberark.Account |
          map('combine', {
            'grant': (
              (item.role == 'SERVICE' and 'MONITORING' in item.user_name)
              | ternary(roles_matrix['MONITORING'].grant, roles_matrix[item.role].grant)
            ),
            'login_profile': (
              (item.role == 'SERVICE' and 'MONITORING' in item.user_name)
              | ternary(roles_matrix['MONITORING'].login_profile, roles_matrix[item.role].login_profile)
            )
          }) |
          list }}
  vars:
    item: "{{ item }}"
  loop: "{{ l_cyberark.Account }}"
