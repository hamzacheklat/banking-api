- name: Passer tout le contenu vaulté
  my_namespace.my_module:
    vault_data: "{{ secrets }}"


- name: Exemple d'utilisation du module custom avec vault
  hosts: localhost
  gather_facts: false

  tasks:
    - name: Charger les variables vaultées
      ansible.builtin.include_vars:
        file: .vars/cyberark.yml
        name: secrets  # les variables deviennent accessibles via "secrets"

    - name: Appeler mon module Python avec toutes les données vaultées
      my_namespace.my_module:
        vault_data: "{{ secrets }}"
