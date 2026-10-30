import ldap3
from ldap3.core.exceptions import LDAPException


class LDAPConnectionError(Exception):
    """Excepción lanzada cuando falla la conexión o la consulta LDAP."""
    pass


class LDAPPoller:
    """Obtiene los miembros actuales de los grupos privilegiados desde Active Directory."""

    def __init__(self, host, port, bind_dn, bind_password, base_dn, groups, use_mock=False, mock_port=8765):
        self.host = host
        self.port = port
        self.bind_dn = bind_dn
        self.bind_password = bind_password
        self.base_dn = base_dn
        self.groups = groups
        self.use_mock = use_mock
        self.mock_port = mock_port
        self._server = None
        self._connection = None

    def _connect(self):
        """Establece la conexión LDAP. En modo mock apunta al servidor local simulado."""
        try:
            if self.use_mock:
                server = ldap3.Server('localhost', port=self.mock_port, get_info=ldap3.NONE)
                # En modo mock se aceptan credenciales ficticias
                connection = ldap3.Connection(
                    server,
                    user=self.bind_dn or 'mock',
                    password=self.bind_password or 'mock',
                    authentication=ldap3.SIMPLE,
                    auto_bind=True,
                )
            else:
                server = ldap3.Server(self.host, port=self.port, get_info=ldap3.NONE)
                connection = ldap3.Connection(
                    server,
                    user=self.bind_dn,
                    password=self.bind_password,
                    authentication=ldap3.SIMPLE,
                    auto_bind=True,
                )
            self._server = server
            self._connection = connection
        except LDAPException as exc:
            raise LDAPConnectionError(f'No se pudo conectar al servidor LDAP: {exc}') from exc

    def _fetch_group_members(self, group_name):
        """Devuelve la lista de dicts con los miembros de un grupo concreto."""
        filtro = f'(&(objectClass=group)(cn={group_name}))'
        try:
            self._connection.search(
                search_base=self.base_dn,
                search_filter=filtro,
                search_scope=ldap3.SUBTREE,
                attributes=['member', 'cn', 'distinguishedName'],
            )
        except LDAPException as exc:
            raise LDAPConnectionError(f'Error al buscar el grupo {group_name}: {exc}') from exc

        miembros = []
        for entrada in self._connection.entries:
            dns_miembros = entrada.member.values if 'member' in entrada else []
            if isinstance(dns_miembros, str):
                dns_miembros = [dns_miembros]
            for dn in dns_miembros:
                try:
                    self._connection.search(
                        search_base=dn,
                        search_filter='(objectClass=user)',
                        search_scope=ldap3.BASE,
                        attributes=['cn', 'sAMAccountName', 'distinguishedName', 'userPrincipalName'],
                    )
                except LDAPException as exc:
                    raise LDAPConnectionError(f'Error al buscar el usuario {dn}: {exc}') from exc

                for usuario in self._connection.entries:
                    miembros.append({
                        'cn': str(usuario.cn) if 'cn' in usuario else '',
                        'sam_account_name': str(usuario.sAMAccountName) if 'sAMAccountName' in usuario else '',
                        'dn': str(usuario.distinguishedName) if 'distinguishedName' in usuario else dn,
                        'upn': str(usuario.userPrincipalName) if 'userPrincipalName' in usuario else '',
                    })
        return miembros

    def fetch_all_groups(self):
        """Recorre todos los grupos configurados y devuelve un dict grupo -> lista de miembros."""
        if self._connection is None:
            self._connect()
        resultado = {}
        try:
            for grupo in self.groups:
                resultado[grupo] = self._fetch_group_members(grupo)
        finally:
            if self._connection is not None:
                self._connection.unbind()
                self._connection = None
        return resultado
