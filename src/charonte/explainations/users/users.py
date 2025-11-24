class UsersExplain():
    def explain_users(self, detail_level='basic'):
        return {
            'concept': 'User Management',
            'what': 'Gerencia usuários do sistema declarativamente',
            'why': 'Evita comandos useradd/userdel manuais e repetitivos',
            'how': 'Compara estado atual vs desejado, aplica diferenças',
            'commands': ['useradd', 'usermod', 'userdel'],
            'files': ['/etc/passwd', '/etc/shadow', '/etc/group'],
            'examples': [
                {
                    'yaml': """users:
  - name: "dex"
    shell: "zsh"
    sudo: True""",
                }
            ],
            'equivalent': [ "useradd -m -s /bin/zsh dex && usermod -aG wheel dex", ],
            'learn_more': ['man useradd', 'man passwd', 'man sudoers']
        }

    def explain_sudo(self, detail_level='basic'):
        """Explica especificamente o campo sudo"""
        return {
            'concept': 'Sudo Access',
            'what': 'Concede privilégios administrativos ao usuário',
            'technical': 'Cria arquivo em /etc/sudoers.d/99-charonte-{user}',
            'security': '⚠️  Acesso root completo - use com cuidado',
            'equivalent': "echo 'dex ALL=(ALL:ALL) ALL' > /etc/sudoers.d/99-charonte-dex",
            'validation': 'visudo -c -f /etc/sudoers.d/99-charonte-dex'
        }
